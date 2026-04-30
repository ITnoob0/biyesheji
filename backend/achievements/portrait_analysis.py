from __future__ import annotations

from dataclasses import dataclass
import logging

from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.db import IntegrityError
from django.db.models import Count, Sum
from django.utils import timezone

from evaluation_rules.models import EvaluationRuleVersion

from .models import Paper, PortraitSnapshot, RuleBasedAchievement
from .scoring_engine import TeacherScoringEngine
from .visibility import APPROVED_STATUS

RUNTIME_SNAPSHOT_VERSION = 'portrait-runtime-v1'
PERSISTED_SNAPSHOT_VERSION = 'portrait-snapshot-v1'
BENCHMARK_CACHE_TTL_SECONDS = 24 * 60 * 60
BENCHMARK_CACHE_VERSION_KEY = 'portrait:benchmark:version'

logger = logging.getLogger(__name__)


def _format_signed(value: float | int) -> str:
    return f'{value:+.1f}' if isinstance(value, float) else f'{value:+d}'


def _build_dimension_change_explanation(
    *,
    key: str,
    name: str,
    current_value: float,
    baseline_value: float,
    current_metrics: dict,
    baseline_metrics: dict,
) -> dict:
    delta = round(current_value - baseline_value, 1)
    direction_text = '\u63d0\u5347' if delta > 0 else '\u56de\u843d' if delta < 0 else '\u6301\u5e73'
    metric_deltas: dict[str, float | int] = {}
    drivers: list[str] = []

    if key == 'academic_output':
        paper_score_delta = round(current_metrics['paper_book_score'] - baseline_metrics['paper_book_score'], 1)
        metric_deltas = {'paper_book_score_delta': paper_score_delta}
        if paper_score_delta:
            drivers.append(f"论文著作积分 {_format_signed(paper_score_delta)} 分")
        interpretation = TeacherScoringEngine.DIMENSION_FORMULAS[key]
    elif key == 'funding_support':
        project_score_delta = round(current_metrics['project_score'] - baseline_metrics['project_score'], 1)
        metric_deltas = {'project_score_delta': project_score_delta}
        if project_score_delta:
            drivers.append(f"科研项目积分 {_format_signed(project_score_delta)} 分")
        interpretation = TeacherScoringEngine.DIMENSION_FORMULAS[key]
    elif key == 'ip_strength':
        award_score_delta = round(current_metrics['award_score'] - baseline_metrics['award_score'], 1)
        metric_deltas = {'award_score_delta': award_score_delta}
        if award_score_delta:
            drivers.append(f"成果获奖积分 {_format_signed(award_score_delta)} 分")
        interpretation = TeacherScoringEngine.DIMENSION_FORMULAS[key]
    elif key == 'academic_reputation':
        transformation_delta = round(current_metrics['transformation_score'] - baseline_metrics['transformation_score'], 1)
        think_tank_delta = round(current_metrics['think_tank_score'] - baseline_metrics['think_tank_score'], 1)
        metric_deltas = {
            'transformation_score_delta': transformation_delta,
            'think_tank_score_delta': think_tank_delta,
        }
        if transformation_delta:
            drivers.append(f"成果转化积分 {_format_signed(transformation_delta)} 分")
        if think_tank_delta:
            drivers.append(f"智库成果积分 {_format_signed(think_tank_delta)} 分")
        interpretation = TeacherScoringEngine.DIMENSION_FORMULAS[key]
    elif key == 'interdisciplinary':
        platform_delta = round(current_metrics['platform_team_score'] - baseline_metrics['platform_team_score'], 1)
        science_pop_delta = round(current_metrics['science_pop_score'] - baseline_metrics['science_pop_score'], 1)
        metric_deltas = {'platform_team_score_delta': platform_delta, 'science_pop_score_delta': science_pop_delta}
        if platform_delta:
            drivers.append(f"平台团队积分 {_format_signed(platform_delta)} 分")
        if science_pop_delta:
            drivers.append(f"科普类获奖积分 {_format_signed(science_pop_delta)} 分")
        interpretation = TeacherScoringEngine.DIMENSION_FORMULAS[key]
    else:
        interpretation = TeacherScoringEngine.DIMENSION_FORMULAS.get(key, '')

    if not drivers:
        drivers.append('\u5f53\u524d\u9636\u6bb5\u5173\u952e\u8f93\u5165\u57fa\u672c\u6301\u5e73\uff0c\u56e0\u6b64\u8be5\u7ef4\u5ea6\u53d8\u5316\u6709\u9650\u3002')

    return {
        'change_summary': f"{name}{direction_text} {abs(delta)} \u5206\uff0c\u5f53\u524d\u6309\u6210\u679c\u5e74\u4efd\u56de\u6eaf\u53e3\u5f84\u89c2\u5bdf\u5230\u8be5\u7ef4\u5ea6\u53d1\u751f\u53d8\u5316\u3002",
        'drivers': drivers[:3],
        'interpretation': interpretation,
        'metric_deltas': metric_deltas,
        'boundary_note': '',
    }


@dataclass(frozen=True)
class PortraitYearBucket:
    year: int
    papers: int
    projects: int
    intellectual_properties: int
    academic_services: int


def _get_current_year() -> int:
    return timezone.now().year


