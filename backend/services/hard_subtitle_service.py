import logging
import os
import re
import threading
import uuid

from backend.services.ffmpeg_task_service import FFmpegTaskService
from backend.utils.temp_dir import get_temp_dir

logger = logging.getLogger(__name__)


class HardSubtitleService(FFmpegTaskService):
    def __init__(self):
        super().__init__('hard-subtitle')

    def generate_ass_file(self, subtitle_content, style_config, output_path):
        ass_content = """[Script Info]
Title: Subtitle
ScriptType: v4.00+
PlayResX: {width}
PlayResY: {height}
WrapStyle: 0

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,{font_name},{font_size},{primary_color},{secondary_color},{outline_color},{back_color},{bold},0,0,0,100,100,0,0,{border_style},{outline},{shadow},2,10,10,{margin_bottom},1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
{events}
"""

        width = style_config.get('width', 1920)
        height = style_config.get('height', 1080)
        font_name = style_config.get('font_name', 'Arial')
        font_size = style_config.get('font_size', 48)
        bold = -1 if style_config.get('bold', False) else 0
        outline_value = style_config.get('outline', 2)
        margin_bottom = style_config.get('margin_bottom', 30)
        use_outline_color = style_config.get('use_outline_color', False)

        outline = outline_value if use_outline_color else 0
        shadow = 0
        border_style = 1

        primary_color = self._rgb_to_ass_color(style_config.get('text_color', '#FFFFFF'))
        outline_color = self._rgb_to_ass_color(style_config.get('outline_color', '#000000'))
        back_color = '&H00000000'

        events = []
        for line in subtitle_content:
            start = self._srt_time_to_ass(line.get('start', '00:00:00,000'))
            end = self._srt_time_to_ass(line.get('end', '00:00:00,000'))
            text = line.get('text', '').replace('\n', '\\N')
            events.append(f"Dialogue: 0,{start},{end},Default,,0,0,0,,{text}")

        return ass_content.format(
            width=width,
            height=height,
            font_name=font_name,
            font_size=font_size,
            primary_color=primary_color,
            secondary_color=primary_color,
            outline_color=outline_color,
            back_color=back_color,
            bold=bold,
            border_style=border_style,
            outline=outline,
            shadow=shadow,
            margin_bottom=margin_bottom,
            events='\n'.join(events)
        )

    def _to_ass_color(self, r, g, b, alpha=255):
        ass_alpha = 255 - max(0, min(255, int(alpha)))
        return f'&H{ass_alpha:02X}{b:02X}{g:02X}{r:02X}'

    def _parse_color(self, color_value):
        if not color_value:
            return 255, 255, 255, 255

        color_value = str(color_value).strip()

        if color_value.startswith('#'):
            hex_color = color_value[1:]
            if len(hex_color) == 3:
                r = int(hex_color[0] * 2, 16)
                g = int(hex_color[1] * 2, 16)
                b = int(hex_color[2] * 2, 16)
                return r, g, b, 255
            if len(hex_color) == 4:
                r = int(hex_color[0] * 2, 16)
                g = int(hex_color[1] * 2, 16)
                b = int(hex_color[2] * 2, 16)
                a = int(hex_color[3] * 2, 16)
                return r, g, b, a
            if len(hex_color) == 6:
                r = int(hex_color[0:2], 16)
                g = int(hex_color[2:4], 16)
                b = int(hex_color[4:6], 16)
                return r, g, b, 255
            if len(hex_color) == 8:
                r = int(hex_color[0:2], 16)
                g = int(hex_color[2:4], 16)
                b = int(hex_color[4:6], 16)
                a = int(hex_color[6:8], 16)
                return r, g, b, a

        rgb_match = re.match(r'^rgba?\((.+)\)$', color_value, re.IGNORECASE)
        if rgb_match:
            parts = [p.strip() for p in rgb_match.group(1).split(',')]
            if len(parts) >= 3:
                r = max(0, min(255, int(float(parts[0]))))
                g = max(0, min(255, int(float(parts[1]))))
                b = max(0, min(255, int(float(parts[2]))))
                a = 255
                if len(parts) >= 4:
                    alpha = float(parts[3])
                    a = max(0, min(255, int(round(alpha * 255 if alpha <= 1 else alpha))))
                return r, g, b, a

        return 255, 255, 255, 255

    def _rgb_to_ass_color(self, color_value):
        r, g, b, a = self._parse_color(color_value)
        return self._to_ass_color(r, g, b, a)

    def _srt_time_to_ass(self, srt_time):
        parts = srt_time.replace(',', '.').split(':')
        hours = int(parts[0])
        minutes = int(parts[1])
        seconds = float(parts[2])
        return f'{hours}:{minutes:02d}:{seconds:05.2f}'

    def generate_hard_subtitle(self, video_path, subtitle_data, output_path, config):
        """提交硬字幕烧录任务,立即返回 {task_id, status}。"""
        task_id = self._create_job()
        threading.Thread(
            target=self._task_thread,
            args=(task_id, video_path, subtitle_data, output_path, config),
            daemon=True
        ).start()
        return {'task_id': task_id, 'status': 'started'}

    def _task_thread(self, task_id, video_path, subtitle_data, output_path, config):
        ass_path = None
        try:
            if not subtitle_data:
                self._update(task_id, status='error', error='字幕内容为空')
                return

            ass_path = os.path.join(get_temp_dir(), f"{uuid.uuid4()}.ass")
            with open(ass_path, 'w', encoding='utf-8') as ass_file:
                ass_file.write(self.generate_ass_file(subtitle_data, config.get('style', {}), ass_path))

            video_encoding = config.get('video_encoding', 'libx264')
            preset = config.get('preset', 'medium')
            crf = str(config.get('crf', 23))
            audio_encoding = config.get('audio_encoding', 'copy')

            # Windows 盘符冒号需要转义,路径分隔符统一为 /
            ass_path_escaped = ass_path.replace('\\', '/').replace(':', '\\:')

            cmd = [
                self.get_ffmpeg_path(),
                '-y',
                '-i', video_path,
                '-vf', f"subtitles='{ass_path_escaped}'",
                '-c:v', video_encoding,
                '-preset', preset,
                '-crf', crf,
                '-c:a', audio_encoding,
                '-movflags', '+faststart',
                output_path
            ]

            duration = self._get_media_duration(video_path)
            self._execute(task_id, cmd, duration, output_path)
        except Exception as e:
            logger.exception('硬字幕任务 %s 失败', task_id)
            self._update(task_id, status='error', error=str(e))
        finally:
            if ass_path:
                try:
                    os.unlink(ass_path)
                except OSError:
                    pass


hard_subtitle_service = HardSubtitleService()
