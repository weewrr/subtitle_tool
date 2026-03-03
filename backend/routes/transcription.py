import os
import uuid
import threading
from flask import Blueprint, request, jsonify

from backend.services.transcription_service import TranscriptionService
from backend.utils.temp_dir import get_transcription_temp_dir

transcription_bp = Blueprint('transcription', __name__, url_prefix='/api/transcribe')
transcription_service = TranscriptionService()

@transcription_bp.route('/start', methods=['POST'])
def start_transcribe():
    data = request.get_json()
    video_path = data.get('video_path')
    model_name = data.get('model', 'base')
    language = data.get('language', None)
    
    if not video_path:
        return jsonify({'error': '请提供视频路径'}), 400
    
    if not os.path.exists(video_path):
        return jsonify({'error': f'文件不存在: {video_path}'}), 400
    
    result = transcription_service.transcribe_async(video_path, model_name, language)
    
    if 'error' in result:
        return jsonify(result), 400
    return jsonify(result)

@transcription_bp.route('/status', methods=['GET'])
def get_transcribe_status():
    return jsonify(transcription_service.get_status())

@transcription_bp.route('/result', methods=['GET'])
def get_transcribe_result():
    result = transcription_service.get_result()
    if result:
        return jsonify(result)
    return jsonify({'error': '没有可用的结果'}), 404

@transcription_bp.route('', methods=['POST'])
def transcribe_upload():
    if 'file' not in request.files:
        return jsonify({'error': '请上传文件'}), 400
    
    upload_file = request.files['file']
    model_name = request.form.get('model', 'base')
    language = request.form.get('language', None)
    engine = request.form.get('engine', 'openai')
    
    ext = os.path.splitext(upload_file.filename)[1].lower()
    tmp_path = os.path.join(get_transcription_temp_dir(), f"{uuid.uuid4()}{ext}")
    upload_file.save(tmp_path)
    
    transcription_service.transcribe_async(tmp_path, model_name, language, engine)
    
    return jsonify({'status': 'started', 'message': '转录任务已启动'})

@transcription_bp.route('/abort', methods=['POST'])
def abort_transcribe():
    transcription_service.abort()
    return jsonify({'status': 'aborted'})
