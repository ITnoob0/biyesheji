from django.contrib.auth import get_user_model
from rest_framework import serializers

from project_guides.models import ProjectGuide


class PortraitAssistantRequestSerializer(serializers.Serializer):
    QUESTION_TYPES = (
        ('portrait_summary', '画像总结'),
        ('achievement_summary', '成果概括'),
        ('guide_reason', '推荐说明'),
    )

    user_id = serializers.IntegerField(required=False)
    question_type = serializers.ChoiceField(choices=QUESTION_TYPES)
    guide_id = serializers.IntegerField(required=False)

    def validate_user_id(self, value):
        if not get_user_model().objects.filter(id=value).exists():
            raise serializers.ValidationError('目标教师不存在。')
        return value

    def validate_guide_id(self, value):
        if not ProjectGuide.objects.filter(id=value).exists():
            raise serializers.ValidationError('目标项目指南不存在。')
        return value

    def validate(self, attrs):
        if attrs.get('question_type') == 'guide_reason' and not attrs.get('guide_id'):
            raise serializers.ValidationError({'guide_id': '选择“推荐说明”时必须指定项目指南。'})
        return attrs
