import os
from urllib.parse import urlparse

from flask import Blueprint, request, send_file

from backend.utils.response import fail

video_bp = Blueprint('video', __name__, url_prefix='/api/video')

VIDEO_MIME_TYPES = {
    '.mp4': 'video/mp4',
    '.avi': 'video/x-msvideo',
    '.mkv': 'video/x-matroska',
    '.mov': 'video/quicktime',
    '.wmv': 'video/x-ms-wmv',
    '.flv': 'video/x-flv',
    '.webm': 'video/webm',
    '.mp3': 'audio/mpeg',
    '.wav': 'audio/wav',
    '.ogg': 'audio/ogg',
    '.flac': 'audio/flac',
    '.aac': 'audio/aac',
    '.m4a': 'audio/mp4',
    '.wma': 'audio/x-ms-wma'
}

# 本地开发源(Vite dev server 等)。浏览器版生产模式与后端同源,无需 CORS;
# 仅回显本机 Origin,拒绝任意外部网站借 localhost 后端读取本地媒体。
_LOCAL_HOSTNAMES = {'localhost', '127.0.0.1', '[::1]', '::1'}


def _is_local_origin(origin):
    if not origin:
        return False
    try:
        parsed = urlparse(origin)
    except ValueError:
        return False
    return parsed.hostname in _LOCAL_HOSTNAMES


@video_bp.after_request
def add_cors_headers(response):
    # 跨域媒体接入 Web Audio(MediaElementAudioSource)时,
    # 缺少 CORS 头会被浏览器安全策略强制输出静音(zeroes)。
    # 仅放行本机 Origin(开发期 Vite dev server),不对外部网站开放。
    origin = request.headers.get('Origin')
    if origin and _is_local_origin(origin):
        response.headers['Access-Control-Allow-Origin'] = origin
        response.headers['Vary'] = 'Origin'
    return response


@video_bp.route('/serve', methods=['GET'])
def serve_video():
    file_path = request.args.get('path')
    if not file_path:
        return fail('请提供文件路径', error_code='VIDEO_PATH_REQUIRED', status=400)

    # 扩展名白名单:只允许媒体文件,防止借本接口读取任意本地文件(源码、密钥等)
    ext = os.path.splitext(file_path)[1].lower()
    if ext not in VIDEO_MIME_TYPES:
        return fail(f'不支持的媒体格式: {ext or "(无扩展名)"}', error_code='VIDEO_FORMAT_NOT_ALLOWED', status=400)

    if not os.path.isfile(file_path):
        return fail('文件不存在', error_code='VIDEO_NOT_FOUND', status=404)

    try:
        return send_file(file_path, mimetype=VIDEO_MIME_TYPES[ext], conditional=True)
    except OSError as e:
        return fail(f'读取文件失败: {e}', error_code='VIDEO_READ_FAILED', status=500)
