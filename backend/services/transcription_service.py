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
            print("正在安装 openai-whisper...")
            subprocess.check_call([sys.executable, '-m', 'pip', 'install', 'openai-whisper', '-q'])
            import whisper
        return whisper

    def _ensure_ffmpeg_installed(self):
        """确保 ffmpeg-python 已安装"""
        try:
            import ffmpeg
        except ImportError:
            print("正在安装 ffmpeg-python...")
            subprocess.check_call([sys.executable, '-m', 'pip', 'install', 'ffmpeg-python', '-q'])
            import ffmpeg
        return ffmpeg

    def _extract_audio(self, video_path, audio_path):
        """从视频提取音频（优化参数，确保和 Whisper 兼容）"""
        ffmpeg = self._ensure_ffmpeg_installed()
        
        if not os.path.exists(video_path):
            raise FileNotFoundError(f"视频文件不存在：{video_path}")
        
        ext = os.path.splitext(video_path)[1].lower()
        if ext not in Config.SUPPORTED_VIDEO_FORMATS and ext not in Config.SUPPORTED_AUDIO_FORMATS:
            raise ValueError(f"不支持的格式：{ext}")
        
        try:
            (
                ffmpeg
                .input(video_path)
                .output(
                    audio_path,
                    format='wav',
                    acodec='pcm_s16le',
                    ac=1,
                    ar=16000,
                    loglevel='error'
                )
                .overwrite_output()
                .run(quiet=True)
            )
            print(f"音频提取完成：{audio_path}")
        except ffmpeg.Error as e:
            raise RuntimeError(f"音频提取失败：{e.stderr.decode('utf-8') if e.stderr else str(e)}")
        except Exception as e:
            raise RuntimeError(f"音频提取异常：{str(e)}")

    def transcribe_file(self, file_path, model_name='base', language=None, engine='openai'):
        """转录文件（同步）"""
        if engine == 'openai':
            return self._transcribe_with_openai(file_path, model_name, language)
        elif engine == 'vosk':
            from backend.services.vosk_service import VoskService
            vosk_service = VoskService()
            # 映射语言到 Vosk 模型代码
            language_map = {
                'en': 'en',
                'zh': 'cn',
                'fr': 'fr',
                'es': 'es',
                'de': 'de',
                'pt': 'pt',
                'it': 'it',
                'nl': 'nl',
                'sv': 'sv',
                'ru': 'ru',
                'fa': 'fa',
                'tr': 'tr',
                'el': 'el',
                'ar': 'ar',
                'uk': 'uk',
                'uz': 'uz',
                'ph': 'ph',
                'kz': 'kz',
                'jp': 'jp',
                'ca': 'ca',
                'hi': 'hi',
                'cz': 'cz',
                'pl': 'pl',
                'br': 'br'
            }
            model_code = language_map.get(language.lower() if language else 'zh', 'cn')
            
            # 更新状态为转录中
            self.transcribe_status['status'] = 'transcribing'
            
            return vosk_service.transcribe_with_vosk(file_path, model_code, self.transcribe_status)
        else:
            # 其他引擎的实现可以在这里添加
            return self._transcribe_with_openai(file_path, model_name, language)

    def _transcribe_with_openai(self, file_path, model_name='base', language=None):
        """使用 OpenAI Whisper 转录"""
        import torch
        whisper = self._ensure_whisper_installed()
        
        device = "cuda" if torch.cuda.is_available() else "cpu"
        print(f"加载 Whisper 模型：{model_name}，设备：{device}")
        model = whisper.load_model(model_name, device=device)
        
        if is_audio_file(file_path):
            audio_path = file_path
            temp_audio_path = None
        else:
            import uuid
            temp_audio_path = os.path.join(get_transcription_temp_dir(), f"{uuid.uuid4()}.wav")
            self._extract_audio(file_path, temp_audio_path)
            audio_path = temp_audio_path
        
        try:
            print("正在识别音频并生成时间轴...")
            self.transcribe_status['status'] = 'transcribing'
            
            lang_code = None
            if language and language.lower() != 'auto-detect':
                lang_map = {
                    'english': 'en',
                    'chinese': 'zh',
                    'japanese': 'ja',
                    'korean': 'ko',
                    'en': 'en',
                    'zh': 'zh',
                    'ja': 'ja',
                    'ko': 'ko'
                }
                lang_code = lang_map.get(language.lower(), language.lower())
            
            # 优化转录参数
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
            
            # 改进时间轴
            segments = self._improve_timestamps(result.get('segments', []))
            result['segments'] = segments
            
            return self._generate_srt(result)
        finally:
            if temp_audio_path and os.path.exists(temp_audio_path):
                os.unlink(temp_audio_path)
                print("临时音频文件已删除")

    def _improve_timestamps(self, segments):
        """改进时间轴准确性"""
        improved_segments = []
        for i, segment in enumerate(segments):
            # 移除过短的段
            if segment['end'] - segment['start'] < 0.5:
                continue
            
            # 合并相邻的短段
            if i > 0 and segment['start'] - improved_segments[-1]['end'] < 0.3:
                improved_segments[-1]['end'] = segment['end']
                improved_segments[-1]['text'] = improved_segments[-1]['text'] + ' ' + segment['text']
            else:
                improved_segments.append(segment)
        
        # 确保时间轴合理
        for i, segment in enumerate(improved_segments):
            # 确保开始时间大于前一个的结束时间
            if i > 0 and segment['start'] <= improved_segments[i-1]['end']:
                segment['start'] = improved_segments[i-1]['end'] + 0.01
        
        return improved_segments

    def transcribe_async(self, file_path, model_name='base', language=None, engine='openai'):
        """异步转录"""
        if self.transcribe_status['transcribing']:
            return {'error': '已有转录任务正在进行中'}
        
        thread = threading.Thread(
            target=self._transcribe_thread,
            args=(file_path, model_name, language, engine)
        )
        thread.start()
        
        return {'message': '开始转录', 'file_path': file_path}

    def _transcribe_thread(self, file_path, model_name, language, engine):
        """转录线程函数"""
        try:
            self.transcribe_status['transcribing'] = True
            self.transcribe_status['progress'] = 0
            self.transcribe_status['status'] = 'loading_model'
            self.transcribe_status['error'] = None
            self._stop_progress = False
            
            # 启动进度更新线程
            progress_thread = threading.Thread(target=self._update_progress)
            progress_thread.start()
            
            result = self.transcribe_file(file_path, model_name, language, engine)
            
            # 转录完成，立即停止进度更新并设置进度为95%
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
            print(f"转录失败：{str(e)}")
        finally:
            # 清理临时文件
            if file_path and os.path.exists(file_path):
                try:
                    os.unlink(file_path)
                    print(f"临时文件已清理：{file_path}")
                except Exception as e:
                    print(f"清理临时文件失败：{str(e)}")
            self.transcribe_status['transcribing'] = False

    def _update_progress(self):
        """进度更新线程函数 - 使用平滑的进度曲线"""
        import math
        
        start_time = time.time()
        
        while not self._stop_progress:
            current_status = self.transcribe_status['status']
            elapsed = time.time() - start_time
            
            if current_status == 'loading_model':
                # 加载模型阶段：0-10%，最多5秒
                progress = min(10, int(elapsed * 2))
                self.transcribe_status['progress'] = progress
            elif current_status == 'transcribing':
                # 转录阶段：10-90%，使用对数曲线让进度更平滑
                # 假设转录通常需要30-60秒，使用对数曲线让进度缓慢增长
                adjusted_elapsed = elapsed - 2.5  # 减去加载模型的时间
                if adjusted_elapsed > 0:
                    # 使用对数曲线：进度增长先快后慢
                    base_progress = 10
                    max_progress = 90
                    # 每10秒增加约20%的进度，但使用对数曲线
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
        
        print(f"SRT 字幕生成完成，共 {len(segments)} 条")
        
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
