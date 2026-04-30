from __future__ import annotations

import csv
import io
from collections import defaultdict
from datetime import date
from decimal import Decimal

from django.contrib.auth import get_user_model

from users.title_catalog import TEACHER_PROFESSIONAL_TITLES

from .models import AcademicService, IntellectualProperty, Paper, Project, RuleBasedAchievement
from .rule_scoring import build_conflict_group_key
from .scoring_engine import TeacherScoringEngine
from .visibility import APPROVED_STATUS

ACHIEVEMENT_TYPE_LABELS = {
    'all': '全部成果',
    'paper': '学术产出',
    'project': '科研项目',
    'award_transform': '奖励与转化',
    'platform_pop': '平台科普',
    'ip': '奖励与转化',
    'service': '平台科普',
}

RANKING_MODE_LABELS = {
    'total_score': '核心科研积分',
    'achievement_total': '成果数量',
    'paper_count': '学术产出数量',
    'project_count': '科研项目数量',
    'paper_book_score': '学术产出积分',
    'project_score': '项目竞争积分',
    'award_transform_score': '奖励转化积分',
    'platform_pop_score': '平台科普积分',
    'collaboration_count': '合作关系',
}

DEFAULT_TEACHER_TITLE_FILTERS = list(TEACHER_PROFESSIONAL_TITLES)

ZERO_RULE_METRICS = TeacherScoringEngine._collect_metrics_from_records([])

RULE_BUCKET_TO_COUNT_FIELD = {
    'paper': 'paper_count',
    'project': 'project_count',
    'ip': 'ip_count',
    'service': 'service_count',
}


def parse_bool_query_param(value: str | None) -> bool | None:
    normalized = (value or '').strip().lower()
    if normalized in {'1', 'true', 'yes'}:
        return True
    if normalized in {'0', 'false', 'no'}:
        return False
    return None


def normalize_year(raw_value):
    if raw_value in (None, ''):
        return None
    try:
        return int(raw_value)
    except (TypeError, ValueError):
        return None


def build_management_data_meta():
    return {
        'source_note': (
            '学院看板以学院审核通过的规则化成果为积分主口径，同时兼容尚未迁入新规则体系的历史成果数量。'
            '成果数量默认做去重统计，积分统计以教师生效积分为准。'
        ),
        'acceptance_scope': '学院审批、成果统计、教师成果总览链路已纳入当前阶段真实应用范围。',
        'future_extension_hint': '如后续历史数据全部完成规则化迁移，可进一步下线旧成果口径并引入离线聚合优化。',
        'realtime_metrics': [
            '教师数量、唯一成果数量、规则积分、待审核成果数量',
            '年度积分趋势与成果数量趋势',
            '教师排行、院系钻取与近期待审核后的生效成果',
        ],
        'offline_candidate_metrics': [
            '大范围历史口径固化后的预计算榜单',
            '复杂跨年度多维度专题报表',
            '审批时长与材料完备度治理分析',
        ],
        'export_note': '导出结果默认同时保留积分与数量字段，便于学院在统计与核验之间切换。',
        'drilldown_scope_note': '当前支持学院、教师两级钻取，并保持与教师成果详情和审核页面口径一致。',
        'statistics_boundary_note': '数量统计强调唯一成果去重，积分统计强调教师个人已生效积分，不将待审核成果计入正式积分。',
    }


def _normalize_achievement_type(achievement_type: str) -> str:
    normalized = (achievement_type or 'all').strip().lower()
    if normalized in {'paper', 'paper_book'}:
        return 'paper'
    if normalized == 'project':
        return 'project'
    if normalized in {'award_transform', 'ip'}:
        return 'award_transform'
    if normalized in {'platform_pop', 'service'}:
        return 'platform_pop'
    return 'all'


def _rule_bucket(item: RuleBasedAchievement) -> str:
    category_code = item.category_code_snapshot or (item.category.code if item.category_id else '')
    if category_code == 'PAPER_BOOK':
        return 'paper'
    if category_code == 'PROJECT':
        return 'project'
    if category_code in {'AWARD', 'TRANSFORMATION', 'THINK_TANK'}:
        return 'ip'
    if category_code in {'PLATFORM_TEAM', 'SCI_POP_AWARD'}:
        return 'service'
    return 'service'


def _rule_type_label(item: RuleBasedAchievement) -> str:
    return item.category_name_snapshot or (item.category.name if item.category_id else '规则成果')


def _score_decimal(value) -> Decimal:
    return Decimal(str(value or 0))


def _apply_year_filter(queryset, year: int | None, year_from: int | None = None, year_to: int | None = None):
    if year is not None:
        return queryset.filter(date_acquired__year=year)
    if year_from is not None:
        queryset = queryset.filter(date_acquired__year__gte=year_from)
    if year_to is not None:
        queryset = queryset.filter(date_acquired__year__lte=year_to)
    return queryset


