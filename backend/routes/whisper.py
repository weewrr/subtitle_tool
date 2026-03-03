import os
import subprocess
import platform
from flask import Blueprint, request, jsonify

from backend.services.whisper_service import WhisperModelService

whisper_bp = Blueprint('whisper', __name__, url_prefix='/api/models')
whisper_service = WhisperModelService()

@whisper_bp.route('/download', methods=['POST'])
def download_model():
    data = request.get_json()
    model_name = data.get('model', 'base')
    result = whisper_service.download_model(model_name)
    
    if 'error' in result:
        return jsonify(result), 400
    return jsonify(result)

@whisper_bp.route('/status', methods=['GET'])
def get_download_status():
    return jsonify(whisper_service.get_status())

@whisper_bp.route('/list', methods=['GET'])
def list_models():
    return jsonify(whisper_service.list_all_models())

@whisper_bp.route('/downloaded', methods=['GET'])
def list_downloaded_models():
    return jsonify(whisper_service.get_downloaded_models())

@whisper_bp.route('/open-folder', methods=['POST'])
def open_model_folder():
    cache_dir = os.path.join(os.path.expanduser("~"), ".cache", "whisper")
    os.makedirs(cache_dir, exist_ok=True)
    try:
        if platform.system() == 'Windows':
            subprocess.run(['explorer', cache_dir])
        elif platform.system() == 'Darwin':
            subprocess.run(['open', cache_dir])
        else:
            subprocess.run(['xdg-open', cache_dir])
        return jsonify({'message': '已打开模型文件夹'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500
