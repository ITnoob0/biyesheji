from rest_framework import serializers
from .models import Paper

class PaperSerializer(serializers.ModelSerializer):
    class Meta:
        model = Paper
        fields = '__all__'  # 暴露所有字段给前端
        read_only_fields = ('created_at',)  # 创建时间是自动生成的，前端不能改