"""统一响应结构层

所有 /api/* 接口统一返回:
    { success: bool, data: Any, error_code: int|str, message: str }

实现方式:
1. ok() / fail() 显式构造工具,供路由直接使用(推荐,语义清晰)
2. install_unified_response(app) 全局 after_request 包装器,
   对所有未加壳的 JSON 响应自动补壳(已统一的自动透传),
   并将 /api/* 路径上的未捕获异常 / HTTPException 转为统一 JSON 错误。

SSE(text/event-stream)与文件流(send_file)不属于 JSON 契约,自动跳过。
"""
import json

from flask import jsonify, request
from werkzeug.exceptions import HTTPException

# 已视为"统一结构"的判定键(三者齐备才透传,避免误伤业务数据里偶发的 success 字段)
_UNIFIED_KEYS = ('success', 'data', 'error_code')


def ok(data=None, message='ok'):
    """成功响应(HTTP 200)"""
    return jsonify({
        'success': True,
        'data': data,
        'error_code': 0,
        'message': message
    })


def fail(message, error_code=-1, status=400, data=None):
    """失败响应,可指定 HTTP 状态码与业务错误码"""
    return jsonify({
        'success': False,
        'data': data,
        'error_code': error_code,
        'message': message
    }), status


def _is_unified(payload):
    return isinstance(payload, dict) and all(k in payload for k in _UNIFIED_KEYS)


def _wrap_success(payload):
    return {
        'success': True,
        'data': payload,
        'error_code': 0,
        'message': 'ok'
    }


def _wrap_error(payload, status_code):
    message = ''
    data = None
    if isinstance(payload, dict):
        # 兼容旧错误结构 {'error': ...} / {'message': ...}
        message = payload.get('message') or payload.get('error') or ''
        data = payload.get('data')
    return {
        'success': False,
        'data': data,
        'error_code': payload.get('error_code') if isinstance(payload, dict) and payload.get('error_code') else status_code,
        'message': message or f'请求失败 (HTTP {status_code})'
    }


def install_unified_response(app):
    """在 Flask app 上安装统一响应包装器与 API 错误处理器"""

    @app.errorhandler(HTTPException)
    def handle_http_exception(e):
        # 仅 API 路径转 JSON,静态资源 404 保持默认行为
        if not request.path.startswith('/api/'):
            return e
        return fail(
            message=e.description or e.name,
            error_code=e.code,
            status=e.code
        )

    @app.errorhandler(Exception)
    def handle_unexpected_exception(e):
        # 仅 API 路径兜底,避免吞掉静态资源异常
        if not request.path.startswith('/api/'):
            raise e
        app.logger.exception('API 未捕获异常: %s %s', request.method, request.path)
        return fail(message=f'服务器内部错误: {e}', error_code=500, status=500)

    @app.after_request
    def unify_json_response(response):
        content_type = response.content_type or ''
        if not content_type.startswith('application/json'):
            return response

        try:
            payload = response.get_json(silent=True)
        except (TypeError, ValueError):
            return response

        if payload is None or _is_unified(payload):
            return response

        if response.status_code >= 400:
            envelope = _wrap_error(payload, response.status_code)
        else:
            envelope = _wrap_success(payload)

        response.set_data(json.dumps(envelope, ensure_ascii=False))
        return response