def _filter_rule_records(records: list[RuleBasedAchievement], achievement_type: str) -> list[RuleBasedAchievement]:
    normalized = _normalize_achievement_type(achievement_type)
    if normalized == 'all':
        return list(records)
    allowed_bucket = {'paper': 'paper', 'project': 'project', 'award_transform': 'ip', 'platform_pop': 'service'}[normalized]
    return [item for item in records if _rule_bucket(item) == allowed_bucket]


def _filter_legacy_type(queryset, achievement_type: str, bucket: str):
    normalized = _normalize_achievement_type(achievement_type)
    if normalized == 'all':
        return queryset
    normalized_bucket = {'paper': 'paper', 'project': 'project', 'award_transform': 'ip', 'platform_pop': 'service'}[normalized]
    return queryset if normalized_bucket == bucket else queryset.none()


def _build_imported_legacy_keys(rule_records: list[RuleBasedAchievement]) -> set[str]:
    imported_keys: set[str] = set()
    for item in rule_records:
        source_key = str((item.factual_payload or {}).get('legacy_source_key', '')).strip()
        if source_key:
            imported_keys.add(source_key)
    return imported_keys


def _build_rule_detail(item: RuleBasedAchievement) -> str:
    parts = [item.rule_title_snapshot or (item.rule_item.title if item.rule_item_id else '')]
    if item.publication_name:
        parts.append(item.publication_name)
    elif item.issuing_organization:
        parts.append(item.issuing_organization)
    return ' / '.join(part for part in parts if part)


def _rule_payload(item: RuleBasedAchievement) -> dict:
    return {
        'type': _rule_bucket(item),
        'type_label': _rule_type_label(item),
        'title': item.title,
        'teacher_id': item.teacher_id,
        'teacher_name': item.teacher.real_name or item.teacher.username,
        'department': item.teacher.department or '未填写院系',
        'date_acquired': item.date_acquired.isoformat(),
        'detail': _build_rule_detail(item),
        'score_value': float(item.final_score or 0),
    }


def _legacy_payload(item, *, bucket: str, detail: str, type_label: str) -> dict:
    return {
        'type': bucket,
        'type_label': type_label,
        'title': item.title,
        'teacher_id': item.teacher_id,
        'teacher_name': item.teacher.real_name or item.teacher.username,
        'department': item.teacher.department or '未填写院系',
        'date_acquired': item.date_acquired.isoformat(),
        'detail': detail,
        'score_value': 0.0,
    }


def _legacy_source_key(prefix: str, item_id: int) -> str:
    return f'legacy-{prefix}-{item_id}'


def _zero_teacher_legacy_stats() -> dict:
    return {
        'paper_count': 0,
        'project_count': 0,
        'ip_count': 0,
        'service_count': 0,
        'achievement_total': 0,
        'collaboration_count': 0,
        'latest_active_year': None,
    }


def _build_teacher_legacy_stats(legacy_records: dict) -> dict[int, dict]:
    stats_map: dict[int, dict] = defaultdict(_zero_teacher_legacy_stats)

    for paper in legacy_records['paper']:
        stats = stats_map[paper.teacher_id]
        stats['paper_count'] += 1
        stats['achievement_total'] += 1
        stats['collaboration_count'] += paper.coauthors.count()
        stats['latest_active_year'] = max(
            [year for year in [stats['latest_active_year'], paper.date_acquired.year if paper.date_acquired else None] if year],
            default=None,
        )

    for project in legacy_records['project']:
        stats = stats_map[project.teacher_id]
        stats['project_count'] += 1
        stats['achievement_total'] += 1
        stats['latest_active_year'] = max(
            [year for year in [stats['latest_active_year'], project.date_acquired.year if project.date_acquired else None] if year],
            default=None,
        )

    for item in legacy_records['ip']:
        stats = stats_map[item.teacher_id]
        stats['ip_count'] += 1
        stats['achievement_total'] += 1
        stats['latest_active_year'] = max(
            [year for year in [stats['latest_active_year'], item.date_acquired.year if item.date_acquired else None] if year],
            default=None,
        )

    for item in legacy_records['service']:
        stats = stats_map[item.teacher_id]
        stats['service_count'] += 1
        stats['achievement_total'] += 1
        stats['latest_active_year'] = max(
            [year for year in [stats['latest_active_year'], item.date_acquired.year if item.date_acquired else None] if year],
            default=None,
        )

    return stats_map


