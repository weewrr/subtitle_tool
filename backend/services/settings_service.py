import os
import sys
import platform
import shutil
import subprocess
import glob as glob_mod
from datetime import datetime, timedelta

from backend.config.settings import Config


class SettingsService:
    """设置与诊断服务"""

    # ============= 环境诊断 =============

    def run_diagnostics(self):
        """运行环境自检，返回可读诊断结果"""
        results = {
            'system': self._check_system(),
            'python': self._check_python(),
            'ffmpeg': self._check_ffmpeg(),
            'gpu': self._check_gpu(),
            'cuda': self._check_cuda(),
            'pytorch': self._check_pytorch(),
            'whisper': self._check_whisper_versions(),
            'models': self._check_installed_models(),
            'paths': self._check_paths(),
            'warnings': [],
            'errors': []
        }

        # 汇总警告和错误
        for category in ['system', 'python', 'ffmpeg', 'gpu', 'cuda', 'pytorch', 'whisper', 'models', 'paths']:
            cat = results[category]
            if isinstance(cat, dict):
                for item in cat.get('warnings', []):
                    results['warnings'].append(item)
                for item in cat.get('errors', []):
                    results['errors'].append(item)

        results['overall_status'] = 'ok' if not results['errors'] else 'error'
        if not results['errors'] and results['warnings']:
            results['overall_status'] = 'warning'

        return results

    def _check_system(self):
        return {
            'os': platform.system(),
            'os_version': platform.version(),
            'os_release': platform.release(),
            'architecture': platform.machine(),
            'hostname': platform.node(),
            'warnings': [],
            'errors': []
        }

    def _check_python(self):
        info = {
            'version': sys.version,
            'executable': sys.executable,
            'pip_available': False,
            'warnings': [],
            'errors': []
        }
        try:
            result = subprocess.run(
                [sys.executable, '-m', 'pip', '--version'],
                capture_output=True, text=True, timeout=10
            )
            info['pip_available'] = result.returncode == 0
            if info['pip_available']:
                info['pip_version'] = result.stdout.strip()
        except Exception:
            info['warnings'].append('pip 不可用，部分功能可能受限')
        return info

    def _check_ffmpeg(self):
        info = {
            'installed': False,
            'version': '',
            'path': '',
            'warnings': [],
            'errors': []
        }
        try:
            result = subprocess.run(
                ['ffmpeg', '-version'],
                capture_output=True, text=True, timeout=10
            )
            if result.returncode == 0:
                info['installed'] = True
                version_line = result.stdout.strip().split('\n')[0]
                info['version'] = version_line
                ffmpeg_path = shutil.which('ffmpeg')
                info['path'] = ffmpeg_path or ''
            else:
                info['errors'].append('ffmpeg 未正确安装，请安装 ffmpeg')
        except FileNotFoundError:
            info['errors'].append('ffmpeg 未找到，请安装 ffmpeg')
        except Exception as e:
            info['errors'].append(f'ffmpeg 检测失败: {str(e)}')
        return info

    def _check_gpu(self):
        info = {
            'available': False,
            'name': '',
            'warnings': [],
            'errors': []
        }
        try:
            # 尝试 nvidia-smi
            result = subprocess.run(
                ['nvidia-smi', '--query-gpu=name', '--format=csv,noheader'],
                capture_output=True, text=True, timeout=10
            )
            if result.returncode == 0:
                info['available'] = True
                info['name'] = result.stdout.strip()
            else:
                info['warnings'].append('未检测到 NVIDIA GPU 或 nvidia-smi 不可用')
        except FileNotFoundError:
            info['warnings'].append('nvidia-smi 未找到，可能未安装 NVIDIA 驱动')
        except Exception as e:
            info['warnings'].append(f'GPU 检测失败: {str(e)}')
        return info

    def _check_cuda(self):
        info = {
            'available': False,
            'version': '',
            'warnings': [],
            'errors': []
        }
        try:
            result = subprocess.run(
                ['nvcc', '--version'],
                capture_output=True, text=True, timeout=10
            )
            if result.returncode == 0:
                info['available'] = True
                for line in result.stdout.strip().split('\n'):
                    if 'release' in line.lower():
                        info['version'] = line.strip()
                        break
        except FileNotFoundError:
            pass
        if not info['available']:
            # 尝试从 nvidia-smi 获取 CUDA 版本
            try:
                result = subprocess.run(
                    ['nvidia-smi'],
                    capture_output=True, text=True, timeout=10
                )
                for line in result.stdout.strip().split('\n'):
                    if 'CUDA Version' in line:
                        info['version'] = line.strip()
                        info['available'] = True
                        break
            except Exception:
                pass
        if not info['available']:
            info['warnings'].append('CUDA Toolkit 未安装或不可用')
        return info

    def _check_pytorch(self):
        info = {
            'installed': False,
            'version': '',
            'cuda_available': False,
            'warnings': [],
            'errors': []
        }
        try:
            import torch
            info['installed'] = True
            info['version'] = torch.__version__
            info['cuda_available'] = torch.cuda.is_available()
            if torch.cuda.is_available():
                info['cuda_version'] = torch.version.cuda or ''
                info['gpu_count'] = torch.cuda.device_count()
            else:
                info['warnings'].append('PyTorch CUDA 不可用，将使用 CPU 推理')
        except ImportError:
            info['errors'].append('PyTorch 未安装，语音识别功能不可用')
        return info

    def _check_whisper_versions(self):
        info = {
            'faster_whisper': {'installed': False, 'version': ''},
            'openai_whisper': {'installed': False, 'version': ''},
            'warnings': [],
            'errors': []
        }
        # faster-whisper
        try:
            import faster_whisper
            info['faster_whisper']['installed'] = True
            info['faster_whisper']['version'] = getattr(faster_whisper, '__version__', 'unknown')
        except ImportError:
            info['warnings'].append('faster-whisper 未安装')
        # openai-whisper
        try:
            import whisper
            info['openai_whisper']['installed'] = True
            info['openai_whisper']['version'] = getattr(whisper, '__version__', 'unknown')
        except ImportError:
            info['warnings'].append('openai-whisper 未安装')
        return info

    def _check_installed_models(self):
        info = {
            'whisper': [],
            'whisper_cpp': [],
            'whisper_ctranslate2': [],
            'total_size_mb': 0,
            'warnings': [],
            'errors': []
        }
        total_size = 0

        # OpenAI Whisper 模型
        whisper_dir = Config.WHISPER_CACHE_DIR
        if os.path.isdir(whisper_dir):
            for item in os.listdir(whisper_dir):
                item_path = os.path.join(whisper_dir, item)
                size = self._get_dir_size(item_path)
                total_size += size
                info['whisper'].append({
                    'name': item,
                    'size_mb': round(size / (1024 * 1024), 2)
                })

        # Whisper.cpp 模型
        cpp_dir = Config.WHISPER_CPP_MODEL_DIR
        if os.path.isdir(cpp_dir):
            for item in os.listdir(cpp_dir):
                item_path = os.path.join(cpp_dir, item)
                if os.path.isfile(item_path):
                    size = os.path.getsize(item_path)
                    total_size += size
                    info['whisper_cpp'].append({
                        'name': item,
                        'size_mb': round(size / (1024 * 1024), 2)
                    })

        # CTranslate2 模型
        ct2_dir = Config.WHISPER_CTRANSLATE2_MODEL_DIR
        if os.path.isdir(ct2_dir):
            for item in os.listdir(ct2_dir):
                item_path = os.path.join(ct2_dir, item)
                size = self._get_dir_size(item_path)
                total_size += size
                info['whisper_ctranslate2'].append({
                    'name': item,
                    'size_mb': round(size / (1024 * 1024), 2)
                })

        info['total_size_mb'] = round(total_size / (1024 * 1024), 2)
        return info

    def _check_paths(self):
        info = {
            'model_path': Config.WHISPER_CACHE_DIR,
            'whisper_cpp_model_path': Config.WHISPER_CPP_MODEL_DIR,
            'whisper_ctranslate2_model_path': Config.WHISPER_CTRANSLATE2_MODEL_DIR,
            'audio_dir': Config.AUDIO_DIR,
            'warnings': [],
            'errors': []
        }
        return info

    # ============= 缓存管理 =============

    def get_cache_stats(self):
        """获取缓存占用统计"""
        stats = {
            'temp_audio': self._get_dir_stats(Config.AUDIO_DIR),
            'temp_audio_mb': 0,
            'temp_waveform': {'file_count': 0, 'total_size': 0},
            'temp_waveform_mb': 0,
            'temp_task_results': {'file_count': 0, 'total_size': 0},
            'temp_task_results_mb': 0,
            'total_mb': 0
        }

        stats['temp_audio_mb'] = round(stats['temp_audio']['total_size'] / (1024 * 1024), 2)

        # 波形缓存（在 audio 目录下的 .waveform 文件）
        waveform_size = 0
        waveform_count = 0
        if os.path.isdir(Config.AUDIO_DIR):
            for f in glob_mod.glob(os.path.join(Config.AUDIO_DIR, '*.waveform*')):
                if os.path.isfile(f):
                    waveform_size += os.path.getsize(f)
                    waveform_count += 1
        stats['temp_waveform'] = {'file_count': waveform_count, 'total_size': waveform_size}
        stats['temp_waveform_mb'] = round(waveform_size / (1024 * 1024), 2)

        # 任务结果（临时字幕文件等）
        task_size = 0
        task_count = 0
        for dir_name in ['OriginalSubtitle', 'translatesubtitles']:
            task_dir = os.path.join(Config.BASE_DIR, dir_name)
            if os.path.isdir(task_dir):
                for f in os.listdir(task_dir):
                    fp = os.path.join(task_dir, f)
                    if os.path.isfile(fp):
                        task_size += os.path.getsize(fp)
                        task_count += 1
        stats['temp_task_results'] = {'file_count': task_count, 'total_size': task_size}
        stats['temp_task_results_mb'] = round(task_size / (1024 * 1024), 2)

        stats['total_mb'] = round(
            (stats['temp_audio']['total_size'] + waveform_size + task_size) / (1024 * 1024), 2
        )
        return stats

    def clean_temp_audio(self):
        """清理临时音频文件"""
        deleted = 0
        errors = []
        if os.path.isdir(Config.AUDIO_DIR):
            for f in os.listdir(Config.AUDIO_DIR):
                fp = os.path.join(Config.AUDIO_DIR, f)
                if os.path.isfile(fp):
                    try:
                        os.remove(fp)
                        deleted += 1
                    except Exception as e:
                        errors.append(f'删除 {f} 失败: {str(e)}')
        return {'deleted': deleted, 'errors': errors}

    def clean_waveform_cache(self):
        """清理波形缓存"""
        deleted = 0
        errors = []
        if os.path.isdir(Config.AUDIO_DIR):
            for f in glob_mod.glob(os.path.join(Config.AUDIO_DIR, '*.waveform*')):
                if os.path.isfile(f):
                    try:
                        os.remove(f)
                        deleted += 1
                    except Exception as e:
                        errors.append(f'删除 {os.path.basename(f)} 失败: {str(e)}')
        return {'deleted': deleted, 'errors': errors}

    def clean_task_results(self):
        """清理任务结果（临时字幕文件）"""
        deleted = 0
        errors = []
        for dir_name in ['OriginalSubtitle', 'translatesubtitles']:
            task_dir = os.path.join(Config.BASE_DIR, dir_name)
            if os.path.isdir(task_dir):
                for f in os.listdir(task_dir):
                    fp = os.path.join(task_dir, f)
                    if os.path.isfile(fp):
                        try:
                            os.remove(fp)
                            deleted += 1
                        except Exception as e:
                            errors.append(f'删除 {f} 失败: {str(e)}')
        return {'deleted': deleted, 'errors': errors}

    # ============= 版本信息 =============

    def get_version_info(self):
        """获取应用版本信息"""
        info = {
            'app_version': '1.0.0',
            'frontend_version': '1.0.0',
            'backend_version': '1.0.0',
            'python_version': sys.version.split()[0],
            'ffmpeg_version': '',
            'cuda_version': ''
        }

        # ffmpeg
        ffmpeg_check = self._check_ffmpeg()
        if ffmpeg_check['installed']:
            info['ffmpeg_version'] = ffmpeg_check['version']

        # CUDA
        cuda_check = self._check_cuda()
        if cuda_check['available']:
            info['cuda_version'] = cuda_check['version']

        # Whisper
        whisper_check = self._check_whisper_versions()
        if whisper_check['faster_whisper']['installed']:
            info['faster_whisper_version'] = whisper_check['faster_whisper']['version']
        if whisper_check['openai_whisper']['installed']:
            info['openai_whisper_version'] = whisper_check['openai_whisper']['version']

        return info

    # ============= 健康检查 =============

    def health_check(self):
        """返回健康检查状态"""
        checks = {
            'backend': True,
            'python': True,
            'ffmpeg': self._check_ffmpeg()['installed'],
            'whisper': False,
            'gpu': self._check_gpu()['available'],
            'disk_space': self._check_disk_space()
        }

        whisper_check = self._check_whisper_versions()
        checks['whisper'] = (
            whisper_check['faster_whisper']['installed'] or
            whisper_check['openai_whisper']['installed']
        )

        checks['overall'] = all([
            checks['backend'], checks['python'], checks['ffmpeg']
        ])

        return checks

    def _check_disk_space(self):
        """检查磁盘空间"""
        try:
            usage = shutil.disk_usage(Config.BASE_DIR)
            return {
                'total_gb': round(usage.total / (1024 ** 3), 2),
                'used_gb': round(usage.used / (1024 ** 3), 2),
                'free_gb': round(usage.free / (1024 ** 3), 2),
                'percent_used': round(usage.used / usage.total * 100, 1)
            }
        except Exception:
            return {'total_gb': 0, 'used_gb': 0, 'free_gb': 0, 'percent_used': 0}

    # ============= 工具方法 =============

    def _get_dir_size(self, path):
        """递归计算目录大小"""
        total = 0
        if os.path.isfile(path):
            return os.path.getsize(path)
        if os.path.isdir(path):
            for dirpath, _dirnames, filenames in os.walk(path):
                for f in filenames:
                    fp = os.path.join(dirpath, f)
                    try:
                        total += os.path.getsize(fp)
                    except OSError:
                        pass
        return total

    def _get_dir_stats(self, path):
        """获取目录统计信息"""
        file_count = 0
        total_size = 0
        if os.path.isdir(path):
            for f in os.listdir(path):
                fp = os.path.join(path, f)
                if os.path.isfile(fp):
                    file_count += 1
                    try:
                        total_size += os.path.getsize(fp)
                    except OSError:
                        pass
        return {'file_count': file_count, 'total_size': total_size}

    def open_directory(self, path):
        """在文件管理器中打开目录"""
        if not os.path.isdir(path):
            os.makedirs(path, exist_ok=True)
        try:
            if platform.system() == 'Windows':
                subprocess.run(['explorer', path])
            elif platform.system() == 'Darwin':
                subprocess.run(['open', path])
            else:
                subprocess.run(['xdg-open', path])
            return True
        except Exception as e:
            return False

    def get_diagnostic_text(self):
        """生成脱敏的诊断文本（用于复制）"""
        diag = self.run_diagnostics()
        lines = []
        lines.append('=== 本地 AI 字幕工作台 诊断报告 ===')
        lines.append(f'时间: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}')
        lines.append('')

        lines.append('--- 系统信息 ---')
        sys_info = diag['system']
        lines.append(f'操作系统: {sys_info["os"]} {sys_info["os_release"]}')
        lines.append(f'架构: {sys_info["architecture"]}')

        lines.append('')
        lines.append('--- Python 环境 ---')
        py_info = diag['python']
        lines.append(f'Python 版本: {py_info["version"].split()[0]}')
        lines.append(f'pip 可用: {"是" if py_info["pip_available"] else "否"}')

        lines.append('')
        lines.append('--- FFmpeg ---')
        ff_info = diag['ffmpeg']
        lines.append(f'已安装: {"是" if ff_info["installed"] else "否"}')
        if ff_info['installed']:
            lines.append(f'版本: {ff_info["version"]}')

        lines.append('')
        lines.append('--- GPU / CUDA ---')
        gpu_info = diag['gpu']
        lines.append(f'GPU 可用: {"是" if gpu_info["available"] else "否"}')
        if gpu_info['available']:
            lines.append(f'GPU 名称: {gpu_info["name"]}')
        cuda_info = diag['cuda']
        lines.append(f'CUDA 可用: {"是" if cuda_info["available"] else "否"}')
        if cuda_info['available']:
            lines.append(f'CUDA 版本: {cuda_info["version"]}')

        lines.append('')
        lines.append('--- PyTorch ---')
        pt_info = diag['pytorch']
        lines.append(f'PyTorch 已安装: {"是" if pt_info["installed"] else "否"}')
        if pt_info['installed']:
            lines.append(f'PyTorch 版本: {pt_info["version"]}')
            lines.append(f'CUDA 可用: {"是" if pt_info["cuda_available"] else "否"}')

        lines.append('')
        lines.append('--- Whisper 引擎 ---')
        wh_info = diag['whisper']
        for engine in ['faster_whisper', 'openai_whisper']:
            e = wh_info[engine]
            name = 'faster-whisper' if engine == 'faster_whisper' else 'openai-whisper'
            lines.append(f'{name}: {"已安装" if e["installed"] else "未安装"}')
            if e['installed']:
                lines.append(f'  版本: {e["version"]}')

        lines.append('')
        lines.append('--- 已安装模型 ---')
        models = diag['models']
        for engine in ['whisper', 'whisper_cpp', 'whisper_ctranslate2']:
            for m in models[engine]:
                lines.append(f'  [{engine}] {m["name"]} ({m["size_mb"]} MB)')
        lines.append(f'总占用: {models["total_size_mb"]} MB')

        lines.append('')
        lines.append('--- 诊断摘要 ---')
        if diag['errors']:
            lines.append('错误:')
            for e in diag['errors']:
                lines.append(f'  - {e}')
        if diag['warnings']:
            lines.append('警告:')
            for w in diag['warnings']:
                lines.append(f'  - {w}')
        if not diag['errors'] and not diag['warnings']:
            lines.append('一切正常')

        return '\n'.join(lines)


settings_service = SettingsService()