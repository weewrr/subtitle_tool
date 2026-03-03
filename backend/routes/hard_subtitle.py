import os
import json
import uuid
from flask import Blueprint, request, jsonify, send_from_directory

from backend.services.hard_subtitle_service import hard_subtitle_service
from backend.utils.temp_dir import get_temp_dir

hard_subtitle_bp = Blueprint('hard_subtitle', __name__, url_prefix='/api/hard-subtitle')

@hard_subtitle_bp.route('/generate', methods=['POST'])
def generate_hard_subtitle():
    if 'video' not in request.files:
        return jsonify({'error': '请上传视频文件'}), 400
    
    video_file = request.files['video']
    subtitle_content = request.form.get('subtitle', '[]')
    config = request.form.get('config', '{}')
    
    try:
        subtitle_data = json.loads(subtitle_content)
        config_data = json.loads(config)
    except json.JSONDecodeError:
        return jsonify({'error': '无效的 JSON 数据'}), 400
    
    ext = os.path.splitext(video_file.filename or '')[1].lower()
    if ext.startswith('.') and 1 <= len(ext) <= 10 and ext[1:].isalnum():
        safe_video_suffix = ext
    else:
        safe_video_suffix = '.mp4'

    temp_dir = get_temp_dir()
    video_path = os.path.join(temp_dir, f"{uuid.uuid4()}{safe_video_suffix}")
    video_file.save(video_path)
    
    output_path = os.path.join(temp_dir, f"{uuid.uuid4()}.mp4")
    
    def progress_callback(info):
        pass
    
    result = hard_subtitle_service.generate_hard_subtitle(
        video_path, subtitle_data, output_path, config_data, progress_callback
    )
    
    return jsonify(result)

@hard_subtitle_bp.route('/generate-from-path', methods=['POST'])
def generate_hard_subtitle_from_path():
    data = request.get_json()
    if not data or 'video_path' not in data:
        return jsonify({'error': '请提供视频文件路径'}), 400
    
    video_path = data['video_path']
    subtitle_data = data.get('subtitle', [])
    config_data = data.get('config', {})
    
    if not os.path.exists(video_path):
        return jsonify({'error': '视频文件不存在'}), 400
    
    temp_dir = get_temp_dir()
    output_path = os.path.join(temp_dir, f"{uuid.uuid4()}.mp4")
    
    def progress_callback(info):
        pass
    
    result = hard_subtitle_service.generate_hard_subtitle(
        video_path, subtitle_data, output_path, config_data, progress_callback
    )
    
    return jsonify(result)

@hard_subtitle_bp.route('/status', methods=['GET'])
def get_hard_subtitle_status():
    return jsonify(hard_subtitle_service.get_status())

@hard_subtitle_bp.route('/abort', methods=['POST'])
def abort_hard_subtitle():
    hard_subtitle_service.abort()
    return jsonify({'status': 'aborted'})

@hard_subtitle_bp.route('/download', methods=['GET'])
def download_hard_subtitle():
    status = hard_subtitle_service.get_status()
    if status.get('status') != 'completed' or not status.get('output_path'):
        return jsonify({'error': '没有可下载的文件'}), 404
    
    output_path = status['output_path']
    if not os.path.exists(output_path):
        return jsonify({'error': '文件不存在'}), 404
    
    return send_from_directory(
        os.path.dirname(output_path),
        os.path.basename(output_path),
        as_attachment=True
    )
