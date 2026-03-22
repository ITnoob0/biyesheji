from __future__ import annotations

import re
from datetime import date

from django.contrib.auth import get_user_model
from django.utils import timezone

from achievements.models import AcademicService, IntellectualProperty, Paper, PaperKeyword, Project, TeachingAchievement
from users.access import COMPARE_SCOPE_MESSAGE, RECOMMENDATION_SCOPE_MESSAGE, ensure_admin_user, ensure_self_or_admin_user
from users.services import get_teacher_profile

from .models import ProjectGuide


def split_text_tokens(raw_text: str) -> list[str]:
    return [
        item.strip()
        for item in re.split(r'[\s,，、；;|/]+', raw_text or '')
        if item.strip()
    ]


class ProjectGuideRecommendationService:
    RULE_PROFILE_BONUS_LABELS = {
        'BALANCED': '均衡规则',
        'KEYWORD_FIRST': '主题优先',
        'DISCIPLINE_FIRST': '学科优先',
        'WINDOW_FIRST': '窗口优先',
        'ACTIVITY_FIRST': '活跃度优先',
    }

    @staticmethod
    def resolve_target_teacher(request, user_id: int | None = None):
        target_user_id = user_id or request.query_params.get('user_id')
        if not target_user_id:
            return request.user

        normalized_user_id = int(target_user_id)
        user_model = get_user_model()
        teacher = user_model.objects.get(id=normalized_user_id)
        try:
            ensure_self_or_admin_user(request.user, teacher, RECOMMENDATION_SCOPE_MESSAGE)
        except Exception as exc:
            raise PermissionError(str(exc)) from exc
        return teacher

    @staticmethod
    def resolve_compare_teacher(request, user_id: int | None = None, primary_teacher=None):
        if not user_id:
            return None

        normalized_user_id = int(user_id)
        try:
            ensure_admin_user(request.user, COMPARE_SCOPE_MESSAGE)
        except Exception as exc:
            raise PermissionError(str(exc)) from exc

        if primary_teacher and normalized_user_id == primary_teacher.id:
            return None

        user_model = get_user_model()
        return user_model.objects.get(id=normalized_user_id)

    @staticmethod
    def build_teacher_feature_pack(user) -> dict:
        profile = get_teacher_profile(user)
        profile_keywords = list(user.research_direction or [])
        profile_keywords.extend(split_text_tokens(profile.research_interests if profile else ''))
        profile_keywords.extend(split_text_tokens(profile.discipline if profile else ''))

        paper_keywords = list(
            PaperKeyword.objects.filter(paper__teacher=user)
            .select_related('keyword')
            .values_list('keyword__name', flat=True)
            .distinct()[:30]
        )

        all_keywords = []
        for keyword in profile_keywords + paper_keywords:
            normalized = keyword.strip()
            if normalized and normalized not in all_keywords:
                all_keywords.append(normalized)

        discipline_tags = []
        for keyword in [profile.discipline if profile else '', user.department or '']:
            normalized = keyword.strip()
            if normalized and normalized not in discipline_tags:
                discipline_tags.append(normalized)

        cutoff_year = timezone.now().date().year - 3
        recent_cutoff = date(cutoff_year, 1, 1)
        recent_activity_count = (
            Paper.objects.filter(teacher=user, date_acquired__gte=recent_cutoff).count()
            + Project.objects.filter(teacher=user, date_acquired__gte=recent_cutoff).count()
            + IntellectualProperty.objects.filter(teacher=user, date_acquired__gte=recent_cutoff).count()
            + TeachingAchievement.objects.filter(teacher=user, date_acquired__gte=recent_cutoff).count()
            + AcademicService.objects.filter(teacher=user, date_acquired__gte=recent_cutoff).count()
        )

        return {
            'teacher': user,
            'keywords': all_keywords[:20],
            'disciplines': discipline_tags[:8],
            'recent_activity_count': recent_activity_count,
            'recent_cutoff_label': f'{cutoff_year} 年以来',
            'activity_level': (
                'HIGH'
                if recent_activity_count >= 4
                else 'MEDIUM'
                if recent_activity_count >= 2
                else 'LOW'
            ),
        }

    @staticmethod
    def _normalized_overlap(source_items: list[str], target_items: list[str]) -> list[str]:
        overlaps = []
        for source in source_items:
            for target in target_items:
                if source == target or source in target or target in source:
                    if target not in overlaps:
                        overlaps.append(target)
        return overlaps

    @classmethod
    def score_guide(cls, guide: ProjectGuide, teacher_pack: dict) -> dict:
        teacher_keywords = teacher_pack['keywords']
        teacher_disciplines = teacher_pack['disciplines']
        matched_keywords = cls._normalized_overlap(teacher_keywords, guide.target_keywords)
        matched_disciplines = cls._normalized_overlap(teacher_disciplines, guide.target_disciplines)

        score = 0
        reasons: list[str] = []
        match_category_tags: list[str] = []
        recommendation_labels: list[str] = list(guide.recommendation_tags or [])
        explanation_dimensions: list[dict] = []
        days_left = None

        if matched_keywords:
            keyword_score = min(40, 14 + len(matched_keywords) * 8)
            score += keyword_score
            reasons.append(f"指南主题与教师研究标签匹配：{', '.join(matched_keywords[:3])}。")
            match_category_tags.append('主题匹配型')
            explanation_dimensions.append(
                {
                    'key': 'keyword_match',
                    'label': '主题标签匹配',
                    'score': keyword_score,
                    'detail': f"命中 {len(matched_keywords)} 个主题标签：{', '.join(matched_keywords[:3])}",
                }
            )

        if matched_disciplines:
            discipline_score = min(25, 10 + len(matched_disciplines) * 6)
            score += discipline_score
            reasons.append(f"指南面向方向与教师所属学科/院系贴合：{', '.join(matched_disciplines[:2])}。")
            match_category_tags.append('学科匹配型')
            explanation_dimensions.append(
                {
                    'key': 'discipline_match',
                    'label': '学科方向匹配',
                    'score': discipline_score,
                    'detail': f"命中 {len(matched_disciplines)} 个学科/院系方向：{', '.join(matched_disciplines[:2])}",
                }
            )

        if teacher_pack['recent_activity_count'] >= 2:
            activity_score = 18
            score += activity_score
            reasons.append(f"教师在{teacher_pack['recent_cutoff_label']}保持成果活跃，具备持续申报基础。")
            match_category_tags.append('活跃度支撑型')
            explanation_dimensions.append(
                {
                    'key': 'activity_support',
                    'label': '活跃度支撑',
                    'score': activity_score,
                    'detail': f"近三年成果活跃度为 {teacher_pack['recent_activity_count']} 项，属于{teacher_pack['activity_level']}活跃区间。",
                }
            )
        elif teacher_pack['recent_activity_count'] == 1:
            activity_score = 10
            score += activity_score
            reasons.append(f"教师在{teacher_pack['recent_cutoff_label']}已有成果沉淀，可结合现有方向尝试申报。")
            match_category_tags.append('活跃度支撑型')
            explanation_dimensions.append(
                {
                    'key': 'activity_support',
                    'label': '活跃度支撑',
                    'score': activity_score,
                    'detail': f"近三年成果活跃度为 {teacher_pack['recent_activity_count']} 项，可作为申报基础。",
                }
            )

        if guide.application_deadline:
            days_left = (guide.application_deadline - timezone.now().date()).days
            if days_left >= 0:
                window_score = 8
                score += window_score
                reasons.append(f"指南仍在申报窗口内，距离截止约 {days_left} 天。")
                match_category_tags.append('窗口友好型')
                explanation_dimensions.append(
                    {
                        'key': 'application_window',
                        'label': '申报窗口友好度',
                        'score': window_score,
                        'detail': f"距离截止约 {days_left} 天，当前仍可准备申报。",
                    }
                )

        if guide.support_amount:
            support_score = 4
            score += support_score
            reasons.append(f"指南明确标注资助强度：{guide.support_amount}。")
            explanation_dimensions.append(
                {
                    'key': 'support_signal',
                    'label': '资助信息明确度',
                    'score': support_score,
                    'detail': f"指南已提供资助强度信息：{guide.support_amount}。",
                }
            )

        profile_bonus_score = 0
        if guide.rule_profile == 'KEYWORD_FIRST' and matched_keywords:
            profile_bonus_score = 8
        elif guide.rule_profile == 'DISCIPLINE_FIRST' and matched_disciplines:
            profile_bonus_score = 8
        elif guide.rule_profile == 'WINDOW_FIRST' and days_left is not None and days_left >= 0:
            profile_bonus_score = 6
        elif guide.rule_profile == 'ACTIVITY_FIRST' and teacher_pack['recent_activity_count'] >= 2:
            profile_bonus_score = 6

        if profile_bonus_score:
            score += profile_bonus_score
            reasons.append(f"该指南采用“{cls.RULE_PROFILE_BONUS_LABELS.get(guide.rule_profile, guide.rule_profile)}”规则档位，当前教师在该维度具备额外优势。")
            explanation_dimensions.append(
                {
                    'key': 'rule_profile_bonus',
                    'label': '规则配置加成',
                    'score': profile_bonus_score,
                    'detail': f"规则档位为 {cls.RULE_PROFILE_BONUS_LABELS.get(guide.rule_profile, guide.rule_profile)}。",
                }
            )

        if not reasons:
            reasons.append('当前教师画像与该指南尚无显著匹配特征，建议仅作备选参考。')

        if score >= 70:
            priority_label = '重点关注'
            recommendation_labels.append('高匹配')
        elif score >= 45:
            priority_label = '建议关注'
            recommendation_labels.append('建议优先评估')
        else:
            priority_label = '可作备选'
            recommendation_labels.append('可作备选')

        if matched_keywords:
            recommendation_labels.append('主题贴合')
        if matched_disciplines:
            recommendation_labels.append('方向贴合')
        if days_left is not None and 0 <= days_left <= 45:
            recommendation_labels.append('近期可申报')
        if teacher_pack['activity_level'] == 'HIGH':
            recommendation_labels.append('适合活跃教师')

        recommendation_summary = '；'.join(reasons[:2])

        return {
            'score': score,
            'reasons': reasons[:4],
            'matched_keywords': matched_keywords[:6],
            'matched_disciplines': matched_disciplines[:4],
            'match_category_tags': match_category_tags[:4],
            'recommendation_labels': list(dict.fromkeys(recommendation_labels))[:8],
            'explanation_dimensions': explanation_dimensions[:6],
            'priority_label': priority_label,
            'recommendation_summary': recommendation_summary,
        }

    @classmethod
    def build_admin_analysis(cls, recommendation_items, teacher_snapshot, compare_teacher_snapshot=None):
        priority_distribution: dict[str, int] = {}
        rule_profile_distribution: dict[str, int] = {}
        label_distribution: dict[str, int] = {}

        for item in recommendation_items:
            priority_distribution[item.priority_label] = priority_distribution.get(item.priority_label, 0) + 1
            rule_profile_label = item.get_rule_profile_display()
            rule_profile_distribution[rule_profile_label] = rule_profile_distribution.get(rule_profile_label, 0) + 1
            for label in item.recommendation_labels:
                label_distribution[label] = label_distribution.get(label, 0) + 1

        return {
            'teacher_name': teacher_snapshot['teacher_name'],
            'comparison_teacher_name': compare_teacher_snapshot['teacher_name'] if compare_teacher_snapshot else '',
            'priority_distribution': priority_distribution,
            'rule_profile_distribution': rule_profile_distribution,
            'top_labels': [
                {'label': label, 'count': count}
                for label, count in sorted(label_distribution.items(), key=lambda item: (-item[1], item[0]))[:6]
            ],
            'recommended_count': len(recommendation_items),
        }

    @classmethod
    def build_recommendations(cls, user, compare_user=None, include_admin_analysis: bool = False) -> dict:
        teacher_pack = cls.build_teacher_feature_pack(user)
        compare_teacher_pack = cls.build_teacher_feature_pack(compare_user) if compare_user else None
        guide_queryset = ProjectGuide.objects.filter(status='OPEN').order_by('application_deadline', '-updated_at')

        recommendation_items = []
        comparison_summary = {
            'primary_better_count': 0,
            'compare_better_count': 0,
            'tie_count': 0,
            'biggest_gap_title': '',
        }
        biggest_gap = None
        for guide in guide_queryset:
            scored = cls.score_guide(guide, teacher_pack)
            compare_scored = cls.score_guide(guide, compare_teacher_pack) if compare_teacher_pack else None

            if scored['score'] <= 0 and (not compare_scored or compare_scored['score'] <= 0):
                continue

            guide.recommendation_score = scored['score']
            guide.recommendation_reasons = scored['reasons']
            guide.matched_keywords = scored['matched_keywords']
            guide.matched_disciplines = scored['matched_disciplines']
            guide.match_category_tags = scored['match_category_tags']
            guide.recommendation_labels = scored['recommendation_labels']
            guide.explanation_dimensions = scored['explanation_dimensions']
            guide.priority_label = scored['priority_label']
            guide.recommendation_summary = scored['recommendation_summary']
            guide.compare_score = compare_scored['score'] if compare_scored else 0
            guide.compare_delta = scored['score'] - (compare_scored['score'] if compare_scored else 0)
            guide.comparison_summary = (
                f"当前教师高出 {guide.compare_delta} 分。"
                if compare_scored and guide.compare_delta > 0
                else f"对比教师高出 {abs(guide.compare_delta)} 分。"
                if compare_scored and guide.compare_delta < 0
                else '两位教师当前规则得分相同。'
                if compare_scored
                else ''
            )

            if compare_scored:
                if guide.compare_delta > 0:
                    comparison_summary['primary_better_count'] += 1
                elif guide.compare_delta < 0:
                    comparison_summary['compare_better_count'] += 1
                else:
                    comparison_summary['tie_count'] += 1

                gap = abs(guide.compare_delta)
                if biggest_gap is None or gap > biggest_gap[0]:
                    biggest_gap = (gap, guide.title)

            recommendation_items.append(guide)

        recommendation_items.sort(
            key=lambda item: (
                item.recommendation_score,
                item.application_deadline or date.max,
                item.updated_at,
            ),
            reverse=True,
        )

        if biggest_gap:
            comparison_summary['biggest_gap_title'] = biggest_gap[1]

        teacher_snapshot = {
            'user_id': user.id,
            'teacher_name': user.real_name or user.username,
            'keywords': teacher_pack['keywords'][:8],
            'disciplines': teacher_pack['disciplines'][:4],
            'recent_activity_count': teacher_pack['recent_activity_count'],
            'activity_level': teacher_pack['activity_level'],
        }
        comparison_teacher_snapshot = (
            {
                'user_id': compare_user.id,
                'teacher_name': compare_user.real_name or compare_user.username,
                'keywords': compare_teacher_pack['keywords'][:8],
                'disciplines': compare_teacher_pack['disciplines'][:4],
                'recent_activity_count': compare_teacher_pack['recent_activity_count'],
                'activity_level': compare_teacher_pack['activity_level'],
            }
            if compare_user and compare_teacher_pack
            else None
        )

        result = {
            'recommendations': recommendation_items[:8],
            'teacher_snapshot': teacher_snapshot,
            'comparison_teacher_snapshot': comparison_teacher_snapshot,
            'comparison_summary': comparison_summary if compare_user else None,
            'data_meta': {
                'source_note': '推荐规则基于教师研究方向、研究兴趣、论文关键词、学科信息与近三年成果活跃度实时计算，不依赖 RAG 或外部抓取。',
                'acceptance_scope': '本能力属于当前阶段扩展方向，以最小可用实现交付。',
                'future_extension_hint': '当规则特征、教师反馈样本和指南语义解析数据足够稳定后，才考虑进入更强模型化推荐；当前仍不引入复杂机器学习推荐模型。',
                'sorting_note': '默认按推荐分数、申报截止时间与最近更新时间综合排序，当前仍是规则增强路线。',
                'current_strategy': '规则增强型推荐（非复杂模型）',
            },
            'empty_state': '当前暂无明显匹配的项目指南，建议先完善研究方向标签或录入最新成果后再查看推荐。',
        }

        if include_admin_analysis:
            result['admin_analysis'] = cls.build_admin_analysis(
                recommendation_items[:8],
                teacher_snapshot,
                comparison_teacher_snapshot,
            )

        return result
