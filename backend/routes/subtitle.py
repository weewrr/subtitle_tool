from flask import Blueprint, request, jsonify

from backend.services.subtitle_service import SubtitleFileService

subtitle_bp = Blueprint('subtitle', __name__, url_prefix='/api/subtitle')

@subtitle_bp.route('/save-original', methods=['POST'])
def save_original_subtitle():
    data = request.get_json()
    srt_content = data.get('srt', '')
    filename = data.get('filename', 'untitled.srt')
    overwrite = data.get('overwrite', False)
    
    result = SubtitleFileService.save_original_subtitle(srt_content, filename, overwrite)
    
    if 'error' in result:
        return jsonify(result), 400
    return jsonify(result)

@subtitle_bp.route('/save-translation', methods=['POST'])
def save_translation_subtitle():
    data = request.get_json()
    srt_content = data.get('srt', '')
    filename = data.get('filename', 'translation.srt')
    overwrite = data.get('overwrite', False)
    
    result = SubtitleFileService.save_translation_subtitle(srt_content, filename, overwrite)
    
    if 'error' in result:
        return jsonify(result), 400
    return jsonify(result)

@subtitle_bp.route('/auto-save', methods=['POST'])
def auto_save_subtitle():
    data = request.get_json()
    srt_content = data.get('srt', '')
    filename = data.get('filename', 'autosave.srt')
    
    result = SubtitleFileService.auto_save_subtitle(srt_content, filename)
    
    if 'error' in result:
        return jsonify(result), 400
    return jsonify(result)
