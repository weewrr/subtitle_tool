import os

class Config:
    # 服务器配置
    HOST = '127.0.0.1'
    PORT = int(os.environ.get('SUBTITLE_TOOL_BACKEND_PORT', 5000))
    DEBUG = os.environ.get('SUBTITLE_TOOL_BACKEND_DEBUG', '1') == '1'
    
    # 文件路径配置
    BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
    ORIGINAL_SUBTITLE_DIR = os.path.join(BASE_DIR, 'OriginalSubtitle')
    TRANSLATION_SUBTITLE_DIR = os.path.join(BASE_DIR, 'translatesubtitles')
    AUDIO_DIR = os.path.join(BASE_DIR, 'audio')
    
    # Whisper 配置
    WHISPER_CACHE_DIR = os.path.join(BASE_DIR, 'model', 'whisper')
    WHISPER_CPP_MODEL_DIR = os.path.join(BASE_DIR, 'model', 'whisper-cpp')
    WHISPER_CPP_DIR = os.path.join(BASE_DIR, 'Release')
    WHISPER_CPP_EXECUTABLE = os.path.join(WHISPER_CPP_DIR, 'whisper-cli.exe')
    WHISPER_CTRANSLATE2_MODEL_DIR = os.path.join(BASE_DIR, 'model', 'whisper-ctranslate2')
    VALID_MODELS = ['tiny', 'base', 'small', 'medium', 'large']
    
    # 文件格式配置
    SUPPORTED_VIDEO_FORMATS = [".mp4", ".mov", ".avi", ".mkv", ".flv", ".wmv", ".webm"]
    SUPPORTED_AUDIO_FORMATS = ['.mp3', '.wav', '.m4a', '.flac', '.ogg']
    
    @classmethod
    def ensure_directories(cls):
        """确保所有必要的目录存在"""
        for directory in [cls.ORIGINAL_SUBTITLE_DIR, cls.TRANSLATION_SUBTITLE_DIR, cls.AUDIO_DIR, cls.WHISPER_CACHE_DIR, cls.WHISPER_CPP_MODEL_DIR, cls.WHISPER_CTRANSLATE2_MODEL_DIR]:
            if not os.path.exists(directory):
                os.makedirs(directory)
