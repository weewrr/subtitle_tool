import os
import uuid
import threading
from flask import Blueprint, request, jsonify

from backend.services.transcription_service import TranscriptionService
from backend.utils.temp_dir import get_transcription_temp_dir

transcription_bp = Blueprint('transcription', __name__, url_prefix='/api/transcribe')
transcription_service = TranscriptionService()

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
    use_gpu = request.form.get('use_gpu', 'true').lower() == 'true'
    
    ext = os.path.splitext(upload_file.filename)[1].lower()
    temp_dir = get_transcription_temp_dir()
    tmp_path = os.path.join(temp_dir, f"{uuid.uuid4()}{ext}")
    
    os.makedirs(temp_dir, exist_ok=True)
    upload_file.save(tmp_path)
    
    if not os.path.exists(tmp_path):
        return jsonify({'error': '文件保存失败'}), 500
    
    transcription_service.transcribe_async(tmp_path, model_name, language, engine, use_gpu)
    
    return jsonify({'status': 'started', 'message': '转录任务已启动'})
