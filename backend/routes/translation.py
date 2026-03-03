from flask import Blueprint, request, jsonify

from backend.services.translation_service import TranslationService

translation_bp = Blueprint('translation', __name__, url_prefix='/api/translate')
translation_service = TranslationService()

@translation_bp.route('', methods=['POST'])
def translate_text():
    data = request.get_json()
    text = data.get('text', '')
    from_lang = data.get('from', 'en')
    to_lang = data.get('to', 'zh')
    engine = data.get('engine', 'ollama')
    model = data.get('model', 'gemma3:1b')
    prompt_template = data.get('prompt_template', None)
    temperature = data.get('temperature', 0.0)
    max_tokens = data.get('max_tokens', 2048)
    keep_formatting = data.get('keep_formatting', True)
    task = data.get('task', 'translate')
    
    if not text:
        return jsonify({'error': '请提供要翻译的文本'}), 400
    
    result = translation_service.translate(text, from_lang, to_lang, engine, model,
                                          prompt_template, temperature, max_tokens, keep_formatting, task)
    return jsonify(result)

@translation_bp.route('/async', methods=['POST'])
def translate_async():
    data = request.get_json()
    text = data.get('text', '')
    from_lang = data.get('from', 'en')
    to_lang = data.get('to', 'zh')
    engine = data.get('engine', 'ollama')
    model = data.get('model', 'gemma3:1b')
    
    if not text:
        return jsonify({'error': '请提供要翻译的文本'}), 400
    
    result = translation_service.translate_async(text, from_lang, to_lang, engine, model)
    
    if 'error' in result:
        return jsonify(result), 400
    return jsonify(result)

@translation_bp.route('/status', methods=['GET'])
def get_translate_status():
    return jsonify(translation_service.get_status())

@translation_bp.route('/result', methods=['GET'])
def get_translate_result():
    result = translation_service.get_result()
    if result:
        return jsonify(result)
    return jsonify({'error': '没有可用的结果'}), 404
