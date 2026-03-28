from __future__ import annotations

import csv
from io import StringIO
from typing import Iterable

from django.db.models import Count, IntegerField, Value
from django.db.models.expressions import Case, When
from django.db.models.functions import ExtractYear
from django.utils import timezone

from .models import Paper, PaperOperationLog


METADATA_ALERT_DEFINITIONS = (
    {
        'code': 'missing_doi',
        'field': 'doi',
        'label': '缺少 DOI',
        'severity': 'warning',
        'message': '建议补充 DOI，方便去重、检索和成果回溯。',
    },
    {
        'code': 'missing_pages',
        'field': 'pages',
        'label': '缺少页码',
        'severity': 'info',
        'message': '建议补充页码范围，方便成果核验与导出。',
    },
    {
        'code': 'missing_source_url',
        'field': 'source_url',
        'label': '缺少来源链接',
        'severity': 'warning',
        'message': '建议补充来源链接，方便回查原始成果页面。',
    },
    {
        'code': 'missing_journal_level',
        'field': 'journal_level',
        'label': '缺少期刊级别',
        'severity': 'info',
        'message': '建议补充 SCI、EI、CCF 等级，方便统计和治理。',
    },
)


def metadata_alert_count_expression():
    expression = Value(0, output_field=IntegerField())
    for definition in METADATA_ALERT_DEFINITIONS:
        expression += Case(
            When(**{definition['field']: ''}, then=Value(1)),
            default=Value(0),
            output_field=IntegerField(),
        )
    return expression


def build_paper_metadata_alert_details(paper: Paper) -> list[dict]:
    details: list[dict] = []
    for definition in METADATA_ALERT_DEFINITIONS:
        if not getattr(paper, definition['field'], ''):
            details.append(
                {
                    'code': definition['code'],
                    'field': definition['field'],
                    'label': definition['label'],
                    'severity': definition['severity'],
                    'message': definition['message'],
                }
            )
    return details


def build_paper_metadata_alerts(paper: Paper) -> list[str]:
    return [item['message'] for item in build_paper_metadata_alert_details(paper)]


def build_metadata_flag_codes(paper: Paper) -> list[str]:
    return [item['code'] for item in build_paper_metadata_alert_details(paper)]


def serialize_operation_log(log: PaperOperationLog) -> dict:
    return {
        'id': log.id,
        'paper': log.paper_id,
        'action': log.action,
        'action_label': log.get_action_display(),
        'source': log.source,
        'source_label': log.get_source_display(),
        'summary': log.summary,
        'changed_fields': log.changed_fields,
        'metadata_flags': log.metadata_flags,
        'paper_title_snapshot': log.paper_title_snapshot,
        'paper_doi_snapshot': log.paper_doi_snapshot,
        'created_at': log.created_at.isoformat(),
    }


def snapshot_paper_fields(paper: Paper) -> dict:
    return {
        'title': paper.title,
        'abstract': paper.abstract,
        'date_acquired': paper.date_acquired.isoformat() if paper.date_acquired else '',
        'paper_type': paper.paper_type,
        'journal_name': paper.journal_name,
        'journal_level': paper.journal_level,
        'published_volume': paper.published_volume,
        'published_issue': paper.published_issue,
        'pages': paper.pages,
        'source_url': paper.source_url,
        'citation_count': paper.citation_count,
        'is_first_author': paper.is_first_author,
        'is_representative': paper.is_representative,
        'doi': paper.doi,
        'coauthors': [item.name for item in paper.coauthors.all().order_by('id')],
    }


def diff_paper_fields(before: dict, after: Paper) -> list[str]:
    current = snapshot_paper_fields(after)
    return [field for field, value in current.items() if before.get(field) != value]


def log_paper_operation(
    *,
    paper: Paper | None,
    teacher,
    action: str,
    source: str,
    summary: str,
    changed_fields: list[str] | None = None,
    metadata_flags: list[str] | None = None,
    title_snapshot: str = '',
    doi_snapshot: str = '',
) -> PaperOperationLog:
    target_paper = paper
    return PaperOperationLog.objects.create(
        paper=target_paper,
        teacher=teacher,
        action=action,
        source=source,
        summary=summary,
        changed_fields=changed_fields or [],
        metadata_flags=metadata_flags or [],
        paper_title_snapshot=title_snapshot or (target_paper.title if target_paper else ''),
        paper_doi_snapshot=doi_snapshot or (target_paper.doi if target_paper else ''),
    )


