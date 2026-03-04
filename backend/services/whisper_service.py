import os
import sys
import subprocess
import threading
from backend.config.settings import Config
from backend.utils.file_utils import format_file_size

class WhisperModelService:
    def __init__(self):
        self.download_status = {
            'downloading': False,
            'model': None,
            'progress': 0,
            'status': 'idle',
            'error': None
        }

    def get_downloaded_models(self):
        """获取已下载的Whisper模型列表"""
        cache_dir = Config.WHISPER_CACHE_DIR
        downloaded = []
        
        if os.path.exists(cache_dir):
            for file in os.listdir(cache_dir):
                if file.endswith('.pt'):
                    model_name = file.replace('.pt', '')
                    file_path = os.path.join(cache_dir, file)
                    file_size = os.path.getsize(file_path)
                    downloaded.append({
                        'name': model_name,
                        'size': format_file_size(file_size),
                        'size_bytes': file_size,
                        'downloaded': True
                    })
        
        return downloaded

    def list_all_models(self):
        """列出所有模型（已下载和可下载）"""
        downloaded = self.get_downloaded_models()
        downloaded_names = [m['name'] for m in downloaded]
        
        all_models = [
            {'name': 'tiny', 'size': '~75 MB', 'description': '最快，准确度较低'},
            {'name': 'base', 'size': '~142 MB', 'description': '快速，准确度一般'},
            {'name': 'small', 'size': '~466 MB', 'description': '平衡速度和准确度'},
            {'name': 'medium', 'size': '~1.5 GB', 'description': '较慢，准确度较高'},
            {'name': 'large', 'size': '~2.9 GB', 'description': '最慢，准确度最高'}
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
        """下载模型（在后台线程中）"""
        if self.download_status['downloading']:
            return {'error': '已有模型正在下载中'}
        
        if model_name not in Config.VALID_MODELS:
            return {'error': f'无效的模型名称: {model_name}'}
        
        thread = threading.Thread(target=self._download_model_thread, args=(model_name,))
        thread.start()
        
        return {'message': f'开始下载 {model_name} 模型', 'model': model_name}

    def _download_model_thread(self, model_name):
        """下载模型的线程函数"""
        try:
            self.download_status['downloading'] = True
            self.download_status['model'] = model_name
            self.download_status['progress'] = 0
            self.download_status['status'] = 'downloading'
            self.download_status['error'] = None
            
            try:
                import whisper
            except ImportError:
                self.download_status['status'] = 'installing_whisper'
                self.download_status['progress'] = 5
                subprocess.check_call([sys.executable, '-m', 'pip', 'install', 'openai-whisper', '-q'])
                self.download_status['status'] = 'downloading'
                self.download_status['progress'] = 10
            
            import whisper
            import threading
            import time
            
            cache_dir = Config.WHISPER_CACHE_DIR
            os.makedirs(cache_dir, exist_ok=True)
            model_path = os.path.join(cache_dir, f'{model_name}.pt')
            
            if os.path.exists(model_path):
                actual_size = os.path.getsize(model_path)
                if actual_size > 1000000:
                    self.download_status['progress'] = 100
                    self.download_status['status'] = 'completed'
                    self.download_status['downloading'] = False
                    return
                else:
                    os.remove(model_path)
            
            model_sizes = {
                'tiny': 75_000_000,
                'base': 150_000_000,
                'small': 500_000_000,
                'medium': 1_500_000_000,
                'large': 3_000_000_000
            }
            expected_size = model_sizes.get(model_name, 500_000_000)
            
            self.download_status['status'] = 'downloading'
            self.download_status['progress'] = 5
            
            download_complete = threading.Event()
            download_error = [None]
            
            def do_download():
                try:
                    whisper.load_model(model_name, download_root=cache_dir)
                except Exception as e:
                    download_error[0] = str(e)
                finally:
                    download_complete.set()
            
            download_thread = threading.Thread(target=do_download)
            download_thread.start()
            
            while not download_complete.is_set():
                if os.path.exists(model_path):
                    current_size = os.path.getsize(model_path)
                    progress = int((current_size / expected_size) * 85)
                    progress = min(progress, 95)
                    self.download_status['progress'] = 5 + progress
                time.sleep(0.2)
            
            download_thread.join()
            
            if download_error[0]:
                raise Exception(download_error[0])
            
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
