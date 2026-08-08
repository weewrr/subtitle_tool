import os
import shutil
import subprocess
import threading


class TtsVideoService:
    """将原视频静音，合并 TTS 配音音频后导出为新视频。"""

    def __init__(self):
        self.progress = 0
        self.status = 'idle'
        self.error = None
        self.output_path = None
        self._process = None
        self._abort = False

    def get_ffmpeg_path(self):
        ffmpeg = shutil.which('ffmpeg')
        if ffmpeg:
            return ffmpeg
        common_paths = [
            r'C:\ffmpeg\bin\ffmpeg.exe',
            r'C:\Program Files\ffmpeg\bin\ffmpeg.exe',
            os.path.expanduser('~/.local/bin/ffmpeg'),
            '/usr/bin/ffmpeg',
            '/usr/local/bin/ffmpeg',
        ]
        for path in common_paths:
            if os.path.exists(path):
                return path
        return 'ffmpeg'

    def _get_media_duration(self, file_path):
        try:
            ffprobe = self.get_ffmpeg_path().replace('ffmpeg', 'ffprobe')
            result = subprocess.run(
                [ffprobe, '-v', 'error', '-show_entries', 'format=duration',
                 '-of', 'default=noprint_wrappers=1:nokey=1', file_path],
                capture_output=True, text=True
            )
            return float(result.stdout.strip())
        except Exception:
            return 0

    @staticmethod
    def _parse_time(time_str):
        parts = time_str.split(':')
        hours = int(parts[0])
        minutes = int(parts[1])
        seconds = float(parts[2])
        return hours * 3600 + minutes * 60 + seconds

    def generate(self, video_path, audio_path, output_path, callback=None):
        def _run():
            try:
                self.status = 'processing'
                self.progress = 0
                self._abort = False
                self.error = None

                ffmpeg_path = self.get_ffmpeg_path()
                # 视频时长作为进度基准；配音音频可能比视频短或长
                duration = self._get_media_duration(video_path)

                # -i video -i audio -map 0:v:0 -map 1:a:0 -c:v copy -c:a aac -b:a 192k -shortest
                # 视频流直接拷贝；音频使用配音音轨；-shortest 以较短流为准
                cmd = [
                    ffmpeg_path,
                    '-y',
                    '-i', video_path,
                    '-i', audio_path,
                    '-map', '0:v:0',
                    '-map', '1:a:0',
                    '-c:v', 'copy',
                    '-c:a', 'aac',
                    '-b:a', '192k',
                    '-shortest',
                    '-movflags', '+faststart',
                    output_path
                ]

                self._process = subprocess.Popen(
                    cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    universal_newlines=True
                )

                stderr_output = []
                while True:
                    if self._abort:
                        self._process.kill()
                        self.status = 'aborted'
                        if callback:
                            callback({'status': 'aborted'})
                        return

                    line = self._process.stderr.readline()
                    if not line and self._process.poll() is not None:
                        break

                    stderr_output.append(line)

                    if 'time=' in line and duration > 0:
                        try:
                            time_str = line.split('time=')[1].split()[0]
                            current_time = self._parse_time(time_str)
                            self.progress = min(100, int(current_time / duration * 100))
                            if callback:
                                callback({'status': 'processing', 'progress': self.progress})
                        except Exception:
                            pass

                if self._process.returncode == 0:
                    self.status = 'completed'
                    self.output_path = output_path
                    self.progress = 100
                    if callback:
                        callback({'status': 'completed', 'output_path': output_path})
                else:
                    self.status = 'error'
                    self.error = 'FFmpeg 处理失败: ' + ''.join(stderr_output[-20:])
                    if callback:
                        callback({'status': 'error', 'error': self.error})

            except Exception as e:
                self.status = 'error'
                self.error = str(e)
                if callback:
                    callback({'status': 'error', 'error': str(e)})

        thread = threading.Thread(target=_run)
        thread.start()
        return {'status': 'started'}

    def abort(self):
        self._abort = True

    def get_status(self):
        return {
            'status': self.status,
            'progress': self.progress,
            'error': self.error,
            'output_path': self.output_path
        }


tts_video_service = TtsVideoService()
