from django.db.models import Sum

from .models import AcademicService, CoAuthor, IntellectualProperty, PaperKeyword, Project, TeachingAchievement
from .services import build_teacher_related_paper_queryset
from .visibility import APPROVED_STATUS


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

    DIMENSION_LABELS = {
        'academic_output': '基础学术产出',
        'funding_support': '经费与项目攻关',
        'ip_strength': '知识产权沉淀',
        'talent_training': '人才培养成效',
        'academic_reputation': '学术活跃与声誉',
        'interdisciplinary': '跨学科融合度',
    }

    DIMENSION_FORMULAS = {
        'academic_output': '论文数量与引用次数共同作用，强调近期可观测的学术产出。',
        'funding_support': '项目数量与累计经费共同估算科研组织与攻关支撑能力。',
        'ip_strength': '知识产权总量与成果转化数量共同反映成果沉淀强度。',
        'talent_training': '教学成果为主，辅以论文协同产出反映育人成效。',
        'academic_reputation': '学术服务、合作作者与引用情况共同反映学术活跃度与影响力。',
        'interdisciplinary': '论文关键词覆盖度与项目参与情况共同反映跨学科融合表现。',
    }

    WEIGHT_SPEC_DETAILS = {
        'academic_output': {
            'name': '基础学术产出',
            'formula_short': '论文数 * 12 + 引用数 * 0.6，上限 100',
            'main_inputs': ['论文数量', '总被引次数'],
            'rationale': '优先反映近期可观测、可核验的学术产出表现。',
        },
        'funding_support': {
            'name': '经费与项目攻关',
            'formula_short': '项目数 * 18 + 经费折算，上限 100',
            'main_inputs': ['项目数量', '累计经费'],
            'rationale': '体现教师获取资源和组织科研攻关的能力。',
        },
        'ip_strength': {
            'name': '知识产权沉淀',
            'formula_short': '知识产权数 * 20 + 转化数 * 18，上限 100',
            'main_inputs': ['知识产权数量', '成果转化数量'],
            'rationale': '体现成果沉淀与应用转化能力。',
        },
        'talent_training': {
            'name': '人才培养成效',
            'formula_short': '教学成果数 * 24 + 论文数 * 2，上限 100',
            'main_inputs': ['教学成果数量', '论文协同产出'],
            'rationale': '体现教学育人投入及与科研产出的联动性。',
        },
        'academic_reputation': {
            'name': '学术活跃与声誉',
            'formula_short': '学术服务、合作作者与引用折算，上限 100',
            'main_inputs': ['学术服务数量', '合作作者数量', '总被引次数'],
            'rationale': '体现学术共同体参与度与外部影响力。',
        },
        'interdisciplinary': {
            'name': '跨学科融合度',
            'formula_short': '关键词数 * 3 + 项目数 * 6，上限 100',
            'main_inputs': ['论文关键词数量', '项目参与情况'],
            'rationale': '体现研究主题覆盖和跨方向协作能力。',
        },
    }

    @classmethod
    def collect_metrics(cls, teacher_user, year: int | None = None):
        papers = build_teacher_related_paper_queryset(teacher_user, approved_only=True, include_claimed=True)
        projects = Project.objects.filter(teacher=teacher_user, status=APPROVED_STATUS)
        intellectual_properties = IntellectualProperty.objects.filter(teacher=teacher_user, status=APPROVED_STATUS)
        teaching_achievements = TeachingAchievement.objects.filter(teacher=teacher_user, status=APPROVED_STATUS)
        academic_services = AcademicService.objects.filter(teacher=teacher_user, status=APPROVED_STATUS)

        if year is not None:
            papers = papers.filter(date_acquired__year=year)
            projects = projects.filter(date_acquired__year=year)
            intellectual_properties = intellectual_properties.filter(date_acquired__year=year)
            teaching_achievements = teaching_achievements.filter(date_acquired__year=year)
            academic_services = academic_services.filter(date_acquired__year=year)

        paper_count = papers.count()
        citation_total = papers.aggregate(total=Sum('citation_count'))['total'] or 0
        project_count = projects.count()
        funding_total = float(projects.aggregate(total=Sum('funding_amount'))['total'] or 0)
        ip_count = intellectual_properties.count()
        transformed_ip_count = intellectual_properties.filter(is_transformed=True).count()
        teaching_count = teaching_achievements.count()
        service_count = academic_services.count()

        paper_ids = list(papers.values_list('id', flat=True))
        keyword_count = PaperKeyword.objects.filter(paper_id__in=paper_ids).count()
        collaborator_count = CoAuthor.objects.filter(paper_id__in=paper_ids).values('name').distinct().count()

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
    def collect_metrics_series(cls, teacher_user, years: list[int]) -> dict[int, dict]:
        normalized_years = [year for year in years if isinstance(year, int)]
        return {year: cls.collect_metrics(teacher_user, year=year) for year in normalized_years}

    @classmethod
    def calculate_total_score(cls, values):
        return round(sum(values[key] * cls.WEIGHTS[key] for key in cls.WEIGHTS), 1)

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
        return [{'key': key, 'name': label, 'value': values[key]} for key, label in cls.DIMENSION_LABELS.items()]

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
    def build_dimension_insights(cls, metrics):
        values = cls.build_dimension_values(metrics)
        source_map = {item['name']: item['description'] for item in cls.build_dimension_sources(metrics)}
        insights = []

        for key, label in cls.DIMENSION_LABELS.items():
            value = values[key]
            if value >= 75:
                level = '优势维度'
            elif value >= 45:
                level = '稳定维度'
            else:
                level = '成长维度'

            evidence = []
            if key == 'academic_output':
                evidence = [f"论文 {metrics['paper_count']} 篇", f"总被引 {metrics['citation_total']} 次"]
            elif key == 'funding_support':
                evidence = [f"项目 {metrics['project_count']} 项", f"经费 {metrics['funding_total']:.2f} 万元"]
            elif key == 'ip_strength':
                evidence = [f"知识产权 {metrics['ip_count']} 项", f"成果转化 {metrics['transformed_ip_count']} 项"]
            elif key == 'talent_training':
                evidence = [f"教学成果 {metrics['teaching_count']} 项", f"协同论文 {metrics['paper_count']} 篇"]
            elif key == 'academic_reputation':
                evidence = [f"学术服务 {metrics['service_count']} 项", f"合作作者 {metrics['collaborator_count']} 位"]
            elif key == 'interdisciplinary':
                evidence = [f"论文关键词 {metrics['keyword_count']} 个", f"参与项目 {metrics['project_count']} 项"]

            insights.append(
                {
                    'key': key,
                    'name': label,
                    'value': value,
                    'weight': round(cls.WEIGHTS[key] * 100, 1),
                    'level': level,
                    'formula_note': cls.DIMENSION_FORMULAS[key],
                    'source_description': source_map.get(label, ''),
                    'evidence': evidence,
                }
            )

        return insights

    @classmethod
    def build_weight_spec(cls, metrics):
        current_values = cls.build_dimension_values(metrics)
        return [
            {
                'key': key,
                'name': cls.WEIGHT_SPEC_DETAILS[key]['name'],
                'weight': round(weight * 100, 1),
                'formula_short': cls.WEIGHT_SPEC_DETAILS[key]['formula_short'],
                'main_inputs': cls.WEIGHT_SPEC_DETAILS[key]['main_inputs'],
                'rationale': cls.WEIGHT_SPEC_DETAILS[key]['rationale'],
                'current_value': current_values[key],
            }
            for key, weight in cls.WEIGHTS.items()
        ]

    @classmethod
    def build_calculation_summary(cls, metrics):
        values = cls.build_dimension_values(metrics)
        total_score = cls.calculate_total_score(values)
        strongest_key = max(values, key=values.get)
        weakest_key = min(values, key=values.get)
        return {
            'weight_mode': 'fixed_weights_runtime_aggregation',
            'formula_note': '综合得分 = 各维度得分 × 固定权重后求和，按实时业务数据即时生成。',
            'total_score': total_score,
            'total_achievements': metrics['total_achievements'],
            'strongest_dimension': {
                'key': strongest_key,
                'name': cls.WEIGHT_SPEC_DETAILS[strongest_key]['name'],
                'value': values[strongest_key],
            },
            'weakest_dimension': {
                'key': weakest_key,
                'name': cls.WEIGHT_SPEC_DETAILS[weakest_key]['name'],
                'value': values[weakest_key],
            },
        }

    @classmethod
    def get_comprehensive_radar_data(cls, teacher_user):
        metrics = cls.collect_metrics(teacher_user)
        values = cls.build_dimension_values(metrics)
        total_score = cls.calculate_total_score(values)

        return {
            'metrics': metrics,
            'radar_dimensions': cls.build_radar_dimensions(metrics),
            'dimension_sources': cls.build_dimension_sources(metrics),
            'dimension_insights': cls.build_dimension_insights(metrics),
            'weight_spec': cls.build_weight_spec(metrics),
            'calculation_summary': cls.build_calculation_summary(metrics),
            'total_score': total_score,
        }
