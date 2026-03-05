from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated
from .models import Paper
from .serializers import PaperSerializer

class PaperViewSet(viewsets.ModelViewSet):
    """
    科研论文的增删改查 API 接口
    """
    queryset = Paper.objects.all().order_by('-publish_date')
    serializer_class = PaperSerializer
    permission_classes = [IsAuthenticated] # 核心：只有携带有效 JWT Token 的登录用户才能访问

    def perform_create(self, serializer):
        # 这里是保存数据到数据库的拦截点
        # TODO: 未来我们将在这里接入 Ollama 大模型，实现摘要的自动提取和标签的智能打标
        serializer.save()