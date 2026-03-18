from __future__ import annotations

import re
from datetime import date

from django.contrib.auth import get_user_model
from django.utils import timezone

from achievements.models import AcademicService, IntellectualProperty, Paper, PaperKeyword, Project, TeachingAchievement
from users.services import get_teacher_profile

from .models import ProjectGuide


def split_text_tokens(raw_text: str) -> list[str]:
    return [
        item.strip()
        for item in re.split(r'[\s,，、；;|/]+', raw_text or '')
        if item.strip()
    ]


class ProjectGuideRecommendationService:
    @staticmethod
    def resolve_target_teacher(request, user_id: int | None = None):
        target_user_id = user_id or request.query_params.get('user_id')
        if not target_user_id:
            return request.user

        normalized_user_id = int(target_user_id)
        if request.user.id != normalized_user_id and not (request.user.is_staff or request.user.is_superuser):
            raise PermissionError('当前账号无权查看其他教师的推荐结果。')

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

        if matched_keywords:
            score += min(40, 14 + len(matched_keywords) * 8)
            reasons.append(f"指南主题与教师研究标签匹配：{', '.join(matched_keywords[:3])}。")
            match_category_tags.append('主题匹配型')

        if matched_disciplines:
            score += min(25, 10 + len(matched_disciplines) * 6)
            reasons.append(f"指南面向方向与教师所属学科/院系贴合：{', '.join(matched_disciplines[:2])}。")
            match_category_tags.append('学科匹配型')

        if teacher_pack['recent_activity_count'] >= 2:
            score += 18
            reasons.append(f"教师在{teacher_pack['recent_cutoff_label']}保持成果活跃，具备持续申报基础。")
            match_category_tags.append('活跃度支撑型')
        elif teacher_pack['recent_activity_count'] == 1:
            score += 10
            reasons.append(f"教师在{teacher_pack['recent_cutoff_label']}已有成果沉淀，可结合现有方向尝试申报。")
            match_category_tags.append('活跃度支撑型')

        if guide.application_deadline:
            days_left = (guide.application_deadline - timezone.now().date()).days
            if days_left >= 0:
                score += 8
                reasons.append(f"指南仍在申报窗口内，距离截止约 {days_left} 天。")
                match_category_tags.append('窗口友好型')

        if guide.support_amount:
            score += 4
            reasons.append(f"指南明确标注资助强度：{guide.support_amount}。")

        if not reasons:
            reasons.append('当前教师画像与该指南尚无显著匹配特征，建议仅作备选参考。')

        if score >= 70:
            priority_label = '重点关注'
        elif score >= 45:
            priority_label = '建议关注'
        else:
            priority_label = '可作备选'

        recommendation_summary = '；'.join(reasons[:2])

        return {
            'score': score,
            'reasons': reasons[:4],
            'matched_keywords': matched_keywords[:6],
            'matched_disciplines': matched_disciplines[:4],
            'match_category_tags': match_category_tags[:4],
            'priority_label': priority_label,
            'recommendation_summary': recommendation_summary,
        }

    @classmethod
    def build_recommendations(cls, user) -> dict:
        teacher_pack = cls.build_teacher_feature_pack(user)
        guide_queryset = ProjectGuide.objects.filter(status='OPEN').order_by('application_deadline', '-updated_at')

        recommendation_items = []
        for guide in guide_queryset:
            scored = cls.score_guide(guide, teacher_pack)
            if scored['score'] <= 0:
                continue

            guide.recommendation_score = scored['score']
            guide.recommendation_reasons = scored['reasons']
            guide.matched_keywords = scored['matched_keywords']
            guide.matched_disciplines = scored['matched_disciplines']
            guide.match_category_tags = scored['match_category_tags']
            guide.priority_label = scored['priority_label']
            guide.recommendation_summary = scored['recommendation_summary']
            recommendation_items.append(guide)

        recommendation_items.sort(
            key=lambda item: (
                item.recommendation_score,
                item.application_deadline or date.max,
                item.updated_at,
            ),
            reverse=True,
        )

        return {
            'recommendations': recommendation_items[:8],
            'teacher_snapshot': {
                'user_id': user.id,
                'teacher_name': user.real_name or user.username,
                'keywords': teacher_pack['keywords'][:8],
                'disciplines': teacher_pack['disciplines'][:4],
                'recent_activity_count': teacher_pack['recent_activity_count'],
            },
            'data_meta': {
                'source_note': '推荐规则基于教师研究方向、研究兴趣、论文关键词、学科信息与近三年成果活跃度实时计算，不依赖 RAG 或外部抓取。',
                'acceptance_scope': '本能力属于当前阶段扩展方向，以最小可用实现交付。',
                'future_extension_hint': '后续可在本接口基础上接入更复杂的智能推荐、政策解析或 RAG 检索层。',
                'sorting_note': '默认按推荐分数、申报截止时间与最近更新时间综合排序，当前仍是规则增强路线。',
                'current_strategy': '规则增强型推荐（非复杂模型）',
            },
            'empty_state': '当前暂无明显匹配的项目指南，建议先完善研究方向标签或录入最新成果后再查看推荐。',
        }
