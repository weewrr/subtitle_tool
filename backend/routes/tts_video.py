import os
import uuid

from flask import Blueprint, request, jsonify, send_from_directory

from backend.services.tts_video_service import tts_video_service
from backend.utils.response import fail
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
                return fail('视频文件名不能为空', error_code='VIDEO_NAME_REQUIRED', status=400)
            ext = os.path.splitext(video_file.filename)[1].lower()
            temp_dir = get_temp_dir()
            video_path = os.path.join(temp_dir, f'{uuid.uuid4()}{ext}')
            video_file.save(video_path)
        else:
            return fail('请提供视频文件或路径', error_code='VIDEO_REQUIRED', status=400)

    # 音频文件：优先使用路径，否则从上传读取
    if not (audio_path and os.path.isfile(audio_path)):
        if 'audio' in request.files:
            audio_file = request.files['audio']
            if not audio_file.filename:
                return fail('音频文件名不能为空', error_code='AUDIO_NAME_REQUIRED', status=400)
            ext = os.path.splitext(audio_file.filename)[1].lower()
            temp_dir = get_temp_dir()
            audio_path = os.path.join(temp_dir, f'{uuid.uuid4()}{ext}')
            audio_file.save(audio_path)
        else:
            return fail('请提供配音音频文件或路径', error_code='AUDIO_REQUIRED', status=400)

    temp_dir = get_temp_dir()
    output_path = os.path.join(temp_dir, f"{uuid.uuid4()}.mp4")

    result = tts_video_service.generate(video_path, audio_path, output_path)
    return jsonify(result), 202


@tts_video_bp.route('/status', methods=['GET'])
def get_tts_video_status():
    # task_id 可选:不传时返回最近一个任务(兼容旧前端)
    status = tts_video_service.get_status(request.args.get('task_id'))
    if status is None:
        return fail('任务不存在', error_code='TASK_NOT_FOUND', status=404)
    return jsonify(status)


@tts_video_bp.route('/abort', methods=['POST'])
def abort_tts_video():
    data = request.get_json(silent=True) or {}
    task_id = data.get('task_id')
    if tts_video_service.cancel(task_id):
        return jsonify({'status': 'cancelling'})
    return fail('没有可取消的任务', error_code='TASK_NOT_FOUND', status=404)


@tts_video_bp.route('/download', methods=['GET'])
def download_tts_video():
    # task_id 可选:不传时取最近完成的任务
    output_path = tts_video_service.get_completed_output(request.args.get('task_id'))
    if not output_path or not os.path.exists(output_path):
        return fail('没有可下载的文件', error_code='RESULT_NOT_FOUND', status=404)

    return send_from_directory(
        os.path.dirname(output_path),
        os.path.basename(output_path),
        as_attachment=True
    )
