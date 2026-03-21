from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.exceptions import PermissionDenied

from .serializers import PortraitAssistantRequestSerializer
from .services import PortraitAssistantService


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
