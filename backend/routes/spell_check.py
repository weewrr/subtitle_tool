from flask import Blueprint, request, jsonify

from backend.services.spell_check_service import SpellCheckService
from backend.services.translation_service import TranslationService

spell_check_bp = Blueprint('spell_check', __name__, url_prefix='/api/spell-check')
spell_check_service = SpellCheckService()
translation_service = TranslationService()

@spell_check_bp.route('', methods=['POST'])
def check_spelling():
    data = request.get_json()
    text = data.get('text', '')
    
    if not text:
        return jsonify({'error': '请提供要检查的文本'}), 400
    
    misspelled = spell_check_service.check_spelling(text)
    return jsonify({'misspelled': misspelled})

@spell_check_bp.route('/ai', methods=['POST'])
def ai_spell_check():
    data = request.get_json()
    text = data.get('text', '')
    engine = data.get('engine', 'ollama')
    model = data.get('model', 'gemma3:1b')
    
    if not text:
        return jsonify({'error': '请提供要检查的文本'}), 400
    
    result = translation_service.translate(
        text=text,
        from_lang='',
        to_lang='',
        engine=engine,
        model=model,
        task='spell_check'
    )
    
    if result.get('error'):
        return jsonify({'error': result['error']}), 500
    
    return jsonify(result)

@spell_check_bp.route('/suggestions', methods=['POST'])
def get_spelling_suggestions():
    data = request.get_json()
    word = data.get('word', '')
    
    if not word:
        return jsonify({'error': '请提供要获取建议的单词'}), 400
    
    suggestions = spell_check_service.get_suggestions(word)
    return jsonify({'suggestions': suggestions})

@spell_check_bp.route('/dictionary/add', methods=['POST'])
def add_to_dictionary():
    data = request.get_json()
    word = data.get('word', '')
    
    if not word:
        return jsonify({'error': '请提供要添加的单词'}), 400
    
    success = spell_check_service.add_to_user_dictionary(word)
    return jsonify({'success': success})

@spell_check_bp.route('/dictionary/remove', methods=['POST'])
def remove_from_dictionary():
    data = request.get_json()
    word = data.get('word', '')
    
    if not word:
        return jsonify({'error': '请提供要移除的单词'}), 400
    
    success = spell_check_service.remove_from_user_dictionary(word)
    return jsonify({'success': success})

@spell_check_bp.route('/names/add', methods=['POST'])
def add_to_names():
    data = request.get_json()
    name = data.get('name', '')
    
    if not name:
        return jsonify({'error': '请提供要添加的人名'}), 400
    
    success = spell_check_service.add_to_name_list(name)
    return jsonify({'success': success})

@spell_check_bp.route('/names/remove', methods=['POST'])
def remove_from_names():
    data = request.get_json()
    name = data.get('name', '')
    
    if not name:
        return jsonify({'error': '请提供要移除的人名'}), 400
    
    success = spell_check_service.remove_from_name_list(name)
    return jsonify({'success': success})

@spell_check_bp.route('/dictionary', methods=['GET'])
def get_dictionary():
    dictionary = spell_check_service.get_user_dictionary()
    return jsonify({'dictionary': dictionary})

@spell_check_bp.route('/names', methods=['GET'])
def get_names():
    names = spell_check_service.get_name_list()
    return jsonify({'names': names})