def _build_snapshot_lock_key(user_id: int, year: int) -> str:
    return f'portrait:snapshot:lock:{user_id}:{year}'


def _serialize_rule_version(version: EvaluationRuleVersion | None, stats: dict | None = None) -> dict | None:
    if version is None:
        return None
    stats = stats or {}
    return {
        'id': version.id,
        'code': version.code,
        'name': version.name,
        'status': version.status,
        'status_label': version.get_status_display(),
        'source_document': version.source_document,
        'summary': version.summary,
        'updated_at': version.updated_at.isoformat() if version.updated_at else None,
        'achievement_total': int(stats.get('achievement_total') or 0),
        'score_total': round(float(stats.get('score_total') or 0.0), 1),
    }


def build_rule_version_scope(user, rule_version_id: int | None = None) -> dict:
    active_version = (
        EvaluationRuleVersion.objects.filter(status=EvaluationRuleVersion.STATUS_ACTIVE)
        .order_by('-updated_at', '-id')
        .first()
    )
    rows = (
        RuleBasedAchievement.objects.filter(teacher=user, status=APPROVED_STATUS)
        .values('version_id')
        .annotate(achievement_total=Count('id'), score_total=Sum('final_score'))
    )
    version_stats = {
        row['version_id']: {
            'achievement_total': row['achievement_total'],
            'score_total': row['score_total'] or 0,
        }
        for row in rows
        if row.get('version_id')
    }
    version_ids = set(version_stats.keys())
    if active_version is not None:
        version_ids.add(active_version.id)
    if rule_version_id is not None:
        version_ids.add(rule_version_id)

    versions = {
        item.id: item
        for item in EvaluationRuleVersion.objects.filter(id__in=version_ids).order_by('-updated_at', '-id')
    }
    selected_version = versions.get(rule_version_id) if rule_version_id is not None else None
    available_versions = [
        _serialize_rule_version(version, version_stats.get(version.id))
        for version in versions.values()
    ]

    if selected_version is None:
        score_scope_note = '当前按全部规则版本累计展示，已审核成果沿用其所属规则版本下冻结的 final_score。'
    else:
        score_scope_note = f'当前仅展示“{selected_version.name}”规则版本下的已审核成果和冻结积分。'

    return {
        'selected_rule_version_id': selected_version.id if selected_version else None,
        'is_all_versions': selected_version is None,
        'selected_version': _serialize_rule_version(selected_version, version_stats.get(selected_version.id) if selected_version else None),
        'active_version': _serialize_rule_version(active_version, version_stats.get(active_version.id) if active_version else None),
        'available_versions': available_versions,
        'score_scope_note': score_scope_note,
        'freeze_note': '规则版本切换后，历史版本已审核成果不按新规则重算；新成果按当前启用规则形成 final_score 后继续累计。',
    }


def _build_dimension_payload_from_metrics(metrics: dict) -> tuple[dict, float]:
    dimension_scores = TeacherScoringEngine.build_dimension_values(metrics)
    total_score = TeacherScoringEngine.calculate_total_score(metrics)
    return dimension_scores, total_score


def _resolve_or_backfill_snapshot(user, year: int) -> tuple[PortraitSnapshot, bool]:
    existing = PortraitSnapshot.objects.filter(user=user, year=year).first()
    if existing:
        return existing, False

    lock_key = _build_snapshot_lock_key(user.id, year)
    lock_acquired = cache.add(lock_key, '1', timeout=5)
    try:
        existing = PortraitSnapshot.objects.filter(user=user, year=year).first()
        if existing:
            return existing, False

        metrics_series = TeacherScoringEngine.collect_metrics_series(user, [year])
        metrics = metrics_series.get(year) or TeacherScoringEngine.collect_metrics(user, year=year)
        dimension_scores, total_score = _build_dimension_payload_from_metrics(metrics)

        try:
            snapshot, created = PortraitSnapshot.objects.get_or_create(
                user=user,
                year=year,
                defaults={
                    'dimension_scores': dimension_scores,
                    'total_score': total_score,
                },
            )
            return snapshot, created
        except IntegrityError:
            snapshot = PortraitSnapshot.objects.filter(user=user, year=year).first()
            if snapshot is not None:
                return snapshot, False
            raise
    finally:
        if lock_acquired:
            cache.delete(lock_key)


def resolve_portrait_payload(user, *, year: int | None = None, rule_version_id: int | None = None) -> dict:
    current_year = _get_current_year()
    selected_year = year if isinstance(year, int) else current_year
    rule_version_scope = build_rule_version_scope(user, rule_version_id=rule_version_id)

    if rule_version_id is not None:
        metrics_year = selected_year if selected_year < current_year else None
        metrics = TeacherScoringEngine.collect_metrics(user, year=metrics_year, rule_version_id=rule_version_id)
        dimension_scores, total_score = _build_dimension_payload_from_metrics(metrics)
        return {
            'year': selected_year,
            'dimension_scores': dimension_scores,
            'total_score': total_score,
            'source': 'rule_version_runtime',
            'snapshot_created': False,
            'snapshot_id': None,
            'rule_version_scope': rule_version_scope,
        }

    # 历史年份优先读取快照，不存在则回溯计算后落库。
    if selected_year < current_year:
        snapshot, created = _resolve_or_backfill_snapshot(user, selected_year)
        return {
            'year': selected_year,
            'dimension_scores': snapshot.dimension_scores or {},
            'total_score': float(snapshot.total_score or 0),
            'source': 'snapshot',
            'snapshot_created': created,
            'snapshot_id': snapshot.id,
            'rule_version_scope': rule_version_scope,
        }

    # 当前年份（或未来参数）按实时口径返回。
    metrics = TeacherScoringEngine.collect_metrics(user)
    dimension_scores, total_score = _build_dimension_payload_from_metrics(metrics)
    return {
        'year': selected_year,
        'dimension_scores': dimension_scores,
        'total_score': total_score,
        'source': 'runtime',
        'snapshot_created': False,
        'snapshot_id': None,
        'rule_version_scope': rule_version_scope,
    }