def _build_rule_scope_data(
    teacher_ids: list[int],
    year: int | None,
    achievement_type: str = 'all',
    year_from: int | None = None,
    year_to: int | None = None,
) -> dict:
    approved_queryset = _apply_year_filter(
        RuleBasedAchievement.objects.select_related('teacher', 'category', 'rule_item').filter(
            teacher_id__in=teacher_ids,
            status='APPROVED',
        ),
        year,
        year_from,
        year_to,
    ).order_by('-date_acquired', '-created_at')
    approved_records = _filter_rule_records(list(approved_queryset), achievement_type)

    records_by_teacher: dict[int, list[RuleBasedAchievement]] = defaultdict(list)
    for item in approved_records:
        records_by_teacher[item.teacher_id].append(item)

    deduped_by_teacher: dict[int, list[RuleBasedAchievement]] = {
        teacher_id: TeacherScoringEngine._dedup_records(records)
        for teacher_id, records in records_by_teacher.items()
    }
    deduped_flat = [item for records in deduped_by_teacher.values() for item in records]
    unique_records = TeacherScoringEngine._dedup_records(deduped_flat)
    metrics_by_teacher = {
        teacher_id: TeacherScoringEngine._collect_metrics_from_records(records)
        for teacher_id, records in deduped_by_teacher.items()
    }

    pending_queryset = _apply_year_filter(
        RuleBasedAchievement.objects.select_related('teacher', 'category', 'rule_item').filter(
            teacher_id__in=teacher_ids,
            status='PENDING_REVIEW',
        ),
        year,
        year_from,
        year_to,
    ).order_by('-date_acquired', '-created_at')
    pending_records = _filter_rule_records(list(pending_queryset), achievement_type)

    pending_counts: dict[int, int] = defaultdict(int)
    for item in pending_records:
        pending_counts[item.teacher_id] += 1

    collaboration_total = 0
    paper_with_collaboration = 0
    for item in deduped_flat:
        if _rule_bucket(item) != 'paper':
            continue
        coauthors = {str(name).strip() for name in (item.coauthor_names or []) if str(name).strip()}
        collaboration_total += len(coauthors)
        if coauthors:
            paper_with_collaboration += 1

    return {
        'approved_records': approved_records,
        'deduped_by_teacher': deduped_by_teacher,
        'deduped_flat': deduped_flat,
        'unique_records': unique_records,
        'metrics_by_teacher': metrics_by_teacher,
        'pending_records': pending_records,
        'pending_count': len(pending_records),
        'pending_counts': dict(pending_counts),
        'imported_legacy_keys': _build_imported_legacy_keys(approved_records),
        'collaboration_total': collaboration_total,
        'paper_with_collaboration': paper_with_collaboration,
    }


def _build_legacy_scope_data(
    teacher_ids: list[int],
    imported_legacy_keys: set[str],
    year: int | None,
    achievement_type: str = 'all',
    year_from: int | None = None,
    year_to: int | None = None,
) -> dict:
    paper_records = list(
        _filter_legacy_type(
            _apply_year_filter(
                Paper.objects.select_related('teacher').prefetch_related('coauthors').filter(
                    teacher_id__in=teacher_ids,
                    status=APPROVED_STATUS,
                ),
                year,
                year_from,
                year_to,
            ),
            achievement_type,
            'paper',
        ).order_by('-date_acquired', '-created_at')
    )
    project_records = list(
        _filter_legacy_type(
            _apply_year_filter(
                Project.objects.select_related('teacher').filter(
                    teacher_id__in=teacher_ids,
                    status=APPROVED_STATUS,
                ),
                year,
                year_from,
                year_to,
            ),
            achievement_type,
            'project',
        ).order_by('-date_acquired', '-created_at')
    )
    ip_records = list(
        _filter_legacy_type(
            _apply_year_filter(
                IntellectualProperty.objects.select_related('teacher').filter(
                    teacher_id__in=teacher_ids,
                    status=APPROVED_STATUS,
                ),
                year,
                year_from,
                year_to,
            ),
            achievement_type,
            'ip',
        ).order_by('-date_acquired', '-created_at')
    )
    service_records = list(
        _filter_legacy_type(
            _apply_year_filter(
                AcademicService.objects.select_related('teacher').filter(
                    teacher_id__in=teacher_ids,
                    status=APPROVED_STATUS,
                ),
                year,
                year_from,
                year_to,
            ),
            achievement_type,
            'service',
        ).order_by('-date_acquired', '-created_at')
    )

    paper_records = [item for item in paper_records if _legacy_source_key('paper', item.id) not in imported_legacy_keys]
    project_records = [item for item in project_records if _legacy_source_key('project', item.id) not in imported_legacy_keys]
    ip_records = [item for item in ip_records if _legacy_source_key('ip', item.id) not in imported_legacy_keys]
    service_records = [item for item in service_records if _legacy_source_key('service', item.id) not in imported_legacy_keys]

    collaboration_total = sum(item.coauthors.count() for item in paper_records)
    paper_with_collaboration = sum(1 for item in paper_records if item.coauthors.exists())

    return {
        'paper': paper_records,
        'project': project_records,
        'ip': ip_records,
        'service': service_records,
        'teacher_stats': _build_teacher_legacy_stats(
            {
                'paper': paper_records,
                'project': project_records,
                'ip': ip_records,
                'service': service_records,
            }
        ),
        'collaboration_total': collaboration_total,
        'paper_with_collaboration': paper_with_collaboration,
    }


