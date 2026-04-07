from __future__ import annotations

from dataclasses import dataclass
import logging

from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.db import IntegrityError
from django.utils import timezone

from .models import (
    AcademicService,
    IntellectualProperty,
    Paper,
    PortraitSnapshot,
    Project,
    TeachingAchievement,
)
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
    direction_text = '提升' if delta > 0 else '回落' if delta < 0 else '持平'
    metric_deltas: dict[str, float | int] = {}
    drivers: list[str] = []

    if key == 'academic_output':
        paper_delta = current_metrics['paper_count'] - baseline_metrics['paper_count']
        citation_delta = current_metrics['citation_total'] - baseline_metrics['citation_total']
        metric_deltas = {'paper_delta': paper_delta, 'citation_delta': citation_delta}
        if paper_delta:
            drivers.append(f"论文数量 {_format_signed(paper_delta)} 篇")
        if citation_delta:
            drivers.append(f"总被引 {_format_signed(citation_delta)} 次")
        interpretation = TeacherScoringEngine.DIMENSION_FORMULAS[key]
    elif key == 'funding_support':
        project_delta = current_metrics['project_count'] - baseline_metrics['project_count']
        funding_delta = round(current_metrics['funding_total'] - baseline_metrics['funding_total'], 1)
        metric_deltas = {'project_delta': project_delta, 'funding_delta': funding_delta}
        if project_delta:
            drivers.append(f"项目数量 {_format_signed(project_delta)} 项")
        if funding_delta:
            drivers.append(f"累计经费 {_format_signed(funding_delta)} 万元")
        interpretation = TeacherScoringEngine.DIMENSION_FORMULAS[key]
    elif key == 'ip_strength':
        ip_delta = current_metrics['ip_count'] - baseline_metrics['ip_count']
        transformed_delta = current_metrics['transformed_ip_count'] - baseline_metrics['transformed_ip_count']
        metric_deltas = {'ip_delta': ip_delta, 'transformed_ip_delta': transformed_delta}
        if ip_delta:
            drivers.append(f"知识产权 {_format_signed(ip_delta)} 项")
        if transformed_delta:
            drivers.append(f"转化成果 {_format_signed(transformed_delta)} 项")
        interpretation = TeacherScoringEngine.DIMENSION_FORMULAS[key]
    elif key == 'talent_training':
        teaching_delta = current_metrics['teaching_count'] - baseline_metrics['teaching_count']
        paper_delta = current_metrics['paper_count'] - baseline_metrics['paper_count']
        metric_deltas = {'teaching_delta': teaching_delta, 'paper_delta': paper_delta}
        if teaching_delta:
            drivers.append(f"教学成果 {_format_signed(teaching_delta)} 项")
        if paper_delta:
            drivers.append(f"协同论文 {_format_signed(paper_delta)} 篇")
        interpretation = TeacherScoringEngine.DIMENSION_FORMULAS[key]
    elif key == 'academic_reputation':
        service_delta = current_metrics['service_count'] - baseline_metrics['service_count']
        collaborator_delta = current_metrics['collaborator_count'] - baseline_metrics['collaborator_count']
        citation_delta = current_metrics['citation_total'] - baseline_metrics['citation_total']
        metric_deltas = {
            'service_delta': service_delta,
            'collaborator_delta': collaborator_delta,
            'citation_delta': citation_delta,
        }
        if service_delta:
            drivers.append(f"学术服务 {_format_signed(service_delta)} 项")
        if collaborator_delta:
            drivers.append(f"合作作者 {_format_signed(collaborator_delta)} 位")
        if citation_delta:
            drivers.append(f"引用表现 {_format_signed(citation_delta)} 次")
        interpretation = TeacherScoringEngine.DIMENSION_FORMULAS[key]
    else:
        keyword_delta = current_metrics['keyword_count'] - baseline_metrics['keyword_count']
        project_delta = current_metrics['project_count'] - baseline_metrics['project_count']
        metric_deltas = {'keyword_delta': keyword_delta, 'project_delta': project_delta}
        if keyword_delta:
            drivers.append(f"论文关键词 {_format_signed(keyword_delta)} 个")
        if project_delta:
            drivers.append(f"参与项目 {_format_signed(project_delta)} 项")
        interpretation = TeacherScoringEngine.DIMENSION_FORMULAS[key]

    if not drivers:
        drivers.append('当前阶段关键输入基本持平，因此维度变化有限。')

    return {
        'change_summary': f"{name}{direction_text} {abs(delta)} 分，当前按成果年份回溯口径观察到该维度发生变化。",
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
    teaching_achievements: int
    academic_services: int


def _get_current_year() -> int:
    return timezone.now().year


def _build_snapshot_lock_key(user_id: int, year: int) -> str:
    return f'portrait:snapshot:lock:{user_id}:{year}'


def _build_dimension_payload_from_metrics(metrics: dict) -> tuple[dict, float]:
    dimension_scores = TeacherScoringEngine.build_dimension_values(metrics)
    total_score = TeacherScoringEngine.calculate_total_score(dimension_scores)
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


def resolve_portrait_payload(user, *, year: int | None = None) -> dict:
    current_year = _get_current_year()
    selected_year = year if isinstance(year, int) else current_year

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


def _build_benchmark_cache_key(*, scope: str, year: int | None, college_id: str | None, version: int) -> str:
    normalized_college = (college_id or '').strip() or 'all'
    normalized_year = year if isinstance(year, int) else 'current'
    return f'portrait:benchmark:v{version}:{scope}:{normalized_college}:{normalized_year}'


def calculate_benchmark_scores(scope: str = 'college', college_id: str | None = None, year: int | None = None) -> dict:
    normalized_scope = scope if scope in {'college', 'university'} else 'college'
    normalized_college = (college_id or '').strip()
    selected_year = year if isinstance(year, int) else None
    version = _get_benchmark_cache_version()
    cache_key = _build_benchmark_cache_key(
        scope=normalized_scope,
        year=selected_year,
        college_id=normalized_college,
        version=version,
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

    payloads = [resolve_portrait_payload(user, year=selected_year) for user in queryset.only('id', 'department')]
    average_payload = _build_average_dimension_payload(payloads)
    payload = {
        'scope': normalized_scope,
        'college_id': normalized_college,
        'label': '全校平均' if normalized_scope == 'university' else '本院平均',
        **average_payload,
    }
    cache.set(cache_key, payload, timeout=BENCHMARK_CACHE_TTL_SECONDS)
    return payload


def calculate_college_comparison_scores(*, year: int | None = None) -> list[dict]:
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
        payload = calculate_benchmark_scores(scope='college', college_id=college_id, year=year)
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


def _resolve_recent_years(user, span: int = 4) -> list[int]:
    year_candidates: set[int] = set()
    for model in (Paper, Project, IntellectualProperty, TeachingAchievement, AcademicService):
        year_candidates.update(
            year
            for year in model.objects.filter(teacher=user, status=APPROVED_STATUS).values_list('date_acquired__year', flat=True)
            if year
        )

    current_year = timezone.now().year
    latest_year = max(max(year_candidates, default=current_year), current_year)
    start_year = latest_year - span + 1
    return list(range(start_year, latest_year + 1))


def build_recent_structure(user, span: int = 4) -> list[dict]:
    years = _resolve_recent_years(user, span=span)
    records: list[dict] = []
    yearly_metrics = TeacherScoringEngine.collect_metrics_series(user, years)

    for year in years:
        metrics = yearly_metrics.get(year, {})
        bucket = PortraitYearBucket(
            year=year,
            papers=metrics.get('paper_count', 0),
            projects=metrics.get('project_count', 0),
            intellectual_properties=metrics.get('ip_count', 0),
            teaching_achievements=metrics.get('teaching_count', 0),
            academic_services=metrics.get('service_count', 0),
        )
        records.append(
            {
                'year': bucket.year,
                'papers': bucket.papers,
                'projects': bucket.projects,
                'intellectual_properties': bucket.intellectual_properties,
                'teaching_achievements': bucket.teaching_achievements,
                'academic_services': bucket.academic_services,
                'total': bucket.papers
                + bucket.projects
                + bucket.intellectual_properties
                + bucket.teaching_achievements
                + bucket.academic_services,
            }
        )

    return records


def build_dimension_trend(user, span: int = 4) -> list[dict]:
    trend_records: list[dict] = []
    years = _resolve_recent_years(user, span=span)
    yearly_metrics = TeacherScoringEngine.collect_metrics_series(user, years)

    for year in years:
        metrics = yearly_metrics.get(year, TeacherScoringEngine.collect_metrics(user, year=year))
        values = TeacherScoringEngine.build_dimension_values(metrics)
        trend_records.append(
            {
                'year': year,
                **values,
                'total_score': TeacherScoringEngine.calculate_total_score(values),
            }
        )

    return trend_records


def build_stage_comparison(user, span: int = 4, *, year: int | None = None) -> dict:
    current_year = _get_current_year()
    selected_year = year if isinstance(year, int) else None

    if selected_year is None:
        years = _resolve_recent_years(user, span=span)
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

    current_payload = resolve_portrait_payload(user, year=selected_year)
    baseline_payload = resolve_portrait_payload(user, year=baseline_year) if baseline_year > 0 else {
        'dimension_scores': {key: 0.0 for key in TeacherScoringEngine.DIMENSION_LABELS.keys()},
        'total_score': 0.0,
        'source': 'runtime',
        'year': baseline_year,
    }

    current_values = current_payload.get('dimension_scores', {}) or {}
    baseline_values = baseline_payload.get('dimension_scores', {}) or {}
    current_metrics = TeacherScoringEngine.collect_metrics(user) if selected_year >= current_year else TeacherScoringEngine.collect_metrics(user, year=selected_year)
    baseline_metrics = TeacherScoringEngine.collect_metrics(user, year=baseline_year) if baseline_year > 0 else {
        'paper_count': 0,
        'citation_total': 0,
        'project_count': 0,
        'funding_total': 0.0,
        'ip_count': 0,
        'transformed_ip_count': 0,
        'teaching_count': 0,
        'service_count': 0,
        'keyword_count': 0,
        'collaborator_count': 0,
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
        summary = f'{selected_year} 年画像综合得分较 {baseline_year} 年提升 {score_delta} 分。'
    elif score_delta < 0:
        summary = f'{selected_year} 年画像综合得分较 {baseline_year} 年回落 {abs(score_delta)} 分。'
    else:
        summary = f'{selected_year} 年画像综合得分与 {baseline_year} 年基本持平。'

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
) -> dict:
    anchor_years = _resolve_recent_years(user, span=span)
    generated_at = timezone.now().isoformat()
    current_year = _get_current_year()
    selected_year = year if isinstance(year, int) else current_year
    trigger_label = '画像页实时生成' if generation_trigger == 'dashboard_request' else '报告接口实时生成'

    if selected_year < current_year:
        snapshot_payload = resolve_portrait_payload(user, year=selected_year)
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
        }

    return {
        'current_mode': 'runtime_projection',
        'generated_at': generated_at,
        'span_years': span,
        'anchor_years': anchor_years,
        'year': selected_year,
        'persistence_status': 'not_persisted',
        'freeze_status': 'response_scoped',
        'snapshot_label': '当前运行时画像快照',
        'snapshot_version': RUNTIME_SNAPSHOT_VERSION,
        'version_semantics': '当前年份按实时聚合计算，历史年份建议使用已冻结快照。',
        'generation_trigger': generation_trigger,
        'generation_trigger_label': trigger_label,
        'freeze_scope_note': '当前快照会在单次接口响应或导出周期内保持一致，但不自动落库。',
        'comparison_ready': len(anchor_years) >= 2,
        'current_boundary_note': '当前画像为实时视图，适合观察最新变化。',
        'frontend_carry_note': '前端承接生成时间、对比口径、权重说明和阶段结论，用于可解释展示与报告导出。',
        'compare_boundary_note': '当前允许运行时快照与历史快照/基线做辅助对比。',
        'next_step_note': '如需年末归档可触发快照生成任务固化当前结果。',
        'recommended_fields': [
            'generated_at',
            'teacher_id',
            'dimension_values',
            'total_score',
            'weight_spec_version',
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
    }


def build_portrait_explanation() -> dict:
    return {
        'overview': '当前教师画像由基础档案、论文、项目、知识产权、教学成果与学术服务实时聚合形成，已从单纯状态页增强为可解释、可比较、可报告化的分析视图。',
        'formation_steps': [
            '先读取教师基础档案中的学院、职称、学科、研究方向与个人简介。',
            '再按成果类型聚合论文、项目、知识产权、教学成果与学术服务，形成多成果全景口径。',
            '最后依据当前轻量评分公式生成雷达维度、综合得分、阶段对比、近年趋势和报告化摘要。',
        ],
        'transparency_note': '当前页面中的分数、趋势、对比和报告摘要都可追溯到明确的数据来源与形成逻辑，不引入黑箱推荐模型。',
        'trend_note': '近年趋势与阶段对比支持“历史快照优先、缺失回溯补齐”的口径，用于观察变化并保留历史稳定性。',
        'snapshot_boundary_note': '历史年份画像快照会落库冻结；当前年份保留实时聚合视图，便于观察新增成果带来的即时变化。',
        'snapshot_version_note': '快照版本区分运行时口径和落库口径：运行时视图用于当前分析，历史快照用于冻结归档。',
        'weight_logic_summary': '综合得分采用固定权重加权求和，强调解释稳定性和实时聚合可用性；权重说明与公式会在前端以结构化卡片展示。',
        'report_boundary_note': '报告化能力支持导出，并可在历史年份读取已冻结快照，降低跨年口径漂移风险。',
    }


def build_portrait_report(user) -> dict:
    radar_result = TeacherScoringEngine.get_comprehensive_radar_data(user)
    metrics = radar_result['metrics']
    weight_spec = TeacherScoringEngine.build_weight_spec(metrics)
    stage_comparison = build_stage_comparison(user)
    snapshot_boundary = build_snapshot_boundary(user, generation_trigger='report_request')
    top_dimension = max(weight_spec, key=lambda item: item['current_value'], default=None)

    highlights = [
        f"总成果 {metrics['total_achievements']} 项，综合得分 {radar_result['total_score']} 分。",
        f"论文 {metrics['paper_count']} 篇、项目 {metrics['project_count']} 项、知识产权 {metrics['ip_count']} 项。",
        f"总被引 {metrics['citation_total']} 次，合作作者 {metrics['collaborator_count']} 位。",
    ]
    if top_dimension:
        highlights.append(f"当前最强维度为“{top_dimension['name']}”，维度得分 {top_dimension['current_value']} 分。")

    return {
        'report_title': f'{user.real_name or user.username} 教师画像分析报告',
        'generated_at': timezone.now().isoformat(),
        'summary': '当前报告基于实时业务数据聚合生成，用于教师画像解释、阶段观察与页面导出，不等同于已冻结归档快照。',
        'highlights': highlights,
        'weight_spec': weight_spec,
        'stage_comparison': stage_comparison,
        'snapshot_boundary': snapshot_boundary,
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
                'title': '形成逻辑',
                'summary': '画像由档案信息与多成果数据实时聚合形成。',
                'bullets': [
                    '基础档案提供学院、职称、学科和研究方向背景。',
                    '成果数据提供论文、项目、知识产权、教学成果和学术服务输入。',
                    '评分结果由固定权重公式实时计算，便于解释与追踪。',
                ],
            },
            {
                'title': '阶段对比',
                'summary': stage_comparison.get('summary', '当前阶段暂无足够样本形成阶段对比。'),
                'bullets': [
                    stage_comparison.get('structured_summary', '当前暂无结构化阶段对比说明。'),
                    stage_comparison.get('coverage_note', '当前暂无覆盖说明。'),
                ]
                + [
                    f"{item['name']}：{item['baseline_value']} -> {item['current_value']}（{item['delta']:+.1f}），{item['change_summary']}"
                    for item in stage_comparison.get('changed_dimensions', [])
                ],
            },
            {
                'title': '快照摘要',
                'summary': f"{snapshot_boundary['snapshot_label']} · {snapshot_boundary['snapshot_version']}",
                'bullets': [
                    snapshot_boundary['version_semantics'],
                    snapshot_boundary['freeze_scope_note'],
                    snapshot_boundary['compare_boundary_note'],
                ],
            },
            {
                'title': '快照边界',
                'summary': snapshot_boundary['current_boundary_note'],
                'bullets': [
                    snapshot_boundary['frontend_carry_note'],
                    snapshot_boundary['next_step_note'],
                ],
            },
        ],
    }


def export_portrait_report_markdown(user) -> str:
    report = build_portrait_report(user)
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
    lines.append('## 维度权重')
    for item in report['weight_spec']:
        lines.append(f"- {item['name']}：权重 {item['weight']}%，当前得分 {item['current_value']}，公式 {item['formula_short']}")
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