def _build_average_dimension_payload(payloads: list[dict]) -> dict:
    if not payloads:
        empty_dimension_scores = {
            key: 0.0
            for key in TeacherScoringEngine.DIMENSION_LABELS.keys()
        }
        return {
            'dimension_scores': empty_dimension_scores,
            'total_score': 0.0,
            'sample_size': 0,
        }

    dimension_totals = {key: 0.0 for key in TeacherScoringEngine.DIMENSION_LABELS.keys()}
    total_scores = 0.0
    for item in payloads:
        score_map = item.get('dimension_scores', {}) or {}
        for key in dimension_totals.keys():
            dimension_totals[key] += float(score_map.get(key, 0.0))
        total_scores += float(item.get('total_score', 0.0))

    sample_size = len(payloads)
    dimension_scores = {
        key: round(value / sample_size, 1)
        for key, value in dimension_totals.items()
    }
    return {
        'dimension_scores': dimension_scores,
        'total_score': round(total_scores / sample_size, 1),
        'sample_size': sample_size,
    }


def _get_benchmark_cache_version() -> int:
    version = cache.get(BENCHMARK_CACHE_VERSION_KEY)
    if isinstance(version, int):
        return version
    cache.set(BENCHMARK_CACHE_VERSION_KEY, 1, timeout=None)
    return 1


def _build_benchmark_cache_key(*, scope: str, year: int | None, college_id: str | None, version: int, rule_version_id: int | None = None) -> str:
    normalized_college = (college_id or '').strip() or 'all'
    normalized_year = year if isinstance(year, int) else 'current'
    normalized_rule_version = rule_version_id if isinstance(rule_version_id, int) else 'all'
    return f'portrait:benchmark:v{version}:{scope}:{normalized_college}:{normalized_year}:rule-{normalized_rule_version}'


def calculate_benchmark_scores(
    scope: str = 'college',
    college_id: str | None = None,
    year: int | None = None,
    rule_version_id: int | None = None,
) -> dict:
    normalized_scope = scope if scope in {'college', 'university'} else 'college'
    normalized_college = (college_id or '').strip()
    selected_year = year if isinstance(year, int) else None
    version = _get_benchmark_cache_version()
    cache_key = _build_benchmark_cache_key(
        scope=normalized_scope,
        year=selected_year,
        college_id=normalized_college,
        version=version,
        rule_version_id=rule_version_id,
    )
    cached = cache.get(cache_key)
    if cached is not None:
        return cached

    user_model = get_user_model()
    queryset = user_model.objects.filter(
        is_active=True,
        is_staff=False,
        is_superuser=False,
    )
    if normalized_scope == 'college':
        if not normalized_college:
            payload = {
                'scope': 'college',
                'college_id': '',
                'label': '本院平均',
                **_build_average_dimension_payload([]),
            }
            cache.set(cache_key, payload, timeout=BENCHMARK_CACHE_TTL_SECONDS)
            return payload
        queryset = queryset.filter(department=normalized_college)

    payloads = [
        resolve_portrait_payload(user, year=selected_year, rule_version_id=rule_version_id)
        for user in queryset.only('id', 'department')
    ]
    average_payload = _build_average_dimension_payload(payloads)
    payload = {
        'scope': normalized_scope,
        'college_id': normalized_college,
        'label': '全校平均' if normalized_scope == 'university' else '本院平均',
        **average_payload,
    }
    cache.set(cache_key, payload, timeout=BENCHMARK_CACHE_TTL_SECONDS)
    return payload


def calculate_college_comparison_scores(*, year: int | None = None, rule_version_id: int | None = None) -> list[dict]:
    user_model = get_user_model()
    college_ids = list(
        user_model.objects.filter(
            is_active=True,
            is_staff=False,
            is_superuser=False,
        )
        .exclude(department='')
        .order_by()
        .values_list('department', flat=True)
        .distinct()
    )
    comparison_rows = []
    for college_id in college_ids:
        payload = calculate_benchmark_scores(scope='college', college_id=college_id, year=year, rule_version_id=rule_version_id)
        comparison_rows.append(
            {
                'college_id': college_id,
                'label': college_id,
                'total_score': payload['total_score'],
                'sample_size': payload['sample_size'],
                'dimension_scores': payload['dimension_scores'],
            }
        )
    return comparison_rows


def invalidate_benchmark_score_cache() -> None:
    version = _get_benchmark_cache_version()
    cache.set(BENCHMARK_CACHE_VERSION_KEY, version + 1, timeout=None)