def build_scope_querysets(
    teacher_ids: list[int],
    year: int | None,
    achievement_type: str = 'all',
    year_from: int | None = None,
    year_to: int | None = None,
) -> dict:
    normalized_type = _normalize_achievement_type(achievement_type)
    rule_scope = _build_rule_scope_data(
        teacher_ids,
        year,
        normalized_type,
        year_from=year_from,
        year_to=year_to,
    )
    legacy_scope = _build_legacy_scope_data(
        teacher_ids,
        rule_scope['imported_legacy_keys'],
        year,
        normalized_type,
        year_from=year_from,
        year_to=year_to,
    )

    legacy_payloads = [
        _legacy_payload(
            item,
            bucket='paper',
            detail=item.journal_name,
            type_label='论文成果',
        )
        for item in legacy_scope['paper']
    ] + [
        _legacy_payload(
            item,
            bucket='project',
            detail=f'{item.get_level_display()} / {item.get_role_display()}',
            type_label='科研项目',
        )
        for item in legacy_scope['project']
    ] + [
        _legacy_payload(
            item,
            bucket='ip',
            detail=item.get_ip_type_display(),
            type_label='知识产权/奖励转化',
        )
        for item in legacy_scope['ip']
    ] + [
        _legacy_payload(
            item,
            bucket='service',
            detail=f'{item.get_service_type_display()} / {item.organization}',
            type_label='平台团队/学术服务',
        )
        for item in legacy_scope['service']
    ]

    rule_unique_payloads = [_rule_payload(item) for item in rule_scope['unique_records']]
    combined_unique_records = sorted(
        legacy_payloads + rule_unique_payloads,
        key=lambda item: (item['date_acquired'], item['title']),
        reverse=True,
    )

    return {
        'achievement_type': normalized_type,
        'legacy': legacy_scope,
        'rule': rule_scope,
        'combined_unique_records': combined_unique_records,
    }


def _count_rule_unique_records_by_bucket(records: list[RuleBasedAchievement]) -> dict[str, int]:
    counter = {'paper': 0, 'project': 0, 'ip': 0, 'service': 0}
    for item in records:
        counter[_rule_bucket(item)] += 1
    return counter


def _count_legacy_records_by_bucket(legacy_scope: dict) -> dict[str, int]:
    return {
        'paper': len(legacy_scope['paper']),
        'project': len(legacy_scope['project']),
        'ip': len(legacy_scope['ip']),
        'service': len(legacy_scope['service']),
    }


def _build_scope_score_totals(rule_scope: dict) -> dict[str, float]:
    metrics_by_teacher = rule_scope['metrics_by_teacher']
    return {
        'paper_book_score': round(sum(item['paper_book_score'] for item in metrics_by_teacher.values()), 1),
        'project_score': round(sum(item['project_score'] for item in metrics_by_teacher.values()), 1),
        'award_transform_score': round(
            sum(
                item['award_score'] + item['transformation_score'] + item['think_tank_score']
                for item in metrics_by_teacher.values()
            ),
            1,
        ),
        'platform_pop_score': round(
            sum(item['platform_team_score'] + item['science_pop_score'] for item in metrics_by_teacher.values()),
            1,
        ),
        'total_score': round(sum(item['total_rule_score'] for item in metrics_by_teacher.values()), 1),
    }


