from __future__ import annotations

import re
from datetime import date, timedelta
from uuid import uuid4

from django.contrib.auth import get_user_model
from django.db.models import Count, Q
from django.utils import timezone

from achievements.models import AcademicService, IntellectualProperty, Paper, PaperKeyword, Project, TeachingAchievement
from achievements.scoring_engine import TeacherScoringEngine
from achievements.visibility import APPROVED_STATUS
from users.access import COMPARE_SCOPE_MESSAGE, RECOMMENDATION_SCOPE_MESSAGE, ensure_admin_user, ensure_self_or_admin_user
from users.services import get_teacher_profile

from .models import ProjectGuide, ProjectGuideFavorite, ProjectGuideRecommendationRecord


def split_text_tokens(raw_text: str) -> list[str]:
    return [item.strip() for item in re.split(r'[\s,，、；;|/]+', raw_text or '') if item.strip()]


class ProjectGuideRecommendationService:
    RULE_PROFILE_BONUS_LABELS = {
        'BALANCED': '均衡规则',
        'KEYWORD_FIRST': '主题优先',
        'DISCIPLINE_FIRST': '学科优先',
        'WINDOW_FIRST': '窗口优先',
        'ACTIVITY_FIRST': '活跃度优先',
        'PORTRAIT_FIRST': '画像联动优先',
        'FOUNDATION_FIRST': '申报基础优先',
    }

    DEFAULT_RULE_CONFIG = {
        'keyword_bonus': 0,
        'discipline_bonus': 0,
        'activity_bonus': 0,
        'window_bonus': 0,
        'support_bonus': 0,
        'portrait_bonus': 0,
    }

    RULE_PROFILE_PRESETS = {
        'BALANCED': {},
        'KEYWORD_FIRST': {'keyword_bonus': 6},
        'DISCIPLINE_FIRST': {'discipline_bonus': 6},
        'WINDOW_FIRST': {'window_bonus': 6},
        'ACTIVITY_FIRST': {'activity_bonus': 6},
        'PORTRAIT_FIRST': {'portrait_bonus': 8, 'keyword_bonus': 2},
        'FOUNDATION_FIRST': {'activity_bonus': 4, 'discipline_bonus': 3, 'support_bonus': 2},
    }

    PORTRAIT_DIMENSION_LABELS = {
        'academic_output': '基础学术产出',
        'funding_support': '经费与项目攻关',
        'ip_strength': '知识产权沉淀',
        'talent_training': '人才培养成效',
        'academic_reputation': '学术活跃与声誉',
        'interdisciplinary': '跨学科融合度',
    }

    FEEDBACK_LABELS = {
        'INTERESTED': '感兴趣',
        'NOT_RELEVANT': '暂不相关',
        'PLAN_TO_APPLY': '计划申报',
        'APPLIED': '已申报',
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

    @classmethod
    def build_teacher_feature_pack(cls, user) -> dict:
        profile = get_teacher_profile(user)
        profile_keywords = list(user.research_direction or [])
        profile_keywords.extend(split_text_tokens(profile.research_interests if profile else ''))
        profile_keywords.extend(split_text_tokens(profile.discipline if profile else ''))

        paper_keywords = list(
            PaperKeyword.objects.filter(paper__teacher=user, paper__status=APPROVED_STATUS)
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
            Paper.objects.filter(teacher=user, status=APPROVED_STATUS, date_acquired__gte=recent_cutoff).count()
            + Project.objects.filter(teacher=user, status=APPROVED_STATUS, date_acquired__gte=recent_cutoff).count()
            + IntellectualProperty.objects.filter(teacher=user, status=APPROVED_STATUS, date_acquired__gte=recent_cutoff).count()
            + TeachingAchievement.objects.filter(teacher=user, status=APPROVED_STATUS, date_acquired__gte=recent_cutoff).count()
            + AcademicService.objects.filter(teacher=user, status=APPROVED_STATUS, date_acquired__gte=recent_cutoff).count()
        )

        radar_result = TeacherScoringEngine.get_comprehensive_radar_data(user)
        portrait_dimensions = sorted(radar_result['radar_dimensions'], key=lambda item: item['value'], reverse=True)
        portrait_map = {item['key']: item for item in radar_result['radar_dimensions']}

        return {
            'teacher': user,
            'keywords': all_keywords[:20],
            'disciplines': discipline_tags[:8],
            'recent_activity_count': recent_activity_count,
            'recent_cutoff_label': f'{cutoff_year} 年以来',
            'activity_level': 'HIGH' if recent_activity_count >= 4 else 'MEDIUM' if recent_activity_count >= 2 else 'LOW',
            'portrait_total_score': radar_result['total_score'],
            'portrait_top_dimensions': portrait_dimensions[:3],
            'portrait_dimension_map': portrait_map,
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
    def build_rule_config_snapshot(cls, guide: ProjectGuide) -> dict:
        snapshot = dict(cls.DEFAULT_RULE_CONFIG)
        snapshot.update(cls.RULE_PROFILE_PRESETS.get(guide.rule_profile, {}))
        for key, value in (guide.rule_config or {}).items():
            if key in snapshot:
                try:
                    snapshot[key] = max(0, min(int(value), 20))
                except (TypeError, ValueError):
                    continue
        return snapshot

    @classmethod
    def build_portrait_dimension_links(cls, teacher_pack: dict, scored: dict, config: dict) -> list[dict]:
        portrait_map = teacher_pack['portrait_dimension_map']
        links = []

        def append_link(key: str, relation: str, detail: str):
            if key not in portrait_map or any(item['key'] == key for item in links):
                return
            links.append(
                {
                    'key': key,
                    'label': cls.PORTRAIT_DIMENSION_LABELS.get(key, key),
                    'relation': relation,
                    'current_value': portrait_map[key]['value'],
                    'detail': detail,
                }
            )

        if scored['matched_keywords']:
            append_link('interdisciplinary', 'direct', '主题关键词匹配会优先联动画像中的跨学科融合度。')
        if scored['matched_disciplines']:
            append_link('funding_support', 'support', '学科方向贴合可支撑项目攻关与组织申报能力解释。')
        if teacher_pack['recent_activity_count'] >= 2:
            append_link('academic_output', 'support', '近三年成果活跃度可作为当前指南推荐的申报基础。')
        if config.get('portrait_bonus', 0) > 0 or teacher_pack['portrait_total_score'] >= 60:
            strongest = teacher_pack['portrait_top_dimensions'][0] if teacher_pack['portrait_top_dimensions'] else None
            if strongest:
                append_link(
                    strongest['key'],
                    'highlight',
                    f"当前指南采用画像联动加成，优先参考教师在“{strongest['name']}”维度的既有优势。",
                )
        return links[:3]

    @classmethod
    def build_supporting_records(cls, user, scored: dict) -> list[dict]:
        records: list[dict] = []
        seen_keys: set[tuple[str, int]] = set()
        matched_keywords = scored.get('matched_keywords') or []
        portrait_dimension_links = scored.get('portrait_dimension_links') or []

        def append_record(record_type: str, instance, reason: str, detail: str):
            if not instance:
                return

            record_key = (record_type, instance.id)
            if record_key in seen_keys:
                return

            seen_keys.add(record_key)
            records.append(
                {
                    'id': instance.id,
                    'type': record_type,
                    'title': instance.title,
                    'detail': detail,
                    'date_acquired': instance.date_acquired.isoformat(),
                    'reason': reason,
                }
            )

        if matched_keywords:
            keyword_filter = Q()
            for keyword in matched_keywords[:4]:
                keyword_filter |= (
                    Q(paperkeyword__keyword__name__icontains=keyword)
                    | Q(title__icontains=keyword)
                    | Q(abstract__icontains=keyword)
                )

            keyword_papers = (
                Paper.objects.filter(teacher=user, status=APPROVED_STATUS)
                .filter(keyword_filter)
                .distinct()
                .order_by('-date_acquired', '-created_at')[:2]
            )
            for paper in keyword_papers:
                overlaps = [
                    keyword
                    for keyword in matched_keywords
                    if keyword in paper.title or keyword in (paper.abstract or '')
                ] or matched_keywords[:2]
                append_record(
                    'paper',
                    paper,
                    f"命中主题关键词：{'、'.join(overlaps[:2])}。",
                    f'{paper.get_paper_type_display()} / {paper.journal_name}',
                )

        dimension_to_candidate = {
            'funding_support': (
                'project',
                Project.objects.filter(teacher=user, status=APPROVED_STATUS).order_by('-date_acquired', '-created_at').first(),
                '当前推荐会参考教师已有项目攻关基础。',
                lambda item: f'{item.get_level_display()} / {item.get_role_display()}',
            ),
            'ip_strength': (
                'intellectual_property',
                IntellectualProperty.objects.filter(teacher=user, status=APPROVED_STATUS).order_by('-date_acquired', '-created_at').first(),
                '当前推荐会参考教师已有知识产权沉淀。',
                lambda item: f'{item.get_ip_type_display()} / 登记号 {item.registration_number}',
            ),
            'talent_training': (
                'teaching_achievement',
                TeachingAchievement.objects.filter(teacher=user, status=APPROVED_STATUS).order_by('-date_acquired', '-created_at').first(),
                '当前推荐会参考教师已有教学与人才培养成果。',
                lambda item: f'{item.get_achievement_type_display()} / {item.level}',
            ),
            'academic_reputation': (
                'academic_service',
                AcademicService.objects.filter(teacher=user, status=APPROVED_STATUS).order_by('-date_acquired', '-created_at').first(),
                '当前推荐会参考教师已有学术共同体贡献记录。',
                lambda item: f'{item.get_service_type_display()} / {item.organization}',
            ),
        }

        for link in portrait_dimension_links:
            candidate = dimension_to_candidate.get(link.get('key'))
            if not candidate:
                continue

            record_type, instance, reason, detail_builder = candidate
            append_record(record_type, instance, reason, detail_builder(instance) if instance else '')
            if len(records) >= 3:
                break

        if len(records) < 3:
            latest_project = Project.objects.filter(teacher=user, status=APPROVED_STATUS).order_by('-date_acquired', '-created_at').first()
            append_record(
                'project',
                latest_project,
                '当前推荐同时参考教师近期项目活跃度。',
                f'{latest_project.get_level_display()} / {latest_project.get_role_display()}' if latest_project else '',
            )

        if len(records) < 3:
            latest_paper = Paper.objects.filter(teacher=user, status=APPROVED_STATUS).order_by('-date_acquired', '-created_at').first()
            append_record(
                'paper',
                latest_paper,
                '当前推荐同时参考教师近期论文产出表现。',
                f'{latest_paper.get_paper_type_display()} / {latest_paper.journal_name}' if latest_paper else '',
            )

        return records[:3]

    @classmethod
    def _append_dimension(cls, bucket: list[dict], *, key: str, label: str, score: int, detail: str):
        bucket.append({'key': key, 'label': label, 'score': int(score), 'max_score': 100, 'detail': detail})

    @classmethod
    def _finalize_dimensions(cls, dimensions: list[dict], total_score: int) -> list[dict]:
        final_total = max(total_score, 1)
        for item in dimensions:
            item['share_percent'] = round(item['score'] / final_total * 100, 1)
        return dimensions[:6]

    @classmethod
    def score_guide(cls, guide: ProjectGuide, teacher_pack: dict) -> dict:
        teacher_keywords = teacher_pack['keywords']
        teacher_disciplines = teacher_pack['disciplines']
        matched_keywords = cls._normalized_overlap(teacher_keywords, guide.target_keywords)
        matched_disciplines = cls._normalized_overlap(teacher_disciplines, guide.target_disciplines)
        config = cls.build_rule_config_snapshot(guide)

        score = 0
        reasons: list[str] = []
        match_category_tags: list[str] = []
        recommendation_labels: list[str] = list(guide.recommendation_tags or [])
        explanation_dimensions: list[dict] = []
        days_left = None

        if matched_keywords:
            keyword_score = min(40, 14 + len(matched_keywords) * 8 + config['keyword_bonus'])
            score += keyword_score
            reasons.append(f"指南主题与教师研究标签匹配：{', '.join(matched_keywords[:3])}。")
            match_category_tags.append('主题匹配型')
            cls._append_dimension(
                explanation_dimensions,
                key='keyword_match',
                label='主题标签匹配',
                score=keyword_score,
                detail=f"命中 {len(matched_keywords)} 个主题标签：{', '.join(matched_keywords[:3])}",
            )

        if matched_disciplines:
            discipline_score = min(25, 10 + len(matched_disciplines) * 6 + config['discipline_bonus'])
            score += discipline_score
            reasons.append(f"指南面向方向与教师所属学科/院系贴合：{', '.join(matched_disciplines[:2])}。")
            match_category_tags.append('学科匹配型')
            cls._append_dimension(
                explanation_dimensions,
                key='discipline_match',
                label='学科方向匹配',
                score=discipline_score,
                detail=f"命中 {len(matched_disciplines)} 个学科/院系方向：{', '.join(matched_disciplines[:2])}",
            )

        if teacher_pack['recent_activity_count'] >= 2:
            activity_score = 18 + config['activity_bonus']
            score += activity_score
            reasons.append(f"教师在{teacher_pack['recent_cutoff_label']}保持成果活跃，具备持续申报基础。")
            match_category_tags.append('活跃度支撑型')
            cls._append_dimension(
                explanation_dimensions,
                key='activity_support',
                label='活跃度支撑',
                score=activity_score,
                detail=f"近三年成果活跃度为 {teacher_pack['recent_activity_count']} 项，属于{teacher_pack['activity_level']}活跃区间。",
            )
        elif teacher_pack['recent_activity_count'] == 1:
            activity_score = 10 + min(config['activity_bonus'], 4)
            score += activity_score
            reasons.append(f"教师在{teacher_pack['recent_cutoff_label']}已有成果沉淀，可结合现有方向尝试申报。")
            match_category_tags.append('活跃度支撑型')
            cls._append_dimension(
                explanation_dimensions,
                key='activity_support',
                label='活跃度支撑',
                score=activity_score,
                detail=f"近三年成果活跃度为 {teacher_pack['recent_activity_count']} 项，可作为申报基础。",
            )

        if guide.application_deadline:
            days_left = (guide.application_deadline - timezone.now().date()).days
            if days_left >= 0:
                window_score = 8 + config['window_bonus']
                score += window_score
                reasons.append(f"指南仍在申报窗口内，距离截止约 {days_left} 天。")
                match_category_tags.append('窗口友好型')
                cls._append_dimension(
                    explanation_dimensions,
                    key='application_window',
                    label='申报窗口友好度',
                    score=window_score,
                    detail=f"距离截止约 {days_left} 天，当前仍可准备申报。",
                )

        if guide.support_amount:
            support_score = 4 + config['support_bonus']
            score += support_score
            reasons.append(f"指南明确标注资助强度：{guide.support_amount}。")
            cls._append_dimension(
                explanation_dimensions,
                key='support_signal',
                label='资助信息明确度',
                score=support_score,
                detail=f"指南已提供资助强度信息：{guide.support_amount}。",
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
        elif guide.rule_profile == 'PORTRAIT_FIRST' and teacher_pack['portrait_total_score'] >= 50:
            profile_bonus_score = 8
        elif guide.rule_profile == 'FOUNDATION_FIRST' and (
            teacher_pack['recent_activity_count'] >= 2 or matched_disciplines
        ):
            profile_bonus_score = 6

        if config['portrait_bonus'] > 0 and teacher_pack['portrait_total_score'] >= 40:
            profile_bonus_score += config['portrait_bonus']

        if profile_bonus_score:
            score += profile_bonus_score
            reasons.append(
                f"该指南采用“{cls.RULE_PROFILE_BONUS_LABELS.get(guide.rule_profile, guide.rule_profile)}”规则档位，当前教师在该维度具备额外优势。"
            )
            cls._append_dimension(
                explanation_dimensions,
                key='rule_profile_bonus',
                label='规则配置加成',
                score=profile_bonus_score,
                detail=(
                    f"规则档位为 {cls.RULE_PROFILE_BONUS_LABELS.get(guide.rule_profile, guide.rule_profile)}，"
                    f"细化配置为 {config}。"
                ),
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
        if config.get('portrait_bonus', 0) > 0 or guide.rule_profile == 'PORTRAIT_FIRST':
            recommendation_labels.append('画像联动')

        portrait_dimension_links = cls.build_portrait_dimension_links(
            teacher_pack,
            {'matched_keywords': matched_keywords, 'matched_disciplines': matched_disciplines},
            config,
        )
        recommendation_summary = '；'.join(reasons[:2])

        return {
            'score': int(score),
            'reasons': reasons[:4],
            'matched_keywords': matched_keywords[:6],
            'matched_disciplines': matched_disciplines[:4],
            'match_category_tags': match_category_tags[:4],
            'recommendation_labels': list(dict.fromkeys(recommendation_labels))[:8],
            'explanation_dimensions': cls._finalize_dimensions(explanation_dimensions, int(score)),
            'priority_label': priority_label,
            'recommendation_summary': recommendation_summary,
            'portrait_dimension_links': portrait_dimension_links,
        }

    @classmethod
    def build_admin_analysis(cls, recommendation_items, teacher_snapshot, compare_teacher_snapshot=None, feedback_summary=None):
        priority_distribution: dict[str, int] = {}
        rule_profile_distribution: dict[str, int] = {}
        label_distribution: dict[str, int] = {}
        feedback_distribution: dict[str, int] = {}
        favorited_count = 0

        for item in recommendation_items:
            priority_distribution[item.priority_label] = priority_distribution.get(item.priority_label, 0) + 1
            rule_profile_label = item.get_rule_profile_display()
            rule_profile_distribution[rule_profile_label] = rule_profile_distribution.get(rule_profile_label, 0) + 1
            if getattr(item, 'is_favorited', False):
                favorited_count += 1
            feedback_label = getattr(item, 'latest_feedback_label', '')
            if feedback_label:
                feedback_distribution[feedback_label] = feedback_distribution.get(feedback_label, 0) + 1
            for label in item.recommendation_labels:
                label_distribution[label] = label_distribution.get(label, 0) + 1

        return {
            'teacher_name': teacher_snapshot['teacher_name'],
            'comparison_teacher_name': compare_teacher_snapshot['teacher_name'] if compare_teacher_snapshot else '',
            'priority_distribution': priority_distribution,
            'rule_profile_distribution': rule_profile_distribution,
            'feedback_distribution': feedback_distribution,
            'favorited_count': favorited_count,
            'responded_guide_count': feedback_summary.get('responded_guide_count', 0) if feedback_summary else 0,
            'response_rate': feedback_summary.get('response_rate') if feedback_summary else 0,
            'positive_feedback_count': feedback_summary.get('positive_feedback_count', 0) if feedback_summary else 0,
            'negative_feedback_count': feedback_summary.get('negative_feedback_count', 0) if feedback_summary else 0,
            'plan_to_apply_count': feedback_summary.get('plan_to_apply_count', 0) if feedback_summary else 0,
            'applied_count': feedback_summary.get('applied_count', 0) if feedback_summary else 0,
            'feedback_record_count': feedback_summary.get('feedback_record_count', 0) if feedback_summary else 0,
            'latest_feedback_at': feedback_summary.get('latest_feedback_at') if feedback_summary else '',
            'top_labels': [
                {'label': label, 'count': count}
                for label, count in sorted(label_distribution.items(), key=lambda item: (-item[1], item[0]))[:6]
            ],
            'recommended_count': len(recommendation_items),
        }

    @classmethod
    def build_history_preview(cls, teacher, limit: int = 6) -> list[ProjectGuideRecommendationRecord]:
        return list(
            ProjectGuideRecommendationRecord.objects.select_related('requested_by', 'guide')
            .filter(teacher=teacher)
            .order_by('-generated_at', '-id')[:limit]
        )

    @classmethod
    def build_feedback_summary(cls, teacher, *, current_recommendation_count: int = 0) -> dict:
        records = list(
            ProjectGuideRecommendationRecord.objects.select_related('guide')
            .filter(teacher=teacher)
            .exclude(feedback_signal='')
            .order_by('guide_id', '-last_feedback_at', '-generated_at', '-id')
        )
        latest_records_by_guide: dict[int, ProjectGuideRecommendationRecord] = {}
        for record in records:
            if not record.guide_id:
                continue
            if record.guide_id not in latest_records_by_guide:
                latest_records_by_guide[record.guide_id] = record

        latest_records = list(latest_records_by_guide.values())
        latest_records.sort(
            key=lambda item: item.last_feedback_at or item.generated_at,
            reverse=True,
        )

        distribution: dict[str, int] = {}
        signal_counts = {
            'INTERESTED': 0,
            'NOT_RELEVANT': 0,
            'PLAN_TO_APPLY': 0,
            'APPLIED': 0,
        }
        for record in latest_records:
            label = cls.FEEDBACK_LABELS.get(record.feedback_signal, record.feedback_signal)
            distribution[label] = distribution.get(label, 0) + 1
            if record.feedback_signal in signal_counts:
                signal_counts[record.feedback_signal] += 1

        favorite_count = ProjectGuideFavorite.objects.filter(teacher=teacher).count()
        responded_guide_count = len(latest_records)
        response_rate = (
            round(responded_guide_count / current_recommendation_count * 100, 1)
            if current_recommendation_count > 0
            else 0
        )
        latest_feedback_time = latest_records[0].last_feedback_at if latest_records else None

        return {
            'distribution': distribution,
            'feedback_record_count': len(records),
            'responded_guide_count': responded_guide_count,
            'current_recommendation_count': current_recommendation_count,
            'response_rate': response_rate,
            'favorite_count': favorite_count,
            'interested_count': signal_counts['INTERESTED'],
            'plan_to_apply_count': signal_counts['PLAN_TO_APPLY'],
            'applied_count': signal_counts['APPLIED'],
            'not_relevant_count': signal_counts['NOT_RELEVANT'],
            'positive_feedback_count': (
                signal_counts['INTERESTED'] + signal_counts['PLAN_TO_APPLY'] + signal_counts['APPLIED']
            ),
            'negative_feedback_count': signal_counts['NOT_RELEVANT'],
            'latest_feedback_at': latest_feedback_time.isoformat() if latest_feedback_time else '',
            'recent_feedback_items': [
                {
                    'guide_id': record.guide_id,
                    'guide_title': record.guide_title_snapshot,
                    'feedback_signal': record.feedback_signal,
                    'feedback_label': record.get_feedback_signal_display(),
                    'feedback_note': record.feedback_note,
                    'last_feedback_at': (record.last_feedback_at or record.generated_at).isoformat(),
                }
                for record in latest_records[:5]
            ],
            'strategy_note': '当前反馈闭环只采集轻量显式信号，用于人工复盘和后续规则迭代，不直接训练复杂排序模型。',
        }

    @classmethod
    def build_portrait_link_summary(cls, teacher_pack: dict) -> dict:
        top_dimensions = teacher_pack['portrait_top_dimensions']
        return {
            'teacher_total_score': teacher_pack['portrait_total_score'],
            'top_dimensions': [{'key': item['key'], 'name': item['name'], 'value': item['value']} for item in top_dimensions],
            'link_note': '当前推荐解释会把项目指南匹配结果与教师画像中的优势维度、活跃度和跨学科特征联动展示。',
        }

    @classmethod
    def get_favorite_ids(cls, teacher) -> list[int]:
        return list(ProjectGuideFavorite.objects.filter(teacher=teacher).values_list('guide_id', flat=True))

    @classmethod
    def persist_recommendation_history(cls, *, teacher, requested_by, recommendation_items, favorite_ids: set[int]) -> str:
        batch_token = str(uuid4())
        records = []
        for item in recommendation_items:
            records.append(
                ProjectGuideRecommendationRecord(
                    teacher=teacher,
                    requested_by=requested_by,
                    guide=item,
                    batch_token=batch_token,
                    guide_title_snapshot=item.title,
                    guide_status_snapshot=item.status,
                    rule_profile_snapshot=item.rule_profile,
                    recommendation_score=item.recommendation_score,
                    priority_label=item.priority_label,
                    recommendation_reasons=item.recommendation_reasons,
                    explanation_dimensions=item.explanation_dimensions,
                    recommendation_labels=item.recommendation_labels,
                    matched_keywords=item.matched_keywords,
                    matched_disciplines=item.matched_disciplines,
                    portrait_dimension_links=item.portrait_dimension_links,
                    is_favorited_snapshot=item.id in favorite_ids,
                    feedback_signal=getattr(item, 'latest_feedback_signal', '') or '',
                    feedback_note=getattr(item, 'latest_feedback_note', '') or '',
                )
            )
        if records:
            ProjectGuideRecommendationRecord.objects.bulk_create(records)
        return batch_token

    @classmethod
    def build_recommendations(cls, user, *, requested_by=None, compare_user=None, include_admin_analysis: bool = False) -> dict:
        teacher_pack = cls.build_teacher_feature_pack(user)
        compare_teacher_pack = cls.build_teacher_feature_pack(compare_user) if compare_user else None
        favorite_ids = set(cls.get_favorite_ids(user))
        latest_feedback_records = {}
        for record in (
            ProjectGuideRecommendationRecord.objects.filter(teacher=user)
            .exclude(feedback_signal='')
            .order_by('guide_id', '-generated_at', '-id')
        ):
            if record.guide_id and record.guide_id not in latest_feedback_records:
                latest_feedback_records[record.guide_id] = record

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

            latest_feedback = latest_feedback_records.get(guide.id)
            guide.recommendation_score = scored['score']
            guide.recommendation_reasons = scored['reasons']
            guide.matched_keywords = scored['matched_keywords']
            guide.matched_disciplines = scored['matched_disciplines']
            guide.match_category_tags = scored['match_category_tags']
            guide.recommendation_labels = scored['recommendation_labels']
            guide.explanation_dimensions = scored['explanation_dimensions']
            guide.priority_label = scored['priority_label']
            guide.recommendation_summary = scored['recommendation_summary']
            guide.portrait_dimension_links = scored['portrait_dimension_links']
            guide.supporting_records = cls.build_supporting_records(user, scored)
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
            guide.is_favorited = guide.id in favorite_ids
            guide.latest_feedback_signal = latest_feedback.feedback_signal if latest_feedback else ''
            guide.latest_feedback_label = latest_feedback.get_feedback_signal_display() if latest_feedback else ''
            guide.latest_feedback_note = latest_feedback.feedback_note if latest_feedback else ''
            guide.last_feedback_at = latest_feedback.last_feedback_at if latest_feedback else None

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
            key=lambda item: (item.recommendation_score, item.application_deadline or date.max, item.updated_at),
            reverse=True,
        )
        recommendation_items = recommendation_items[:8]

        if biggest_gap:
            comparison_summary['biggest_gap_title'] = biggest_gap[1]

        history_batch_token = cls.persist_recommendation_history(
            teacher=user,
            requested_by=requested_by or user,
            recommendation_items=recommendation_items,
            favorite_ids=favorite_ids,
        )

        teacher_snapshot = {
            'user_id': user.id,
            'teacher_name': user.real_name or user.username,
            'keywords': teacher_pack['keywords'][:8],
            'disciplines': teacher_pack['disciplines'][:4],
            'recent_activity_count': teacher_pack['recent_activity_count'],
            'activity_level': teacher_pack['activity_level'],
            'portrait_total_score': teacher_pack['portrait_total_score'],
            'portrait_top_dimensions': [
                {'key': item['key'], 'name': item['name'], 'value': item['value']}
                for item in teacher_pack['portrait_top_dimensions']
            ],
        }
        comparison_teacher_snapshot = (
            {
                'user_id': compare_user.id,
                'teacher_name': compare_user.real_name or compare_user.username,
                'keywords': compare_teacher_pack['keywords'][:8],
                'disciplines': compare_teacher_pack['disciplines'][:4],
                'recent_activity_count': compare_teacher_pack['recent_activity_count'],
                'activity_level': compare_teacher_pack['activity_level'],
                'portrait_total_score': compare_teacher_pack['portrait_total_score'],
                'portrait_top_dimensions': [
                    {'key': item['key'], 'name': item['name'], 'value': item['value']}
                    for item in compare_teacher_pack['portrait_top_dimensions']
                ],
            }
            if compare_user and compare_teacher_pack
            else None
        )

        feedback_summary = cls.build_feedback_summary(
            user,
            current_recommendation_count=len(recommendation_items),
        )

        result = {
            'recommendations': recommendation_items,
            'teacher_snapshot': teacher_snapshot,
            'comparison_teacher_snapshot': comparison_teacher_snapshot,
            'comparison_summary': comparison_summary if compare_user else None,
            'favorites': {'guide_ids': sorted(favorite_ids), 'total_count': len(favorite_ids)},
            'history_preview': cls.build_history_preview(user),
            'feedback_summary': feedback_summary,
            'portrait_link_summary': cls.build_portrait_link_summary(teacher_pack),
            'history_batch_token': history_batch_token,
            'data_meta': {
                'source_note': '推荐规则基于教师研究方向、研究兴趣、论文关键词、学科信息、画像维度与近三年成果活跃度实时计算，不依赖 RAG 或外部抓取。',
                'acceptance_scope': '本能力属于当前阶段扩展方向，以最小可用实现交付。',
                'future_extension_hint': '当规则特征、教师反馈样本和指南语义解析数据足够稳定后，才考虑进入更强模型化推荐；当前仍不引入复杂机器学习推荐模型。',
                'sorting_note': '默认按推荐分数、申报截止时间与最近更新时间综合排序，当前仍是规则增强路线。',
                'current_strategy': '规则增强型推荐（非复杂模型）',
                'feedback_scope_note': '当前反馈机制只采集轻量显式信号，用于后续规则迭代与人工复盘，不直接训练复杂模型。',
                'history_scope_note': '当前推荐历史记录的是规则增强结果快照与反馈信号，尚不等同于完整推荐实验平台。',
                'favorite_scope_note': '收藏已持久化到后端，可跨会话保留。',
                'portrait_link_note': '推荐解释已增加与教师画像维度的联动说明，帮助理解为什么推荐这个指南。',
                'feedback_ranking_boundary': '当前仅预留反馈影响排序的数据边界，暂不根据少量反馈直接重排推荐结果。',
                'interaction_enabled': bool(requested_by and requested_by.id == user.id),
            },
            'empty_state': '当前暂无明显匹配的项目指南，建议先完善研究方向标签或录入最新成果后再查看推荐。',
        }

        if include_admin_analysis:
            result['admin_analysis'] = cls.build_admin_analysis(
                recommendation_items,
                teacher_snapshot,
                comparison_teacher_snapshot,
                feedback_summary=feedback_summary,
            )

        return result

    @classmethod
    def toggle_favorite(cls, *, teacher, guide: ProjectGuide, is_favorited: bool) -> dict:
        if is_favorited:
            ProjectGuideFavorite.objects.get_or_create(teacher=teacher, guide=guide)
        else:
            ProjectGuideFavorite.objects.filter(teacher=teacher, guide=guide).delete()
        favorite_ids = cls.get_favorite_ids(teacher)
        return {
            'guide_id': guide.id,
            'is_favorited': is_favorited,
            'favorite_ids': favorite_ids,
            'favorite_count': len(favorite_ids),
        }

    @classmethod
    def capture_feedback(cls, *, teacher, guide: ProjectGuide, feedback_signal: str, feedback_note: str) -> dict:
        latest_record = (
            ProjectGuideRecommendationRecord.objects.filter(teacher=teacher, guide=guide)
            .order_by('-generated_at', '-id')
            .first()
        )

        if latest_record is None:
            teacher_pack = cls.build_teacher_feature_pack(teacher)
            scored = cls.score_guide(guide, teacher_pack)
            latest_record = ProjectGuideRecommendationRecord.objects.create(
                teacher=teacher,
                requested_by=teacher,
                guide=guide,
                batch_token=str(uuid4()),
                guide_title_snapshot=guide.title,
                guide_status_snapshot=guide.status,
                rule_profile_snapshot=guide.rule_profile,
                recommendation_score=scored['score'],
                priority_label=scored['priority_label'],
                recommendation_reasons=scored['reasons'],
                explanation_dimensions=scored['explanation_dimensions'],
                recommendation_labels=scored['recommendation_labels'],
                matched_keywords=scored['matched_keywords'],
                matched_disciplines=scored['matched_disciplines'],
                portrait_dimension_links=scored['portrait_dimension_links'],
                is_favorited_snapshot=ProjectGuideFavorite.objects.filter(teacher=teacher, guide=guide).exists(),
            )

        latest_record.feedback_signal = feedback_signal
        latest_record.feedback_note = feedback_note.strip()
        latest_record.last_feedback_at = timezone.now()
        latest_record.save(update_fields=['feedback_signal', 'feedback_note', 'last_feedback_at'])

        return {
            'guide_id': guide.id,
            'feedback_signal': latest_record.feedback_signal,
            'feedback_label': latest_record.get_feedback_signal_display(),
            'feedback_note': latest_record.feedback_note,
            'last_feedback_at': latest_record.last_feedback_at,
        }

    @classmethod
    def build_lifecycle_summary(cls):
        queryset = ProjectGuide.objects.all()
        now = timezone.now().date()
        warning_deadline = now + timedelta(days=30)
        status_distribution = {item['status']: item['count'] for item in queryset.values('status').annotate(count=Count('id'))}
        rule_profile_distribution = {
            item['rule_profile']: item['count']
            for item in queryset.values('rule_profile').annotate(count=Count('id'))
        }

        return {
            'total_count': queryset.count(),
            'draft_count': status_distribution.get('DRAFT', 0),
            'open_count': status_distribution.get('OPEN', 0),
            'closed_count': status_distribution.get('CLOSED', 0),
            'archived_count': status_distribution.get('ARCHIVED', 0),
            'deadline_warning_count': queryset.filter(
                status='OPEN',
                application_deadline__isnull=False,
                application_deadline__gte=now,
                application_deadline__lte=warning_deadline,
            ).count(),
            'stale_open_count': queryset.filter(status='OPEN').filter(
                Q(application_deadline__isnull=True) | Q(updated_at__lt=timezone.now() - timedelta(days=60))
            ).count(),
            'config_coverage_count': queryset.exclude(rule_config={}).count(),
            'status_distribution': status_distribution,
            'rule_profile_distribution': rule_profile_distribution,
        }
