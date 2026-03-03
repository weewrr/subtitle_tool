import os
from flask import Blueprint, request, send_file, jsonify

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

@video_bp.route('/serve', methods=['GET'])
def serve_video():
    file_path = request.args.get('path')
    if not file_path:
        return jsonify({'error': '请提供文件路径'}), 400
    
    if not os.path.exists(file_path):
        return jsonify({'error': '文件不存在'}), 404
    
    try:
        ext = os.path.splitext(file_path)[1].lower()
        mimetype = VIDEO_MIME_TYPES.get(ext, 'application/octet-stream')
        return send_file(file_path, mimetype=mimetype)
    except Exception as e:
        return jsonify({'error': str(e)}), 500
