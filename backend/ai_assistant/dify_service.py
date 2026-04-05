import json
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from django.conf import settings


class DifyAssistantService:
    @staticmethod
    def _build_disabled_payload(message: str) -> dict:
        return {
            'status': 'fallback',
            'assistant_mode': 'dify-proxy',
            'answer': 'AI 助手暂未完成配置，请联系管理员补充 Dify 地址与密钥后再试。',
            'conversation_id': '',
            'model': 'dify-unconfigured',
            'question': message,
            'error': 'dify_not_configured',
        }

    @staticmethod
    def _base_url() -> str:
        base_url = (getattr(settings, 'DIFY_BASE_URL', '') or '').strip().rstrip('/')
        return base_url

    @classmethod
    def _chat_endpoint(cls) -> str:
        base_url = cls._base_url()
        return f'{base_url}/chat-messages' if base_url else ''

    @classmethod
    def _workflow_endpoint(cls) -> str:
        base_url = cls._base_url()
        return f'{base_url}/workflows/run' if base_url else ''

    @staticmethod
    def _post_json(*, endpoint: str, api_key: str, timeout: int, payload: dict) -> dict:
        request = Request(
            endpoint,
            data=json.dumps(payload).encode('utf-8'),
            headers={
                'Authorization': f'Bearer {api_key}',
                'Content-Type': 'application/json',
                'Accept': 'application/json',
                # Dify Cloud may be protected by WAF/Cloudflare rules that block default urllib UA.
                'User-Agent': 'BiShe-Dify-Proxy/1.0 (+https://api.dify.ai)',
            },
            method='POST',
        )
        with urlopen(request, timeout=timeout) as response:
            body = response.read().decode('utf-8')
        return json.loads(body) if body else {}

    @staticmethod
    def _resolve_current_page(route_path: str, context_hint: str) -> str:
        source = (route_path or context_hint or '').lower()
        if 'project-recommendations/preparation' in source:
            return 'project-preparation'
        if 'project-recommendations' in source:
            return 'project-recommendation'
        if 'academy-dashboard' in source:
            return 'academy-dashboard'
        if 'dashboard' in source:
            return 'portrait-dashboard'
        if 'profile-editor' in source or '/entry' in source:
            return 'achievement-center'
        return 'general'

    @staticmethod
    def _extract_workflow_answer(data: dict) -> str:
        # Workflow blocking mode usually returns answer in data.outputs, key name depends on End node variable.
        payload = data.get('data') if isinstance(data.get('data'), dict) else {}
        outputs = payload.get('outputs')

        if isinstance(outputs, dict):
            for key in ('output', 'answer', 'text', 'result'):
                value = outputs.get(key)
                if isinstance(value, str) and value.strip():
                    return value
            for value in outputs.values():
                if isinstance(value, str) and value.strip():
                    return value
            if outputs:
                return json.dumps(outputs, ensure_ascii=False)

        if isinstance(outputs, str) and outputs.strip():
            return outputs

        for key in ('answer', 'output', 'text', 'result'):
            value = data.get(key)
            if isinstance(value, str) and value.strip():
                return value
        return ''

    @classmethod
    def chat(
        cls,
        *,
        user,
        message: str,
        conversation_id: str = '',
        context_hint: str = '',
        route_path: str = '',
    ) -> dict:
        chat_endpoint = cls._chat_endpoint()
        workflow_endpoint = cls._workflow_endpoint()
        api_key = (getattr(settings, 'DIFY_API_KEY', '') or '').strip()
        timeout = int(getattr(settings, 'DIFY_REQUEST_TIMEOUT', 30) or 30)

        if (not chat_endpoint and not workflow_endpoint) or not api_key:
            return cls._build_disabled_payload(message)

        chat_payload = {
            'inputs': {
                'context_hint': context_hint,
                'route_path': route_path,
                'role': 'admin' if user.is_superuser else 'teacher',
                'department': user.department or '',
                'title': user.title or '',
            },
            'query': message,
            'response_mode': 'blocking',
            'conversation_id': conversation_id or '',
            'user': f'user-{user.id}',
        }

        workflow_payload = {
            'inputs': {
                'draft': message,
                'current_role': 'admin' if user.is_superuser else 'teacher',
                'current_page': cls._resolve_current_page(route_path, context_hint),
                'page_context': context_hint or '',
                'answer_style': '简洁执行型',
                'language': '简体中文',
            },
            'response_mode': 'blocking',
            'user': f'user-{user.id}',
        }

        try:
            data = cls._post_json(
                endpoint=chat_endpoint,
                api_key=api_key,
                timeout=timeout,
                payload=chat_payload,
            )
            answer = data.get('answer') or ''
            if answer:
                return {
                    'status': 'ok',
                    'assistant_mode': 'dify-proxy',
                    'answer': answer,
                    'conversation_id': data.get('conversation_id') or conversation_id or '',
                    'model': data.get('model') or 'dify-chat',
                    'question': message,
                    'message_id': data.get('message_id') or '',
                }
        except HTTPError as exc:
            if exc.code not in (400, 404, 405):
                return {
                    'status': 'fallback',
                    'assistant_mode': 'dify-proxy',
                    'answer': 'AI 助手暂时不可用，请稍后重试。',
                    'conversation_id': conversation_id or '',
                    'model': 'dify-http-error',
                    'question': message,
                    'error': f'http_{exc.code}',
                }
        except URLError:
            return {
                'status': 'fallback',
                'assistant_mode': 'dify-proxy',
                'answer': 'AI 助手连接失败，请检查 Dify 服务状态后重试。',
                'conversation_id': conversation_id or '',
                'model': 'dify-network-error',
                'question': message,
                'error': 'network_error',
            }
        except Exception:
            return {
                'status': 'fallback',
                'assistant_mode': 'dify-proxy',
                'answer': 'AI 助手发生异常，已回退为安全提示。',
                'conversation_id': conversation_id or '',
                'model': 'dify-exception',
                'question': message,
                'error': 'unknown_error',
            }

        # Fallback path for Workflow applications (no chat-messages support).
        try:
            workflow_data = cls._post_json(
                endpoint=workflow_endpoint,
                api_key=api_key,
                timeout=timeout,
                payload=workflow_payload,
            )
            workflow_answer = cls._extract_workflow_answer(workflow_data)
            if workflow_answer:
                return {
                    'status': 'ok',
                    'assistant_mode': 'dify-proxy',
                    'answer': workflow_answer,
                    'conversation_id': '',
                    'model': 'dify-workflow',
                    'question': message,
                    'message_id': (
                        workflow_data.get('data', {}).get('workflow_run_id')
                        if isinstance(workflow_data.get('data'), dict)
                        else ''
                    ),
                }
        except HTTPError as exc:
            return {
                'status': 'fallback',
                'assistant_mode': 'dify-proxy',
                'answer': 'AI 助手暂时不可用，请稍后重试。',
                'conversation_id': conversation_id or '',
                'model': 'dify-http-error',
                'question': message,
                'error': f'http_{exc.code}',
            }
        return {
            'status': 'fallback',
            'assistant_mode': 'dify-proxy',
            'answer': '助手未返回有效内容，请换个问题再试。',
            'conversation_id': conversation_id or '',
            'model': 'dify-empty-output',
            'question': message,
            'error': 'empty_output',
        }
