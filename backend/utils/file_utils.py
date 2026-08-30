import os

def format_file_size(size_bytes):
    """格式化文件大小"""
    if size_bytes < 1024:
        return f"{size_bytes} B"
    elif size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.1f} KB"
    elif size_bytes < 1024 * 1024 * 1024:
        return f"{size_bytes / (1024 * 1024):.1f} MB"
    else:
        return f"{size_bytes / (1024 * 1024 * 1024):.1f} GB"

def ensure_directory(directory):
    """确保目录存在"""
    if not os.path.exists(directory):
        os.makedirs(directory)
    return directory

def sanitize_filename(filename):
    """净化用户提供的文件名,防止路径遍历(../、绝对路径、盘符等)。

    保留中文等 Unicode 字符(werkzeug 的 secure_filename 会全部剔除,不适用)。
    返回 None 表示无法得到安全文件名。
    """
    if not filename or not isinstance(filename, str):
        return None
    # 统一分隔符后取最后一段,剥离任何目录成分
    name = filename.replace('\\', '/').rsplit('/', 1)[-1].strip()
    # 过滤 Windows 保留字符与控制字符,拒绝 . / .. 等特殊名
    name = ''.join(ch for ch in name if ord(ch) >= 32 and ch not in '<>:"|?*')
    if name in ('', '.', '..'):
        return None
    return name

def get_file_extension(filename):
    """获取文件扩展名"""
    return os.path.splitext(filename)[1].lower()

def is_video_file(filename):
    """检查是否为视频文件"""
    from backend.config.settings import Config
    return get_file_extension(filename) in Config.SUPPORTED_VIDEO_FORMATS

def is_audio_file(filename):
    """检查是否为音频文件"""
    from backend.config.settings import Config
    return get_file_extension(filename) in Config.SUPPORTED_AUDIO_FORMATS
