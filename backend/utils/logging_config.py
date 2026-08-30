"""日志配置:控制台 + RotatingFileHandler(logs/backend.log, 5MB x 3)"""
import logging
import os
import sys
from logging.handlers import RotatingFileHandler

from backend.config.settings import Config

_CONFIGURED = False


def setup_logging():
    """初始化应用日志。幂等,重复调用无副作用。"""
    global _CONFIGURED
    if _CONFIGURED:
        return

    log_dir = os.path.join(Config.BASE_DIR, 'logs')
    try:
        os.makedirs(log_dir, exist_ok=True)
        file_handler = RotatingFileHandler(
            os.path.join(log_dir, 'backend.log'),
            maxBytes=5 * 1024 * 1024,
            backupCount=3,
            encoding='utf-8'
        )
        handlers = [logging.StreamHandler(sys.stdout), file_handler]
    except OSError:
        # 日志目录不可写时仅保留控制台输出
        handlers = [logging.StreamHandler(sys.stdout)]

    logging.basicConfig(
        level=logging.DEBUG if Config.DEBUG else logging.INFO,
        format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
        handlers=handlers
    )
    # werkzeug 每个请求两行访问日志过于冗长,降低到 WARNING
    logging.getLogger('werkzeug').setLevel(logging.WARNING)
    _CONFIGURED = True
