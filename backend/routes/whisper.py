import os
import subprocess
import platform
from flask import Blueprint, request, jsonify

from backend.config.settings import Config
from backend.services.whisper_service import WhisperModelService
from backend.services.whisper_cpp_service import WhisperCppService
from backend.services.whisper_ctranslate2_service import WhisperCTranslate2Service

whisper_bp = Blueprint('whisper', __name__, url_prefix='/api/models')
whisper_service = WhisperModelService()
whisper_cpp_service = WhisperCppService()
whisper_ctranslate2_service = WhisperCTranslate2Service()

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
    cache_dir = Config.WHISPER_CACHE_DIR
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

# Whisper.cpp 模型管理
@whisper_bp.route('/whisper-cpp/list', methods=['GET'])
def list_whisper_cpp_models():
    return jsonify(whisper_cpp_service.list_all_models())

@whisper_bp.route('/whisper-cpp/download', methods=['POST'])
def download_whisper_cpp_model():
    data = request.get_json()
    model_name = data.get('model', 'ggml-base')
    result = whisper_cpp_service.download_model(model_name)
    
    if 'error' in result:
        return jsonify(result), 400
    return jsonify(result)

@whisper_bp.route('/whisper-cpp/status', methods=['GET'])
def get_whisper_cpp_model_status():
    return jsonify(whisper_cpp_service.get_status())

# Whisper-CTranslate2 模型管理
@whisper_bp.route('/whisper-ctranslate2/list', methods=['GET'])
def list_whisper_ctranslate2_models():
    return jsonify(whisper_ctranslate2_service.list_all_models())

@whisper_bp.route('/whisper-ctranslate2/download', methods=['POST'])
def download_whisper_ctranslate2_model():
    data = request.get_json()
    model_name = data.get('model', 'base')
    result = whisper_ctranslate2_service.download_model(model_name)
    
    if 'error' in result:
        return jsonify(result), 400
    return jsonify(result)

@whisper_bp.route('/whisper-ctranslate2/status', methods=['GET'])
def get_whisper_ctranslate2_model_status():
    return jsonify(whisper_ctranslate2_service.get_status())

@whisper_bp.route('/whisper-ctranslate2/reset', methods=['POST'])
def reset_whisper_ctranslate2_model_status():
    whisper_ctranslate2_service._reset_status()
    return jsonify({'message': '状态已重置'})