def _resolve_recent_years(user, span: int = 4, rule_version_id: int | None = None) -> list[int]:
    year_candidates: set[int] = set()
    queryset = RuleBasedAchievement.objects.filter(teacher=user, status=APPROVED_STATUS)
    if rule_version_id is not None:
        queryset = queryset.filter(version_id=rule_version_id)
    year_candidates.update(
        year
        for year in queryset.values_list('date_acquired__year', flat=True)
        if year
    )

    current_year = timezone.now().year
    latest_year = max(max(year_candidates, default=current_year), current_year)
    start_year = latest_year - span + 1
    return list(range(start_year, latest_year + 1))


def build_recent_structure(user, span: int = 4, rule_version_id: int | None = None) -> list[dict]:
    years = _resolve_recent_years(user, span=span, rule_version_id=rule_version_id)
    records: list[dict] = []
    yearly_metrics = TeacherScoringEngine.collect_metrics_series(user, years, rule_version_id=rule_version_id)

    for year in years:
        metrics = yearly_metrics.get(year, {})
        bucket = PortraitYearBucket(
            year=year,
            papers=metrics.get('paper_count', 0),
            projects=metrics.get('project_count', 0),
            intellectual_properties=metrics.get('award_count', 0) + metrics.get('transformation_count', 0) + metrics.get('think_tank_count', 0),
            academic_services=metrics.get('platform_count', 0) + metrics.get('science_pop_count', 0),
        )
        records.append(
            {
                'year': bucket.year,
                'papers': bucket.papers,
                'projects': bucket.projects,
                'intellectual_properties': bucket.intellectual_properties,
                'academic_services': bucket.academic_services,
                'total': bucket.papers
                + bucket.projects
                + bucket.intellectual_properties
                + bucket.academic_services,
            }
        )

    return records


def build_dimension_trend(user, span: int = 4, rule_version_id: int | None = None) -> list[dict]:
    trend_records: list[dict] = []
    years = _resolve_recent_years(user, span=span, rule_version_id=rule_version_id)
    yearly_metrics = TeacherScoringEngine.collect_metrics_series(user, years, rule_version_id=rule_version_id)

    for year in years:
        metrics = yearly_metrics.get(year, TeacherScoringEngine.collect_metrics(user, year=year, rule_version_id=rule_version_id))
        values = TeacherScoringEngine.build_dimension_values(metrics)
        trend_records.append(
            {
                'year': year,
                **values,
                'total_score': TeacherScoringEngine.calculate_total_score(metrics),
            }
        )

    return trend_records


def build_stage_comparison(user, span: int = 4, *, year: int | None = None, rule_version_id: int | None = None) -> dict:
    current_year = _get_current_year()
    selected_year = year if isinstance(year, int) else None

    if selected_year is None:
        years = _resolve_recent_years(user, span=span, rule_version_id=rule_version_id)
        if len(years) < 2:
            return {
                'available': False,
                'compare_mode': 'runtime_snapshot_vs_projection_baseline',
                'reference_type': 'yearly_projection_baseline',
                'summary': '当前画像样本仍较少，后续补充更多年度成果后可展示阶段对比。',
                'coverage_note': '当前仅保留阶段对比接口边界，不强行构造伪时间序列。',
                'structured_summary': '当前还没有足够年度样本，不输出阶段差异解释。',
            }
        selected_year = years[-1]

    baseline_year = selected_year - 1

    current_payload = resolve_portrait_payload(user, year=selected_year, rule_version_id=rule_version_id)
    baseline_payload = resolve_portrait_payload(user, year=baseline_year, rule_version_id=rule_version_id) if baseline_year > 0 else {
        'dimension_scores': {key: 0.0 for key in TeacherScoringEngine.DIMENSION_LABELS.keys()},
        'total_score': 0.0,
        'source': 'runtime',
        'year': baseline_year,
    }

    current_values = current_payload.get('dimension_scores', {}) or {}
    baseline_values = baseline_payload.get('dimension_scores', {}) or {}
    current_metrics = (
        TeacherScoringEngine.collect_metrics(user, rule_version_id=rule_version_id)
        if selected_year >= current_year
        else TeacherScoringEngine.collect_metrics(user, year=selected_year, rule_version_id=rule_version_id)
    )
    baseline_metrics = TeacherScoringEngine.collect_metrics(user, year=baseline_year, rule_version_id=rule_version_id) if baseline_year > 0 else {
        'paper_count': 0,
        'representative_paper_count': 0,
        'project_count': 0,
        'funding_total': 0.0,
        'award_count': 0,
        'ip_count': 0,
        'transformation_count': 0,
        'think_tank_count': 0,
        'transformed_ip_count': 0,
        'platform_count': 0,
        'science_pop_count': 0,
        'service_count': 0,
        'keyword_count': 0,
        'collaborator_count': 0,
        'paper_book_score': 0.0,
        'project_score': 0.0,
        'award_score': 0.0,
        'transformation_score': 0.0,
        'think_tank_score': 0.0,
        'platform_team_score': 0.0,
        'science_pop_score': 0.0,
        'total_achievements': 0,
    }
    label_map = TeacherScoringEngine.DIMENSION_LABELS
    changed_dimensions = []
    for key in label_map.keys():
        current_value = float(current_values.get(key, 0.0))
        baseline_value = float(baseline_values.get(key, 0.0))
        delta = round(current_value - baseline_value, 1)
        changed_dimensions.append(
            {
                'key': key,
                'name': label_map.get(key, key),
                'current_value': current_value,
                'baseline_value': baseline_value,
                'delta': delta,
                'trend': 'up' if delta > 0 else 'down' if delta < 0 else 'flat',
                **_build_dimension_change_explanation(
                    key=key,
                    name=label_map.get(key, key),
                    current_value=current_value,
                    baseline_value=baseline_value,
                    current_metrics=current_metrics,
                    baseline_metrics=baseline_metrics,
                ),
            }
        )

    current_total_score = round(float(current_payload.get('total_score', 0.0)), 1)
    baseline_total_score = round(float(baseline_payload.get('total_score', 0.0)), 1)
    score_delta = round(current_total_score - baseline_total_score, 1)
    achievement_delta = int(current_metrics['total_achievements'] - baseline_metrics['total_achievements'])

    if score_delta > 0:
        summary = f'{selected_year} 年科研积分总分较 {baseline_year} 年提升 {score_delta} 分。'
    elif score_delta < 0:
        summary = f'{selected_year} 年科研积分总分较 {baseline_year} 年回落 {abs(score_delta)} 分。'
    else:
        summary = f'{selected_year} 年科研积分总分与 {baseline_year} 年基本持平。'

    return {
        'available': True,
        'compare_mode': 'snapshot_or_runtime_vs_previous_year',
        'reference_type': 'historical_snapshot_or_projection',
        'current_label': f'{selected_year} 年',
        'baseline_label': f'{baseline_year} 年',
        'current_total_score': current_total_score,
        'baseline_total_score': baseline_total_score,
        'score_delta': score_delta,
        'current_total_achievements': current_metrics['total_achievements'],
        'baseline_total_achievements': baseline_metrics['total_achievements'],
        'achievement_delta': achievement_delta,
        'changed_dimensions': changed_dimensions,
        'summary': summary,
        'structured_summary': (
            f"当前画像与 {baseline_year} 年相比，"
            f"{'整体提升' if score_delta > 0 else '整体回落' if score_delta < 0 else '整体保持稳定'}。"
        ),
        'largest_change_dimension': max(changed_dimensions, key=lambda item: abs(item['delta'])) if changed_dimensions else None,
        'coverage_note': '若目标年份快照已冻结，则优先使用快照；若缺失则按历史年份回溯计算并落库。',
    }


