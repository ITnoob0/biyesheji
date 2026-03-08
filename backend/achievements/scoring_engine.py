# backend/achievements/scoring_engine.py
from django.db.models import Sum
from .models import Paper, Project

class TeacherScoringEngine:
    """
    教师科研能力自动评分引擎 (基于六维加权模型)
    """
    WEIGHTS = {
        'papers': 0.25,      
        'projects': 0.30,    
        'ip': 0.15,          
        'teaching': 0.15,    
        'service': 0.10,     
        'interdisciplinary': 0.05 
    }

    @classmethod
    def calculate_paper_score(cls, teacher_user):
        papers = Paper.objects.filter(teacher=teacher_user)
        score = 0
        for paper in papers:
            if paper.journal_level in ['CCF-A', 'SCI-1区']:
                score += 50
            elif paper.journal_level in ['CCF-B', 'SCI-2区']:
                score += 30
            else:
                score += 10
            score += paper.citation_count * 0.5 
        return min(score, 100.0)

    @classmethod
    def calculate_project_score(cls, teacher_user):
        projects = Project.objects.filter(teacher=teacher_user)
        score = 0
        for proj in projects:
            if proj.level == 'NATIONAL':
                score += 60
            elif proj.level == 'PROVINCIAL':
                score += 30
        total_funding = projects.aggregate(total=Sum('funding_amount'))['total'] or 0
        score += float(total_funding) * 0.5 
        return min(score, 100.0)
    
    @classmethod
    def get_comprehensive_radar_data(cls, teacher_user):
        scores = {
            'papers': cls.calculate_paper_score(teacher_user),
            'projects': cls.calculate_project_score(teacher_user),
            'ip': 80.0,         # 暂用模拟初始值
            'teaching': 75.0,   # 暂用模拟初始值
            'service': 60.0,    # 暂用模拟初始值
            'interdisciplinary': 40.0 # 暂用模拟初始值
        }
        
        total_score = sum(scores[key] * cls.WEIGHTS[key] for key in scores)
        
        return {
            'radar_dimensions': [
                {'name': '基础学术产出', 'value': scores['papers']},
                {'name': '经费吸附与攻坚', 'value': scores['projects']},
                {'name': '硬核知识产权', 'value': scores['ip']},
                {'name': '人才培养成效', 'value': scores['teaching']},
                {'name': '学术活跃与声誉', 'value': scores['service']},
                {'name': '跨学科融合度', 'value': scores['interdisciplinary']},
            ],
            'total_score': round(total_score, 1)
        }