def build_yearly_trend(querysets: dict) -> list[dict]:
    yearly = defaultdict(
        lambda: {
            'paper_count': 0,
            'project_count': 0,
            'ip_count': 0,
            'service_count': 0,
            'achievement_total': 0,
            'total_score': Decimal('0'),
            'active_teacher_ids': set(),
        }
    )

    legacy_scope = querysets['legacy']
    for item in legacy_scope['paper']:
        year = item.date_acquired.year
        yearly[year]['paper_count'] += 1
        yearly[year]['achievement_total'] += 1
        yearly[year]['active_teacher_ids'].add(item.teacher_id)
    for item in legacy_scope['project']:
        year = item.date_acquired.year
        yearly[year]['project_count'] += 1
        yearly[year]['achievement_total'] += 1
        yearly[year]['active_teacher_ids'].add(item.teacher_id)
    for item in legacy_scope['ip']:
        year = item.date_acquired.year
        yearly[year]['ip_count'] += 1
        yearly[year]['achievement_total'] += 1
        yearly[year]['active_teacher_ids'].add(item.teacher_id)
    for item in legacy_scope['service']:
        year = item.date_acquired.year
        yearly[year]['service_count'] += 1
        yearly[year]['achievement_total'] += 1
        yearly[year]['active_teacher_ids'].add(item.teacher_id)

    rule_scope = querysets['rule']
    unique_rule_counts_by_year = defaultdict(lambda: {'paper': 0, 'project': 0, 'ip': 0, 'service': 0, 'achievement_total': 0})
    for item in rule_scope['unique_records']:
        item_year = item.date_acquired.year
        bucket = _rule_bucket(item)
        unique_rule_counts_by_year[item_year][bucket] += 1
        unique_rule_counts_by_year[item_year]['achievement_total'] += 1
        yearly[item_year]['active_teacher_ids'].add(item.teacher_id)

    for item in rule_scope['deduped_flat']:
        item_year = item.date_acquired.year
        yearly[item_year]['total_score'] += _score_decimal(item.final_score)
        yearly[item_year]['active_teacher_ids'].add(item.teacher_id)

    for year, counter in unique_rule_counts_by_year.items():
        yearly[year]['paper_count'] += counter['paper']
        yearly[year]['project_count'] += counter['project']
        yearly[year]['ip_count'] += counter['ip']
        yearly[year]['service_count'] += counter['service']
        yearly[year]['achievement_total'] += counter['achievement_total']

    return [
        {
            'year': year,
            'paper_count': payload['paper_count'],
            'project_count': payload['project_count'],
            'ip_count': payload['ip_count'],
            'service_count': payload['service_count'],
            'teaching_count': 0,
            'achievement_total': payload['achievement_total'],
            'total_score': round(float(payload['total_score']), 1),
            'active_teacher_count': len(payload['active_teacher_ids']),
        }
        for year, payload in sorted(yearly.items())
    ]


def build_trend_summary(yearly_trend: list[dict]) -> dict:
    if not yearly_trend:
        return {
            'latest_year': None,
            'previous_year': None,
            'latest_total': 0,
            'previous_total': 0,
            'total_delta': 0,
            'paper_delta': 0,
            'project_delta': 0,
            'direction': 'flat',
            'description': '当前筛选范围内暂无足够的年度成果数据。',
        }

    latest = yearly_trend[-1]
    previous = yearly_trend[-2] if len(yearly_trend) > 1 else None
    total_delta = latest['achievement_total'] - (previous['achievement_total'] if previous else 0)
    paper_delta = latest['paper_count'] - (previous['paper_count'] if previous else 0)
    project_delta = latest['project_count'] - (previous['project_count'] if previous else 0)
    score_delta = latest.get('total_score', 0) - (previous.get('total_score', 0) if previous else 0)
    direction = 'up' if score_delta > 0 else 'down' if score_delta < 0 else 'flat'

    if previous:
        description = (
            f"{latest['year']} 年核心科研积分较 {previous['year']} 年"
            f"{'提升' if score_delta > 0 else '下降' if score_delta < 0 else '持平'} {abs(score_delta):.1f} 分，"
            f"唯一成果数变化 {total_delta:+d}，其中学术产出 {paper_delta:+d}、科研项目 {project_delta:+d}。"
        )
    else:
        description = (
            f"{latest['year']} 年当前累计核心科研积分 {latest.get('total_score', 0):.1f} 分，"
            f"唯一成果数 {latest['achievement_total']} 项。"
        )

    return {
        'latest_year': latest['year'],
        'previous_year': previous['year'] if previous else None,
        'latest_total': latest['achievement_total'],
        'previous_total': previous['achievement_total'] if previous else 0,
        'total_delta': total_delta,
        'paper_delta': paper_delta,
        'project_delta': project_delta,
        'direction': direction,
        'description': description,
    }


def build_scope_comparison_trend(scope_querysets: dict, baseline_querysets: dict, limit: int = 5) -> list[dict]:
    scope_trend = {item['year']: item for item in build_yearly_trend(scope_querysets)}
    baseline_trend = {item['year']: item for item in build_yearly_trend(baseline_querysets)}
    years = sorted(set(scope_trend) | set(baseline_trend))
    if len(years) > limit:
        years = years[-limit:]

    records = []
    for year in years:
        scope_item = scope_trend.get(year, {})
        baseline_item = baseline_trend.get(year, {})
        records.append(
            {
                'year': year,
                'scope_achievement_total': scope_item.get('achievement_total', 0),
                'baseline_achievement_total': baseline_item.get('achievement_total', 0),
                'scope_paper_count': scope_item.get('paper_count', 0),
                'baseline_paper_count': baseline_item.get('paper_count', 0),
                'scope_total_score': scope_item.get('total_score', 0),
                'baseline_total_score': baseline_item.get('total_score', 0),
            }
        )
    return records


