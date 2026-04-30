from __future__ import annotations

from collections import Counter

from django.db.models import Count

from achievements.models import PaperKeyword
from achievements.services import build_teacher_related_paper_queryset


def _paper_queryset(teacher):
    return build_teacher_related_paper_queryset(teacher, approved_only=True)


def _build_collaboration_overview(teacher):
    paper_queryset = _paper_queryset(teacher)
    collaborator_rows = list(
        paper_queryset.filter(coauthors__isnull=False)
        .values('coauthors__name')
        .annotate(count=Count('coauthors__id'))
        .order_by('-count', 'coauthors__name')
    )

    collaborator_total = len([item for item in collaborator_rows if item['coauthors__name']])
    paper_count = paper_queryset.count()
    collaboration_links = sum(item['count'] for item in collaborator_rows)
    average_per_paper = round(collaboration_links / paper_count, 1) if paper_count else 0
    strongest = next((item for item in collaborator_rows if item['coauthors__name']), None)

    return {
        'paper_count': paper_count,
        'collaborator_total': collaborator_total,
        'collaboration_links': collaboration_links,
        'average_collaborators_per_paper': average_per_paper,
        'strongest_collaborator': {
            'name': strongest['coauthors__name'],
            'count': strongest['count'],
        }
        if strongest
        else None,
    }


def _build_collaboration_circle_overview(teacher):
    paper_queryset = _paper_queryset(teacher)
    collaborator_rows = [
        {'name': item['coauthors__name'], 'count': item['count']}
        for item in (
            paper_queryset.filter(coauthors__isnull=False)
            .values('coauthors__name')
            .annotate(count=Count('coauthors__id'))
            .order_by('-count', 'coauthors__name')
        )
        if item['coauthors__name']
    ]

    core_ring = [item for item in collaborator_rows if item['count'] >= 3]
    active_ring = [item for item in collaborator_rows if item['count'] == 2]
    extended_ring = [item for item in collaborator_rows if item['count'] == 1]
    total = len(collaborator_rows)

    if not total:
        return {
            'core_collaborator_count': 0,
            'active_collaborator_count': 0,
            'extended_collaborator_count': 0,
            'core_collaborators': [],
            'active_collaborators': [],
            'extended_collaborators': [],
            'description': '当前尚未形成可用的合作圈层概览，录入更多论文与合作作者后可逐步形成。',
            'threshold_note': '当前圈层规则保留为轻量阈值说明，不执行复杂社区发现算法。',
        }

    return {
        'core_collaborator_count': len(core_ring),
        'active_collaborator_count': len(active_ring),
        'extended_collaborator_count': len(extended_ring),
        'core_collaborators': core_ring[:4],
        'active_collaborators': active_ring[:4],
        'extended_collaborators': extended_ring[:4],
        'description': (
            '当前按共同署名次数做轻量圈层概览：3 次及以上视为核心合作圈，2 次视为活跃合作圈，1 次视为扩展合作圈。'
        ),
        'threshold_note': '当前圈层分析只基于已加载合作关系做轻量阈值划分，不等同于复杂社区发现或图聚类结果。',
    }


def _build_collaborator_type_breakdown(teacher):
    counters = Counter(_paper_queryset(teacher).filter(coauthors__isnull=False).values_list('coauthors__is_internal', flat=True))

    internal_count = counters.get(True, 0)
    external_count = counters.get(False, 0)
    total = internal_count + external_count

    return {
        'internal_count': internal_count,
        'external_count': external_count,
        'internal_ratio': round((internal_count / total) * 100, 1) if total else 0,
        'external_ratio': round((external_count / total) * 100, 1) if total else 0,
        'description': (
            '当前按合作作者是否关联内部教师账号区分内外部合作。'
            if total
            else '当前尚未形成可用的合作者类型分析数据。'
        ),
    }


