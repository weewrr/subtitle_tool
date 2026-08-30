from flask import Blueprint, request, jsonify

from backend.services.translation_service import TranslationService
from backend.utils.response import fail

translation_bp = Blueprint('translation', __name__, url_prefix='/api/translate')
translation_service = TranslationService()

# 同步翻译接口的兜底超时(秒)。
# 各引擎 HTTP 客户端已有 (10, 120) 超时;此值为同步路由的整体上限,
# 防止异常场景(LLM 挂起、网络黑洞)长时间占用 worker。
SYNC_TRANSLATE_TIMEOUT = 150

# 超时错误文案(引擎层无法区分,统一提示)
_TIMEOUT_MESSAGE = f'翻译请求超时(超过 {SYNC_TRANSLATE_TIMEOUT} 秒),请检查网络或改用可用的引擎'


@translation_bp.route('', methods=['POST'])
def translate_text():
    data = request.get_json()
    text = data.get('text', '')
    from_lang = data.get('from', 'en')
    to_lang = data.get('to', 'zh')
    engine = data.get('engine', 'ollama')
    model = data.get('model', 'gemma3:1b')
    prompt_template = data.get('prompt_template', None)
    duration = data.get('duration', None)
    api_key = data.get('api_key', None)
    temperature = data.get('temperature', 0.0)
    max_tokens = data.get('max_tokens', 2048)
    keep_formatting = data.get('keep_formatting', True)
    task = data.get('task', 'translate')

    if not text:
        return fail('请提供要翻译的文本', error_code='TEXT_REQUIRED', status=400)

    try:
        result = translation_service.translate(
            text, from_lang, to_lang, engine, model,
            prompt_template, temperature, max_tokens, keep_formatting, task,
            duration=duration, api_key=api_key
        )
    except TimeoutError:
        return fail(_TIMEOUT_MESSAGE, error_code='TRANSLATE_TIMEOUT', status=504)

    # 服务层失败时返回 {'translated': 原文, 'error': ...},
    # 必须以非 2xx 暴露,否则故障被伪装成"译文与原文相同"
    if result.get('error'):
        return fail(result['error'], error_code='TRANSLATE_ENGINE_ERROR', status=502)

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
        return fail('请提供要翻译的文本', error_code='TEXT_REQUIRED', status=400)

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