def build_snapshot_boundary(
    user,
    span: int = 4,
    *,
    generation_trigger: str = 'dashboard_request',
    year: int | None = None,
    rule_version_id: int | None = None,
) -> dict:
    anchor_years = _resolve_recent_years(user, span=span, rule_version_id=rule_version_id)
    generated_at = timezone.now().isoformat()
    current_year = _get_current_year()
    selected_year = year if isinstance(year, int) else current_year
    trigger_label = '画像页实时生成' if generation_trigger == 'dashboard_request' else '报告接口实时生成'
    rule_version_scope = build_rule_version_scope(user, rule_version_id=rule_version_id)

    if selected_year < current_year and rule_version_id is None:
        snapshot_payload = resolve_portrait_payload(user, year=selected_year, rule_version_id=rule_version_id)
        snapshot = PortraitSnapshot.objects.filter(user=user, year=selected_year).first()
        return {
            'current_mode': 'historical_snapshot',
            'generated_at': generated_at,
            'span_years': span,
            'anchor_years': anchor_years,
            'year': selected_year,
            'persistence_status': 'persisted',
            'freeze_status': 'database_frozen',
            'snapshot_label': f'{selected_year} 年画像快照',
            'snapshot_version': PERSISTED_SNAPSHOT_VERSION,
            'version_semantics': '历史年份优先读取已落库快照；缺失时按历史口径回溯计算并立即固化。',
            'generation_trigger': generation_trigger,
            'generation_trigger_label': trigger_label,
            'freeze_scope_note': '历史快照落库后固定，不会因后续成果补录或删除而自动回写。',
            'comparison_ready': len(anchor_years) >= 2,
            'current_boundary_note': '当前为历史冻结快照视图，已具备归档稳定性。',
            'frontend_carry_note': '前端承接快照年份、冻结状态和阶段对比说明，用于历史分析。',
            'compare_boundary_note': '历史对比优先使用快照；若快照缺失由后端回溯并固化后再比较。',
            'next_step_note': '如需批量年末快照，可增加定时任务统一落库。',
            'recommended_fields': [
                'year',
                'teacher_id',
                'dimension_scores',
                'total_score',
                'created_at',
            ],
            'current_snapshot': {
                'label': f'{selected_year} 年画像快照',
                'kind': 'persisted_snapshot',
                'version': PERSISTED_SNAPSHOT_VERSION,
                'generated_at': (snapshot.created_at.isoformat() if snapshot else generated_at),
                'freeze_scope': 'database_row',
                'generation_trigger': generation_trigger,
                'snapshot_created': bool(snapshot_payload.get('snapshot_created')),
            },
            'rule_version_scope': rule_version_scope,
        }

    return {
        'current_mode': 'rule_version_projection' if rule_version_id is not None else 'runtime_projection',
        'generated_at': generated_at,
        'span_years': span,
        'anchor_years': anchor_years,
        'year': selected_year,
        'persistence_status': 'not_persisted',
        'freeze_status': 'response_scoped',
        'snapshot_label': '当前运行时画像快照',
        'snapshot_version': RUNTIME_SNAPSHOT_VERSION,
        'version_semantics': '当前年份按实时聚合计算；若选择历史规则版本，则按该版本下已审核成果的冻结 final_score 聚合。',
        'generation_trigger': generation_trigger,
        'generation_trigger_label': trigger_label,
        'freeze_scope_note': rule_version_scope['freeze_note'] if rule_version_id is not None else '当前快照会在单次接口响应或导出周期内保持一致，但不自动落库。',
        'comparison_ready': len(anchor_years) >= 2,
        'current_boundary_note': '当前画像为实时视图，适合观察最新变化。',
        'frontend_carry_note': '前端承接生成时间、对比口径、积分结构说明和阶段结论，用于可解释展示与报告导出。',
        'compare_boundary_note': '当前允许运行时快照与历史快照/基线做辅助对比。',
        'next_step_note': '如需年末归档可触发快照生成任务固化当前结果。',
        'recommended_fields': [
            'generated_at',
            'teacher_id',
            'dimension_values',
            'total_score',
            'score_scope_version',
            'data_scope_note',
            'source_range',
        ],
        'current_snapshot': {
            'label': '当前运行时画像快照',
            'kind': 'runtime_snapshot_view',
            'version': RUNTIME_SNAPSHOT_VERSION,
            'generated_at': generated_at,
            'freeze_scope': 'single_response',
            'generation_trigger': generation_trigger,
        },
        'rule_version_scope': rule_version_scope,
    }


