from __future__ import annotations

from dataclasses import dataclass

from django.utils import timezone

from .models import AcademicService, IntellectualProperty, Paper, Project, TeachingAchievement
from .scoring_engine import TeacherScoringEngine


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


def build_portrait_explanation() -> dict:
    return {
        'overview': '当前教师画像由基础档案、论文、项目、知识产权、教学成果与学术服务实时聚合形成，用于展示当前分析视图而非单一结果页。',
        'formation_steps': [
            '先读取教师基础档案中的学院、职称、学科、研究方向与个人简介。',
            '再按成果类型聚合论文、项目、知识产权、教学成果与学术服务，形成多成果全景口径。',
            '最后依据当前轻量评分公式生成雷达维度、综合得分、近年趋势与结构化分析结果。',
        ],
        'transparency_note': '当前页面中的分数、趋势和结构都可追溯到明确的数据来源说明，不使用黑盒式模型结论。',
        'trend_note': '近年趋势基于成果发生年份回溯计算，用于观察近年变化，不等同于已经固化存档的年度画像快照。',
        'snapshot_boundary_note': '后续如需引入画像快照，应新增快照时间点、冻结口径与版本说明；本次仅预留口径说明，不实现完整快照存储。',
    }
