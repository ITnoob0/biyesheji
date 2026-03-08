# backend/achievements/views.py
from rest_framework import viewsets
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.db.models import Sum

from .models import Paper, Project, ResearchKeyword, PaperKeyword
from .serializers import PaperSerializer
from ai_assistant.utils import AcademicAI
from graph_engine.utils import Neo4jEngine
from .scoring_engine import TeacherScoringEngine

class PaperViewSet(viewsets.ModelViewSet):
    # 注意这里：也改成了 -date_acquired
    queryset = Paper.objects.all().order_by('-date_acquired')
    serializer_class = PaperSerializer
    # permission_classes = [IsAuthenticated] 

    def perform_create(self, serializer):
        # 1. 保存到 MySQL
        instance = serializer.save()
        
        # 2. 调用 AI 提取关键词 (适配新的关键词多对多表)
        kw_names = []
        if instance.abstract and len(instance.abstract) > 10:
            ai = AcademicAI()
            kw_names = ai.extract_tags(instance.title, instance.abstract)
            for kw in kw_names:
                # 动态存入或获取独立的研究关键词节点
                kw_obj, _ = ResearchKeyword.objects.get_or_create(name=kw)
                PaperKeyword.objects.create(paper=instance, keyword=kw_obj)
            
        # 3. 将关系网络同步到 Neo4j 图数据库
        try:
            # 适配新的作者体系：核心教师 + 外部合作者
            author_names = [instance.teacher.username] 
            for coauthor in instance.coauthors.all():
                author_names.append(coauthor.name)

            graph = Neo4jEngine()
            graph.sync_paper_to_graph(
                paper_id=instance.id,
                title=instance.title,
                author_names=author_names,
                keywords=kw_names
            )
            graph.close()
        except Exception as e:
            print(f"❌ 同步到图数据库失败: {e}")


class TeacherDashboardStatsView(APIView):
    """
    提供给前端 Dashboard 概览页的数据接口
    """
    def get(self, request):
        from django.contrib.auth import get_user_model
        User = get_user_model()
        
        user = request.user if request.user.is_authenticated else User.objects.first()

        if not user:
            return Response({"error": "暂无教师数据，请先在后台创建用户"}, status=404)

        radar_result = TeacherScoringEngine.get_comprehensive_radar_data(user)
        
        total_papers = Paper.objects.filter(teacher=user).count()
        total_citations = Paper.objects.filter(teacher=user).aggregate(Sum('citation_count'))['citation_count__sum'] or 0
        total_projects = Project.objects.filter(teacher=user).count()

        return Response({
            "statistics": [
                { "title": "总发文量", "value": total_papers, "suffix": "篇", "icon": "Document", "iconClass": "icon-blue", "trend": 12.5 },
                { "title": "总被引频次", "value": total_citations, "suffix": "次", "icon": "Star", "iconClass": "icon-orange", "trend": 8.2 },
                { "title": "综合科研评分", "value": radar_result['total_score'], "suffix": "分", "icon": "Trophy", "iconClass": "icon-red", "trend": 5.0 },
                { "title": "主持/参与项目", "value": total_projects, "suffix": "项", "icon": "Reading", "iconClass": "icon-green", "trend": 0.0 }
            ],
            "radar_data": radar_result['radar_dimensions']
        })