def build_portrait_explanation() -> dict:
    return {
        'overview': '\u5f53\u524d\u6559\u5e08\u753b\u50cf\u7531\u5df2\u7ecf\u5b66\u9662\u5ba1\u6838\u901a\u8fc7\u7684\u89c4\u5219\u5316\u79d1\u7814\u6210\u679c\u5b9e\u65f6\u805a\u5408\u5f62\u6210\uff0c\u5f3a\u8c03\u89c4\u5219\u53ef\u8ffd\u6eaf\u3001\u79ef\u5206\u53ef\u89e3\u91ca\u3001\u753b\u50cf\u53ef\u6bd4\u8f83\u3002',
        'formation_steps': [
            '\u5148\u8bfb\u53d6\u6559\u5e08\u57fa\u7840\u6863\u6848\u4e2d\u7684\u5b66\u9662\u3001\u804c\u79f0\u3001\u5b66\u79d1\u3001\u7814\u7a76\u65b9\u5411\u4e0e\u4e2a\u4eba\u7b80\u4ecb\u3002',
            '\u518d\u6309\u8bc4\u4ef7\u89c4\u5219\u7684\u5927\u7c7b\u4e0e\u52a0\u5206\u9879\u805a\u5408\u5df2\u901a\u8fc7\u5ba1\u6838\u7684\u8bba\u6587\u8457\u4f5c\u3001\u9879\u76ee\u3001\u83b7\u5956\u3001\u8f6c\u5316\u3001\u667a\u5e93\u3001\u5e73\u53f0\u56e2\u961f\u4e0e\u79d1\u666e\u7c7b\u6210\u679c\u3002',
            '\u6700\u540e\u4f9d\u636e\u5ba1\u6838\u901a\u8fc7\u6210\u679c\u7684 final_score \u76f4\u63a5\u6c42\u548c\u5f62\u6210\u79d1\u7814\u79ef\u5206\u603b\u5206\uff0c\u5e76\u540c\u6b65\u751f\u6210\u4e94\u7ef4\u79d1\u7814\u96f7\u8fbe\u3001\u9636\u6bb5\u5bf9\u6bd4\u3001\u8fd1\u5e74\u8d8b\u52bf\u548c\u62a5\u544a\u5316\u6458\u8981\u3002',
        ],
        'transparency_note': '\u5f53\u524d\u9875\u9762\u4e2d\u7684\u5206\u6570\u3001\u8d8b\u52bf\u3001\u5bf9\u6bd4\u548c\u62a5\u544a\u6458\u8981\u90fd\u53ef\u8ffd\u6eaf\u5230\u660e\u786e\u7684\u6570\u636e\u6765\u6e90\u4e0e\u5f62\u6210\u903b\u8f91\uff0c\u4e0d\u5f15\u5165\u9ed1\u7bb1\u63a8\u8350\u6a21\u578b\u3002',
        'trend_note': '\u8fd1\u5e74\u8d8b\u52bf\u4e0e\u9636\u6bb5\u5bf9\u6bd4\u652f\u6301\u201c\u5386\u53f2\u5feb\u7167\u4f18\u5148\u3001\u7f3a\u5931\u56de\u6eaf\u8865\u9f50\u201d\u7684\u53e3\u5f84\uff0c\u7528\u4e8e\u89c2\u5bdf\u79d1\u7814\u80fd\u529b\u53d8\u5316\u5e76\u4fdd\u7559\u5386\u53f2\u7a33\u5b9a\u6027\u3002',
        'snapshot_boundary_note': '\u5386\u53f2\u5e74\u4efd\u753b\u50cf\u5feb\u7167\u4f1a\u843d\u5e93\u51bb\u7ed3\uff1b\u5f53\u524d\u5e74\u4efd\u4fdd\u7559\u5b9e\u65f6\u805a\u5408\u89c6\u56fe\uff0c\u4fbf\u4e8e\u89c2\u5bdf\u65b0\u589e\u79d1\u7814\u6210\u679c\u5e26\u6765\u7684\u5373\u65f6\u53d8\u5316\u3002',
        'snapshot_version_note': '\u5feb\u7167\u7248\u672c\u533a\u5206\u8fd0\u884c\u65f6\u53e3\u5f84\u548c\u843d\u5e93\u53e3\u5f84\uff1a\u8fd0\u884c\u65f6\u89c6\u56fe\u7528\u4e8e\u5f53\u524d\u5206\u6790\uff0c\u5386\u53f2\u5feb\u7167\u7528\u4e8e\u51bb\u7ed3\u5f52\u6863\u3002',
        'weight_logic_summary': '\u79d1\u7814\u79ef\u5206\u603b\u5206\u4e0d\u505a\u5927\u7c7b\u4e8c\u6b21\u52a0\u6743\uff0c\u6309\u5ba1\u6838\u901a\u8fc7\u4e14\u53bb\u91cd\u540e\u7684\u6210\u679c final_score \u76f4\u63a5\u76f8\u52a0\uff1b\u4e94\u7ef4\u96f7\u8fbe\u53ea\u7528\u4e8e\u7ed3\u6784\u89e3\u91ca\u548c\u8d8b\u52bf\u89c2\u5bdf\u3002',
        'report_boundary_note': '\u62a5\u544a\u5316\u80fd\u529b\u652f\u6301\u5bfc\u51fa\uff0c\u5e76\u53ef\u5728\u5386\u53f2\u5e74\u4efd\u8bfb\u53d6\u5df2\u51bb\u7ed3\u5feb\u7167\uff0c\u964d\u4f4e\u8de8\u5e74\u53e3\u5f84\u6f02\u79fb\u98ce\u9669\u3002',
    }