def _build_theme_hotspots(teacher):
    paper_ids = list(_paper_queryset(teacher).values_list('id', flat=True))
    keyword_ranking = list(
        PaperKeyword.objects.filter(paper_id__in=paper_ids)
        .values('keyword__name')
        .annotate(count=Count('keyword_id'))
        .order_by('-count', 'keyword__name')[:8]
    )

    top_keywords = [
        {'name': item['keyword__name'], 'count': item['count']}
        for item in keyword_ranking
        if item['keyword__name']
    ]

    total_keyword_mentions = sum(item['count'] for item in top_keywords)
    top_three_mentions = sum(item['count'] for item in top_keywords[:3])
    focus_ratio = round((top_three_mentions / total_keyword_mentions) * 100, 1) if total_keyword_mentions else 0

    recent_years = sorted(
        {
            year
            for year in _paper_queryset(teacher).values_list('date_acquired__year', flat=True)
            if year
        },
        reverse=True,
    )[:3]

    yearly_focus = []
    for year in sorted(recent_years):
        yearly_keywords = list(
            PaperKeyword.objects.filter(
                paper_id__in=paper_ids,
                paper__date_acquired__year=year,
            )
            .values('keyword__name')
            .annotate(count=Count('keyword_id'))
            .order_by('-count', 'keyword__name')[:3]
        )
        yearly_focus.append(
            {
                'year': year,
                'keywords': [
                    {'name': item['keyword__name'], 'count': item['count']}
                    for item in yearly_keywords
                    if item['keyword__name']
                ],
            }
        )

    return {
        'top_keywords': top_keywords,
        'focus_ratio': focus_ratio,
        'focus_label': (
            '主题聚焦较强'
            if focus_ratio >= 65
            else '主题布局均衡'
            if focus_ratio >= 40
            else '主题覆盖较广'
        ),
        'yearly_focus': yearly_focus,
        'description': '当前热点分析基于论文关键词出现频次统计，不包含复杂主题聚类。',
    }


def build_graph_analysis(teacher):
    collaboration_overview = _build_collaboration_overview(teacher)
    collaboration_circle_overview = _build_collaboration_circle_overview(teacher)
    collaborator_type_breakdown = _build_collaborator_type_breakdown(teacher)
    theme_hotspots = _build_theme_hotspots(teacher)

    top_collaborators = []
    if collaboration_overview['strongest_collaborator']:
        strongest = collaboration_overview['strongest_collaborator']
        top_collaborators.append(strongest)

    collaborator_rows = list(
        _paper_queryset(teacher).filter(coauthors__isnull=False)
        .values('coauthors__name')
        .annotate(count=Count('coauthors__id'))
        .order_by('-count', 'coauthors__name')[:5]
    )
    for item in collaborator_rows:
        if item['coauthors__name'] and all(existing['name'] != item['coauthors__name'] for existing in top_collaborators):
            top_collaborators.append({'name': item['coauthors__name'], 'count': item['count']})

    top_keywords = theme_hotspots['top_keywords'][:5]

    highlight_cards = [
        {
            'title': '合作网络概览',
            'value': f"{collaboration_overview['collaborator_total']} 位",
            'detail': (
                f"共形成 {collaboration_overview['collaboration_links']} 条合作边，平均每篇论文 {collaboration_overview['average_collaborators_per_paper']} 位合作者。"
                if collaboration_overview['paper_count']
                else '录入论文与合作作者后会形成合作网络概览。'
            ),
        },
        {
            'title': '合作者类型',
            'value': (
                f"内 {collaborator_type_breakdown['internal_count']} / 外 {collaborator_type_breakdown['external_count']}"
                if collaborator_type_breakdown['internal_count'] or collaborator_type_breakdown['external_count']
                else '暂无'
            ),
            'detail': collaborator_type_breakdown['description'],
        },
        {
            'title': '研究主题热点',
            'value': theme_hotspots['top_keywords'][0]['name'] if theme_hotspots['top_keywords'] else '暂无',
            'detail': (
                f"Top3 关键词集中度 {theme_hotspots['focus_ratio']}%，{theme_hotspots['focus_label']}。"
                if theme_hotspots['top_keywords']
                else '录入论文摘要并生成关键词后会形成研究主题热点分析。'
            ),
        },
        {
            'title': '合作圈层概览',
            'value': (
                f"核心 {collaboration_circle_overview['core_collaborator_count']} / 活跃 {collaboration_circle_overview['active_collaborator_count']}"
                if collaboration_overview['collaborator_total']
                else '暂无'
            ),
            'detail': collaboration_circle_overview['description'],
        },
    ]

    return {
        'top_collaborators': top_collaborators[:5],
        'top_keywords': top_keywords,
        'network_overview': {
            'paper_count': collaboration_overview['paper_count'],
            'collaborator_total': collaboration_overview['collaborator_total'],
            'keyword_total': len(theme_hotspots['top_keywords']),
        },
        'collaboration_overview': collaboration_overview,
        'collaboration_circle_overview': collaboration_circle_overview,
        'collaborator_type_breakdown': collaborator_type_breakdown,
        'theme_hotspots': theme_hotspots,
        'highlight_cards': highlight_cards,
        'scope_note': '当前属于轻量图分析展示，已提供合作网络概览、合作圈层概览、合作者类型和研究主题热点，不构成复杂图挖掘平台。',
        'analysis_level': 'lightweight-analysis',
        'analysis_method_note': '当前分析以图节点关系、合作作者标记和论文关键词频次为基础，适合解释与演示；合作圈层为轻量阈值划分，不等同于社区发现、复杂路径推理或主题聚类结果。',
    }
