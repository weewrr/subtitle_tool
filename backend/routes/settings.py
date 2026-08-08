import os
import platform
from flask import Blueprint, request, jsonify

from backend.config.settings import Config
from backend.services.settings_service import settings_service

settings_bp = Blueprint('settings', __name__, url_prefix='/api')


def make_response(success=True, data=None, error_code=None, message=''):
    """统一返回结构"""
    return jsonify({
        'success': success,
        'data': data,
        'error_code': error_code,
        'message': message
    })


# ============= 健康检查 =============

@settings_bp.route('/health', methods=['GET'])
def health_check():
    result = settings_service.health_check()
    return make_response(data=result)


# ============= 诊断 =============

@settings_bp.route('/diagnostics', methods=['GET'])
def run_diagnostics():
    try:
        result = settings_service.run_diagnostics()
        return make_response(data=result)
    except Exception as e:
        return make_response(
            success=False,
            error_code='DIAGNOSTICS_FAILED',
            message=f'运行环境诊断失败: {str(e)}'
        ), 500


@settings_bp.route('/diagnostics/text', methods=['GET'])
def get_diagnostic_text():
    try:
        text = settings_service.get_diagnostic_text()
        return make_response(data={'text': text})
    except Exception as e:
        return make_response(
            success=False,
            error_code='DIAGNOSTICS_TEXT_FAILED',
            message=f'生成诊断文本失败: {str(e)}'
        ), 500


# ============= 版本信息 =============

@settings_bp.route('/version', methods=['GET'])
def get_version_info():
    try:
        result = settings_service.get_version_info()
        return make_response(data=result)
    except Exception as e:
        return make_response(
            success=False,
            error_code='VERSION_FAILED',
            message=f'获取版本信息失败: {str(e)}'
        ), 500


# ============= 缓存管理 =============

@settings_bp.route('/cache/stats', methods=['GET'])
def get_cache_stats():
    try:
        result = settings_service.get_cache_stats()
        return make_response(data=result)
    except Exception as e:
        return make_response(
            success=False,
            error_code='CACHE_STATS_FAILED',
            message=f'获取缓存统计失败: {str(e)}'
        ), 500


@settings_bp.route('/cache/clean/audio', methods=['POST'])
def clean_temp_audio():
    try:
        result = settings_service.clean_temp_audio()
        return make_response(
            data=result,
            message=f'已清理 {result["deleted"]} 个临时音频文件'
        )
    except Exception as e:
        return make_response(
            success=False,
            error_code='CACHE_CLEAN_AUDIO_FAILED',
            message=f'清理临时音频失败: {str(e)}'
        ), 500


@settings_bp.route('/cache/clean/waveform', methods=['POST'])
def clean_waveform_cache():
    try:
        result = settings_service.clean_waveform_cache()
        return make_response(
            data=result,
            message=f'已清理 {result["deleted"]} 个波形缓存文件'
        )
    except Exception as e:
        return make_response(
            success=False,
            error_code='CACHE_CLEAN_WAVEFORM_FAILED',
            message=f'清理波形缓存失败: {str(e)}'
        ), 500


@settings_bp.route('/cache/clean/task-results', methods=['POST'])
def clean_task_results():
    try:
        result = settings_service.clean_task_results()
        return make_response(
            data=result,
            message=f'已清理 {result["deleted"]} 个任务结果文件'
        )
    except Exception as e:
        return make_response(
            success=False,
            error_code='CACHE_CLEAN_TASK_FAILED',
            message=f'清理任务结果失败: {str(e)}'
        ), 500


# ============= 目录操作 =============

@settings_bp.route('/open-directory', methods=['POST'])
def open_directory():
    data = request.get_json() or {}
    dir_type = data.get('type', 'model')

    dir_map = {
        'model': Config.WHISPER_CACHE_DIR,
        'whisper_cpp': Config.WHISPER_CPP_MODEL_DIR,
        'whisper_ctranslate2': Config.WHISPER_CTRANSLATE2_MODEL_DIR,
        'audio': Config.AUDIO_DIR,
        'temp': Config.AUDIO_DIR,
        'logs': os.path.join(Config.BASE_DIR, 'logs')
    }

    path = dir_map.get(dir_type)
    if not path:
        return make_response(
            success=False,
            error_code='INVALID_DIR_TYPE',
            message=f'无效的目录类型: {dir_type}'
        ), 400

    if not os.path.isdir(path):
        os.makedirs(path, exist_ok=True)

    success = settings_service.open_directory(path)
    if success:
        return make_response(message='已打开目录')
    else:
        return make_response(
            success=False,
            error_code='OPEN_DIR_FAILED',
            message='打开目录失败'
        ), 500


# ============= 日志目录 =============

@settings_bp.route('/open-logs', methods=['POST'])
def open_logs_directory():
    logs_dir = os.path.join(Config.BASE_DIR, 'logs')
    os.makedirs(logs_dir, exist_ok=True)
    success = settings_service.open_directory(logs_dir)
    if success:
        return make_response(message='已打开日志目录')
    else:
        return make_response(
            success=False,
            error_code='OPEN_LOGS_FAILED',
            message='打开日志目录失败'
        ), 500