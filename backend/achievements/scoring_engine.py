from __future__ import annotations

from decimal import Decimal

from django.db.models import Sum

from .models import RuleBasedAchievement
from .rule_scoring import build_conflict_group_key, tokenize_keywords


class TeacherScoringEngine:
    """
    Aggregate the teacher portrait from approved, rule-driven achievements.

    This replaces the old fixed formula that relied on hard-coded paper/project/IP
    tables. Only achievements approved by the college admin are counted.
    """

    WEIGHTS = {
        'academic_output': 0.0,
        'funding_support': 0.0,
        'ip_strength': 0.0,
        'academic_reputation': 0.0,
        'interdisciplinary': 0.0,
    }

    DIMENSION_LABELS = {
        'academic_output': '学术产出与著作',
        'funding_support': '项目竞争与资源获取',
        'ip_strength': '成果获奖与学术荣誉',
        'academic_reputation': '转化服务与智库贡献',
        'interdisciplinary': '平台团队与科普影响',
    }

    DIMENSION_FORMULAS = {
        'academic_output': '画像展示分 = min(论文著作原始积分 ÷ 30, 100)。',
        'funding_support': '画像展示分 = min(科研项目原始积分 ÷ 30, 100)。',
        'ip_strength': '画像展示分 = min(科研成果获奖原始积分 ÷ 20, 100)。',
        'academic_reputation': '画像展示分 = min((成果转化原始积分 + 智库成果原始积分) ÷ 18, 100)。',
        'interdisciplinary': '画像展示分 = min((平台团队原始积分 + 科普类获奖原始积分) ÷ 18, 100)。',
    }

    WEIGHT_SPEC_DETAILS = {
        'academic_output': {
            'name': '学术产出与著作',
            'formula_short': 'min(论文著作原始积分 ÷ 30, 100)',
            'main_inputs': ['论文著作类成果积分'],
            'rationale': '归集正式学术产出类成果。',
        },
        'funding_support': {
            'name': '项目竞争与资源获取',
            'formula_short': 'min(科研项目原始积分 ÷ 30, 100)',
            'main_inputs': ['科研项目成果积分'],
            'rationale': '归集科研项目类成果。',
        },
        'ip_strength': {
            'name': '成果获奖与学术荣誉',
            'formula_short': 'min(科研成果获奖原始积分 ÷ 20, 100)',
            'main_inputs': ['科研成果获奖积分'],
            'rationale': '归集科研成果获奖类成果。',
        },
        'academic_reputation': {
            'name': '转化服务与智库贡献',
            'formula_short': 'min((成果转化原始积分 + 智库成果原始积分) ÷ 18, 100)',
            'main_inputs': ['成果转化成果', '智库成果'],
            'rationale': '归集成果转化与智库贡献类成果。',
        },
        'interdisciplinary': {
            'name': '平台团队与科普影响',
            'formula_short': 'min((平台团队原始积分 + 科普类获奖原始积分) ÷ 18, 100)',
            'main_inputs': ['平台与团队成果', '科普类获奖成果'],
            'rationale': '归集平台团队建设与科普影响类成果。',
        },
    }

    CATEGORY_BUCKETS = {
        'paper_book': {'PAPER_BOOK'},
        'projects': {'PROJECT'},
        'award_transform': {'AWARD', 'TRANSFORMATION', 'THINK_TANK'},
        'platform_pop': {'PLATFORM_TEAM', 'SCI_POP_AWARD'},
    }

    @classmethod
    def _approved_queryset(cls, teacher_user, year: int | None = None, rule_version_id: int | None = None):
        queryset = (
            RuleBasedAchievement.objects.select_related('category', 'rule_item')
            .filter(teacher=teacher_user, status='APPROVED')
            .order_by('-date_acquired', '-created_at')
        )
        if year is not None:
            queryset = queryset.filter(date_acquired__year=year)
        if rule_version_id is not None:
            queryset = queryset.filter(version_id=rule_version_id)
        return queryset

    @classmethod
    def _dedup_records(cls, queryset):
        grouped: dict[str, RuleBasedAchievement] = {}
        ordered = list(queryset)
        for item in ordered:
            key = build_conflict_group_key(item)
            current = grouped.get(key)
            if current is None:
                grouped[key] = item
                continue
            if item.rule_item.multi_match_policy == item.rule_item.MULTI_MATCH_STACKABLE:
                grouped[f'{key}:stack:{item.id}'] = item
                continue
            if Decimal(str(item.final_score or 0)) > Decimal(str(current.final_score or 0)):
                grouped[key] = item
        return list(grouped.values())

    @classmethod
    def collect_metrics(cls, teacher_user, year: int | None = None, rule_version_id: int | None = None):
        records = cls._dedup_records(cls._approved_queryset(teacher_user, year=year, rule_version_id=rule_version_id))
        return cls._collect_metrics_from_records(records)

    @classmethod
    def _collect_metrics_from_records(cls, records):
        category_scores = {
            'PAPER_BOOK': Decimal('0'),
            'PROJECT': Decimal('0'),
            'AWARD': Decimal('0'),
            'TRANSFORMATION': Decimal('0'),
            'THINK_TANK': Decimal('0'),
            'PLATFORM_TEAM': Decimal('0'),
            'SCI_POP_AWARD': Decimal('0'),
        }
        counts = {
            'PAPER_BOOK': 0,
            'PROJECT': 0,
            'AWARD': 0,
            'TRANSFORMATION': 0,
            'THINK_TANK': 0,
            'PLATFORM_TEAM': 0,
            'SCI_POP_AWARD': 0,
        }
        amount_total = Decimal('0')
        representative_count = 0
        keyword_set: set[str] = set()
        collaborator_set: set[str] = set()

        for item in records:
            code = item.category_code_snapshot or (item.category.code if item.category_id else '')
            if code in category_scores:
                category_scores[code] += Decimal(str(item.final_score or 0))
                counts[code] += 1
            if item.amount_value:
                amount_total += Decimal(str(item.amount_value))
            if item.is_representative:
                representative_count += 1
            keyword_set.update(tokenize_keywords(item.keywords_text))
            collaborator_set.update(
                str(name).strip()
                for name in (item.coauthor_names or [])
                if str(name).strip()
            )

        return {
            'paper_count': counts['PAPER_BOOK'],
            'representative_paper_count': representative_count,
            'project_count': counts['PROJECT'],
            'funding_total': float(amount_total),
            'award_count': counts['AWARD'],
            'ip_count': counts['AWARD'],
            'transformation_count': counts['TRANSFORMATION'],
            'think_tank_count': counts['THINK_TANK'],
            'transformed_ip_count': counts['TRANSFORMATION'],
            'platform_count': counts['PLATFORM_TEAM'],
            'science_pop_count': counts['SCI_POP_AWARD'],
            'service_count': counts['PLATFORM_TEAM'] + counts['SCI_POP_AWARD'],
            'keyword_count': len(keyword_set),
            'collaborator_count': len(collaborator_set),
            'paper_book_score': float(category_scores['PAPER_BOOK']),
            'project_score': float(category_scores['PROJECT']),
            'award_score': float(category_scores['AWARD']),
            'transformation_score': float(category_scores['TRANSFORMATION']),
            'think_tank_score': float(category_scores['THINK_TANK']),
            'platform_team_score': float(category_scores['PLATFORM_TEAM']),
            'science_pop_score': float(category_scores['SCI_POP_AWARD']),
            'total_rule_score': float(sum(category_scores.values(), Decimal('0'))),
            'total_achievements': len(records),
        }

    @classmethod
    def collect_metrics_series(cls, teacher_user, years: list[int], rule_version_id: int | None = None) -> dict[int, dict]:
        normalized_years = [year for year in years if isinstance(year, int)]
        return {year: cls.collect_metrics(teacher_user, year=year, rule_version_id=rule_version_id) for year in normalized_years}

    @classmethod
    def calculate_total_score(cls, metrics):
        return round(float(metrics.get('total_rule_score', 0.0) or 0.0), 1)

    @classmethod
    def build_dimension_raw_scores(cls, metrics):
        return {
            'academic_output': round(float(metrics.get('paper_book_score', 0.0) or 0.0), 1),
            'funding_support': round(float(metrics.get('project_score', 0.0) or 0.0), 1),
            'ip_strength': round(float(metrics.get('award_score', 0.0) or 0.0), 1),
            'academic_reputation': round(
                float(metrics.get('transformation_score', 0.0) or 0.0)
                + float(metrics.get('think_tank_score', 0.0) or 0.0),
                1,
            ),
            'interdisciplinary': round(
                float(metrics.get('platform_team_score', 0.0) or 0.0)
                + float(metrics.get('science_pop_score', 0.0) or 0.0),
                1,
            ),
        }

    @classmethod
    def build_dimension_values(cls, metrics):
        academic_output = min(metrics['paper_book_score'] / 30, 100)
        funding_support = min(metrics['project_score'] / 30, 100)
        research_awards = min(metrics['award_score'] / 20, 100)
        transformation_service = min((metrics['transformation_score'] + metrics['think_tank_score']) / 18, 100)
        platform_influence = min((metrics['platform_team_score'] + metrics['science_pop_score']) / 18, 100)

        return {
            'academic_output': round(academic_output, 1),
            'funding_support': round(funding_support, 1),
            'ip_strength': round(research_awards, 1),
            'academic_reputation': round(transformation_service, 1),
            'interdisciplinary': round(platform_influence, 1),
        }

    @classmethod
    def build_radar_dimensions(cls, metrics):
        values = cls.build_dimension_values(metrics)
        return [{'key': key, 'name': label, 'value': values[key]} for key, label in cls.DIMENSION_LABELS.items()]

    @classmethod
    def build_dimension_sources(cls, metrics):
        return [
            {
                'name': '学术产出与著作',
                'description': '纳入成果大类：论文、著作、译著、工具书、专辑、歌曲等学术产出。',
            },
            {
                'name': '项目竞争与资源获取',
                'description': '纳入成果大类：科研项目。',
            },
            {
                'name': '成果获奖与学术荣誉',
                'description': '纳入成果大类：科研成果获奖。',
            },
            {
                'name': '转化服务与智库贡献',
                'description': '纳入成果大类：成果转化、智库成果。',
            },
            {
                'name': '平台团队与科普影响',
                'description': '纳入成果大类：平台与团队、科普类获奖。',
            },
        ]

    @classmethod
    def build_dimension_insights(cls, metrics):
        values = cls.build_dimension_values(metrics)
        raw_scores = cls.build_dimension_raw_scores(metrics)
        source_map = {item['name']: item['description'] for item in cls.build_dimension_sources(metrics)}
        evidence_map = {
            'academic_output': [f"论文著作积分 {metrics['paper_book_score']:.1f} 分"],
            'funding_support': [f"科研项目积分 {metrics['project_score']:.1f} 分"],
            'ip_strength': [f"科研成果获奖积分 {metrics['award_score']:.1f} 分"],
            'academic_reputation': [
                f"成果转化积分 {metrics['transformation_score']:.1f} 分",
                f"智库成果积分 {metrics['think_tank_score']:.1f} 分",
            ],
            'interdisciplinary': [
                f"平台团队积分 {metrics['platform_team_score']:.1f} 分",
                f"科普类获奖积分 {metrics['science_pop_score']:.1f} 分",
            ],
        }
        insights = []

        for key, label in cls.DIMENSION_LABELS.items():
            value = values[key]
            if value >= 75:
                level = '优势维度'
            elif value >= 45:
                level = '稳定维度'
            else:
                level = '成长维度'

            insights.append(
                {
                    'key': key,
                    'name': label,
                    'value': value,
                    'weight': 0.0,
                    'raw_score': raw_scores[key],
                    'score_role': 'display_only',
                    'level': level,
                    'formula_note': cls.DIMENSION_FORMULAS[key],
                    'source_description': source_map.get(label, ''),
                    'evidence': evidence_map.get(key, []),
                }
            )

        return insights

    @classmethod
    def build_weight_spec(cls, metrics):
        current_values = cls.build_dimension_values(metrics)
        raw_scores = cls.build_dimension_raw_scores(metrics)
        return [
            {
                'key': key,
                'name': cls.WEIGHT_SPEC_DETAILS[key]['name'],
                'weight': 0.0,
                'raw_score': raw_scores[key],
                'score_role': 'display_only',
                'formula_short': cls.WEIGHT_SPEC_DETAILS[key]['formula_short'],
                'main_inputs': cls.WEIGHT_SPEC_DETAILS[key]['main_inputs'],
                'rationale': cls.WEIGHT_SPEC_DETAILS[key]['rationale'],
                'current_value': current_values[key],
                'aggregation_note': '科研成果积分总分按审核通过且去重后的成果 final_score 直接相加；该维度仅用于结构展示。',
            }
            for key in cls.WEIGHT_SPEC_DETAILS.keys()
        ]

    @classmethod
    def build_calculation_summary(cls, metrics):
        values = cls.build_dimension_values(metrics)
        raw_scores = cls.build_dimension_raw_scores(metrics)
        total_score = cls.calculate_total_score(metrics)
        strongest_key = max(raw_scores, key=raw_scores.get)
        weakest_key = min(raw_scores, key=raw_scores.get)
        return {
            'weight_mode': 'direct_rule_score_sum',
            'formula_note': '科研成果积分总分 = 审核通过且去重后的成果 final_score 直接相加；五维雷达只做结构展示，不参与二次加权。',
            'total_score': total_score,
            'total_achievements': metrics['total_achievements'],
            'strongest_dimension': {
                'key': strongest_key,
                'name': cls.WEIGHT_SPEC_DETAILS[strongest_key]['name'],
                'value': raw_scores[strongest_key],
                'display_value': values[strongest_key],
            },
            'weakest_dimension': {
                'key': weakest_key,
                'name': cls.WEIGHT_SPEC_DETAILS[weakest_key]['name'],
                'value': raw_scores[weakest_key],
                'display_value': values[weakest_key],
            },
        }

    @classmethod
    def get_comprehensive_radar_data(cls, teacher_user, rule_version_id: int | None = None):
        metrics = cls.collect_metrics(teacher_user, rule_version_id=rule_version_id)
        total_score = cls.calculate_total_score(metrics)

        return {
            'metrics': metrics,
            'radar_dimensions': cls.build_radar_dimensions(metrics),
            'dimension_sources': cls.build_dimension_sources(metrics),
            'dimension_insights': cls.build_dimension_insights(metrics),
            'weight_spec': cls.build_weight_spec(metrics),
            'calculation_summary': cls.build_calculation_summary(metrics),
            'total_score': total_score,
        }
