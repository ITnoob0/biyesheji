# backend/achievements/views.py
from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated
from .models import Paper
from .serializers import PaperSerializer
from ai_assistant.utils import AcademicAI
from graph_engine.utils import Neo4jEngine  # <--- 引入图谱引擎

class PaperViewSet(viewsets.ModelViewSet):
    queryset = Paper.objects.all().order_by('-publish_date')
    serializer_class = PaperSerializer
    permission_classes = [IsAuthenticated]

    def perform_create(self, serializer):
        # 1. 保存到 MySQL
        instance = serializer.save()
        
        # 2. 调用 AI 提取关键词
        keywords = []
        if instance.abstract and len(instance.abstract) > 10:
            ai = AcademicAI()
            keywords = ai.extract_tags(instance.title, instance.abstract)
            instance.keywords = keywords
            instance.save()
            
        # 3. 将关系网络同步到 Neo4j
        try:
            # 获取所有关联的系统内作者名字 (如果是多对多关系)
            author_names = [author.real_name or author.username for author in instance.authors.all()]
            
            # 如果还有外部作者，也加进去
            if instance.external_authors:
                external_list = [name.strip() for name in instance.external_authors.split(',')]
                author_names.extend(external_list)
            
            # 如果没有作者兜底
            if not author_names:
                author_names = ["未知作者"]

            # 启动图引擎进行同步
            graph = Neo4jEngine()
            graph.sync_paper_to_graph(
                paper_id=instance.id,
                title=instance.title,
                author_names=author_names,
                keywords=instance.keywords
            )
            graph.close()
        except Exception as e:
            print(f"❌ 同步到图数据库失败: {e}")