def build_paper_summary_payload(queryset, request=None) -> dict:
    yearly_distribution = list(
        queryset.annotate(year=ExtractYear('date_acquired'))
        .values('year')
        .annotate(count=Count('id'))
        .order_by('-year')
    )
    type_distribution = list(
        queryset.values('paper_type')
        .annotate(count=Count('id'))
        .order_by('-count', 'paper_type')
    )
    latest_records = queryset.order_by('-date_acquired', '-created_at')[:5]
    duplicate_doi_groups = list(
        queryset.exclude(doi='')
        .values('doi')
        .annotate(count=Count('id'))
        .filter(count__gt=1)
        .order_by('-count', 'doi')
    )

    alert_breakdown = []
    for definition in METADATA_ALERT_DEFINITIONS:
        alert_breakdown.append(
            {
                'code': definition['code'],
                'label': definition['label'],
                'severity': definition['severity'],
                'count': queryset.filter(**{definition['field']: ''}).count(),
            }
        )

    recent_records = []
    for paper in latest_records:
        recent_records.append(
            {
                'id': paper.id,
                'title': paper.title,
                'date_acquired': paper.date_acquired.isoformat(),
                'paper_type': paper.paper_type,
                'paper_type_display': paper.get_paper_type_display(),
                'journal_name': paper.journal_name,
                'citation_count': paper.citation_count,
                'is_representative': paper.is_representative,
                'metadata_alerts': build_paper_metadata_alerts(paper),
                'metadata_alert_details': build_paper_metadata_alert_details(paper),
            }
        )

    return {
        'total_count': queryset.count(),
        'representative_count': queryset.filter(is_representative=True).count(),
        'recent_count': queryset.filter(date_acquired__year__gte=timezone.now().year - 2).count(),
        'missing_doi_count': queryset.filter(doi='').count(),
        'missing_source_url_count': queryset.filter(source_url='').count(),
        'incomplete_metadata_count': queryset.filter(
            metadata_alert_count__gt=0
        ).count()
        if hasattr(queryset, 'query')
        else queryset.filter(pages='').count(),
        'duplicate_doi_count': len(duplicate_doi_groups),
        'yearly_distribution': [
            {'year': item['year'], 'count': item['count']}
            for item in yearly_distribution
            if item['year'] is not None
        ],
        'type_distribution': [
            {
                'paper_type': item['paper_type'],
                'label': dict(Paper.PAPER_TYPES).get(item['paper_type'], item['paper_type']),
                'count': item['count'],
            }
            for item in type_distribution
        ],
        'recent_records': recent_records,
        'metadata_alert_breakdown': alert_breakdown,
    }


def build_representative_overview(queryset) -> dict:
    representative_queryset = queryset.filter(is_representative=True).order_by(
        '-citation_count',
        '-date_acquired',
        '-created_at',
    )
    top_items = [
        {
            'id': paper.id,
            'title': paper.title,
            'journal_name': paper.journal_name,
            'date_acquired': paper.date_acquired.isoformat(),
            'citation_count': paper.citation_count,
            'metadata_alerts': build_paper_metadata_alerts(paper),
        }
        for paper in representative_queryset[:5]
    ]
    return {
        'count': representative_queryset.count(),
        'top_items': top_items,
    }


def build_cleanup_suggestions(queryset) -> list[dict]:
    suggestions = [
        {
            'key': 'normalize_text_fields',
            'label': '标准化 DOI/链接/卷期页',
            'description': '统一 DOI 大小写并清理多余空白，适合做低风险批量清洗。',
            'count': queryset.exclude(doi='').count()
            + queryset.exclude(source_url='').count()
            + queryset.exclude(pages='').count(),
            'example_ids': list(queryset.values_list('id', flat=True)[:5]),
        },
        {
            'key': 'review_missing_doi',
            'label': '补齐 DOI',
            'description': '当前记录缺少 DOI，建议回查原始成果页后补录。',
            'count': queryset.filter(doi='').count(),
            'example_ids': list(queryset.filter(doi='').values_list('id', flat=True)[:5]),
        },
        {
            'key': 'review_missing_source_url',
            'label': '补齐来源链接',
            'description': '当前记录缺少来源链接，后续导出与核验成本较高。',
            'count': queryset.filter(source_url='').count(),
            'example_ids': list(queryset.filter(source_url='').values_list('id', flat=True)[:5]),
        },
        {
            'key': 'review_missing_pages',
            'label': '补齐页码',
            'description': '当前记录缺少页码范围，建议按期刊或会议原文补录。',
            'count': queryset.filter(pages='').count(),
            'example_ids': list(queryset.filter(pages='').values_list('id', flat=True)[:5]),
        },
    ]
    return [item for item in suggestions if item['count'] > 0]


def build_compare_candidates(queryset) -> list[dict]:
    return [
        {
            'id': paper.id,
            'title': paper.title,
            'journal_name': paper.journal_name,
            'date_acquired': paper.date_acquired.isoformat(),
            'citation_count': paper.citation_count,
            'is_representative': paper.is_representative,
        }
        for paper in queryset.order_by('-date_acquired', '-citation_count', '-created_at')[:20]
    ]


