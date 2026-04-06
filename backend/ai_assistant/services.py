from __future__ import annotations

import re

from django.conf import settings
from django.contrib.auth import get_user_model

from achievements.portrait_analysis import build_snapshot_boundary
from achievements.academy_dashboard_analysis import build_scope_querysets
from achievements.models import AcademicService, IntellectualProperty, Paper, Project, TeachingAchievement
from achievements.scoring_engine import TeacherScoringEngine
from achievements.visibility import APPROVED_STATUS
from project_guides.models import ProjectGuide
from project_guides.services import ProjectGuideRecommendationService
from users.access import ACADEMY_SCOPE_MESSAGE, ASSISTANT_SCOPE_MESSAGE, ensure_admin_user, ensure_self_or_admin_user
from users.services import get_teacher_profile

from .utils import AcademicAI


class PortraitAssistantService:
    @staticmethod
    def resolve_target_teacher(request, user_id: int | None = None):
        target_user_id = user_id or request.user.id
        teacher = get_user_model().objects.get(id=target_user_id)
        ensure_self_or_admin_user(request.user, teacher, ASSISTANT_SCOPE_MESSAGE)
        return teacher

    @staticmethod
    def _resolve_recommendation_status(teacher) -> tuple[str, dict | None]:
        open_guide_total = ProjectGuide.objects.filter(status='OPEN').count()
        if open_guide_total <= 0:
            return 'no_open_guides', None

        recommendation_result = ProjectGuideRecommendationService.build_recommendations(teacher)
        if not recommendation_result['recommendations']:
            return 'no_match', recommendation_result
        return 'available', recommendation_result

    @staticmethod
    def _resolve_graph_status(metrics: dict) -> str:
        if metrics.get('total_achievements', 0) <= 0:
            return 'no_data'
        if not getattr(settings, 'ENABLE_NEO4J', False):
            return 'mysql_fallback'
        return 'neo4j_preferred'

    @staticmethod
    def _resolve_profile_missing_fields(teacher, profile) -> list[str]:
        fields = []
        if not (teacher.department or (profile and profile.department)):
            fields.append('院系')
        if not (teacher.title or (profile and profile.title)):
            fields.append('职称')
        if not (profile and profile.discipline):
            fields.append('学科')
        if not (profile and profile.research_interests):
            fields.append('研究兴趣')
        if not teacher.research_direction:
            fields.append('研究方向')
        if not teacher.bio:
            fields.append('个人简介')
        return fields

    @classmethod
    def _build_source_governance(
        cls,
        *,
        metrics: dict | None = None,
        snapshot_boundary: dict | None = None,
        recommendation_status: str | None = None,
        graph_status: str | None = None,
        missing_profile_fields: list[str] | None = None,
        academy_mode: bool = False,
    ) -> dict:
        degraded_flags: list[str] = []
        unavailable_flags: list[str] = []

        if snapshot_boundary and snapshot_boundary.get('persistence_status') == 'not_persisted':
            degraded_flags.append('教师画像历史快照尚未持久化，当前说明基于运行时分析视图。')

        if recommendation_status == 'no_open_guides':
            degraded_flags.append('当前没有开放中的项目指南，推荐链路只保留边界说明。')
        elif recommendation_status == 'no_match':
            degraded_flags.append('当前没有明显高匹配指南，推荐链路会回退为规则边界解释。')

        if graph_status == 'mysql_fallback':
            degraded_flags.append('图谱当前按 MySQL 关系链路解释，复杂图计算不在当前问答范围内。')
        elif graph_status == 'neo4j_preferred':
            degraded_flags.append('图谱遵循 Neo4j 优先、MySQL 回退链路；当前问答只解释轻量图分析边界。')
        elif graph_status == 'no_data':
            unavailable_flags.append('当前成果数据不足，无法形成可验证的图谱证据。')

        if metrics and metrics.get('total_achievements', 0) <= 0:
            unavailable_flags.append('当前尚无成果入库，部分画像和推荐说明只能返回边界提示。')
        elif metrics and metrics.get('total_achievements', 0) < 2:
            degraded_flags.append('当前成果样本较少，部分趋势与联动解释仅供辅助参考。')

        if missing_profile_fields:
            degraded_flags.append(f"教师基础档案仍缺少：{'、'.join(missing_profile_fields[:4])}。")

        return {
            'answer_mode': '系统内真实数据模板化问答',
            'scope_label': '仅使用系统内真实资料、成果、推荐结果、图谱链路说明和学院统计。',
            'verification_note': (
                '来源卡片会标注所属模块、可验证页面和当前可用状态，用户应回到对应页面核验。'
                if not academy_mode
                else '学院问答仅服务管理员统计视角，来源卡片会回到学院看板中的真实统计区。'
            ),
            'degraded_flags': degraded_flags,
            'unavailable_flags': unavailable_flags,
        }

    @staticmethod
    def _base_meta():
        return {
            'scope_note': '当前为受控的轻量智能辅助链路，仅基于系统内真实教师资料、成果聚合、推荐结果和学院统计生成，不调用外部知识库。',
            'non_coverage_note': '当前不支持开放领域问答、外部知识检索、自由多轮推理或面向全网资料的通用知识回答。',
            'acceptance_scope': '本能力属于当前阶段增强项，以模板化、可解释、可回退的问答辅助方式交付。',
            'boundary_notes': [
                '答案只使用当前系统已有资料和统计结果。',
                '当数据缺失时，系统会明确提示信息不足，而不是虚构补全。',
                '图谱、推荐和画像快照都可能因为配置、数据量或口径边界进入降级说明模式。',
                '当前回答更适合做系统内说明与辅助，不等同于完整知识平台。',
            ],
        }

    @staticmethod
    def _source_detail(
        label: str,
        value: str,
        note: str,
        link: dict | None = None,
        *,
        module: str = '',
        module_label: str = '',
        page_label: str = '',
        availability_status: str = 'ok',
        availability_label: str = '可验证',
        verification_text: str = '',
    ):
        payload = {
            'label': label,
            'value': value,
            'note': note,
            'module': module,
            'module_label': module_label,
            'page_label': page_label,
            'availability_status': availability_status,
            'availability_label': availability_label,
            'verification_text': verification_text,
        }
        if link:
            payload['link'] = link
        return payload

    @staticmethod
    def _evidence_link(
        *,
        label: str,
        page: str,
        section: str,
        dimension_key: str = '',
        guide_id: int | None = None,
        record_type: str = '',
        record_id: int | None = None,
        department: str = '',
        year: int | None = None,
        note: str = '',
    ):
        payload = {
            'label': label,
            'page': page,
            'section': section,
        }
        if dimension_key:
            payload['dimension_key'] = dimension_key
        if guide_id:
            payload['guide_id'] = guide_id
        if record_type:
            payload['record_type'] = record_type
        if record_id:
            payload['record_id'] = record_id
        if department:
            payload['department'] = department
        if year:
            payload['year'] = year
        if note:
            payload['note'] = note
        return payload

    @classmethod
    def _build_teacher_fallback_payload(
        cls,
        *,
        question_type: str,
        teacher,
        title: str,
        answer: str,
        reason: str,
        source_details: list[dict],
        boundary_notes: list[str] | None = None,
    ):
        payload = cls._base_meta()
        payload.update(
            {
                'status': 'fallback',
                'title': title,
                'answer': answer,
                'data_sources': ['系统内真实页面与实时聚合结果'],
                'source_details': source_details,
                'question_type': question_type,
                'failure_notice': reason,
                'teacher_snapshot': {
                    'user_id': teacher.id,
                    'teacher_name': teacher.real_name or teacher.username,
                    'department': teacher.department or '',
                    'title': teacher.title or '',
                },
            }
        )
        if boundary_notes:
            payload['boundary_notes'] = payload['boundary_notes'] + boundary_notes
        return payload

    @staticmethod
    def _collect_recent_records(teacher, limit: int = 3) -> list[dict]:
        collections = [
            ('paper', Paper.objects.filter(teacher=teacher, status=APPROVED_STATUS)),
            ('project', Project.objects.filter(teacher=teacher, status=APPROVED_STATUS)),
            ('intellectual_property', IntellectualProperty.objects.filter(teacher=teacher, status=APPROVED_STATUS)),
            ('teaching_achievement', TeachingAchievement.objects.filter(teacher=teacher, status=APPROVED_STATUS)),
            ('academic_service', AcademicService.objects.filter(teacher=teacher, status=APPROVED_STATUS)),
        ]

        records = []
        for record_type, queryset in collections:
            instance = queryset.order_by('-date_acquired').first()
            if not instance:
                continue
            records.append(
                {
                    'id': instance.id,
                    'type': record_type,
                    'title': instance.title,
                    'date_acquired': instance.date_acquired,
                }
            )

        return sorted(records, key=lambda item: item['date_acquired'], reverse=True)[:limit]

    @classmethod
    def _portrait_summary(cls, teacher):
        profile = get_teacher_profile(teacher)
        radar = TeacherScoringEngine.get_comprehensive_radar_data(teacher)
        metrics = radar['metrics']
        top_dimensions = sorted(radar['radar_dimensions'], key=lambda item: item['value'], reverse=True)[:2]

        answer = (
            f"{teacher.real_name or teacher.username}当前来自{teacher.department or '未填写院系'}，"
            f"职称为{teacher.title or '未填写职称'}。系统已汇总其成果 {metrics['total_achievements']} 项，"
            f"其中论文 {metrics['paper_count']} 篇、项目 {metrics['project_count']} 项、知识产权 {metrics['ip_count']} 项。"
            f"从画像维度看，当前更突出的能力是{top_dimensions[0]['name']}和{top_dimensions[1]['name']}。"
            f"{'研究兴趣主要包括' + profile.research_interests if profile and profile.research_interests else '当前研究兴趣信息仍可继续完善。'}"
        )

        return {
            'title': '教师科研画像总结',
            'answer': answer,
            'data_sources': [
                '教师基础资料',
                '实时画像评分引擎',
                '多成果聚合统计',
            ],
            'source_details': [
                cls._source_detail(
                    '教师资料',
                    teacher.real_name or teacher.username,
                    '来自当前系统中的教师基础档案。',
                    cls._evidence_link(
                        label='回到画像说明区',
                        page='portrait',
                        section='portrait-explanation',
                        note='当前摘要仍以实时聚合画像为准。',
                    ),
                    module='portrait',
                    module_label='画像模块',
                    page_label='教师画像主页',
                    verification_text='可在画像形成说明区核验当前教师资料与画像口径。',
                ),
                cls._source_detail(
                    '成果总量',
                    f"{metrics['total_achievements']} 项",
                    '来自论文、项目、知识产权、教学成果和学术服务实时聚合。',
                    cls._evidence_link(
                        label='查看支撑成果区',
                        page='portrait',
                        section='portrait-achievements',
                        note='当前只回跳到权限范围内的真实成果证据区。',
                    ),
                    module='achievement',
                    module_label='成果模块',
                    page_label='教师画像主页 / 代表性成果区',
                    availability_status='limited' if metrics['total_achievements'] < 2 else 'ok',
                    availability_label='样本偏少' if metrics['total_achievements'] < 2 else '可验证',
                    verification_text='可回到画像页代表性成果区继续核验累计成果来源。',
                ),
                cls._source_detail(
                    '画像优势维度',
                    '、'.join(item['name'] for item in top_dimensions),
                    '来自当前画像评分引擎的维度结果。',
                    cls._evidence_link(
                        label='回到画像维度证据区',
                        page='portrait',
                        section='portrait-dimensions',
                        dimension_key=top_dimensions[0]['key'],
                        note='当前优先定位到最突出的画像维度。',
                    ),
                    module='portrait',
                    module_label='画像模块',
                    page_label='教师画像主页',
                    verification_text='可在画像维度证据区核验维度得分和支撑说明。',
                ),
            ],
        }

    @classmethod
    def _portrait_dimension_reason(cls, teacher):
        radar = TeacherScoringEngine.get_comprehensive_radar_data(teacher)
        dimension_insights = radar['dimension_insights']
        top_insights = sorted(dimension_insights, key=lambda item: item['value'], reverse=True)[:2]

        answer = (
            f"当前画像并不是凭空生成，而是依据既有成果与教师资料做维度聚合。"
            f"当前最强的两个维度是{top_insights[0]['name']}和{top_insights[1]['name']}，"
            f"对应得分分别为 {top_insights[0]['value']} 和 {top_insights[1]['value']}。"
            f"系统判断的主要依据包括：{top_insights[0]['formula_note']}；{top_insights[1]['formula_note']}。"
        )

        return {
            'title': '教师画像如何形成',
            'answer': answer,
            'data_sources': [
                '画像维度评分结果',
                '画像维度证据摘要',
            ],
            'source_details': [
                cls._source_detail(
                    item['name'],
                    f"评分 {item['value']} / 权重 {item['weight']}%",
                    '来自当前画像维度计算与证据摘要。',
                    cls._evidence_link(
                        label='回到该维度证据区',
                        page='portrait',
                        section='portrait-dimensions',
                        dimension_key=item['key'],
                        note='当前维度说明仍以实时评分与证据标签为准。',
                    ),
                    module='portrait',
                    module_label='画像模块',
                    page_label='教师画像主页',
                    verification_text='可回到对应画像维度卡片核验评分、公式和证据标签。',
                )
                for item in top_insights
            ],
            'related_reasons': [evidence for item in top_insights for evidence in item.get('evidence', [])[:2]],
        }

    @classmethod
    def _portrait_data_governance(cls, teacher):
        profile = get_teacher_profile(teacher)
        metrics = TeacherScoringEngine.collect_metrics(teacher)
        snapshot_boundary = build_snapshot_boundary(teacher)
        missing_profile_fields = cls._resolve_profile_missing_fields(teacher, profile)
        graph_status = cls._resolve_graph_status(metrics)
        recommendation_status, _ = cls._resolve_recommendation_status(teacher)

        if metrics['total_achievements'] <= 0 and len(missing_profile_fields) >= 4:
            return cls._build_teacher_fallback_payload(
                question_type='portrait_data_governance',
                teacher=teacher,
                title='画像数据仍不足以形成稳定治理说明',
                answer='当前教师的基础档案与成果样本都偏少，系统已回退为数据缺口说明模式。建议先完善基础档案并录入真实成果后，再查看更完整的画像治理说明。',
                reason='当前画像链路存在基础档案缺口和成果样本不足，暂不输出过度解释。',
                source_details=[
                    cls._source_detail(
                        '当前成果样本',
                        '0 项',
                        '尚未形成可稳定解释的画像样本。',
                        cls._evidence_link(label='回到成果录入页', page='achievement-entry', section='achievement-records'),
                        module='achievement',
                        module_label='成果模块',
                        page_label='教师成果录入中心',
                        availability_status='fallback',
                        availability_label='样本不足',
                        verification_text='先录入真实成果，再回到画像与问答核验。',
                    ),
                    cls._source_detail(
                        '档案缺口',
                        '、'.join(missing_profile_fields[:4]),
                        '基础档案字段不足时，画像解释只保留口径与边界说明。',
                        cls._evidence_link(label='回到画像说明区', page='portrait', section='portrait-explanation'),
                        module='portrait',
                        module_label='画像模块',
                        page_label='教师画像主页',
                        availability_status='fallback',
                        availability_label='档案不足',
                        verification_text='可先完善基础档案，再回到画像主页核验。',
                    ),
                ],
                boundary_notes=[
                    '当前画像快照尚未持久化，运行时分析不会替代正式历史档案。',
                    '当档案和成果同时不足时，系统只返回缺口说明，不会伪造画像结论。',
                ],
            )

        completeness_ratio = round((6 - len(missing_profile_fields)) / 6 * 100, 1)
        answer = (
            f"当前画像说明仍是系统内真实数据驱动的运行时分析视图。"
            f"档案完整度约为 {completeness_ratio}% ，当前累计成果 {metrics['total_achievements']} 项。"
            f"画像快照状态为 {snapshot_boundary['persistence_status']}，说明当前还没有正式落库的历史快照。"
            f"{'仍建议优先补充：' + '、'.join(missing_profile_fields[:3]) + '。' if missing_profile_fields else '当前基础档案字段已能支撑常规画像解释。'}"
        )

        return {
            'title': '画像数据口径与缺口说明',
            'answer': answer,
            'data_sources': ['教师基础档案', '画像快照边界', '多成果聚合统计'],
            'source_details': [
                cls._source_detail(
                    '档案完整度',
                    f'{completeness_ratio}%',
                    '按院系、职称、学科、研究兴趣、研究方向和个人简介六类字段做轻量检查。',
                    cls._evidence_link(label='回到画像说明区', page='portrait', section='portrait-explanation'),
                    module='portrait',
                    module_label='画像模块',
                    page_label='教师画像主页',
                    availability_status='limited' if missing_profile_fields else 'ok',
                    availability_label='待补充' if missing_profile_fields else '可验证',
                    verification_text='画像说明区可核验当前口径与快照边界。',
                ),
                cls._source_detail(
                    '快照状态',
                    snapshot_boundary['persistence_status'],
                    snapshot_boundary['current_boundary_note'],
                    cls._evidence_link(label='查看画像形成说明', page='portrait', section='portrait-explanation'),
                    module='portrait',
                    module_label='画像模块',
                    page_label='教师画像主页',
                    availability_status='limited',
                    availability_label='快照未落库',
                    verification_text='当前快照只作为运行时分析视图使用。',
                ),
                cls._source_detail(
                    '成果基础',
                    f"{metrics['total_achievements']} 项",
                    '成果量决定画像解释和趋势说明的稳定程度。',
                    cls._evidence_link(label='回到成果证据区', page='portrait', section='portrait-achievements'),
                    module='achievement',
                    module_label='成果模块',
                    page_label='教师画像主页 / 代表性成果区',
                    availability_status='limited' if metrics['total_achievements'] < 2 else 'ok',
                    availability_label='样本偏少' if metrics['total_achievements'] < 2 else '可验证',
                    verification_text='可回到代表性成果区和成果录入页继续核验。',
                ),
            ],
            'related_reasons': [f'待补字段：{item}' for item in missing_profile_fields[:3]],
            'source_governance': cls._build_source_governance(
                metrics=metrics,
                snapshot_boundary=snapshot_boundary,
                recommendation_status=recommendation_status,
                graph_status=graph_status,
                missing_profile_fields=missing_profile_fields,
            ),
        }

    @classmethod
    def _achievement_summary(cls, teacher):
        metrics = TeacherScoringEngine.collect_metrics(teacher)
        latest_paper = Paper.objects.filter(teacher=teacher, status=APPROVED_STATUS).order_by('-date_acquired').first()
        latest_project = Project.objects.filter(teacher=teacher, status=APPROVED_STATUS).order_by('-date_acquired').first()
        latest_ip = IntellectualProperty.objects.filter(teacher=teacher, status=APPROVED_STATUS).order_by('-date_acquired').first()
        latest_teaching = TeachingAchievement.objects.filter(teacher=teacher, status=APPROVED_STATUS).order_by('-date_acquired').first()
        latest_service = AcademicService.objects.filter(teacher=teacher, status=APPROVED_STATUS).order_by('-date_acquired').first()

        latest_items = [
            item
            for item in [
                latest_paper.title if latest_paper else '',
                latest_project.title if latest_project else '',
                latest_ip.title if latest_ip else '',
                latest_teaching.title if latest_teaching else '',
                latest_service.title if latest_service else '',
            ]
            if item
        ]

        answer = (
            f"{teacher.real_name or teacher.username}当前累计成果 {metrics['total_achievements']} 项，"
            f"结构上以论文 {metrics['paper_count']} 篇、项目 {metrics['project_count']} 项为核心，"
            f"并辅以知识产权 {metrics['ip_count']} 项、教学成果 {metrics['teaching_count']} 项、学术服务 {metrics['service_count']} 项。"
            f"其中论文总被引 {metrics['citation_total']} 次。"
            f"{'近期较新的代表性事项包括：' + '、'.join(latest_items[:3]) + '。' if latest_items else '当前系统中尚无足够的近期成果用于总结。'}"
        )

        return {
            'title': '教师近年成果结构概括',
            'answer': answer,
            'data_sources': [
                '多成果实时聚合统计',
                '当前教师的代表性成果记录',
            ],
            'source_details': [
                cls._source_detail(
                    '论文与项目',
                    f"{metrics['paper_count']} 篇 / {metrics['project_count']} 项",
                    '当前成果结构的主干来源。',
                    cls._evidence_link(
                        label='查看成果记录区',
                        page='achievement-entry',
                        section='achievement-records',
                        record_type='paper',
                        note='当前成果问答只回跳到系统内真实成果记录。',
                    ),
                    module='achievement',
                    module_label='成果模块',
                    page_label='教师成果录入中心',
                    verification_text='可在成果录入页核验论文与项目的真实记录。',
                ),
                cls._source_detail(
                    '支撑成果',
                    f"知产 {metrics['ip_count']} / 教学 {metrics['teaching_count']} / 服务 {metrics['service_count']}",
                    '用于补充教师成果全景。',
                    cls._evidence_link(
                        label='查看画像成果证据区',
                        page='portrait',
                        section='portrait-achievements',
                        note='画像页会展示当前教师最近的代表性成果。',
                    ),
                    module='portrait',
                    module_label='画像模块',
                    page_label='教师画像主页 / 代表性成果区',
                    verification_text='可在画像页代表性成果区继续核验支撑成果。',
                ),
                cls._source_detail(
                    '近期事项',
                    '、'.join(latest_items[:3]) if latest_items else '暂无',
                    '来自当前教师最近的成果记录。',
                    cls._evidence_link(
                        label='回到成果录入页',
                        page='achievement-entry',
                        section='achievement-records',
                        note='当前问答不虚构未入库成果。',
                    ),
                    module='achievement',
                    module_label='成果模块',
                    page_label='教师成果录入中心',
                    availability_status='limited' if not latest_items else 'ok',
                    availability_label='近期不足' if not latest_items else '可验证',
                    verification_text='仅展示系统内已入库的近期成果，不补写外部信息。',
                ),
            ],
        }

    @classmethod
    def _achievement_portrait_link(cls, teacher):
        metrics = TeacherScoringEngine.collect_metrics(teacher)
        radar = TeacherScoringEngine.get_comprehensive_radar_data(teacher)
        top_dimensions = sorted(radar['radar_dimensions'], key=lambda item: item['value'], reverse=True)[:2]
        recent_records = cls._collect_recent_records(teacher, limit=3)

        if metrics['total_achievements'] <= 0:
            return cls._build_teacher_fallback_payload(
                question_type='achievement_portrait_link',
                teacher=teacher,
                title='当前成果不足以支撑画像联动说明',
                answer='当前系统中尚无可验证成果记录，无法说明“成果如何支撑画像”。建议先录入论文、项目或其他成果后，再查看画像联动解释。',
                reason='当前没有成果入库，画像联动链路已回退为边界提示。',
                source_details=[
                    cls._source_detail(
                        '成果记录',
                        '0 项',
                        '当前无法形成成果到画像的证据链。',
                        cls._evidence_link(label='回到成果录入页', page='achievement-entry', section='achievement-records'),
                        module='achievement',
                        module_label='成果模块',
                        page_label='教师成果录入中心',
                        availability_status='fallback',
                        availability_label='无数据',
                        verification_text='先补录真实成果，再回到问答与画像页面核验。',
                    ),
                    cls._source_detail(
                        '画像说明',
                        '已回退为边界提示',
                        '当前不会伪造画像证据结论。',
                        cls._evidence_link(label='查看画像说明区', page='portrait', section='portrait-explanation'),
                        module='portrait',
                        module_label='画像模块',
                        page_label='教师画像主页',
                        availability_status='fallback',
                        availability_label='已降级',
                        verification_text='画像说明区会展示当前口径与边界。',
                    ),
                ],
                boundary_notes=[
                    '成果为空时，画像联动只返回缺口说明。',
                ],
            )

        dimension_messages = []
        if metrics.get('paper_count', 0) > 0:
            dimension_messages.append(f"论文 {metrics['paper_count']} 篇主要支撑“学术产出”维度。")
        if metrics.get('project_count', 0) > 0:
            dimension_messages.append(f"项目 {metrics['project_count']} 项会强化“项目与经费支撑”维度。")
        if metrics.get('ip_count', 0) > 0:
            dimension_messages.append(f"知识产权 {metrics['ip_count']} 项可补强“知识产权与转化”维度。")
        if metrics.get('teaching_count', 0) > 0:
            dimension_messages.append(f"教学成果 {metrics['teaching_count']} 项会进入“人才培养与教学贡献”维度。")
        if metrics.get('service_count', 0) > 0:
            dimension_messages.append(f"学术服务 {metrics['service_count']} 项会补充“学术影响与服务”维度。")

        answer = (
            f"当前成果与画像之间是有明确映射关系的。系统累计识别到成果 {metrics['total_achievements']} 项，"
            f"会按成果类型分别汇入画像维度。"
            f"当前更突出的画像维度是{'、'.join(item['name'] for item in top_dimensions)}。"
            f"{' '.join(dimension_messages[:3])}"
        )

        primary_record = recent_records[0] if recent_records else None
        primary_dimension = top_dimensions[0] if top_dimensions else None

        return {
            'title': '成果如何支撑画像',
            'answer': answer,
            'data_sources': ['成果记录', '实时画像评分引擎', '画像维度证据摘要'],
            'source_details': [
                cls._source_detail(
                    '当前主维度',
                    '、'.join(item['name'] for item in top_dimensions) or '暂无',
                    '画像维度结果会把不同成果类型汇入对应维度得分。',
                    cls._evidence_link(
                        label='查看画像维度证据区',
                        page='portrait',
                        section='portrait-dimensions',
                        dimension_key=primary_dimension['key'] if primary_dimension else '',
                        note='当前优先定位到本次解释涉及的主维度。',
                    ),
                    module='portrait',
                    module_label='画像模块',
                    page_label='教师画像主页',
                    verification_text='可在画像维度证据区核验维度得分和形成说明。',
                ),
                cls._source_detail(
                    '代表性成果',
                    primary_record['title'] if primary_record else '暂无',
                    '优先引用近期真实成果作为画像解释样本。',
                    cls._evidence_link(
                        label='查看支撑成果记录',
                        page='achievement-entry',
                        section='achievement-records',
                        record_type=primary_record['type'] if primary_record else '',
                        record_id=primary_record['id'] if primary_record else None,
                        note='当前只回跳到系统内已入库的真实成果。',
                    ),
                    module='achievement',
                    module_label='成果模块',
                    page_label='教师成果录入中心',
                    verification_text='可在成果录入页核验该成果的具体记录。',
                ),
                cls._source_detail(
                    '画像成果证据',
                    f"{metrics['total_achievements']} 项参与画像解释",
                    '画像页代表性成果区会承接本次解释所依赖的真实成果样本。',
                    cls._evidence_link(
                        label='回到画像成果证据区',
                        page='portrait',
                        section='portrait-achievements',
                        record_type=primary_record['type'] if primary_record else '',
                        record_id=primary_record['id'] if primary_record else None,
                    ),
                    module='portrait',
                    module_label='画像模块',
                    page_label='教师画像主页 / 代表性成果区',
                    verification_text='可在画像成果区回看当前解释引用的成果样本。',
                ),
            ],
            'related_reasons': dimension_messages[:4],
        }

    @classmethod
    def _achievement_recommendation_link(cls, teacher):
        metrics = TeacherScoringEngine.collect_metrics(teacher)
        recommendation_status, result = cls._resolve_recommendation_status(teacher)

        if recommendation_status == 'no_open_guides':
            return cls._build_teacher_fallback_payload(
                question_type='achievement_recommendation_link',
                teacher=teacher,
                title='当前没有开放指南可供联动解释',
                answer='当前项目指南模块没有开放中的指南，因此无法输出“成果如何支撑推荐”的具体推荐结论。系统会保留成果与推荐边界说明，并提示你回到推荐页核验当前开放状态。',
                reason='当前没有开放中的项目指南，推荐链路已降级。',
                source_details=[
                    cls._source_detail(
                        '推荐状态',
                        '0 条开放指南',
                        '推荐服务不会为未开放指南生成推荐结论。',
                        cls._evidence_link(label='查看推荐结果页', page='recommendations', section='recommendation-evidence'),
                        module='recommendation',
                        module_label='推荐模块',
                        page_label='项目指南推荐页',
                        availability_status='fallback',
                        availability_label='无开放指南',
                        verification_text='可先回到推荐页确认当前指南开放状态。',
                    ),
                    cls._source_detail(
                        '当前成果样本',
                        f"{metrics['total_achievements']} 项",
                        '成果数据会保留，但不会被包装成不存在的推荐结论。',
                        cls._evidence_link(label='回到成果记录区', page='achievement-entry', section='achievement-records'),
                        module='achievement',
                        module_label='成果模块',
                        page_label='教师成果录入中心',
                        availability_status='limited',
                        availability_label='可验证',
                        verification_text='成果仍可在成果录入页继续核验。',
                    ),
                ],
                boundary_notes=['没有开放指南时，系统只给出推荐边界说明，不伪造推荐结果。'],
            )

        recommendations = result['recommendations'] if result else []
        if recommendation_status == 'no_match' or not recommendations:
            return cls._build_teacher_fallback_payload(
                question_type='achievement_recommendation_link',
                teacher=teacher,
                title='当前成果尚未形成明显高匹配推荐',
                answer='当前已有真实成果数据，但规则增强推荐服务尚未识别到明显高匹配指南。系统会回退为边界说明，建议补充研究方向标签、近期成果或等待新的开放指南后再查看。',
                reason='当前没有明显高匹配推荐，推荐链路已回退为规则边界解释。',
                source_details=[
                    cls._source_detail(
                        '推荐结果',
                        '暂无高匹配',
                        '这表示当前规则命中不足，而不是系统可以随意补全推荐。',
                        cls._evidence_link(label='查看推荐结果页', page='recommendations', section='recommendation-evidence'),
                        module='recommendation',
                        module_label='推荐模块',
                        page_label='项目指南推荐页',
                        availability_status='fallback',
                        availability_label='匹配不足',
                        verification_text='可回到推荐页查看空状态说明与完善建议。',
                    ),
                    cls._source_detail(
                        '画像维度',
                        '可继续核验',
                        '推荐不足时，仍可先从画像维度和成果记录反查研究方向与标签是否充分。',
                        cls._evidence_link(label='查看画像维度证据区', page='portrait', section='portrait-dimensions'),
                        module='portrait',
                        module_label='画像模块',
                        page_label='教师画像主页',
                        availability_status='limited',
                        availability_label='可回查',
                        verification_text='可从画像维度区继续核验当前方向标签与能力分布。',
                    ),
                ],
                boundary_notes=['当前推荐仍是规则增强路线，不会因为问答需要而虚构推荐命中。'],
            )

        top_guide = recommendations[0]
        supporting_records = getattr(top_guide, 'supporting_records', None) or []
        portrait_dimension_links = getattr(top_guide, 'portrait_dimension_links', None) or []
        lead_record = supporting_records[0] if supporting_records else None
        lead_dimension = portrait_dimension_links[0] if portrait_dimension_links else None

        answer = (
            f"当前成果会通过规则增强推荐服务支撑项目指南判断。"
            f"系统当前最看好的指南是“{top_guide.title}”，推荐分数为 {top_guide.recommendation_score}，"
            f"优先级为{top_guide.priority_label}。"
            f"{'系统已引用 ' + str(len(supporting_records)) + ' 条真实支撑成果。' if supporting_records else '当前推荐主要依据研究方向标签、学科方向和近期活跃度。'}"
        )

        return {
            'title': '成果如何支撑推荐',
            'answer': answer,
            'data_sources': ['项目指南推荐结果', '推荐支撑成果', '画像联动维度'],
            'source_details': [
                cls._source_detail(
                    '目标指南',
                    top_guide.title,
                    '当前问答只解释系统中已生成的真实推荐结果。',
                    cls._evidence_link(
                        label='查看该指南推荐证据',
                        page='recommendations',
                        section='recommendation-evidence',
                        guide_id=top_guide.id,
                        note='推荐页会展示分数、理由、标签与支撑成果。',
                    ),
                    module='recommendation',
                    module_label='推荐模块',
                    page_label='项目指南推荐页',
                    verification_text='可在推荐页核验该指南的分数、标签和支撑成果。',
                ),
                cls._source_detail(
                    '支撑成果',
                    lead_record['title'] if lead_record else '当前以研究方向与画像规则支撑',
                    '优先引用推荐结果中显式列出的真实支撑成果。',
                    cls._evidence_link(
                        label='查看支撑成果记录',
                        page='achievement-entry',
                        section='achievement-records',
                        record_type=lead_record['type'] if lead_record else '',
                        record_id=lead_record['id'] if lead_record else None,
                        note='当前只回跳到推荐结果已显式引用的成果。',
                    ),
                    module='achievement',
                    module_label='成果模块',
                    page_label='教师成果录入中心',
                    availability_status='limited' if not lead_record else 'ok',
                    availability_label='规则支撑' if not lead_record else '可验证',
                    verification_text='可在成果录入页核验具体成果记录，或回到推荐页查看完整支撑清单。',
                ),
                cls._source_detail(
                    '画像联动维度',
                    lead_dimension['label'] if lead_dimension else '暂无显式联动维度',
                    '推荐解释会复用推荐服务已给出的画像维度联动结果。',
                    cls._evidence_link(
                        label='查看画像联动维度',
                        page='portrait',
                        section='portrait-dimensions',
                        dimension_key=lead_dimension['key'] if lead_dimension else '',
                    ),
                    module='portrait',
                    module_label='画像模块',
                    page_label='教师画像主页',
                    availability_status='limited' if not lead_dimension else 'ok',
                    availability_label='部分联动' if not lead_dimension else '可验证',
                    verification_text='可在画像维度区核验该推荐引用的画像能力维度。',
                ),
            ],
            'related_reasons': list(getattr(top_guide, 'recommendation_reasons', [])[:4]),
            'guide_snapshot': {
                'guide_id': top_guide.id,
                'title': top_guide.title,
            },
        }

    @classmethod
    def _graph_status(cls, teacher):
        metrics = TeacherScoringEngine.collect_metrics(teacher)
        graph_status = cls._resolve_graph_status(metrics)

        if graph_status == 'no_data':
            return cls._build_teacher_fallback_payload(
                question_type='graph_status',
                teacher=teacher,
                title='当前图谱证据仍未形成',
                answer='当前尚无足够成果记录来形成可验证的学术社交拓扑图，因此问答只保留图谱边界说明。建议先补录论文或项目后，再查看图谱链路与合作网络。',
                reason='当前成果不足，暂无法形成图谱证据。',
                source_details=[
                    cls._source_detail(
                        '图谱状态',
                        '未形成',
                        '图谱证据建立在真实成果与合作关系基础上。',
                        cls._evidence_link(label='回到成果录入页', page='achievement-entry', section='achievement-records'),
                        module='graph',
                        module_label='图谱模块',
                        page_label='教师画像主页 / 图谱板块',
                        availability_status='fallback',
                        availability_label='无图谱证据',
                        verification_text='需先补录真实成果，才能形成图谱链路。',
                    ),
                    cls._source_detail(
                        '成果基础',
                        '0 项',
                        '当前无法构建合作网络和主题热点分析。',
                        cls._evidence_link(label='查看画像说明区', page='portrait', section='portrait-explanation'),
                        module='achievement',
                        module_label='成果模块',
                        page_label='教师画像主页',
                        availability_status='fallback',
                        availability_label='无数据',
                        verification_text='当前画像说明区会展示数据不足边界。',
                    ),
                ],
                boundary_notes=['图谱当前仍是轻量增强能力，不会在无数据时伪造拓扑关系。'],
            )

        collaborator_count = metrics.get('collaborator_count', 0)
        if graph_status == 'mysql_fallback':
            answer = (
                f"当前图谱说明按 MySQL 回退链路解释。系统已识别成果 {metrics['total_achievements']} 项、合作作者 {collaborator_count} 位，"
                f"仍可继续展示轻量合作网络和主题热点分析，但不会把当前能力包装成复杂图挖掘平台。"
            )
            status_label = ('fallback', 'MySQL 回退')
            note = '当前问答依据系统图谱回退口径说明，可回到画像页图谱板块核验。'
        else:
            answer = (
                f"当前图谱遵循 Neo4j 优先、MySQL 回退的系统口径。系统已识别成果 {metrics['total_achievements']} 项、合作作者 {collaborator_count} 位，"
                f"问答当前只解释轻量合作网络、主题热点和回退边界，不延伸为复杂图挖掘结论。"
            )
            status_label = ('limited', '轻量图分析')
            note = '当前问答依据系统图谱配置说明，可回到画像页图谱板块核验当前展示口径。'

        return {
            'title': '图谱链路与降级状态',
            'answer': answer,
            'data_sources': ['图谱配置口径', '成果聚合结果', '画像页图谱板块'],
            'source_details': [
                cls._source_detail(
                    '图谱链路',
                    status_label[1],
                    '系统保持 Neo4j 优先、MySQL 回退，不把图谱变成主链路强依赖。',
                    cls._evidence_link(
                        label='查看画像页图谱板块',
                        page='portrait',
                        section='portrait-graph',
                        note=note,
                    ),
                    module='graph',
                    module_label='图谱模块',
                    page_label='教师画像主页 / 图谱板块',
                    availability_status=status_label[0],
                    availability_label=status_label[1],
                    verification_text='图谱板块会展示当前轻量关系网络与口径提示。',
                ),
                cls._source_detail(
                    '成果基础',
                    f"{metrics['total_achievements']} 项 / 合作作者 {collaborator_count} 位",
                    '图谱证据仍建立在系统内真实成果和合作记录基础上。',
                    cls._evidence_link(label='回到画像成果证据区', page='portrait', section='portrait-achievements'),
                    module='achievement',
                    module_label='成果模块',
                    page_label='教师画像主页 / 代表性成果区',
                    verification_text='可从成果区反查图谱形成所依赖的真实成果基础。',
                ),
                cls._source_detail(
                    '边界说明',
                    '轻量图分析',
                    '当前问答只说明拓扑展示与回退边界，不输出复杂图挖掘判断。',
                    cls._evidence_link(label='查看画像说明区', page='portrait', section='portrait-explanation'),
                    module='portrait',
                    module_label='画像模块',
                    page_label='教师画像主页',
                    availability_status='limited',
                    availability_label='边界提示',
                    verification_text='画像说明区可继续核验当前图谱和画像的总体边界。',
                ),
            ],
        }

    @classmethod
    def _guide_reason(cls, teacher, guide_id: int):
        result = ProjectGuideRecommendationService.build_recommendations(teacher)
        guide = next((item for item in result['recommendations'] if item.id == guide_id), None)
        target_guide = ProjectGuide.objects.get(id=guide_id)

        if guide is None:
            answer = (
                f"当前系统尚未将“{target_guide.title}”识别为该教师的高匹配推荐项。"
                f"这通常意味着教师画像中的研究标签、学科方向或近期活跃度与该指南主题重合度较低。"
            )
            reasons = ['当前暂无显著规则命中，建议作为备选参考。']
            source_details = [
                cls._source_detail(
                    '指南标题',
                    target_guide.title,
                    '当前已在系统中登记，但未进入高匹配结果。',
                    cls._evidence_link(
                        label='回到推荐证据区',
                        page='recommendations',
                        section='recommendation-evidence',
                        guide_id=target_guide.id,
                        note='当前将定位到对应指南卡片与解释区。',
                    ),
                ),
                cls._source_detail(
                    '当前状态',
                    '未命中高匹配',
                    '说明规则命中不足，不代表该指南完全不可关注。',
                    cls._evidence_link(
                        label='查看推荐结果页',
                        page='recommendations',
                        section='recommendation-evidence',
                        guide_id=target_guide.id,
                    ),
                ),
            ]
        else:
            answer = (
                f"系统推荐“{guide.title}”，主要因为其主题与教师当前研究标签、学科方向和近期成果活跃度之间存在规则匹配。"
                f"当前推荐优先级为{guide.priority_label}，推荐分数为 {guide.recommendation_score}。"
                f"重点依据包括：{'；'.join(guide.recommendation_reasons[:3])}。"
            )
            reasons = guide.recommendation_reasons
            source_details = [
                cls._source_detail(
                    '推荐分数',
                    str(guide.recommendation_score),
                    '来自当前规则增强型推荐服务。',
                    cls._evidence_link(
                        label='回到该指南推荐卡片',
                        page='recommendations',
                        section='recommendation-evidence',
                        guide_id=guide.id,
                        note='当前推荐页会展示该指南的分数、理由与支撑成果。',
                    ),
                ),
                cls._source_detail(
                    '推荐优先级',
                    guide.priority_label,
                    '依据当前分数区间自动归类。',
                    cls._evidence_link(
                        label='查看画像联动维度',
                        page='portrait',
                        section='portrait-dimensions',
                        dimension_key=(guide.portrait_dimension_links[0]['key'] if guide.portrait_dimension_links else ''),
                        note='当前只定位到当前推荐已显式联动的画像维度。',
                    ),
                ),
                cls._source_detail(
                    '规则命中',
                    '、'.join(guide.match_category_tags) or '暂无',
                    '来自主题、学科、活跃度与窗口等规则。',
                    cls._evidence_link(
                        label='查看该指南支撑成果',
                        page='achievement-entry',
                        section='achievement-records',
                        record_type=(guide.supporting_records[0]['type'] if getattr(guide, 'supporting_records', None) else ''),
                        record_id=(guide.supporting_records[0]['id'] if getattr(guide, 'supporting_records', None) else None),
                        note='当前只回跳到推荐页已显式引用的真实支撑成果。',
                    ),
                ),
            ]

        return {
            'title': '项目指南推荐原因说明',
            'answer': answer,
            'data_sources': [
                '推荐规则服务',
                '教师研究方向、学科和成果活跃度',
                '项目指南主题关键词与申报条件',
            ],
            'source_details': source_details,
            'related_reasons': reasons,
            'guide_snapshot': {
                'guide_id': target_guide.id,
                'title': target_guide.title,
            },
        }

    @classmethod
    def _guide_overview(cls, teacher):
        result = ProjectGuideRecommendationService.build_recommendations(teacher)
        recommendations = result['recommendations'][:3]
        if not recommendations:
            answer = '当前系统尚未识别出明显高匹配的项目指南，建议先完善研究方向标签或补充最新成果后再查看推荐结果。'
            source_details = [
                cls._source_detail(
                    '推荐结果数',
                    '0 条',
                    '当前规则增强服务下暂无明显高匹配结果。',
                    cls._evidence_link(
                        label='查看推荐结果页',
                        page='recommendations',
                        section='recommendation-evidence',
                    ),
                ),
            ]
        else:
            top_titles = '、'.join(item.title for item in recommendations)
            top_tags = []
            for item in recommendations:
                top_tags.extend(item.recommendation_labels[:2])
            answer = (
                f"系统当前更倾向推荐的指南包括：{top_titles}。"
                f"这些推荐主要围绕{'、'.join(list(dict.fromkeys(top_tags))[:4]) or '主题匹配与方向贴合'}展开，"
                f"整体说明当前教师在相关主题、学科方向或近期活跃度上与这些指南更贴合。"
            )
            source_details = [
                cls._source_detail(
                    '推荐结果数',
                    f"{len(recommendations)} 条",
                    '取当前推荐结果中的前 3 条高优先项。',
                    cls._evidence_link(
                        label='查看推荐证据区',
                        page='recommendations',
                        section='recommendation-evidence',
                        guide_id=recommendations[0].id,
                    ),
                ),
                cls._source_detail(
                    '高频标签',
                    '、'.join(list(dict.fromkeys(top_tags))[:4]) or '暂无',
                    '来自推荐结果标签汇总。',
                    cls._evidence_link(
                        label='回到推荐说明区',
                        page='recommendations',
                        section='recommendation-evidence',
                    ),
                ),
            ]

        return {
            'title': '当前推荐概览',
            'answer': answer,
            'data_sources': [
                '项目指南推荐结果',
                '推荐标签与规则命中信息',
            ],
            'source_details': source_details,
        }

    @classmethod
    def _academy_summary(cls, request, department: str = '', year: int | None = None):
        ensure_admin_user(request.user, ACADEMY_SCOPE_MESSAGE)

        user_model = get_user_model()
        teachers = user_model.objects.filter(is_superuser=False)
        if department:
            teachers = teachers.filter(department=department)
        teacher_ids = list(teachers.values_list('id', flat=True))
        querysets = build_scope_querysets(teacher_ids, year)

        paper_total = querysets['paper'].count()
        project_total = querysets['project'].count()
        ip_total = querysets['ip'].count()
        teaching_total = querysets['teaching'].count()
        service_total = querysets['service'].count()
        achievement_total = paper_total + project_total + ip_total + teaching_total + service_total

        scope_label = department or '全校'
        time_label = f'{year} 年' if year else '当前全量时间范围'
        answer = (
            f"{scope_label}在{time_label}下共覆盖教师 {teachers.count()} 人，累计成果 {achievement_total} 项，"
            f"其中论文 {paper_total} 篇、项目 {project_total} 项、知识产权 {ip_total} 项、教学成果 {teaching_total} 项、学术服务 {service_total} 项。"
            f"该回答仅用于管理辅助说明，仍基于当前系统中的实时聚合结果。"
        )

        return {
            'title': '学院统计概览',
            'answer': answer,
            'data_sources': [
                '学院看板实时聚合数据',
                '教师、成果与合作记录',
            ],
            'source_details': [
                cls._source_detail(
                    '分析范围',
                    scope_label,
                    '来自管理员当前选择的院系范围。',
                    cls._evidence_link(
                        label='回到学院排行区',
                        page='academy-dashboard',
                        section='academy-ranking',
                        department=department,
                        year=year,
                    ),
                ),
                cls._source_detail(
                    '时间范围',
                    time_label,
                    '可选按年份缩小统计口径。',
                    cls._evidence_link(
                        label='回到学院钻取区',
                        page='academy-dashboard',
                        section='academy-drilldown',
                        department=department,
                        year=year,
                    ),
                ),
                cls._source_detail(
                    '成果总量',
                    f'{achievement_total} 项',
                    '来自学院看板实时聚合接口口径。',
                    cls._evidence_link(
                        label='查看学院看板',
                        page='academy-dashboard',
                        section='academy-ranking',
                        department=department,
                        year=year,
                        note='当前学院问答只回跳到管理员可访问的真实统计区。',
                    ),
                ),
            ],
            'academy_snapshot': {
                'department': department,
                'year': year,
                'teacher_total': teachers.count(),
                'achievement_total': achievement_total,
            },
        }

    @classmethod
    def build_failure_payload(cls, question_type: str, teacher=None, reason: str = ''):
        payload = cls._base_meta()
        payload.update(
            {
                'status': 'fallback',
                'title': '问答结果已降级为说明模式',
                'answer': '当前智能辅助结果暂时无法完整生成，系统已回退为基础说明模式。你仍可继续使用画像、成果、推荐和学院看板等主链路页面。',
                'data_sources': ['系统内既有页面与实时聚合结果'],
                'source_details': [
                    cls._source_detail(
                        '回退原因',
                        reason or '当前问答链路处理失败',
                        '不会影响主链路页面访问。',
                        module='assistant',
                        module_label='问答模块',
                        page_label='智能问答页',
                        availability_status='fallback',
                        availability_label='已降级',
                        verification_text='可回到画像、成果、推荐或看板页面继续核验。',
                    ),
                ],
                'question_type': question_type,
                'failure_notice': '问答异常已被拦截，当前仅返回安全的回退说明。',
                'source_governance': {
                    'answer_mode': '系统安全回退',
                    'scope_label': '当前仅保留系统内页面级说明，不继续生成新的问答结论。',
                    'verification_note': '请回到原始业务页面继续核验，问答回退不会影响主链路使用。',
                    'degraded_flags': ['问答主链路当前已回退为安全说明模式。'],
                    'unavailable_flags': [],
                },
            }
        )
        if teacher is not None:
            payload['teacher_snapshot'] = {
                'user_id': teacher.id,
                'teacher_name': teacher.real_name or teacher.username,
                'department': teacher.department or '',
                'title': teacher.title or '',
            }
        return payload

    @classmethod
    def build_answer(
        cls,
        request,
        teacher,
        question_type: str,
        guide_id: int | None = None,
        department: str = '',
        year: int | None = None,
    ):
        if question_type == 'portrait_summary':
            payload = cls._portrait_summary(teacher)
        elif question_type == 'portrait_dimension_reason':
            payload = cls._portrait_dimension_reason(teacher)
        elif question_type == 'portrait_data_governance':
            payload = cls._portrait_data_governance(teacher)
        elif question_type == 'achievement_summary':
            payload = cls._achievement_summary(teacher)
        elif question_type == 'achievement_portrait_link':
            payload = cls._achievement_portrait_link(teacher)
        elif question_type == 'achievement_recommendation_link':
            payload = cls._achievement_recommendation_link(teacher)
        elif question_type == 'guide_overview':
            payload = cls._guide_overview(teacher)
        elif question_type == 'graph_status':
            payload = cls._graph_status(teacher)
        elif question_type == 'academy_summary':
            payload = cls._academy_summary(request, department=department, year=year)
        else:
            payload = cls._guide_reason(teacher, guide_id or 0)

        payload.update(cls._base_meta())
        payload.setdefault('status', 'ok')
        payload['question_type'] = question_type
        if question_type != 'academy_summary':
            profile = get_teacher_profile(teacher)
            metrics = TeacherScoringEngine.collect_metrics(teacher)
            snapshot_boundary = build_snapshot_boundary(teacher)
            recommendation_status, _ = cls._resolve_recommendation_status(teacher)
            graph_status = cls._resolve_graph_status(metrics)
            missing_profile_fields = cls._resolve_profile_missing_fields(teacher, profile)
            governance = cls._build_source_governance(
                metrics=metrics,
                snapshot_boundary=snapshot_boundary,
                recommendation_status=recommendation_status,
                graph_status=graph_status,
                missing_profile_fields=missing_profile_fields,
            )
            payload.setdefault('source_governance', governance)
            extra_boundary_notes = governance['degraded_flags'][:2] + governance['unavailable_flags'][:2]
            if extra_boundary_notes:
                payload['boundary_notes'] = list(dict.fromkeys((payload.get('boundary_notes') or []) + extra_boundary_notes))
            payload['teacher_snapshot'] = {
                'user_id': teacher.id,
                'teacher_name': teacher.real_name or teacher.username,
                'department': teacher.department or '',
                'title': teacher.title or '',
            }
        else:
            payload.setdefault(
                'source_governance',
                cls._build_source_governance(
                    recommendation_status=None,
                    graph_status=None,
                    academy_mode=True,
                ),
            )
        return payload


