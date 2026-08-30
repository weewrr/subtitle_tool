import json
import os
import uuid

from flask import Blueprint, request, jsonify, send_from_directory

from backend.services.hard_subtitle_service import hard_subtitle_service
from backend.utils.response import fail
from backend.utils.temp_dir import get_temp_dir

hard_subtitle_bp = Blueprint('hard_subtitle', __name__, url_prefix='/api/hard-subtitle')


def _submit_job(video_path, subtitle_data, config_data):
    output_path = os.path.join(get_temp_dir(), f"{uuid.uuid4()}.mp4")
    result = hard_subtitle_service.generate_hard_subtitle(
        video_path, subtitle_data, output_path, config_data
    )
    return jsonify(result), 202


@hard_subtitle_bp.route('/generate', methods=['POST'])
def generate_hard_subtitle():
    if 'video' not in request.files:
        return fail('请上传视频文件', error_code='VIDEO_REQUIRED', status=400)

    video_file = request.files['video']
    subtitle_content = request.form.get('subtitle', '[]')
    config = request.form.get('config', '{}')

    try:
        subtitle_data = json.loads(subtitle_content)
        config_data = json.loads(config)
    except json.JSONDecodeError:
        return fail('无效的 JSON 数据', error_code='INVALID_JSON', status=400)

    ext = os.path.splitext(video_file.filename or '')[1].lower()
    if ext.startswith('.') and 1 <= len(ext) <= 10 and ext[1:].isalnum():
        safe_video_suffix = ext
    else:
        safe_video_suffix = '.mp4'

    temp_dir = get_temp_dir()
    video_path = os.path.join(temp_dir, f"{uuid.uuid4()}{safe_video_suffix}")
    video_file.save(video_path)

    return _submit_job(video_path, subtitle_data, config_data)


@hard_subtitle_bp.route('/generate-from-path', methods=['POST'])
def generate_hard_subtitle_from_path():
    data = request.get_json() or {}
    video_path = data.get('video_path')

    if not video_path or not os.path.exists(video_path):
        return fail('视频文件不存在', error_code='VIDEO_NOT_FOUND', status=400)

    return _submit_job(video_path, data.get('subtitle', []), data.get('config', {}))


@hard_subtitle_bp.route('/status', methods=['GET'])
def get_hard_subtitle_status():
    # task_id 可选:不传时返回最近一个任务(兼容旧前端)
    status = hard_subtitle_service.get_status(request.args.get('task_id'))
    if status is None:
        return fail('任务不存在', error_code='TASK_NOT_FOUND', status=404)
    return jsonify(status)


@hard_subtitle_bp.route('/abort', methods=['POST'])
def abort_hard_subtitle():
    data = request.get_json(silent=True) or {}
    task_id = data.get('task_id')
    if hard_subtitle_service.cancel(task_id):
        return jsonify({'status': 'cancelling'})
    return fail('没有可取消的任务', error_code='TASK_NOT_FOUND', status=404)


@hard_subtitle_bp.route('/download', methods=['GET'])
def download_hard_subtitle():
    # task_id 可选:不传时取最近完成的任务
    output_path = hard_subtitle_service.get_completed_output(request.args.get('task_id'))
    if not output_path or not os.path.exists(output_path):
        return fail('没有可下载的文件', error_code='RESULT_NOT_FOUND', status=404)

    return send_from_directory(
        os.path.dirname(output_path),
        os.path.basename(output_path),
        as_attachment=True
    )
