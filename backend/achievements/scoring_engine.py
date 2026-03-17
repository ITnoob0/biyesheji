from django.db.models import Sum

from .models import AcademicService, CoAuthor, IntellectualProperty, Paper, PaperKeyword, Project, TeachingAchievement


class TeacherScoringEngine:
    """
    Aggregate portrait dimensions from the current relational data.
    The formulas are intentionally lightweight so the homepage can stay real-time
    without introducing snapshot or batch recomputation infrastructure.
    """

    WEIGHTS = {
        'academic_output': 0.24,
        'funding_support': 0.20,
        'ip_strength': 0.16,
        'talent_training': 0.14,
        'academic_reputation': 0.14,
        'interdisciplinary': 0.12,
    }

    @classmethod
    def collect_metrics(cls, teacher_user):
        papers = Paper.objects.filter(teacher=teacher_user)
        projects = Project.objects.filter(teacher=teacher_user)
        intellectual_properties = IntellectualProperty.objects.filter(teacher=teacher_user)
        teaching_achievements = TeachingAchievement.objects.filter(teacher=teacher_user)
        academic_services = AcademicService.objects.filter(teacher=teacher_user)

        paper_count = papers.count()
        citation_total = papers.aggregate(total=Sum('citation_count'))['total'] or 0
        project_count = projects.count()
        funding_total = float(projects.aggregate(total=Sum('funding_amount'))['total'] or 0)
        ip_count = intellectual_properties.count()
        transformed_ip_count = intellectual_properties.filter(is_transformed=True).count()
        teaching_count = teaching_achievements.count()
        service_count = academic_services.count()
        keyword_count = PaperKeyword.objects.filter(paper__teacher=teacher_user).count()
        collaborator_count = CoAuthor.objects.filter(paper__teacher=teacher_user).values('name').distinct().count()

        return {
            'paper_count': paper_count,
            'citation_total': citation_total,
            'project_count': project_count,
            'funding_total': funding_total,
            'ip_count': ip_count,
            'transformed_ip_count': transformed_ip_count,
            'teaching_count': teaching_count,
            'service_count': service_count,
            'keyword_count': keyword_count,
            'collaborator_count': collaborator_count,
            'total_achievements': paper_count + project_count + ip_count + teaching_count + service_count,
        }

    @classmethod
    def build_dimension_values(cls, metrics):
        academic_output = min(metrics['paper_count'] * 12 + metrics['citation_total'] * 0.6, 100)
        funding_support = min(metrics['project_count'] * 18 + min(metrics['funding_total'], 60) * 1.1, 100)
        ip_strength = min(metrics['ip_count'] * 20 + metrics['transformed_ip_count'] * 18, 100)
        talent_training = min(metrics['teaching_count'] * 24 + metrics['paper_count'] * 2, 100)
        academic_reputation = min(
            metrics['service_count'] * 22
            + min(metrics['collaborator_count'] * 4, 20)
            + min(metrics['citation_total'] * 0.2, 18),
            100,
        )
        interdisciplinary = min(metrics['keyword_count'] * 3 + metrics['project_count'] * 6, 100)

        return {
            'academic_output': round(academic_output, 1),
            'funding_support': round(funding_support, 1),
            'ip_strength': round(ip_strength, 1),
            'talent_training': round(talent_training, 1),
            'academic_reputation': round(academic_reputation, 1),
            'interdisciplinary': round(interdisciplinary, 1),
        }

    @classmethod
    def build_radar_dimensions(cls, metrics):
        values = cls.build_dimension_values(metrics)
        return [
            {'name': '基础学术产出', 'value': values['academic_output']},
            {'name': '经费与项目攻关', 'value': values['funding_support']},
            {'name': '知识产权沉淀', 'value': values['ip_strength']},
            {'name': '人才培养成效', 'value': values['talent_training']},
            {'name': '学术活跃与声誉', 'value': values['academic_reputation']},
            {'name': '跨学科融合度', 'value': values['interdisciplinary']},
        ]

    @classmethod
    def build_dimension_sources(cls, metrics):
        return [
            {
                'name': '基础学术产出',
                'description': f"依据论文 {metrics['paper_count']} 篇、总被引 {metrics['citation_total']} 次综合估计。",
            },
            {
                'name': '经费与项目攻关',
                'description': f"依据项目 {metrics['project_count']} 项、累计经费 {metrics['funding_total']:.2f} 万元估计。",
            },
            {
                'name': '知识产权沉淀',
                'description': f"依据知识产权 {metrics['ip_count']} 项，其中转化 {metrics['transformed_ip_count']} 项估计。",
            },
            {
                'name': '人才培养成效',
                'description': f"依据教学成果 {metrics['teaching_count']} 项，并参考论文产出协同估计。",
            },
            {
                'name': '学术活跃与声誉',
                'description': f"依据学术服务 {metrics['service_count']} 项、合作作者 {metrics['collaborator_count']} 位估计。",
            },
            {
                'name': '跨学科融合度',
                'description': f"依据论文关键词 {metrics['keyword_count']} 个、项目参与情况估计。",
            },
        ]

    @classmethod
    def get_comprehensive_radar_data(cls, teacher_user):
        metrics = cls.collect_metrics(teacher_user)
        values = cls.build_dimension_values(metrics)
        total_score = sum(values[key] * cls.WEIGHTS[key] for key in cls.WEIGHTS)

        return {
            'metrics': metrics,
            'radar_dimensions': cls.build_radar_dimensions(metrics),
            'dimension_sources': cls.build_dimension_sources(metrics),
            'total_score': round(total_score, 1),
        }