def build_department_distribution(teachers) -> list[dict]:
    distribution = defaultdict(int)
    for department in teachers.values_list('department', flat=True):
        distribution[department or '未填写院系'] += 1
    return [
        {'name': department, 'value': count}
        for department, count in sorted(distribution.items(), key=lambda item: (-item[1], item[0]))
    ]


def build_comparison_department_distribution(primary_department: str, compare_department: str, teachers) -> list[dict]:
    target_departments = [item for item in [primary_department, compare_department] if item]
    if not target_departments:
        return []
    return build_department_distribution(teachers.filter(department__in=target_departments))


def build_teacher_rank(teachers, querysets: dict, rank_by: str = 'total_score') -> list[dict]:
    safe_rank_by = rank_by if rank_by in RANKING_MODE_LABELS else 'total_score'
    legacy_stats_map = querysets['legacy']['teacher_stats']
    rule_metrics_map = querysets['rule']['metrics_by_teacher']
    pending_counts = querysets['rule']['pending_counts']

    teacher_rank = []
    for teacher in teachers:
        legacy_stats = legacy_stats_map.get(teacher.id, _zero_teacher_legacy_stats())
        rule_metrics = rule_metrics_map.get(teacher.id, ZERO_RULE_METRICS)
        award_transform_count = rule_metrics['award_count'] + rule_metrics['transformation_count'] + rule_metrics['think_tank_count']
        platform_pop_count = rule_metrics['platform_count'] + rule_metrics['science_pop_count']
        award_transform_score = rule_metrics['award_score'] + rule_metrics['transformation_score'] + rule_metrics['think_tank_score']
        platform_pop_score = rule_metrics['platform_team_score'] + rule_metrics['science_pop_score']

        item = {
            'user_id': teacher.id,
            'teacher_name': teacher.real_name or teacher.username,
            'department': teacher.department or '未填写院系',
            'title': getattr(teacher, 'title', '') or '未填写职称',
            'paper_count': legacy_stats['paper_count'] + rule_metrics['paper_count'],
            'project_count': legacy_stats['project_count'] + rule_metrics['project_count'],
            'ip_count': legacy_stats['ip_count'] + award_transform_count,
            'teaching_count': 0,
            'service_count': legacy_stats['service_count'] + platform_pop_count,
            'award_transform_count': legacy_stats['ip_count'] + award_transform_count,
            'platform_pop_count': legacy_stats['service_count'] + platform_pop_count,
            'collaboration_count': legacy_stats['collaboration_count'] + rule_metrics['collaborator_count'],
            'achievement_total': legacy_stats['achievement_total'] + rule_metrics['total_achievements'],
            'pending_count': pending_counts.get(teacher.id, 0),
            'latest_active_year': max(
                [year for year in [legacy_stats['latest_active_year']] if year],
                default=None,
            ),
            'paper_book_score': round(rule_metrics['paper_book_score'], 1),
            'project_score': round(rule_metrics['project_score'], 1),
            'award_transform_score': round(award_transform_score, 1),
            'platform_pop_score': round(platform_pop_score, 1),
            'total_score': round(rule_metrics['total_rule_score'], 1),
        }
        if rule_metrics_map.get(teacher.id):
            latest_rule_year = max(
                (record.date_acquired.year for record in querysets['rule']['deduped_by_teacher'].get(teacher.id, []) if record.date_acquired),
                default=None,
            )
            item['latest_active_year'] = max(
                [year for year in [item['latest_active_year'], latest_rule_year] if year],
                default=None,
            )

        item['rank_value'] = item.get(safe_rank_by, item['total_score'])
        item['rank_label'] = RANKING_MODE_LABELS.get(safe_rank_by, '核心科研积分')
        teacher_rank.append(item)

    teacher_rank.sort(
        key=lambda item: (
            item['rank_value'],
            item['total_score'],
            item['achievement_total'],
            item['paper_count'],
        ),
        reverse=True,
    )
    return teacher_rank


def build_department_breakdown(teachers, querysets: dict) -> list[dict]:
    rows = build_teacher_rank(teachers, querysets, rank_by='total_score')
    grouped = defaultdict(
        lambda: {
            'department': '',
            'teacher_count': 0,
            'achievement_total': 0,
            'paper_count': 0,
            'project_count': 0,
            'ip_count': 0,
            'teaching_count': 0,
            'service_count': 0,
            'collaboration_count': 0,
            'score_total': 0.0,
            'pending_count': 0,
        }
    )
    for row in rows:
        target = grouped[row['department']]
        target['department'] = row['department']
        target['teacher_count'] += 1
        target['achievement_total'] += row['achievement_total']
        target['paper_count'] += row['paper_count']
        target['project_count'] += row['project_count']
        target['ip_count'] += row['ip_count']
        target['service_count'] += row['service_count']
        target['collaboration_count'] += row['collaboration_count']
        target['score_total'] += row['total_score']
        target['pending_count'] += row['pending_count']

    result = list(grouped.values())
    result.sort(key=lambda item: (item['score_total'], item['achievement_total'], item['department']), reverse=True)
    return result[:12]


