from django.contrib.auth import get_user_model
from rest_framework import serializers

from project_guides.models import ProjectGuide


class PortraitAssistantRequestSerializer(serializers.Serializer):
    QUESTION_TYPES = (
        ('portrait_summary', '画像总结'),
        ('portrait_dimension_reason', '画像形成说明'),
        ('portrait_data_governance', '画像数据口径与缺口说明'),
        ('achievement_summary', '成果概括'),
        ('achievement_portrait_link', '成果与画像联动说明'),
        ('achievement_recommendation_link', '成果与推荐联动说明'),
        ('guide_reason', '推荐说明'),
        ('guide_overview', '推荐概览'),
        ('graph_status', '图谱链路与降级状态'),
        ('academy_summary', '学院统计概览'),
    )

    user_id = serializers.IntegerField(required=False)
    question_type = serializers.ChoiceField(choices=QUESTION_TYPES)
    guide_id = serializers.IntegerField(required=False)
    department = serializers.CharField(required=False, allow_blank=True)
    year = serializers.IntegerField(required=False)

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
        if attrs.get('year') is not None and attrs['year'] < 1900:
            raise serializers.ValidationError({'year': '年份参数无效。'})
        return attrs


class AssistantChatRequestSerializer(serializers.Serializer):
    user_id = serializers.IntegerField(required=False)
    message = serializers.CharField(max_length=1200)
    context_hint = serializers.CharField(required=False, allow_blank=True, max_length=120)
    limit = serializers.IntegerField(required=False, min_value=1, max_value=8, default=4)

    def validate_user_id(self, value):
        raise serializers.ValidationError('当前聊天助手仅支持当前登录账号问答，不支持指定教师。')


class DifyAssistantChatRequestSerializer(serializers.Serializer):
    message = serializers.CharField(max_length=2000)
    conversation_id = serializers.CharField(required=False, allow_blank=True, max_length=120)
    context_hint = serializers.CharField(required=False, allow_blank=True, max_length=120)
    route_path = serializers.CharField(required=False, allow_blank=True, max_length=260)
