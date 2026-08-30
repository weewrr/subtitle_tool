import logging
import threading

from backend.services.ffmpeg_task_service import FFmpegTaskService

logger = logging.getLogger(__name__)


class TtsVideoService(FFmpegTaskService):
    """将原视频静音，合并 TTS 配音音频后导出为新视频。"""

    def __init__(self):
        super().__init__('tts-video')

    def generate(self, video_path, audio_path, output_path):
        """提交配音合成任务,立即返回 {task_id, status}。"""
        task_id = self._create_job()
        threading.Thread(
            target=self._task_thread,
            args=(task_id, video_path, audio_path, output_path),
            daemon=True
        ).start()
        return {'task_id': task_id, 'status': 'started'}

    def _task_thread(self, task_id, video_path, audio_path, output_path):
        try:
            # 视频时长作为进度基准;配音音频可能比视频短或长
            duration = self._get_media_duration(video_path)

            # -i video -i audio -map 0:v:0 -map 1:a:0 -c:v copy -c:a aac -b:a 192k -shortest
            # 视频流直接拷贝;音频使用配音音轨;-shortest 以较短流为准
            cmd = [
                self.get_ffmpeg_path(),
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

            self._execute(task_id, cmd, duration, output_path)
        except Exception as e:
            logger.exception('配音视频任务 %s 失败', task_id)
            self._update(task_id, status='error', error=str(e))


tts_video_service = TtsVideoService()
