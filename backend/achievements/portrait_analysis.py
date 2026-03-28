from __future__ import annotations

from dataclasses import dataclass

from django.utils import timezone

from .models import AcademicService, IntellectualProperty, Paper, Project, TeachingAchievement
from .scoring_engine import TeacherScoringEngine

RUNTIME_SNAPSHOT_VERSION = 'portrait-runtime-v1'


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
        interpretation = '基础学术产出同时受论文数量与引用表现影响。'
    elif key == 'funding_support':
        project_delta = current_metrics['project_count'] - baseline_metrics['project_count']
        funding_delta = round(current_metrics['funding_total'] - baseline_metrics['funding_total'], 1)
        metric_deltas = {'project_delta': project_delta, 'funding_delta': funding_delta}
        if project_delta:
            drivers.append(f"项目数量 {_format_signed(project_delta)} 项")
        if funding_delta:
            drivers.append(f"累计经费 {_format_signed(funding_delta)} 万元")
        interpretation = '经费与项目攻关维度由项目数量和经费规模共同驱动。'
    elif key == 'ip_strength':
        ip_delta = current_metrics['ip_count'] - baseline_metrics['ip_count']
        transformed_delta = current_metrics['transformed_ip_count'] - baseline_metrics['transformed_ip_count']
        metric_deltas = {'ip_delta': ip_delta, 'transformed_ip_delta': transformed_delta}
        if ip_delta:
            drivers.append(f"知识产权 {_format_signed(ip_delta)} 项")
        if transformed_delta:
            drivers.append(f"转化成果 {_format_signed(transformed_delta)} 项")
        interpretation = '知识产权维度会同时参考产权数量与转化情况。'
    elif key == 'talent_training':
        teaching_delta = current_metrics['teaching_count'] - baseline_metrics['teaching_count']
        paper_delta = current_metrics['paper_count'] - baseline_metrics['paper_count']
        metric_deltas = {'teaching_delta': teaching_delta, 'paper_delta': paper_delta}
        if teaching_delta:
            drivers.append(f"教学成果 {_format_signed(teaching_delta)} 项")
        if paper_delta:
            drivers.append(f"协同论文 {_format_signed(paper_delta)} 篇")
        interpretation = '人才培养成效既受教学成果数量影响，也会参考论文协同支撑。'
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
        interpretation = '学术活跃与声誉维度会综合学术服务、合作网络和引用表现。'
    else:
        keyword_delta = current_metrics['keyword_count'] - baseline_metrics['keyword_count']
        project_delta = current_metrics['project_count'] - baseline_metrics['project_count']
        metric_deltas = {'keyword_delta': keyword_delta, 'project_delta': project_delta}
        if keyword_delta:
            drivers.append(f"论文关键词 {_format_signed(keyword_delta)} 个")
        if project_delta:
            drivers.append(f"参与项目 {_format_signed(project_delta)} 项")
        interpretation = '跨学科融合度主要由关键词覆盖度和项目参与情况共同支撑。'

    if not drivers:
        drivers.append('当前阶段关键输入基本持平，因此维度变化有限。')

    return {
        'change_summary': f"{name}{direction_text} {abs(delta)} 分，当前按成果年份回溯口径观察到该维度发生变化。",
        'drivers': drivers[:3],
        'interpretation': interpretation,
        'metric_deltas': metric_deltas,
        'boundary_note': '当前变化解释基于成果发生年份回溯估算，只用于辅助比较，不等同于正式冻结历史快照。',
    }


@dataclass(frozen=True)
class PortraitYearBucket:
    year: int
    papers: int
    projects: int
    intellectual_properties: int
    teaching_achievements: int
    academic_services: int


