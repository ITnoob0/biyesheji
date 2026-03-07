# backend/achievements/views.py
from rest_framework import viewsets
from .models import Paper
from .serializers import PaperSerializer
from ai_assistant.utils import AcademicAI # 引入 AI 工具类

class PaperViewSet(viewsets.ModelViewSet):
    queryset = Paper.objects.all().order_by('-publish_date')
    serializer_class = PaperSerializer

    def perform_create(self, serializer):
        # 1. 保存论文原始数据到 MySQL
        instance = serializer.save()
        
        # 2. 如果存在摘要，启动 AI 提取
        if instance.abstract and len(instance.abstract) > 10:
            ai = AcademicAI()
            tags = ai.extract_tags(instance.title, instance.abstract)
            
            # 3. 将 AI 生成的标签存入数据库的关键词字段
            instance.keywords = tags
            instance.save()