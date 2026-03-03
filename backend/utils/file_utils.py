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