def build_portrait_report(user, rule_version_id: int | None = None) -> dict:
    radar_result = TeacherScoringEngine.get_comprehensive_radar_data(user, rule_version_id=rule_version_id)
    metrics = radar_result['metrics']
    weight_spec = TeacherScoringEngine.build_weight_spec(metrics)
    stage_comparison = build_stage_comparison(user, rule_version_id=rule_version_id)
    snapshot_boundary = build_snapshot_boundary(user, generation_trigger='report_request', rule_version_id=rule_version_id)
    rule_version_scope = build_rule_version_scope(user, rule_version_id=rule_version_id)
    top_dimension = max(weight_spec, key=lambda item: item['current_value'], default=None)

    highlights = [
        f"\u603b\u6210\u679c {metrics['total_achievements']} \u9879\uff0c\u79d1\u7814\u79ef\u5206\u603b\u5206 {radar_result['total_score']} \u5206\u3002",
        f"\u8bba\u6587\u8457\u4f5c {metrics['paper_count']} \u9879\u3001\u79d1\u7814\u9879\u76ee {metrics['project_count']} \u9879\u3001\u6210\u679c\u83b7\u5956 {metrics['award_count']} \u9879\u3002",
        f"\u6210\u679c\u8f6c\u5316 {metrics['transformation_count']} \u9879\u3001\u5e73\u53f0\u56e2\u961f {metrics['platform_count']} \u9879\u3001\u79d1\u666e\u7c7b\u6210\u679c {metrics['science_pop_count']} \u9879\u3002",
    ]
    if top_dimension:
        highlights.append(f"\u5f53\u524d\u6700\u5f3a\u7ef4\u5ea6\u4e3a\u201c{top_dimension['name']}\u201d\uff0c\u7ef4\u5ea6\u5f97\u5206 {top_dimension['current_value']} \u5206\u3002")

    return {
        'report_title': f"{user.real_name or user.username} \u6559\u5e08\u753b\u50cf\u5206\u6790\u62a5\u544a",
        'generated_at': timezone.now().isoformat(),
        'summary': '\u5f53\u524d\u62a5\u544a\u57fa\u4e8e\u5b9e\u65f6\u4e1a\u52a1\u6570\u636e\u805a\u5408\u751f\u6210\uff0c\u7528\u4e8e\u6559\u5e08\u753b\u50cf\u89e3\u91ca\u3001\u9636\u6bb5\u89c2\u5bdf\u4e0e\u9875\u9762\u5bfc\u51fa\uff0c\u4e0d\u7b49\u540c\u4e8e\u5df2\u51bb\u7ed3\u5f52\u6863\u5feb\u7167\u3002',
        'highlights': highlights,
        'weight_spec': weight_spec,
        'stage_comparison': stage_comparison,
        'snapshot_boundary': snapshot_boundary,
        'rule_version_scope': rule_version_scope,
        'snapshot_digest': {
            'label': snapshot_boundary['snapshot_label'],
            'version': snapshot_boundary['snapshot_version'],
            'generated_at': snapshot_boundary['generated_at'],
            'generation_trigger_label': snapshot_boundary['generation_trigger_label'],
            'freeze_scope_note': snapshot_boundary['freeze_scope_note'],
            'compare_boundary_note': snapshot_boundary['compare_boundary_note'],
        },
        'sections': [
            {
                'title': '\u5f62\u6210\u903b\u8f91',
                'summary': '\u753b\u50cf\u7531\u6863\u6848\u4fe1\u606f\u4e0e\u79d1\u7814\u76f8\u5173\u6210\u679c\u6570\u636e\u5b9e\u65f6\u805a\u5408\u5f62\u6210\u3002',
                'bullets': [
                    '\u57fa\u7840\u6863\u6848\u63d0\u4f9b\u5b66\u9662\u3001\u804c\u79f0\u3001\u5b66\u79d1\u548c\u7814\u7a76\u65b9\u5411\u80cc\u666f\u3002',
                    '\u79d1\u7814\u753b\u50cf\u8f93\u5165\u805a\u7126\u8bba\u6587\u3001\u9879\u76ee\u3001\u77e5\u8bc6\u4ea7\u6743\u548c\u5b66\u672f\u670d\u52a1\uff0c\u6559\u5b66\u6210\u679c\u4fdd\u7559\u5728\u6210\u679c\u5168\u666f\u4e2d\u4f46\u4e0d\u8fdb\u5165\u79d1\u7814\u753b\u50cf\u8bc4\u5206\u3002',
                    '\u79d1\u7814\u79ef\u5206\u603b\u5206\u7531\u5ba1\u6838\u901a\u8fc7\u6210\u679c final_score \u53bb\u91cd\u540e\u76f4\u63a5\u7d2f\u52a0\uff0c\u4e94\u7ef4\u96f7\u8fbe\u7528\u4e8e\u89e3\u91ca\u7ed3\u6784\u800c\u975e\u52a0\u6743\u603b\u5206\u3002',
                ],
            },
            {
                'title': '\u9636\u6bb5\u5bf9\u6bd4',
                'summary': stage_comparison.get('summary', '\u5f53\u524d\u9636\u6bb5\u6682\u65e0\u8db3\u591f\u6837\u672c\u5f62\u6210\u9636\u6bb5\u5bf9\u6bd4\u3002'),
                'bullets': [
                    stage_comparison.get('structured_summary', '\u5f53\u524d\u6682\u65e0\u7ed3\u6784\u5316\u9636\u6bb5\u5bf9\u6bd4\u8bf4\u660e\u3002'),
                    stage_comparison.get('coverage_note', '\u5f53\u524d\u6682\u65e0\u8986\u76d6\u8bf4\u660e\u3002'),
                ]
                + [
                    f"{item['name']}\uff1a{item['baseline_value']} -> {item['current_value']}\uff08{item['delta']:+.1f}\uff09\uff0c{item['change_summary']}"
                    for item in stage_comparison.get('changed_dimensions', [])
                ],
            },
            {
                'title': '\u5feb\u7167\u6458\u8981',
                'summary': f"{snapshot_boundary['snapshot_label']} / {snapshot_boundary['snapshot_version']}",
                'bullets': [
                    snapshot_boundary['version_semantics'],
                    snapshot_boundary['freeze_scope_note'],
                    snapshot_boundary['compare_boundary_note'],
                ],
            },
            {
                'title': '\u5feb\u7167\u8fb9\u754c',
                'summary': snapshot_boundary['current_boundary_note'],
                'bullets': [
                    snapshot_boundary['frontend_carry_note'],
                    snapshot_boundary['next_step_note'],
                ],
            },
        ],
    }


