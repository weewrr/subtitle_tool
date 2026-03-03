import os
import re
import subprocess
import threading
import shutil
import uuid
from pathlib import Path

from backend.utils.temp_dir import get_temp_dir


class HardSubtitleService:
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

    def _rgb_to_ass_color_with_opacity(self, color_value, opacity):
        r, g, b, _ = self._parse_color(color_value)
        alpha = max(0, min(255, int(round(opacity * 255))))
        return self._to_ass_color(r, g, b, alpha)
    
    def _srt_time_to_ass(self, srt_time):
        parts = srt_time.replace(',', '.').split(':')
        hours = int(parts[0])
        minutes = int(parts[1])
        seconds = float(parts[2])
        return f'{hours}:{minutes:02d}:{seconds:05.2f}'
    
    def generate_hard_subtitle(self, video_path, subtitle_data, output_path, config, callback=None):
        def _run():
            try:
                self.status = 'processing'
                self.progress = 0
                self._abort = False
                self.error = None
                
                ffmpeg_path = self.get_ffmpeg_path()
                print(f"[DEBUG] FFmpeg path: {ffmpeg_path}")
                print(f"[DEBUG] Video path: {video_path}")
                print(f"[DEBUG] Output path: {output_path}")
                print(f"[DEBUG] Subtitle data count: {len(subtitle_data)}")
                
                with open(os.path.join(get_temp_dir(), f"{uuid.uuid4()}.ass"), 'w', encoding='utf-8') as ass_file:
                    ass_content = self.generate_ass_file(subtitle_data, config.get('style', {}), ass_file.name)
                    ass_file.write(ass_content)
                    ass_path = ass_file.name
                
                print(f"[DEBUG] ASS file path: {ass_path}")
                print(f"[DEBUG] ASS content preview: {ass_content[:500]}...")
                
                video_encoding = config.get('video_encoding', 'libx264')
                preset = config.get('preset', 'medium')
                crf = str(config.get('crf', 23))
                audio_encoding = config.get('audio_encoding', 'copy')
                
                ass_path_escaped = ass_path.replace('\\', '/').replace(':', '\\:')
                
                cmd = [
                    ffmpeg_path,
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
                
                print(f"[DEBUG] FFmpeg command: {' '.join(cmd)}")
                
                self._process = subprocess.Popen(
                    cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    universal_newlines=True
                )
                
                duration = self._get_video_duration(video_path)
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
                        except:
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
                
                os.unlink(ass_path)
                
            except Exception as e:
                self.status = 'error'
                self.error = str(e)
                if callback:
                    callback({'status': 'error', 'error': str(e)})
        
        thread = threading.Thread(target=_run)
        thread.start()
        return {'status': 'started'}
    
    def _get_video_duration(self, video_path):
        try:
            ffprobe = self.get_ffmpeg_path().replace('ffmpeg', 'ffprobe')
            result = subprocess.run(
                [ffprobe, '-v', 'error', '-show_entries', 'format=duration', '-of', 'default=noprint_wrappers=1:nokey=1', video_path],
                capture_output=True,
                text=True
            )
            return float(result.stdout.strip())
        except:
            return 0
    
    def _parse_time(self, time_str):
        parts = time_str.split(':')
        hours = int(parts[0])
        minutes = int(parts[1])
        seconds = float(parts[2])
        return hours * 3600 + minutes * 60 + seconds
    
    def abort(self):
        self._abort = True
    
    def get_status(self):
        return {
            'status': self.status,
            'progress': self.progress,
            'error': self.error,
            'output_path': self.output_path
        }


hard_subtitle_service = HardSubtitleService()
