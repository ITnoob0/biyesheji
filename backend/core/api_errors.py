from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from django.conf import settings
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import exception_handler as drf_exception_handler


DEFAULT_MESSAGES = {
    status.HTTP_400_BAD_REQUEST: "请求参数校验未通过，请检查后重试。",
    status.HTTP_401_UNAUTHORIZED: "登录状态无效或已过期，请重新登录。",
    status.HTTP_403_FORBIDDEN: "当前账号没有权限执行此操作。",
    status.HTTP_404_NOT_FOUND: "目标资源不存在或已被删除。",
    status.HTTP_500_INTERNAL_SERVER_ERROR: "系统处理请求时出现异常，请稍后重试。",
}

DEFAULT_NEXT_STEPS = {
    status.HTTP_400_BAD_REQUEST: "请检查输入内容后重试。",
    status.HTTP_401_UNAUTHORIZED: "请重新登录后再继续操作。",
    status.HTTP_403_FORBIDDEN: "请确认当前身份权限或切换账号后重试。",
    status.HTTP_404_NOT_FOUND: "请确认目标数据是否存在。",
    status.HTTP_500_INTERNAL_SERVER_ERROR: "请稍后重试；若持续失败，请联系管理员并提供请求编号。",
}


def _coerce_text(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value.strip()
    return str(value).strip()


def _extract_first_message(data: Any) -> str:
    if isinstance(data, str):
        return _coerce_text(data)

    if isinstance(data, list):
        for item in data:
            message = _extract_first_message(item)
            if message:
                return message
        return ""

    if isinstance(data, Mapping):
        if "error" in data and isinstance(data["error"], Mapping):
            error_message = _extract_first_message(data["error"].get("message"))
            if error_message:
                return error_message

        if "detail" in data:
            detail_message = _extract_first_message(data["detail"])
            if detail_message:
                return detail_message

        if "non_field_errors" in data:
            non_field_message = _extract_first_message(data["non_field_errors"])
            if non_field_message:
                return non_field_message

        for key, value in data.items():
            if key in {"detail", "error", "request_id", "status_code"}:
                continue
            message = _extract_first_message(value)
            if message:
                return message

    return ""


def _normalize_field_errors(data: Any) -> dict[str, list[str]]:
    if not isinstance(data, Mapping):
        return {}

    field_errors: dict[str, list[str]] = {}
    for key, value in data.items():
        if key in {"detail", "error", "request_id", "status_code"}:
            continue

        if isinstance(value, list):
            normalized = [_coerce_text(item) for item in value if _coerce_text(item)]
        else:
            text = _coerce_text(value)
            normalized = [text] if text else []

        if normalized:
            field_errors[str(key)] = normalized

    return field_errors


def _resolve_request_id(request: Any | None) -> str:
    return _coerce_text(getattr(request, "request_id", "")) or "unknown"


def _resolve_error_code(exc: Exception) -> str:
    get_codes = getattr(exc, "get_codes", None)
    if callable(get_codes):
        codes = get_codes()
        if isinstance(codes, str) and codes.strip():
            return codes.strip()

    return _coerce_text(getattr(exc, "default_code", "")) or "api_error"


def build_api_error_payload(
    *,
    status_code: int,
    message: str,
    code: str,
    request: Any | None = None,
    next_step: str | None = None,
    field_errors: dict[str, list[str]] | None = None,
    debug_hint: str | None = None,
) -> dict[str, Any]:
    request_id = _resolve_request_id(request)
    normalized_message = _coerce_text(message) or DEFAULT_MESSAGES.get(status_code, DEFAULT_MESSAGES[500])
    normalized_next_step = _coerce_text(next_step) or DEFAULT_NEXT_STEPS.get(
        status_code,
        DEFAULT_NEXT_STEPS[status.HTTP_500_INTERNAL_SERVER_ERROR],
    )

    payload: dict[str, Any] = {
        "success": False,
        "detail": normalized_message,
        "request_id": request_id,
        "error": {
            "code": _coerce_text(code) or "api_error",
            "message": normalized_message,
            "status": status_code,
            "recoverable": status_code < 500,
            "next_step": normalized_next_step,
            "request_id": request_id,
        },
    }

    if field_errors:
        payload["field_errors"] = field_errors
        payload["error"]["field_errors"] = field_errors
        payload.update(field_errors)

    if settings.DEBUG and debug_hint:
        payload["error"]["debug_hint"] = _coerce_text(debug_hint)

    return payload


def api_error_response(
    *,
    status_code: int,
    message: str,
    code: str,
    request: Any | None = None,
    next_step: str | None = None,
    field_errors: dict[str, list[str]] | None = None,
    debug_hint: str | None = None,
) -> Response:
    return Response(
        build_api_error_payload(
            status_code=status_code,
            message=message,
            code=code,
            request=request,
            next_step=next_step,
            field_errors=field_errors,
            debug_hint=debug_hint,
        ),
        status=status_code,
    )


def custom_exception_handler(exc: Exception, context: dict[str, Any]) -> Response | None:
    response = drf_exception_handler(exc, context)
    if response is None:
        return None

    request = context.get("request")
    status_code = response.status_code
    response_data = response.data

    response.data = build_api_error_payload(
        status_code=status_code,
        message=_extract_first_message(response_data) or DEFAULT_MESSAGES.get(status_code, DEFAULT_MESSAGES[500]),
        code=_resolve_error_code(exc),
        request=request,
        next_step=DEFAULT_NEXT_STEPS.get(status_code),
        field_errors=_normalize_field_errors(response_data),
        debug_hint="当前为开发环境，请查看后端控制台日志并结合请求编号排查问题。",
    )
    return response
