import os
import sys
import subprocess
import threading
import time
from backend.utils.time_utils import format_time_srt
from backend.utils.file_utils import is_audio_file
from backend.config.settings import Config
from backend.utils.temp_dir import get_transcription_temp_dir


class TranscriptionService:
    def __init__(self):
        self.transcribe_status = {
            'transcribing': False,
            'progress': 0,
            'status': 'idle',
            'error': None,
            'result': None
        }
        self._stop_progress = False

    def _ensure_whisper_installed(self):
        """确保 Whisper 已安装"""
        try:
            import whisper
        except ImportError:
            subprocess.check_call([sys.executable, '-m', 'pip', 'install', 'openai-whisper', '-q'])
            import whisper
        return whisper

    def _ensure_ffmpeg_installed(self):
        """确保 ffmpeg-python 已安装"""
        try:
            import ffmpeg
        except ImportError:
            subprocess.check_call([sys.executable, '-m', 'pip', 'install', 'ffmpeg-python', '-q'])
            import ffmpeg
        return ffmpeg

    def _extract_audio(self, video_path, audio_path):
        """从视频提取音频（优化参数，确保和 Whisper 兼容）"""
        import subprocess
        
        if not os.path.exists(video_path):
            raise FileNotFoundError(f"视频文件不存在：{video_path}")
        
        ext = os.path.splitext(video_path)[1].lower()
        if ext not in Config.SUPPORTED_VIDEO_FORMATS and ext not in Config.SUPPORTED_AUDIO_FORMATS:
            raise ValueError(f"不支持的格式：{ext}")
        
        output_dir = os.path.dirname(audio_path)
        if output_dir:
            os.makedirs(output_dir, exist_ok=True)
        
        cmd = [
            'ffmpeg',
            '-y',
            '-i', video_path,
            '-vn',
            '-acodec', 'pcm_s16le',
            '-ac', '1',
            '-ar', '16000',
            audio_path
        ]
        
        try:
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            if result.returncode != 0:
                error_msg = result.stderr if result.stderr else "未知错误"
                raise RuntimeError(f"音频提取失败：{error_msg}")
            
            if not os.path.exists(audio_path):
                raise RuntimeError("音频文件未生成")
                
        except FileNotFoundError:
            raise RuntimeError("FFmpeg 未安装或不在 PATH 中")
        except Exception as e:
            raise RuntimeError(f"音频提取异常：{str(e)}")

    def transcribe_file(self, file_path, model_name='base', language=None, engine='openai', use_gpu=True):
        """转录文件（同步）"""
        if engine == 'openai':
            return self._transcribe_with_openai(file_path, model_name, language, use_gpu)
        elif engine == 'whisper-cpp':
            return self._transcribe_with_whisper_cpp(file_path, model_name, language)
        elif engine == 'whisper-ctranslate2':
            return self._transcribe_with_whisper_ctranslate2(file_path, model_name, language, use_gpu)
        elif engine == 'vosk':
            from backend.services.vosk_service import VoskService
            vosk_service = VoskService()
            language_map = {
                'en': 'en', 'zh': 'cn', 'fr': 'fr', 'es': 'es', 'de': 'de',
                'pt': 'pt', 'it': 'it', 'nl': 'nl', 'sv': 'sv', 'ru': 'ru',
                'fa': 'fa', 'tr': 'tr', 'el': 'el', 'ar': 'ar', 'uk': 'uk',
                'uz': 'uz', 'ph': 'ph', 'kz': 'kz', 'jp': 'jp', 'ca': 'ca',
                'hi': 'hi', 'cz': 'cz', 'pl': 'pl', 'br': 'br'
            }
            model_code = language_map.get(language.lower() if language else 'zh', 'cn')
            self.transcribe_status['status'] = 'transcribing'
            return vosk_service.transcribe_with_vosk(file_path, model_code, self.transcribe_status)
        else:
            return self._transcribe_with_openai(file_path, model_name, language, use_gpu)

    def _transcribe_with_openai(self, file_path, model_name='base', language=None, use_gpu=True):
        """使用 OpenAI Whisper 转录"""
        import torch
        whisper = self._ensure_whisper_installed()
        
        device = "cuda" if use_gpu and torch.cuda.is_available() else "cpu"
        model = whisper.load_model(model_name, device=device, download_root=Config.WHISPER_CACHE_DIR)
        
        if is_audio_file(file_path):
            audio_path = file_path
            temp_audio_path = None
        else:
            import uuid
            temp_audio_path = os.path.join(get_transcription_temp_dir(), f"{uuid.uuid4()}.wav")
            self._extract_audio(file_path, temp_audio_path)
            audio_path = temp_audio_path
        
        try:
            self.transcribe_status['status'] = 'transcribing'
            
            lang_code = None
            if language and language.lower() != 'auto-detect':
                lang_map = {
                    'english': 'en', 'chinese': 'zh', 'japanese': 'ja', 'korean': 'ko',
                    'en': 'en', 'zh': 'zh', 'ja': 'ja', 'ko': 'ko'
                }
                lang_code = lang_map.get(language.lower(), language.lower())
            
            result = model.transcribe(
                audio_path,
                language=lang_code,
                verbose=False,
                word_timestamps=True,
                fp16=(device == "cuda"),
                temperature=0.0,
                best_of=5,
                beam_size=5,
                patience=1.0
            )
            
            segments = self._improve_timestamps(result.get('segments', []))
            result['segments'] = segments
            
            return self._generate_srt(result)
        finally:
            if temp_audio_path and os.path.exists(temp_audio_path):
                os.unlink(temp_audio_path)

    def _transcribe_with_whisper_cpp(self, file_path, model_name='ggml-base', language=None):
        """使用 Whisper.cpp 转录"""
        from backend.services.whisper_cpp_service import WhisperCppService
        whisper_cpp_service = WhisperCppService()
        
        if is_audio_file(file_path):
            audio_path = file_path
            temp_audio_path = None
        else:
            import uuid
            temp_audio_path = os.path.join(get_transcription_temp_dir(), f"{uuid.uuid4()}.wav")
            self._extract_audio(file_path, temp_audio_path)
            audio_path = temp_audio_path
        
        try:
            self.transcribe_status['status'] = 'transcribing'
            
            lang_code = None
            if language and language.lower() != 'auto-detect':
                lang_map = {
                    'english': 'en', 'chinese': 'zh', 'japanese': 'ja', 'korean': 'ko',
                    'en': 'en', 'zh': 'zh', 'ja': 'ja', 'ko': 'ko'
                }
                lang_code = lang_map.get(language.lower(), language.lower())
            
            result = whisper_cpp_service.transcribe(audio_path, model_name, lang_code)
            return self._parse_srt(result['srt'])
        finally:
            if temp_audio_path and os.path.exists(temp_audio_path):
                os.unlink(temp_audio_path)

    def _transcribe_with_whisper_ctranslate2(self, file_path, model_name='base', language=None, use_gpu=True):
        """使用 Whisper-CTranslate2 转录"""
        from backend.services.whisper_ctranslate2_service import WhisperCTranslate2Service
        whisper_ct2_service = WhisperCTranslate2Service()
        
        if is_audio_file(file_path):
            audio_path = file_path
            temp_audio_path = None
        else:
            import uuid
            temp_audio_path = os.path.join(get_transcription_temp_dir(), f"{uuid.uuid4()}.wav")
            self._extract_audio(file_path, temp_audio_path)
            audio_path = temp_audio_path
        
        try:
            self.transcribe_status['status'] = 'transcribing'
            
            lang_code = None
            if language and language.lower() != 'auto-detect':
                lang_map = {
                    'english': 'en', 'chinese': 'zh', 'japanese': 'ja', 'korean': 'ko',
                    'en': 'en', 'zh': 'zh', 'ja': 'ja', 'ko': 'ko'
                }
                lang_code = lang_map.get(language.lower(), language.lower())
            
            result = whisper_ct2_service.transcribe(audio_path, model_name, lang_code, use_gpu)
            return self._parse_srt(result['srt'])
        finally:
            if temp_audio_path and os.path.exists(temp_audio_path):
                os.unlink(temp_audio_path)

    def _parse_srt(self, srt_content):
        """解析 SRT 内容"""
        segments = []
        lines = srt_content.strip().split('\n')
        
        i = 0
        while i < len(lines):
            if lines[i].strip().isdigit():
                i += 1
                if i < len(lines):
                    time_str = lines[i].strip()
                    start_end = time_str.split(' --> ')
                    if len(start_end) == 2:
                        start_time = self._srt_time_to_seconds(start_end[0])
                        end_time = self._srt_time_to_seconds(start_end[1])
                        i += 1
                        text_lines = []
                        while i < len(lines) and lines[i].strip():
                            text_lines.append(lines[i].strip())
                            i += 1
                        text = ' '.join(text_lines)
                        if text:
                            segments.append({
                                'start': start_time,
                                'end': end_time,
                                'text': text
                            })
            i += 1
        
        return {
            'text': ' '.join([seg['text'] for seg in segments]),
            'srt': srt_content,
            'segments': segments,
            'language': 'unknown'
        }

    def _srt_time_to_seconds(self, time_str):
        """将 SRT 时间格式转换为秒"""
        parts = time_str.replace(',', '.').split(':')
        hours = int(parts[0])
        minutes = int(parts[1])
        seconds = float(parts[2])
        return hours * 3600 + minutes * 60 + seconds

    def _improve_timestamps(self, segments):
        """改进时间轴准确性"""
        improved_segments = []
        for i, segment in enumerate(segments):
            if segment['end'] - segment['start'] < 0.5:
                continue
            
            if i > 0 and segment['start'] - improved_segments[-1]['end'] < 0.3:
                improved_segments[-1]['end'] = segment['end']
                improved_segments[-1]['text'] = improved_segments[-1]['text'] + ' ' + segment['text']
            else:
                improved_segments.append(segment)
        
        for i, segment in enumerate(improved_segments):
            if i > 0 and segment['start'] <= improved_segments[i-1]['end']:
                segment['start'] = improved_segments[i-1]['end'] + 0.01
        
        return improved_segments

    def transcribe_async(self, file_path, model_name='base', language=None, engine='openai', use_gpu=True):
        """异步转录"""
        if self.transcribe_status['transcribing']:
            return {'error': '已有转录任务正在进行中'}
        
        thread = threading.Thread(
            target=self._transcribe_thread,
            args=(file_path, model_name, language, engine, use_gpu)
        )
        thread.start()
        
        return {'message': '开始转录', 'file_path': file_path}

    def _transcribe_thread(self, file_path, model_name, language, engine, use_gpu):
        """转录线程函数"""
        try:
            self.transcribe_status['transcribing'] = True
            self.transcribe_status['progress'] = 0
            self.transcribe_status['status'] = 'loading_model'
            self.transcribe_status['error'] = None
            self._stop_progress = False
            
            progress_thread = threading.Thread(target=self._update_progress)
            progress_thread.start()
            
            result = self.transcribe_file(file_path, model_name, language, engine, use_gpu)
            
            self._stop_progress = True
            self.transcribe_status['progress'] = 95
            progress_thread.join()
            
            self.transcribe_status['progress'] = 100
            self.transcribe_status['status'] = 'completed'
            self.transcribe_status['result'] = result
        except Exception as e:
            self._stop_progress = True
            self.transcribe_status['status'] = 'error'
            self.transcribe_status['error'] = str(e)
        finally:
            if file_path and os.path.exists(file_path):
                try:
                    os.unlink(file_path)
                except:
                    pass
            self.transcribe_status['transcribing'] = False

    def _update_progress(self):
        """进度更新线程函数 - 使用平滑的进度曲线"""
        import math
        
        start_time = time.time()
        
        while not self._stop_progress:
            current_status = self.transcribe_status['status']
            elapsed = time.time() - start_time
            
            if current_status == 'loading_model':
                progress = min(10, int(elapsed * 2))
                self.transcribe_status['progress'] = progress
            elif current_status == 'transcribing':
                adjusted_elapsed = elapsed - 2.5
                if adjusted_elapsed > 0:
                    base_progress = 10
                    max_progress = 90
                    progress = base_progress + int(30 * math.log10(1 + adjusted_elapsed / 5))
                    progress = min(progress, max_progress)
                    self.transcribe_status['progress'] = progress
            
            time.sleep(0.2)

    def _generate_srt(self, result):
        """生成SRT内容（优化时间格式，适配剪映）"""
        segments = []
        srt_content = ''
        idx = 1
        
        for segment in result.get("segments", []):
            start_time = format_time_srt(segment["start"])
            end_time = format_time_srt(segment["end"])
            text = segment["text"].strip()
            
            if not text:
                continue
            
            segments.append({
                'start': segment['start'],
                'end': segment['end'],
                'text': text
            })
            
            srt_content += f"{idx}\n"
            srt_content += f"{start_time} --> {end_time}\n"
            srt_content += f"{text}\n\n"
            idx += 1
        
        return {
            'text': result.get('text', ''),
            'srt': srt_content,
            'segments': segments,
            'language': result.get('language', 'unknown')
        }

    def get_status(self):
        """获取转录状态"""
        return self.transcribe_status

    def get_result(self):
        """获取转录结果"""
        if self.transcribe_status['result']:
            result = self.transcribe_status['result']
            self.transcribe_status['result'] = None
            return result
        return None
    
    def abort(self):
        """中止转录"""
        self._stop_progress = True
        self.transcribe_status['transcribing'] = False
        self.transcribe_status['status'] = 'aborted'
        self.transcribe_status['progress'] = 0