def build_collaboration_overview(_paper_queryset, _collaboration_queryset, paper_total: int, *, querysets: dict | None = None) -> dict:
    if querysets is None:
        return {
            'coauthor_relation_total': 0,
            'teachers_with_collaboration': 0,
            'paper_with_collaboration': 0,
            'average_coauthors_per_paper': 0,
        }

    legacy_scope = querysets['legacy']
    rule_scope = querysets['rule']
    coauthor_relation_total = legacy_scope['collaboration_total'] + rule_scope['collaboration_total']
    paper_with_collaboration = legacy_scope['paper_with_collaboration'] + rule_scope['paper_with_collaboration']
    teacher_ids = set()
    for paper in legacy_scope['paper']:
        if paper.coauthors.exists():
            teacher_ids.add(paper.teacher_id)
    for teacher_id, metrics in rule_scope['metrics_by_teacher'].items():
        if metrics['collaborator_count'] > 0:
            teacher_ids.add(teacher_id)

    return {
        'coauthor_relation_total': coauthor_relation_total,
        'teachers_with_collaboration': len(teacher_ids),
        'paper_with_collaboration': paper_with_collaboration,
        'average_coauthors_per_paper': round(coauthor_relation_total / paper_total, 2) if paper_total else 0,
    }


def build_comparison_summary(
    current_metrics: dict,
    baseline_metrics: dict,
    year: int | None,
    achievement_type: str = 'all',
    compare_department: str = '',
) -> dict:
    baseline_teacher_total = baseline_metrics['teacher_total'] or 1
    baseline_achievement_total = baseline_metrics['achievement_total'] or 1
    baseline_score_total = baseline_metrics['score_total'] or 1
    scope_label = '当前筛选范围'
    compare_label = compare_department or (f'{year} 年全校口径' if year else '全校口径')
    type_label = ACHIEVEMENT_TYPE_LABELS.get(_normalize_achievement_type(achievement_type), '全部成果')
    return {
        'scope_label': scope_label,
        'compare_label': compare_label,
        'teacher_total': current_metrics['teacher_total'],
        'teacher_share': round(current_metrics['teacher_total'] / baseline_teacher_total * 100, 1),
        'achievement_total': current_metrics['achievement_total'],
        'achievement_share': round(current_metrics['achievement_total'] / baseline_achievement_total * 100, 1),
        'collaboration_total': current_metrics['collaboration_total'],
        'collaboration_density': round(current_metrics['collaboration_total'] / current_metrics['teacher_total'], 2)
        if current_metrics['teacher_total']
        else 0,
        'score_total': current_metrics['score_total'],
        'score_share': round(current_metrics['score_total'] / baseline_score_total * 100, 1),
        'description': (
            f"当前筛选范围在“{type_label}”口径下共有唯一成果 {current_metrics['achievement_total']} 项、"
            f"核心科研积分 {current_metrics['score_total']:.1f} 分，约占 {compare_label} 同口径积分的 "
            f"{round(current_metrics['score_total'] / baseline_score_total * 100, 1)}%。"
        ),
    }


def build_filter_options(teachers=None):
    if teachers is None:
        user_model = get_user_model()
        teachers = user_model.objects.filter(is_superuser=False, is_staff=False)

    rule_years = RuleBasedAchievement.objects.filter(status='APPROVED').values_list('date_acquired__year', flat=True)
    legacy_years = list(Paper.objects.filter(status=APPROVED_STATUS).values_list('date_acquired__year', flat=True))
    legacy_years += list(Project.objects.filter(status=APPROVED_STATUS).values_list('date_acquired__year', flat=True))
    legacy_years += list(IntellectualProperty.objects.filter(status=APPROVED_STATUS).values_list('date_acquired__year', flat=True))
    legacy_years += list(AcademicService.objects.filter(status=APPROVED_STATUS).values_list('date_acquired__year', flat=True))
    years = sorted({year for year in list(rule_years) + legacy_years if year})

    dynamic_titles = [item for item in teachers.values_list('title', flat=True) if item]
    teacher_titles = []
    for title in DEFAULT_TEACHER_TITLE_FILTERS + sorted(set(dynamic_titles)):
        if title and title not in teacher_titles:
            teacher_titles.append(title)

    return {
        'departments': sorted({item for item in teachers.values_list('department', flat=True) if item}),
        'teacher_titles': teacher_titles,
        'teachers': [
            {
                'user_id': teacher.id,
                'teacher_name': teacher.real_name or teacher.username,
                'department': teacher.department or '未填写院系',
                'title': getattr(teacher, 'title', '') or '未填写职称',
            }
            for teacher in teachers.order_by('department', 'id')
        ],
        'years': years,
        'achievement_types': [
            {'value': 'all', 'label': '全部成果'},
            {'value': 'paper', 'label': '学术产出'},
            {'value': 'project', 'label': '科研项目'},
            {'value': 'award_transform', 'label': '奖励与转化'},
            {'value': 'platform_pop', 'label': '平台科普'},
        ],
        'ranking_modes': [{'value': key, 'label': value} for key, value in RANKING_MODE_LABELS.items()],
    }


