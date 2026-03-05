# backend/achievements/views.py
from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated
from .models import Paper
from .serializers import PaperSerializer
from ai_assistant.utils import AcademicAI # 引入我们刚写的 AI 工具

class PaperViewSet(viewsets.ModelViewSet):
    queryset = Paper.objects.all().order_by('-publish_date')
    serializer_class = PaperSerializer
    permission_classes = [IsAuthenticated]

    def perform_create(self, serializer):
        # 1. 先保存基础数据
        instance = serializer.save()
        
        # 2. 只有在有摘要的情况下才调用 AI
        if instance.abstract and len(instance.abstract) > 10:
            ai = AcademicAI()
            keywords = ai.extract_keywords(instance.title, instance.abstract)
            
            # 3. 将提取的关键词保存回数据库
            instance.keywords = keywords
            instance.save()