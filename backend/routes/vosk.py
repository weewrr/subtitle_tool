from flask import Blueprint, request, jsonify

from backend.services.vosk_service import VoskService

vosk_bp = Blueprint('vosk', __name__, url_prefix='/api/models/vosk')
vosk_service = VoskService()

@vosk_bp.route('/list', methods=['GET'])
def list_vosk_models():
    return jsonify(vosk_service.get_models())

@vosk_bp.route('/download', methods=['POST'])
def download_vosk_model():
    data = request.get_json()
    model_code = data.get('model_code')
    
    if not model_code:
        return jsonify({'error': '请提供模型代码'}), 400
    
    try:
        result = vosk_service.download_model(model_code)
        return jsonify({'message': result})
    except Exception as e:
        return jsonify({'error': str(e)}), 400

@vosk_bp.route('/status', methods=['GET'])
def get_vosk_download_status():
    return jsonify(vosk_service.get_download_status())
