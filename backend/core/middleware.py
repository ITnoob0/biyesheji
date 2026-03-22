from __future__ import annotations

import logging
import uuid

from django.http import JsonResponse
from django.utils.deprecation import MiddlewareMixin

from .api_errors import build_api_error_payload


logger = logging.getLogger(__name__)


class RequestIdMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        request.request_id = request.headers.get("X-Request-ID") or uuid.uuid4().hex[:12]
        response = self.get_response(request)
        response["X-Request-ID"] = request.request_id
        return response


class ApiExceptionMiddleware(MiddlewareMixin):
    def process_exception(self, request, exception):
        if not request.path.startswith("/api/"):
            return None

        request_id = getattr(request, "request_id", uuid.uuid4().hex[:12])
        request.request_id = request_id
        logger.exception(
            "Unhandled API exception request_id=%s method=%s path=%s",
            request_id,
            request.method,
            request.path,
        )
        payload = build_api_error_payload(
            status_code=500,
            message="系统处理请求时出现异常，请稍后重试。",
            code="internal_server_error",
            request=request,
            next_step="请稍后重试；若持续失败，请联系管理员并提供请求编号。",
            debug_hint="当前为开发环境，请查看后端控制台堆栈并结合请求编号排查问题。",
        )
        response = JsonResponse(payload, status=500)
        response["X-Request-ID"] = request_id
        return response
