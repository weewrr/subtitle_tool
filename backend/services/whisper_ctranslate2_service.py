import os
import sys
import subprocess
import threading
from backend.config.settings import Config
from backend.utils.file_utils import format_file_size

class WhisperCTranslate2Service:
    def __init__(self):
        self.download_status = {
            'downloading': False,
            'model': None,
            'progress': 0,
            'status': 'idle',
            'error': None
        }
        self._ensure_directory()
        self._reset_status()

    def _reset_status(self):
        """重置下载状态"""
        self.download_status = {
            'downloading': False,
            'model': None,
            'progress': 0,
            'status': 'idle',
            'error': None
        }

    def _ensure_directory(self):
        """确保模型目录存在"""
        os.makedirs(Config.WHISPER_CTRANSLATE2_MODEL_DIR, exist_ok=True)

    def _ensure_faster_whisper_installed(self):
        """确保 faster-whisper 已安装"""
        try:
            from faster_whisper import WhisperModel
            return WhisperModel
        except ImportError:
            subprocess.check_call([sys.executable, '-m', 'pip', 'install', 'faster-whisper', '-i', 'https://pypi.tuna.tsinghua.edu.cn/simple', '-q'])
            from faster_whisper import WhisperModel
            return WhisperModel

    def get_downloaded_models(self):
        """获取已下载的 Whisper-CTranslate2 模型列表"""
        downloaded = []
        
        if os.path.exists(Config.WHISPER_CTRANSLATE2_MODEL_DIR):
            for item in os.listdir(Config.WHISPER_CTRANSLATE2_MODEL_DIR):
                if item.startswith('models--Systran--faster-whisper-'):
                    model_name = item.replace('models--Systran--faster-whisper-', '')
                    model_path = os.path.join(Config.WHISPER_CTRANSLATE2_MODEL_DIR, item)
                    
                    snapshots_dir = os.path.join(model_path, 'snapshots')
                    if os.path.exists(snapshots_dir):
                        for snapshot in os.listdir(snapshots_dir):
                            snapshot_path = os.path.join(snapshots_dir, snapshot)
                            if os.path.exists(os.path.join(snapshot_path, 'model.bin')):
                                downloaded.append({
                                    'name': model_name,
                                    'size': self._get_dir_size(model_path),
                                    'downloaded': True
                                })
                                break
        
        return downloaded

    def _get_dir_size(self, path):
        """获取目录大小"""
        total_size = 0
        try:
            for dirpath, dirnames, filenames in os.walk(path):
                for filename in filenames:
                    filepath = os.path.join(dirpath, filename)
                    if os.path.exists(filepath):
                        total_size += os.path.getsize(filepath)
        except:
            pass
        return format_file_size(total_size)

    def list_all_models(self):
        """列出所有 Whisper-CTranslate2 模型"""
        downloaded = self.get_downloaded_models()
        downloaded_names = [m['name'] for m in downloaded]
        
        all_models = [
            {'name': 'tiny', 'size': '~39 MB', 'description': '最快，准确度较低'},
            {'name': 'base', 'size': '~74 MB', 'description': '快速，准确度一般'},
            {'name': 'small', 'size': '~244 MB', 'description': '平衡速度和准确度'},
            {'name': 'medium', 'size': '~1.5 GB', 'description': '较慢，准确度较高'},
            {'name': 'large-v1', 'size': '~2.9 GB', 'description': '慢，准确度高'},
            {'name': 'large-v2', 'size': '~2.9 GB', 'description': '慢，准确度高'},
            {'name': 'large-v3', 'size': '~2.9 GB', 'description': '最慢，准确度最高'}
        ]
        
        result = []
        for model in downloaded:
            result.append(model)
        
        for model in all_models:
            if model['name'] not in downloaded_names:
                model['downloaded'] = False
                result.append(model)
        
        return result

    def download_model(self, model_name):
        """下载 Whisper-CTranslate2 模型（在后台线程中）"""
        if self.download_status['downloading']:
            return {'error': '已有模型正在下载中'}
        
        thread = threading.Thread(target=self._download_model_thread, args=(model_name,))
        thread.start()
        
        return {'message': f'开始下载 Whisper-CTranslate2 模型: {model_name}', 'model': model_name}

    def _download_model_thread(self, model_name):
        """下载模型的线程函数"""
        try:
            self.download_status['downloading'] = True
            self.download_status['model'] = model_name
            self.download_status['progress'] = 0
            self.download_status['status'] = 'downloading'
            self.download_status['error'] = None
            
            WhisperModel = self._ensure_faster_whisper_installed()
            
            self.download_status['status'] = 'downloading'
            self.download_status['progress'] = 10
            
            model = WhisperModel(
                model_name,
                device="cpu",
                compute_type="int8",
                download_root=Config.WHISPER_CTRANSLATE2_MODEL_DIR
            )
            
            self.download_status['progress'] = 100
            self.download_status['status'] = 'completed'
            self.download_status['downloading'] = False
        except Exception as e:
            error_msg = str(e)
            self.download_status['status'] = 'error'
            self.download_status['error'] = error_msg
            self.download_status['downloading'] = False

    def get_status(self):
        """获取下载状态"""
        return self.download_status

    def transcribe(self, audio_path, model_name='base', language=None, use_gpu=True):
        """使用 Whisper-CTranslate2 转录音频"""
        WhisperModel = self._ensure_faster_whisper_installed()
        
        device = "cpu"
        compute_type = "int8"
        
        if use_gpu:
            try:
                import torch
                if torch.cuda.is_available():
                    device = "cuda"
                    compute_type = "float16"
            except:
                pass
        
        try:
            model = WhisperModel(
                model_name,
                device=device,
                compute_type=compute_type,
                download_root=Config.WHISPER_CTRANSLATE2_MODEL_DIR
            )
        except Exception as e:
            if device == "cuda":
                device = "cpu"
                compute_type = "int8"
                model = WhisperModel(
                    model_name,
                    device=device,
                    compute_type=compute_type,
                    download_root=Config.WHISPER_CTRANSLATE2_MODEL_DIR
                )
            else:
                raise
        
        segments, info = model.transcribe(
            audio_path,
            language=language,
            beam_size=5,
            best_of=5,
            temperature=0.0
        )
        
        segments_list = list(segments)
        
        srt_content = self._generate_srt_from_segments(segments_list)
        
        return {
            'srt': srt_content,
            'language': info.language,
            'language_probability': info.language_probability
        }

    def _generate_srt_from_segments(self, segments):
        """从 segments 生成 SRT 内容"""
        srt_lines = []
        for i, segment in enumerate(segments, 1):
            start_time = self._format_timestamp(segment.start)
            end_time = self._format_timestamp(segment.end)
            text = segment.text.strip()
            
            srt_lines.append(f"{i}")
            srt_lines.append(f"{start_time} --> {end_time}")
            srt_lines.append(text)
            srt_lines.append("")
        
        return "\n".join(srt_lines)

    def _format_timestamp(self, seconds):
        """格式化时间戳为 SRT 格式"""
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = seconds % 60
        milliseconds = int((secs % 1) * 1000)
        secs = int(secs)
        
        return f"{hours:02d}:{minutes:02d}:{secs:02d},{milliseconds:03d}"
