import os
import uuid
from flask import Blueprint, Response, jsonify, request, stream_with_context

from backend.services.transcription_service import TranscriptionService
from backend.utils.temp_dir import get_transcription_temp_dir

transcription_bp = Blueprint('transcription', __name__, url_prefix='/api/transcribe')
transcription_service = TranscriptionService()

@transcription_bp.route('', methods=['POST'])
def transcribe_upload():
    # 支持文件上传或文件路径两种方式
    file_path = request.form.get('file_path', '')
    if file_path and os.path.isfile(file_path):
        path = file_path  # 直接使用已有路径，无需复制
    elif 'file' in request.files:
        upload_file = request.files['file']
        if not upload_file.filename:
            return jsonify({'error': '文件名不能为空'}), 400
        ext = os.path.splitext(upload_file.filename)[1].lower()
        temp_dir = get_transcription_temp_dir(); os.makedirs(temp_dir, exist_ok=True)
        path = os.path.join(temp_dir, f'{uuid.uuid4()}{ext}')
        upload_file.save(path)
    else:
        return jsonify({'error': '请上传文件或提供文件路径'}), 400

    task = transcription_service.transcribe_async(
        path,
        request.form.get('model', 'base'),
        request.form.get('language'),
        request.form.get('engine', 'openai'),
        request.form.get('use_gpu', 'true').lower() == 'true'
    )
    return jsonify(task), 202

@transcription_bp.route('/<task_id>', methods=['GET'])
def get_transcribe_status(task_id):
    status = transcription_service.get_status(task_id)
    return (jsonify(status), 200) if status else (jsonify({'error': '任务不存在'}), 404)

@transcription_bp.route('/<task_id>/result', methods=['GET'])
def get_transcribe_result(task_id):
    result = transcription_service.get_result(task_id)
    return (jsonify(result), 200) if result else (jsonify({'error': '结果尚不可用'}), 404)

@transcription_bp.route('/<task_id>/events', methods=['GET'])
def transcribe_events(task_id):
    if not transcription_service.get_status(task_id): return jsonify({'error': '任务不存在'}), 404
    response = Response(stream_with_context(transcription_service.event_stream(task_id)), mimetype='text/event-stream')
    response.headers['Cache-Control'] = 'no-cache'; response.headers['X-Accel-Buffering'] = 'no'
    return response

@transcription_bp.route('/<task_id>/cancel', methods=['POST'])
def cancel_transcription(task_id):
    return (jsonify({'status': 'cancelling'}), 202) if transcription_service.cancel(task_id) else (jsonify({'error': '任务不存在'}), 404)