def export_portrait_report_markdown(user, rule_version_id: int | None = None) -> str:
    report = build_portrait_report(user, rule_version_id=rule_version_id)
    lines = [
        f"# {report['report_title']}",
        '',
        f"- 生成时间：{report['generated_at']}",
        f"- 报告说明：{report['summary']}",
        '',
        '## 画像摘要',
    ]
    lines.extend([f"- {item}" for item in report['highlights']])
    lines.append('')
    lines.append('## 维度积分结构')
    for item in report['weight_spec']:
        lines.append(f"- {item['name']}：原始积分 {item.get('raw_score', 0)}，雷达展示分 {item['current_value']}，说明 {item['formula_short']}")
    lines.append('')
    lines.append('## 快照摘要')
    lines.append(
        f"- {report['snapshot_digest']['label']}：{report['snapshot_digest']['version']} / {report['snapshot_digest']['generation_trigger_label']}"
    )
    lines.append(f"- {report['snapshot_digest']['freeze_scope_note']}")
    lines.append(f"- {report['snapshot_digest']['compare_boundary_note']}")
    lines.append('')
    lines.append('## 阶段对比')
    lines.append(f"- {report['stage_comparison'].get('summary', '暂无阶段对比')}")
    lines.append(f"- {report['stage_comparison'].get('structured_summary', '暂无结构化变化说明')}")
    for item in report['stage_comparison'].get('changed_dimensions', []):
        lines.append(f"- {item['name']}：{item['baseline_value']} -> {item['current_value']}（{item['delta']:+.1f}）")
        lines.append(f"  - 变化说明：{item['change_summary']}")
        for driver in item.get('drivers', []):
            lines.append(f"  - 驱动因素：{driver}")
    lines.append('')
    lines.append('## 快照边界')
    lines.append(f"- {report['snapshot_boundary']['current_boundary_note']}")
    lines.append(f"- {report['snapshot_boundary']['next_step_note']}")
    return '\n'.join(lines)