def build_compare_payload(left: Paper, right: Paper) -> dict:
    left_alerts = build_paper_metadata_alert_details(left)
    right_alerts = build_paper_metadata_alert_details(right)
    left_keywords = {item.keyword.name for item in left.paperkeyword_set.select_related('keyword').all()}
    right_keywords = {item.keyword.name for item in right.paperkeyword_set.select_related('keyword').all()}
    left_coauthors = {item.name for item in left.coauthors.all()}
    right_coauthors = {item.name for item in right.coauthors.all()}

    def completeness_score(paper: Paper) -> int:
        return sum(
            1
            for field in ('doi', 'pages', 'source_url', 'journal_level')
            if getattr(paper, field, '')
        )

    left_score = completeness_score(left)
    right_score = completeness_score(right)
    comparison_rows = [
        {'field': 'paper_type', 'label': '成果类型', 'left': left.get_paper_type_display(), 'right': right.get_paper_type_display()},
        {'field': 'journal_name', 'label': '期刊/会议', 'left': left.journal_name, 'right': right.journal_name},
        {'field': 'date_acquired', 'label': '发表时间', 'left': left.date_acquired.isoformat(), 'right': right.date_acquired.isoformat()},
        {'field': 'citation_count', 'label': '引用次数', 'left': left.citation_count, 'right': right.citation_count},
        {'field': 'is_representative', 'label': '代表作', 'left': '是' if left.is_representative else '否', 'right': '是' if right.is_representative else '否'},
        {'field': 'metadata_completeness', 'label': '元数据完整度', 'left': left_score, 'right': right_score},
    ]

    return {
        'left': {
            'id': left.id,
            'title': left.title,
            'metadata_alerts': left_alerts,
            'keywords': sorted(left_keywords),
            'coauthors': sorted(left_coauthors),
        },
        'right': {
            'id': right.id,
            'title': right.title,
            'metadata_alerts': right_alerts,
            'keywords': sorted(right_keywords),
            'coauthors': sorted(right_coauthors),
        },
        'comparison_rows': comparison_rows,
        'summary': {
            'citation_gap': left.citation_count - right.citation_count,
            'metadata_completeness_gap': left_score - right_score,
            'shared_keywords': sorted(left_keywords & right_keywords),
            'shared_coauthors': sorted(left_coauthors & right_coauthors),
            'left_alert_count': len(left_alerts),
            'right_alert_count': len(right_alerts),
        },
    }


def build_governance_overview(queryset, teacher) -> dict:
    recent_logs = PaperOperationLog.objects.filter(teacher=teacher, paper_id__in=queryset.values_list('id', flat=True))
    return {
        'summary': build_paper_summary_payload(queryset),
        'representative_overview': build_representative_overview(queryset),
        'cleanup_suggestions': build_cleanup_suggestions(queryset),
        'compare_candidates': build_compare_candidates(queryset),
        'recent_operations': [serialize_operation_log(item) for item in recent_logs.order_by('-created_at', '-id')[:12]],
    }


def export_papers_as_csv(papers: Iterable[Paper]) -> str:
    output = StringIO()
    writer = csv.writer(output)
    writer.writerow(
        [
            'ID',
            '标题',
            '成果类型',
            '期刊/会议',
            '发表时间',
            '引用次数',
            '代表作',
            'DOI',
            '来源链接',
            '卷号',
            '期号',
            '页码',
            '期刊级别',
            '元数据提醒',
        ]
    )
    for paper in papers:
        writer.writerow(
            [
                paper.id,
                paper.title,
                paper.get_paper_type_display(),
                paper.journal_name,
                paper.date_acquired.isoformat(),
                paper.citation_count,
                '是' if paper.is_representative else '否',
                paper.doi,
                paper.source_url,
                paper.published_volume,
                paper.published_issue,
                paper.pages,
                paper.journal_level,
                '；'.join(build_paper_metadata_alerts(paper)),
            ]
        )
    return output.getvalue()


def normalize_selected_papers(papers: Iterable[Paper]) -> list[Paper]:
    updated_papers: list[Paper] = []
    for paper in papers:
        next_doi = (paper.doi or '').strip().lower()
        next_source_url = (paper.source_url or '').strip()
        next_pages = (paper.pages or '').strip()
        next_journal_level = (paper.journal_level or '').strip()
        next_volume = (paper.published_volume or '').strip()
        next_issue = (paper.published_issue or '').strip()

        changed_fields = []
        if paper.doi != next_doi:
            paper.doi = next_doi
            changed_fields.append('doi')
        if paper.source_url != next_source_url:
            paper.source_url = next_source_url
            changed_fields.append('source_url')
        if paper.pages != next_pages:
            paper.pages = next_pages
            changed_fields.append('pages')
        if paper.journal_level != next_journal_level:
            paper.journal_level = next_journal_level
            changed_fields.append('journal_level')
        if paper.published_volume != next_volume:
            paper.published_volume = next_volume
            changed_fields.append('published_volume')
        if paper.published_issue != next_issue:
            paper.published_issue = next_issue
            changed_fields.append('published_issue')

        if changed_fields:
            paper.save(update_fields=changed_fields)
            updated_papers.append(paper)
    return updated_papers
