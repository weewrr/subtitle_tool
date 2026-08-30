"""FFmpeg 后台任务基类

为硬字幕烧录、TTS 视频合成等 FFmpeg 长任务提供统一的多任务管理:
- 每次生成为独立 task_id,并发任务互不覆盖
- 基于 stderr time= 的进度解析
- 取消:置位 + kill 进程
- 终态任务保留 1 小时供轮询/下载,过期自动清理
"""
import logging
import os
import shutil
import subprocess
import threading
import time
import uuid

logger = logging.getLogger(__name__)

_TERMINAL_STATES = {'completed', 'error', 'aborted'}
_JOB_TTL_SECONDS = 3600


class FFmpegTaskService:
    def __init__(self, service_name):
        self.service_name = service_name
        self._jobs = {}
        self._processes = {}
        self._lock = threading.Lock()

    # ---------- 可执行文件定位 ----------

    @staticmethod
    def _find_tool(name):
        """先查 PATH,再查常见安装位置,最后原样返回交给系统解析。"""
        found = shutil.which(name)
        if found:
            return found
        candidates = [
            rf'C:\{name}\bin\{name}.exe',
            rf'C:\Program Files\{name}\bin\{name}.exe',
            os.path.expanduser(f'~/.local/bin/{name}'),
            f'/usr/bin/{name}',
            f'/usr/local/bin/{name}',
        ]
        for path in candidates:
            if os.path.exists(path):
                return path
        return name

    def get_ffmpeg_path(self):
        return self._find_tool('ffmpeg')

    def _get_ffprobe_path(self):
        return self._find_tool('ffprobe')

    def _get_media_duration(self, file_path):
        """ffprobe 取媒体时长(秒),失败返回 0(进度条退化为不确定)。"""
        try:
            result = subprocess.run(
                [self._get_ffprobe_path(), '-v', 'error', '-show_entries', 'format=duration',
                 '-of', 'default=noprint_wrappers=1:nokey=1', file_path],
                capture_output=True, text=True,
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
            )
            return float(result.stdout.strip())
        except (OSError, ValueError):
            return 0

    @staticmethod
    def _parse_time(time_str):
        parts = time_str.split(':')
        hours = int(parts[0])
        minutes = int(parts[1])
        seconds = float(parts[2])
        return hours * 3600 + minutes * 60 + seconds

    # ---------- 任务管理 ----------

    def _create_job(self):
        task_id = str(uuid.uuid4())
        job = {
            'task_id': task_id,
            'status': 'processing',
            'progress': 0,
            'error': None,
            'output_path': None,
            'cancel_requested': False,
            'created_at': time.time(),
        }
        with self._lock:
            self._cleanup_expired_locked()
            self._jobs[task_id] = job
        return task_id

    def _cleanup_expired_locked(self):
        """清理过期终态任务(调用方需持有锁)。"""
        now = time.time()
        expired = [tid for tid, job in self._jobs.items()
                   if job['status'] in _TERMINAL_STATES
                   and now - job['created_at'] > _JOB_TTL_SECONDS]
        for tid in expired:
            self._jobs.pop(tid, None)
            self._processes.pop(tid, None)

    def _update(self, task_id, **changes):
        with self._lock:
            job = self._jobs.get(task_id)
            if job is not None:
                job.update(changes)

    def _is_cancelled(self, task_id):
        with self._lock:
            job = self._jobs.get(task_id)
            return bool(job and job.get('cancel_requested'))

    def _latest_job_locked(self, predicate=None):
        """按创建时间取最近一个任务;可传谓词过滤(如仅活跃任务)。"""
        candidates = [job for job in self._jobs.values()
                      if predicate is None or predicate(job)]
        if not candidates:
            return None
        return max(candidates, key=lambda job: job['created_at'])

    def get_status(self, task_id=None):
        """查询任务状态;不传 task_id 时返回最近一个任务(兼容旧前端轮询)。"""
        with self._lock:
            job = self._jobs.get(task_id) if task_id else self._latest_job_locked()
            if job is None:
                return None
            return {
                'task_id': job['task_id'],
                'status': job['status'],
                'progress': job['progress'],
                'error': job['error'],
                'output_path': job['output_path'],
            }

    def get_completed_output(self, task_id=None):
        """取已完成任务的产物路径;不传 task_id 时取最近完成的任务。"""
        with self._lock:
            if task_id:
                job = self._jobs.get(task_id)
                if job and job['status'] == 'completed':
                    return job.get('output_path')
                return None
            job = self._latest_job_locked(lambda j: j['status'] == 'completed')
            return job.get('output_path') if job else None

    def cancel(self, task_id=None):
        """取消任务;不传 task_id 时取消最近一个活跃任务。"""
        with self._lock:
            job = self._jobs.get(task_id) if task_id else self._latest_job_locked(
                lambda j: j['status'] not in _TERMINAL_STATES)
            if job is None:
                return False
            job['cancel_requested'] = True
            job['status'] = 'cancelling'
            process = self._processes.get(job['task_id'])
        if process is not None and process.poll() is None:
            try:
                process.kill()
            except OSError:
                pass
        return True

    # ---------- FFmpeg 执行 ----------

    def _execute(self, task_id, cmd, duration, output_path):
        """执行 FFmpeg 并跟踪进度,内部完成终态更新。

        返回 True 表示成功;False 表示失败/取消(状态已写入任务)。
        """
        if self._is_cancelled(task_id):
            self._update(task_id, status='aborted')
            return False

        logger.info('[%s] task %s ffmpeg: %s', self.service_name, task_id, ' '.join(cmd))
        try:
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.PIPE,
                universal_newlines=True,
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
            )
        except OSError as e:
            self._update(task_id, status='error', error=f'无法启动 FFmpeg: {e}')
            return False

        with self._lock:
            self._processes[task_id] = process

        stderr_tail = []
        try:
            while True:
                line = process.stderr.readline()
                if not line:
                    if process.poll() is not None:
                        break
                    continue
                stderr_tail.append(line.rstrip('\n'))
                del stderr_tail[:-40]  # 只保留末尾,避免长任务内存膨胀
                if 'time=' in line and duration > 0:
                    try:
                        time_str = line.split('time=')[1].split()[0]
                        current = self._parse_time(time_str)
                        self._update(task_id, progress=min(99, int(current / duration * 100)))
                    except (ValueError, IndexError):
                        pass
            process.wait()
        finally:
            with self._lock:
                self._processes.pop(task_id, None)

        if process.returncode == 0:
            self._update(task_id, status='completed', progress=100, output_path=output_path)
            return True

        if self._is_cancelled(task_id):
            self._update(task_id, status='aborted')
        else:
            self._update(task_id, status='error',
                         error='FFmpeg 处理失败: ' + '\n'.join(stderr_tail[-20:]))
        return False