def build_recent_achievement_records(teacher_ids: list[int], achievement_type: str = 'all', limit: int = 8) -> list[dict]:
    querysets = build_scope_querysets(teacher_ids, None, achievement_type)
    return querysets['combined_unique_records'][:limit]


def build_teacher_drilldown(teacher, querysets: dict, achievement_type: str = 'all') -> dict:
    rows = build_teacher_rank(get_user_model().objects.filter(id=teacher.id), querysets, rank_by='total_score')
    summary = rows[0] if rows else None
    return {
        'selected_teacher_summary': summary,
        'teacher_recent_achievements': build_recent_achievement_records([teacher.id], achievement_type=achievement_type, limit=8),
    }


def build_department_drilldown(teachers, department_name: str, querysets: dict, rank_by: str = 'total_score') -> dict:
    department_teachers = teachers.filter(department=department_name)
    teacher_ids = list(department_teachers.values_list('id', flat=True))
    scoped_querysets = build_scope_querysets(teacher_ids, None, 'all')
    top_teachers = build_teacher_rank(department_teachers, scoped_querysets, rank_by=rank_by)[:6]
    recent_records = build_recent_achievement_records(teacher_ids, limit=8)
    return {
        'selected_department_summary': {
            'department': department_name,
            'teacher_count': department_teachers.count(),
            'top_teacher_count': len(top_teachers),
            'recent_record_count': len(recent_records),
        },
        'department_top_teachers': top_teachers,
        'department_recent_achievements': recent_records,
    }


def export_academy_csv(
    *,
    export_target: str,
    statistics: list[dict],
    yearly_trend: list[dict],
    comparison_trend: list[dict],
    department_breakdown: list[dict],
    top_active_teachers: list[dict],
    recent_records: list[dict],
) -> str:
    output = io.StringIO()
    writer = csv.writer(output)

    if export_target == 'departments':
        writer.writerow(['院系', '教师数', '核心科研积分', '唯一成果数', '学术产出', '科研项目', '奖励与转化', '平台科普', '待审核'])
        for item in department_breakdown:
            writer.writerow(
                [
                    item['department'],
                    item['teacher_count'],
                    round(item.get('score_total', 0), 1),
                    item['achievement_total'],
                    item['paper_count'],
                    item['project_count'],
                    item['ip_count'],
                    item['service_count'],
                    item.get('pending_count', 0),
                ]
            )
        return '\ufeff' + output.getvalue()

    if export_target == 'trend':
        writer.writerow(['年份', '当前范围积分', '当前范围成果数', '全校积分', '全校成果数'])
        for item in comparison_trend:
            writer.writerow(
                [
                    item['year'],
                    item.get('scope_total_score', 0),
                    item['scope_achievement_total'],
                    item.get('baseline_total_score', 0),
                    item['baseline_achievement_total'],
                ]
            )
        return '\ufeff' + output.getvalue()

    if export_target == 'recent_records':
        writer.writerow(['成果类型', '标题', '教师', '院系', '日期', '说明', '积分'])
        for item in recent_records:
            writer.writerow(
                [
                    item['type_label'],
                    item['title'],
                    item['teacher_name'],
                    item['department'],
                    item['date_acquired'],
                    item['detail'],
                    item.get('score_value', 0),
                ]
            )
        return '\ufeff' + output.getvalue()

    writer.writerow(['指标', '数值', '说明'])
    for item in statistics:
        writer.writerow([item['title'], item['value'], item.get('helper', '')])
    writer.writerow([])
    writer.writerow(['教师', '院系', '职称', '核心科研积分', '唯一成果数', '学术产出', '科研项目', '奖励与转化', '平台科普', '待审核'])
    for item in top_active_teachers:
        writer.writerow(
            [
                item['teacher_name'],
                item['department'],
                item['title'],
                item.get('total_score', 0),
                item['achievement_total'],
                item['paper_count'],
                item['project_count'],
                item.get('award_transform_count', item['ip_count']),
                item.get('platform_pop_count', item['service_count']),
                item.get('pending_count', 0),
            ]
        )
    return '\ufeff' + output.getvalue()