class AssistantChatService:
    @staticmethod
    def resolve_chat_teacher(request):
        # 当前聊天助手统一按“当前登录账号”回答；管理员不再指定其他教师。
        return request.user

    @staticmethod
    def _tokenize(text: str) -> list[str]:
        if not text:
            return []
        chinese_tokens = re.findall(r'[\u4e00-\u9fff]{2,}', text)
        english_tokens = re.findall(r'[A-Za-z][A-Za-z\-]{1,}', text.lower())
        return [token.strip().lower() for token in chinese_tokens + english_tokens if token.strip()]

    @classmethod
    def _build_knowledge_chunks(cls, request, teacher) -> list[dict]:
        profile = get_teacher_profile(teacher)
        metrics = TeacherScoringEngine.collect_metrics(teacher)
        recent_records = PortraitAssistantService._collect_recent_records(teacher, limit=5)
        recommendation_result = ProjectGuideRecommendationService.build_recommendations(
            teacher,
            requested_by=request.user,
        )
        top_recommendations = (recommendation_result.get('recommendations') or [])[:3]

        chunks: list[dict] = [
            {
                'id': 'S1',
                'title': '教师画像基础信息',
                'module': 'portrait',
                'content': (
                    f"教师：{teacher.real_name or teacher.username}；院系：{teacher.department or '未填写'}；"
                    f"职称：{teacher.title or '未填写'}；学科：{profile.discipline if profile else '未填写'}；"
                    f"研究兴趣：{profile.research_interests if profile and profile.research_interests else '未填写'}。"
                ),
                'link': {
                    'label': '查看画像主页',
                    'page': 'portrait',
                    'section': 'portrait-explanation',
                    'note': '当前回答来源于系统内教师画像与资料快照。',
                },
            },
            {
                'id': 'S2',
                'title': '成果聚合统计',
                'module': 'achievement',
                'content': (
                    f"成果总数 {metrics.get('total_achievements', 0)}；论文 {metrics.get('paper_count', 0)}；"
                    f"项目 {metrics.get('project_count', 0)}；知识产权 {metrics.get('ip_count', 0)}；"
                    f"教学成果 {metrics.get('teaching_count', 0)}；学术服务 {metrics.get('service_count', 0)}。"
                ),
                'link': {
                    'label': '查看成果证据',
                    'page': 'achievement-entry',
                    'section': 'achievement-records',
                    'note': '可回跳到成果列表核验当前统计口径。',
                },
            },
            {
                'id': 'S3',
                'title': '推荐结果概览',
                'module': 'recommendation',
                'content': (
                    f"当前可用推荐 {len(recommendation_result.get('recommendations') or [])} 项；"
                    f"收藏 {len((recommendation_result.get('favorites') or {}).get('guide_ids') or [])} 项；"
                    f"推荐策略：{(recommendation_result.get('data_meta') or {}).get('current_strategy', '规则增强推荐')}。"
                ),
                'link': {
                    'label': '查看推荐结果',
                    'page': 'recommendations',
                    'section': 'recommendation-evidence',
                    'note': '可回到推荐页查看项目级证据。',
                },
            },
            {
                'id': 'S4',
                'title': '系统边界说明',
                'module': 'assistant',
                'content': (
                    '当前助手为系统内知识增强回答，不调用外部公开网络知识；'
                    '当证据不足时会明确提示信息边界，不虚构教师成果或推荐命中。'
                ),
                'link': {
                    'label': '查看助手页面',
                    'page': 'assistant',
                    'section': 'assistant-answer',
                    'note': '可在助手页面继续追问并查看来源卡片。',
                },
            },
        ]

        for index, item in enumerate(top_recommendations, start=1):
            chunks.append(
                {
                    'id': f'R{index}',
                    'title': f"推荐项目：{item.get('title', '未命名指南')}",
                    'module': 'recommendation',
                    'content': (
                        f"推荐分 {item.get('recommendation_score', 0)}；优先级 {item.get('priority_label', '未标注')}；"
                        f"摘要：{item.get('recommendation_summary', '') or item.get('summary', '') or '暂无摘要'}"
                    ),
                    'link': {
                        'label': '回到推荐详情',
                        'page': 'recommendations',
                        'section': 'recommendation-evidence',
                        'guide_id': item.get('id'),
                        'note': '可回到推荐模块核验该项目详情。',
                    },
                }
            )

        if recent_records:
            recent_titles = '；'.join(record['title'] for record in recent_records[:3])
            chunks.append(
                {
                    'id': 'A1',
                    'title': '近期成果线索',
                    'module': 'achievement',
                    'content': f"近期成果包括：{recent_titles}。",
                    'link': {
                        'label': '查看成果列表',
                        'page': 'achievement-entry',
                        'section': 'achievement-records',
                        'note': '可回到成果模块查看原始记录。',
                    },
                }
            )

        return chunks

    @classmethod
    def _retrieve_chunks(cls, question: str, chunks: list[dict], limit: int = 4) -> list[dict]:
        question_tokens = set(cls._tokenize(question))
        ranked: list[dict] = []

        for chunk in chunks:
            chunk_tokens = set(cls._tokenize(f"{chunk.get('title', '')} {chunk.get('content', '')}"))
            overlap = len(question_tokens & chunk_tokens)
            contains_bonus = 1 if question and question in f"{chunk.get('title', '')}{chunk.get('content', '')}" else 0
            score = overlap + contains_bonus
            ranked.append({**chunk, 'score': score})

        ranked.sort(key=lambda item: item['score'], reverse=True)
        positive = [item for item in ranked if item['score'] > 0]
        selected = positive[:limit] if positive else ranked[:limit]
        return selected

    @staticmethod
    def _invoke_optional_llm(question: str, context_chunks: list[dict]) -> tuple[str | None, str]:
        model_name = getattr(settings, 'ASSISTANT_CHAT_MODEL', 'qwen2.5-fast')
        ai = AcademicAI(model_name=model_name)
        if ai.llm is None:
            return None, 'rules-fallback'

        context_lines = []
        for item in context_chunks:
            context_lines.append(f"[{item['id']}] {item['title']}：{item['content']}")
        context_block = '\n'.join(context_lines)

        prompt = (
            "你是高校教师科研画像系统的AI助手。"
            "请仅基于给定证据回答，不要引入外部知识，不要编造。"
            "回答使用中文，结构清晰，必要时标注证据编号如[S1]。\n\n"
            f"用户问题：{question}\n\n"
            f"可用证据：\n{context_block}\n"
        )
        try:
            response = ai.llm.invoke(prompt)
            normalized = str(response).strip()
            return (normalized or None), model_name
        except Exception:
            return None, 'rules-fallback'

    @staticmethod
    def _build_fallback_answer(question: str, context_chunks: list[dict]) -> str:
        if not context_chunks:
            return '当前没有检索到可验证的系统内证据，建议补充教师资料或成果后再提问。'
        lines = [
            f"已基于系统内证据检索到 {len(context_chunks)} 条相关信息，先给出可核验摘要：",
        ]
        for item in context_chunks[:3]:
            lines.append(f"- [{item['id']}] {item['title']}：{item['content']}")
        lines.append(f"你的问题是“{question}”，如需更细内容可继续追问并指定关注点（如成果、推荐或画像）。")
        return '\n'.join(lines)

    @classmethod
    def build_chat_answer(cls, request, *, message: str, context_hint: str = '', limit: int = 4) -> dict:
        teacher = cls.resolve_chat_teacher(request)
        chunks = cls._build_knowledge_chunks(request, teacher)
        retrieved = cls._retrieve_chunks(message, chunks, limit=limit)

        llm_answer, model_name = cls._invoke_optional_llm(message, retrieved)
        status = 'ok' if llm_answer else 'fallback'
        answer_text = llm_answer or cls._build_fallback_answer(message, retrieved)
        base_meta = PortraitAssistantService._base_meta()

        return {
            'status': status,
            'title': 'AI 助手回答',
            'answer': answer_text,
            'assistant_mode': 'rag-chat',
            'model': model_name,
            'question': message,
            'context_hint': context_hint,
            'scope_note': base_meta['scope_note'],
            'non_coverage_note': base_meta['non_coverage_note'],
            'acceptance_scope': base_meta['acceptance_scope'],
            'boundary_notes': base_meta['boundary_notes'],
            'teacher_snapshot': {
                'user_id': teacher.id,
                'teacher_name': teacher.real_name or teacher.username,
                'department': teacher.department or '',
                'title': teacher.title or '',
            },
            'sources': [
                {
                    'id': item['id'],
                    'title': item['title'],
                    'module': item['module'],
                    'snippet': item['content'],
                    'score': item['score'],
                    'link': item.get('link'),
                }
                for item in retrieved
            ],
        }