def _resolve_recent_years(user, span: int = 4) -> list[int]:
    year_candidates: set[int] = set()
    for model in (Paper, Project, IntellectualProperty, TeachingAchievement, AcademicService):
        year_candidates.update(
            year
            for year in model.objects.filter(teacher=user).values_list('date_acquired__year', flat=True)
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


def build_stage_comparison(user, span: int = 4) -> dict:
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

    latest_year = years[-1]
    previous_year = years[-2]
    yearly_metrics = TeacherScoringEngine.collect_metrics_series(user, years)
    current_metrics = yearly_metrics.get(latest_year, TeacherScoringEngine.collect_metrics(user, year=latest_year))
    baseline_metrics = yearly_metrics.get(previous_year, TeacherScoringEngine.collect_metrics(user, year=previous_year))
    current_values = TeacherScoringEngine.build_dimension_values(current_metrics)
    baseline_values = TeacherScoringEngine.build_dimension_values(baseline_metrics)

    label_map = {
        item['key']: item['name'] for item in TeacherScoringEngine.build_weight_spec(current_metrics)
    }
    changed_dimensions = []
    for key, current_value in current_values.items():
        baseline_value = baseline_values.get(key, 0)
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

    changed_dimensions.sort(key=lambda item: abs(item['delta']), reverse=True)
    current_total_score = TeacherScoringEngine.calculate_total_score(current_values)
    baseline_total_score = TeacherScoringEngine.calculate_total_score(baseline_values)
    score_delta = round(current_total_score - baseline_total_score, 1)
    achievement_delta = current_metrics['total_achievements'] - baseline_metrics['total_achievements']

    if score_delta > 0:
        summary = f'{latest_year} 年画像综合得分较 {previous_year} 年提升 {score_delta} 分。'
    elif score_delta < 0:
        summary = f'{latest_year} 年画像综合得分较 {previous_year} 年回落 {abs(score_delta)} 分。'
    else:
        summary = f'{latest_year} 年画像综合得分与 {previous_year} 年基本持平。'

    return {
        'available': True,
        'compare_mode': 'runtime_snapshot_vs_projection_baseline',
        'reference_type': 'yearly_projection_baseline',
        'current_label': f'{latest_year} 年',
        'baseline_label': f'{previous_year} 年',
        'current_total_score': current_total_score,
        'baseline_total_score': baseline_total_score,
        'score_delta': score_delta,
        'current_total_achievements': current_metrics['total_achievements'],
        'baseline_total_achievements': baseline_metrics['total_achievements'],
        'achievement_delta': achievement_delta,
        'changed_dimensions': changed_dimensions[:4],
        'summary': summary,
        'structured_summary': (
            f"当前运行时画像快照与 {previous_year} 年成果投影基线相比，"
            f"{'整体提升' if score_delta > 0 else '整体回落' if score_delta < 0 else '整体保持稳定'}。"
        ),
        'largest_change_dimension': changed_dimensions[0] if changed_dimensions else None,
        'coverage_note': '当前阶段对比基于成果发生年份回溯估算，用于分析变化趋势，不等同于已落库冻结快照。',
    }


def build_snapshot_boundary(user, span: int = 4, *, generation_trigger: str = 'dashboard_request') -> dict:
    anchor_years = _resolve_recent_years(user, span=span)
    generated_at = timezone.now().isoformat()
    trigger_label = '画像页实时生成' if generation_trigger == 'dashboard_request' else '报告接口实时生成'
    return {
        'current_mode': 'runtime_projection',
        'generated_at': generated_at,
        'span_years': span,
        'anchor_years': anchor_years,
        'persistence_status': 'not_persisted',
        'freeze_status': 'response_scoped',
        'snapshot_label': '当前运行时画像快照',
        'snapshot_version': RUNTIME_SNAPSHOT_VERSION,
        'version_semantics': 'v1 表示当前固定权重公式 + 运行时实时聚合口径下的快照视图，不代表已落库历史版本。',
        'generation_trigger': generation_trigger,
        'generation_trigger_label': trigger_label,
        'freeze_scope_note': '当前快照会在单次接口响应或导出周期内保持一致，用于页面展示和报告导出，但不会落库冻结。',
        'comparison_ready': len(anchor_years) >= 2,
        'current_boundary_note': '当前画像快照仅以“运行时生成的分析视图”方式承接，不落库保存，不作为正式历史档案。',
        'frontend_carry_note': '前端当前承接生成时间、对比口径、权重说明和阶段结论，用于可解释展示与报告导出。',
        'compare_boundary_note': '当前允许运行时画像快照与按成果年份回溯的阶段基线做辅助对比，但不能替代正式历史快照对比。',
        'next_step_note': '后续如需正式快照落库，应补快照时间点、冻结口径、版本号、生成任务来源和回溯说明。',
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
        'trend_note': '近年趋势与阶段对比基于成果发生年份回溯计算，用于观察变化，不等同于已经冻结存档的正式年度画像快照。',
        'snapshot_boundary_note': '当前阶段先明确快照口径、接口边界和前端承接方式，不强行新增快照表；后续如需落库，应单独定义冻结口径与版本策略。',
        'snapshot_version_note': '当前运行时画像快照采用固定版本语义承接：版本号描述的是口径与公式，而不是数据库中的正式历史存档版本。',
        'weight_logic_summary': '综合得分采用固定权重加权求和，强调解释稳定性和实时聚合可用性；权重说明与公式会在前端以结构化卡片展示。',
        'report_boundary_note': '当前报告化能力以实时生成的结构化画像报告为主，支持导出；不宣称已具备完整离线归档报表体系。',
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
