from flask import Flask
from flask_cors import CORS

# CORS 放行范围:
# - 本机任意端口 http(s) 源(浏览器开发模式 Vite dev server 等)
# - app:// 源(Electron 生产模式渲染进程,标准+secure 协议)
# 不再放行 *,防止外部网页直接调用 localhost 后端接口。
_ALLOWED_ORIGIN_PATTERNS = [
    r'^https?://(localhost|127\.0\.0\.1|\[::1\])(:\d+)?$',
    r'^app://.*$',
]

from backend.config.settings import Config
from backend.utils.logging_config import setup_logging
from backend.utils.response import install_unified_response

setup_logging()
from backend.routes import (
    whisper_bp,
    vosk_bp,
    transcription_bp,
    subtitle_bp,
    translation_bp,
    spell_check_bp,
    hard_subtitle_bp,
    waveform_bp,
    tts_bp,
    video_bp,
    settings_bp,
    tts_video_bp
)

def create_app():
    app = Flask(__name__)

    # 上传大小上限:超限返回 413(由统一异常处理器转为 JSON),防止磁盘被写满
    app.config['MAX_CONTENT_LENGTH'] = Config.MAX_UPLOAD_SIZE

    CORS(app, resources={r"/api/*": {"origins": _ALLOWED_ORIGIN_PATTERNS}})

    # 所有 /api/* JSON 响应统一包装为 {success, data, error_code, message}
    install_unified_response(app)

    # 启动时清理 Temp 目录中的过期文件（>24h），并每 6 小时定期清理
    from backend.utils.temp_dir import cleanup_temp_dir
    cleanup_temp_dir()

    import threading

    def _periodic_cleanup():
        import time
        while True:
            time.sleep(6 * 3600)
            cleanup_temp_dir()

    threading.Thread(target=_periodic_cleanup, daemon=True).start()

    app.register_blueprint(whisper_bp)
    app.register_blueprint(vosk_bp)
    app.register_blueprint(transcription_bp)
    app.register_blueprint(subtitle_bp)
    app.register_blueprint(translation_bp)
    app.register_blueprint(spell_check_bp)
    app.register_blueprint(hard_subtitle_bp)
    app.register_blueprint(waveform_bp)
    app.register_blueprint(tts_bp)
    app.register_blueprint(video_bp)
    app.register_blueprint(settings_bp)
    app.register_blueprint(tts_video_bp)

    return app
