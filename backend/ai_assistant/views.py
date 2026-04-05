from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.exceptions import PermissionDenied

from .dify_service import DifyAssistantService
from .serializers import AssistantChatRequestSerializer, DifyAssistantChatRequestSerializer, PortraitAssistantRequestSerializer
from .services import AssistantChatService, PortraitAssistantService


class PortraitAssistantView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = PortraitAssistantRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        teacher = None
        try:
            teacher = PortraitAssistantService.resolve_target_teacher(
                request,
                serializer.validated_data.get('user_id'),
            )
            payload = PortraitAssistantService.build_answer(
                request,
                teacher,
                serializer.validated_data['question_type'],
                serializer.validated_data.get('guide_id'),
                serializer.validated_data.get('department', ''),
                serializer.validated_data.get('year'),
            )
        except PermissionDenied:
            raise
        except Exception as exc:
            payload = PortraitAssistantService.build_failure_payload(
                serializer.validated_data['question_type'],
                teacher=teacher,
                reason=str(exc),
            )
        return Response(payload)


class AssistantChatView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = AssistantChatRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            payload = AssistantChatService.build_chat_answer(
                request,
                message=serializer.validated_data['message'],
                context_hint=serializer.validated_data.get('context_hint', ''),
                limit=serializer.validated_data.get('limit', 4),
            )
        except PermissionDenied:
            raise
        except Exception as exc:
            payload = {
                'status': 'fallback',
                'title': 'AI 助手回答已回退',
                'answer': '当前聊天助手暂不可用，已回退为安全说明模式。你可以稍后重试。',
                'assistant_mode': 'rag-chat',
                'model': 'rules-fallback',
                'question': serializer.validated_data['message'],
                'scope_note': '当前回答仅基于系统内已有数据与页面级安全说明。',
                'non_coverage_note': '当前不提供外部开放知识问答。',
                'acceptance_scope': '本能力处于增强迭代阶段，发生异常时优先保证可控与可回退。',
                'boundary_notes': [f'回退原因：{exc}'],
                'teacher_snapshot': {
                    'user_id': request.user.id,
                    'teacher_name': request.user.real_name or request.user.username,
                    'department': request.user.department or '',
                    'title': request.user.title or '',
                },
                'sources': [
                    {
                        'id': 'F1',
                        'title': '回退说明',
                        'module': 'assistant',
                        'snippet': f'聊天链路异常，系统已回退。原因：{exc}',
                        'score': 0,
                        'link': {
                            'label': '查看助手页面',
                            'page': 'assistant',
                            'section': 'assistant-answer',
                            'note': '当前为安全回退说明，不影响其他业务页面。',
                        },
                    }
                ],
            }
        return Response(payload)


class DifyAssistantChatView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = DifyAssistantChatRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        payload = DifyAssistantService.chat(
            user=request.user,
            message=serializer.validated_data['message'],
            conversation_id=serializer.validated_data.get('conversation_id', ''),
            context_hint=serializer.validated_data.get('context_hint', ''),
            route_path=serializer.validated_data.get('route_path', ''),
        )
        return Response(payload)
