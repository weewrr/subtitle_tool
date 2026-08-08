import os
import uuid
from flask import Blueprint, request, jsonify, send_from_directory

from backend.services.tts_video_service import tts_video_service
from backend.utils.temp_dir import get_temp_dir

tts_video_bp = Blueprint('tts_video', __name__, url_prefix='/api/tts-video')


@tts_video_bp.route('/generate', methods=['POST'])
def generate_tts_video():
    """合并 TTS 配音到视频。
    支持文件路径（Electron）或文件上传（浏览器）两种方式。
    """
    video_path = request.form.get('video_path', '')
    audio_path = request.form.get('audio_path', '')

    # 视频文件：优先使用路径，否则从上传读取
    if not (video_path and os.path.isfile(video_path)):
        if 'video' in request.files:
            video_file = request.files['video']
            if not video_file.filename:
                return jsonify({'error': '视频文件名不能为空'}), 400
            ext = os.path.splitext(video_file.filename)[1].lower()
            temp_dir = get_temp_dir()
            os.makedirs(temp_dir, exist_ok=True)
            video_path = os.path.join(temp_dir, f'{uuid.uuid4()}{ext}')
            video_file.save(video_path)
        else:
            return jsonify({'error': '请提供视频文件或路径'}), 400

    # 音频文件：优先使用路径，否则从上传读取
    if not (audio_path and os.path.isfile(audio_path)):
        if 'audio' in request.files:
            audio_file = request.files['audio']
            if not audio_file.filename:
                return jsonify({'error': '音频文件名不能为空'}), 400
            ext = os.path.splitext(audio_file.filename)[1].lower()
            temp_dir = get_temp_dir()
            os.makedirs(temp_dir, exist_ok=True)
            audio_path = os.path.join(temp_dir, f'{uuid.uuid4()}{ext}')
            audio_file.save(audio_path)
        else:
            return jsonify({'error': '请提供配音音频文件或路径'}), 400

    temp_dir = get_temp_dir()
    output_path = os.path.join(temp_dir, f"{uuid.uuid4()}.mp4")

    result = tts_video_service.generate(video_path, audio_path, output_path)
    return jsonify(result)


@tts_video_bp.route('/status', methods=['GET'])
def get_tts_video_status():
    return jsonify(tts_video_service.get_status())


@tts_video_bp.route('/abort', methods=['POST'])
def abort_tts_video():
    tts_video_service.abort()
    return jsonify({'status': 'aborted'})


@tts_video_bp.route('/download', methods=['GET'])
def download_tts_video():
    status = tts_video_service.get_status()
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
