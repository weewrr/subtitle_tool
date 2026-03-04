import os
import sys
import subprocess
import threading
import requests
import tempfile
from backend.config.settings import Config
from backend.utils.file_utils import format_file_size

class WhisperCppService:
    def __init__(self):
        self.download_status = {
            'downloading': False,
            'model': None,
            'progress': 0,
            'status': 'idle',
            'error': None
        }
        self._ensure_directory()

    def _ensure_directory(self):
        """确保模型目录存在"""
        os.makedirs(Config.WHISPER_CPP_MODEL_DIR, exist_ok=True)

    def get_downloaded_models(self):
        """获取已下载的 Whisper.cpp 模型列表"""
        downloaded = []
        
        if os.path.exists(Config.WHISPER_CPP_MODEL_DIR):
            for file in os.listdir(Config.WHISPER_CPP_MODEL_DIR):
                if file.endswith('.bin'):
                    model_name = file.replace('.bin', '')
                    file_path = os.path.join(Config.WHISPER_CPP_MODEL_DIR, file)
                    file_size = os.path.getsize(file_path)
                    downloaded.append({
                        'name': model_name,
                        'size': format_file_size(file_size),
                        'size_bytes': file_size,
                        'downloaded': True
                    })
        
        return downloaded

    def list_all_models(self):
        """列出所有 Whisper.cpp 模型"""
        downloaded = self.get_downloaded_models()
        downloaded_names = [m['name'] for m in downloaded]
        
        all_models = [
            {'name': 'ggml-tiny.en', 'size': '~14 MB', 'description': '英文专用，最快，准确度较低'},
            {'name': 'ggml-tiny', 'size': '~39 MB', 'description': '多语言，最快，准确度较低'},
            {'name': 'ggml-base.en', 'size': '~29 MB', 'description': '英文专用，快速，准确度一般'},
            {'name': 'ggml-base', 'size': '~74 MB', 'description': '多语言，快速，准确度一般'},
            {'name': 'ggml-small.en', 'size': '~96 MB', 'description': '英文专用，平衡速度和准确度'},
            {'name': 'ggml-small', 'size': '~244 MB', 'description': '多语言，平衡速度和准确度'},
            {'name': 'ggml-medium.en', 'size': '~482 MB', 'description': '英文专用，较慢，准确度较高'},
            {'name': 'ggml-medium', 'size': '~1.5 GB', 'description': '多语言，较慢，准确度较高'},
            {'name': 'ggml-large-v3', 'size': '~2.9 GB', 'description': '多语言，最慢，准确度最高'}
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
        """下载 Whisper.cpp 模型"""
        if self.download_status['downloading']:
            return {'error': '已有模型正在下载中'}
        
        thread = threading.Thread(target=self._download_model_thread, args=(model_name,))
        thread.start()
        
        return {'message': f'开始下载 Whisper.cpp 模型: {model_name}', 'model': model_name}

    def _download_model_thread(self, model_name):
        """下载模型的线程函数"""
        try:
            self.download_status['downloading'] = True
            self.download_status['model'] = model_name
            self.download_status['progress'] = 0
            self.download_status['status'] = 'downloading'
            self.download_status['error'] = None
            
            model_urls = {
                'ggml-tiny.en': 'https://huggingface.co/ggerganov/whisper.cpp/resolve/main/ggml-tiny.en.bin',
                'ggml-tiny': 'https://huggingface.co/ggerganov/whisper.cpp/resolve/main/ggml-tiny.bin',
                'ggml-base.en': 'https://huggingface.co/ggerganov/whisper.cpp/resolve/main/ggml-base.en.bin',
                'ggml-base': 'https://huggingface.co/ggerganov/whisper.cpp/resolve/main/ggml-base.bin',
                'ggml-small.en': 'https://huggingface.co/ggerganov/whisper.cpp/resolve/main/ggml-small.en.bin',
                'ggml-small': 'https://huggingface.co/ggerganov/whisper.cpp/resolve/main/ggml-small.bin',
                'ggml-medium.en': 'https://huggingface.co/ggerganov/whisper.cpp/resolve/main/ggml-medium.en.bin',
                'ggml-medium': 'https://huggingface.co/ggerganov/whisper.cpp/resolve/main/ggml-medium.bin',
                'ggml-large-v3': 'https://huggingface.co/ggerganov/whisper.cpp/resolve/main/ggml-large-v3.bin'
            }
            
            if model_name not in model_urls:
                raise Exception(f'不支持的模型: {model_name}')
            
            url = model_urls[model_name]
            output_path = os.path.join(Config.WHISPER_CPP_MODEL_DIR, f'{model_name}.bin')
            
            response = requests.get(url, stream=True)
            response.raise_for_status()
            
            total_size = int(response.headers.get('content-length', 0))
            downloaded_size = 0
            
            with open(output_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
                        downloaded_size += len(chunk)
                        
                        if total_size > 0:
                            progress = int((downloaded_size / total_size) * 100)
                            self.download_status['progress'] = progress
            
            self.download_status['progress'] = 100
            self.download_status['status'] = 'completed'
            self.download_status['downloading'] = False
        except Exception as e:
            self.download_status['status'] = 'error'
            self.download_status['error'] = str(e)
            self.download_status['downloading'] = False

    def get_status(self):
        """获取下载状态"""
        return self.download_status

    def is_available(self):
        """检查 Whisper.cpp 是否可用"""
        return os.path.exists(Config.WHISPER_CPP_EXECUTABLE)

    def transcribe(self, audio_path, model_name='ggml-base', language=None):
        """使用 Whisper.cpp 转录音频"""
        model_path = os.path.join(Config.WHISPER_CPP_MODEL_DIR, f'{model_name}.bin')
        
        if not os.path.exists(model_path):
            raise Exception(f'模型文件不存在: {model_path}')
        
        if not self.is_available():
            raise Exception(f'Whisper.cpp 可执行文件不存在: {Config.WHISPER_CPP_EXECUTABLE}')
        
        output_dir = tempfile.mkdtemp()
        audio_basename = os.path.splitext(os.path.basename(audio_path))[0]
        
        cmd = [
            Config.WHISPER_CPP_EXECUTABLE,
            '-m', model_path,
            '-f', audio_path,
            '-otxt',
            '-osrt',
            '-of', os.path.join(output_dir, audio_basename)
        ]
        
        if language:
            cmd.extend(['-l', language])
        
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            cwd=Config.WHISPER_CPP_DIR
        )
        
        if result.returncode != 0:
            raise Exception(f'转录失败: {result.stderr}')
        
        srt_path = os.path.join(output_dir, f'{audio_basename}.srt')
        if not os.path.exists(srt_path):
            raise Exception('未生成 SRT 文件')
        
        with open(srt_path, 'r', encoding='utf-8') as f:
            srt_content = f.read()
        
        try:
            import shutil
            shutil.rmtree(output_dir)
        except:
            pass
        
        return {'srt': srt_content}
