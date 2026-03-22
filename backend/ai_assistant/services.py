from __future__ import annotations

from django.contrib.auth import get_user_model

from achievements.academy_dashboard_analysis import build_scope_querysets
from achievements.models import AcademicService, IntellectualProperty, Paper, Project, TeachingAchievement
from achievements.scoring_engine import TeacherScoringEngine
from project_guides.models import ProjectGuide
from project_guides.services import ProjectGuideRecommendationService
from users.access import ACADEMY_SCOPE_MESSAGE, ASSISTANT_SCOPE_MESSAGE, ensure_admin_user, ensure_self_or_admin_user
from users.services import get_teacher_profile


class PortraitAssistantService:
    @staticmethod
    def resolve_target_teacher(request, user_id: int | None = None):
        target_user_id = user_id or request.user.id
        teacher = get_user_model().objects.get(id=target_user_id)
        ensure_self_or_admin_user(request.user, teacher, ASSISTANT_SCOPE_MESSAGE)
        return teacher

    @staticmethod
    def _base_meta():
        return {
            'scope_note': '当前为受控的轻量智能辅助链路，仅基于系统内真实教师资料、成果聚合、推荐结果和学院统计生成，不调用外部知识库。',
            'non_coverage_note': '当前不支持开放领域问答、外部知识检索、自由多轮推理或面向全网资料的通用知识回答。',
            'acceptance_scope': '本能力属于当前阶段增强项，以模板化、可解释、可回退的问答辅助方式交付。',
            'boundary_notes': [
                '答案只使用当前系统已有资料和统计结果。',
                '当数据缺失时，系统会明确提示信息不足，而不是虚构补全。',
                '当前回答更适合做系统内说明与辅助，不等同于完整知识平台。',
            ],
        }

    @staticmethod
    def _source_detail(label: str, value: str, note: str):
        return {
            'label': label,
            'value': value,
            'note': note,
        }

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
                cls._source_detail('教师资料', teacher.real_name or teacher.username, '来自当前系统中的教师基础档案。'),
                cls._source_detail('成果总量', f"{metrics['total_achievements']} 项", '来自论文、项目、知识产权、教学成果和学术服务实时聚合。'),
                cls._source_detail('画像优势维度', '、'.join(item['name'] for item in top_dimensions), '来自当前画像评分引擎的维度结果。'),
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
                cls._source_detail(item['name'], f"评分 {item['value']} / 权重 {item['weight']}%", '来自当前画像维度计算与证据摘要。')
                for item in top_insights
            ],
            'related_reasons': [evidence for item in top_insights for evidence in item.get('evidence', [])[:2]],
        }

    @classmethod
    def _achievement_summary(cls, teacher):
        metrics = TeacherScoringEngine.collect_metrics(teacher)
        latest_paper = Paper.objects.filter(teacher=teacher).order_by('-date_acquired').first()
        latest_project = Project.objects.filter(teacher=teacher).order_by('-date_acquired').first()
        latest_ip = IntellectualProperty.objects.filter(teacher=teacher).order_by('-date_acquired').first()
        latest_teaching = TeachingAchievement.objects.filter(teacher=teacher).order_by('-date_acquired').first()
        latest_service = AcademicService.objects.filter(teacher=teacher).order_by('-date_acquired').first()

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
                cls._source_detail('论文与项目', f"{metrics['paper_count']} 篇 / {metrics['project_count']} 项", '当前成果结构的主干来源。'),
                cls._source_detail('支撑成果', f"知产 {metrics['ip_count']} / 教学 {metrics['teaching_count']} / 服务 {metrics['service_count']}", '用于补充教师成果全景。'),
                cls._source_detail('近期事项', '、'.join(latest_items[:3]) if latest_items else '暂无', '来自当前教师最近的成果记录。'),
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
                cls._source_detail('指南标题', target_guide.title, '当前已在系统中登记，但未进入高匹配结果。'),
                cls._source_detail('当前状态', '未命中高匹配', '说明规则命中不足，不代表该指南完全不可关注。'),
            ]
        else:
            answer = (
                f"系统推荐“{guide.title}”，主要因为其主题与教师当前研究标签、学科方向和近期成果活跃度之间存在规则匹配。"
                f"当前推荐优先级为{guide.priority_label}，推荐分数为 {guide.recommendation_score}。"
                f"重点依据包括：{'；'.join(guide.recommendation_reasons[:3])}。"
            )
            reasons = guide.recommendation_reasons
            source_details = [
                cls._source_detail('推荐分数', str(guide.recommendation_score), '来自当前规则增强型推荐服务。'),
                cls._source_detail('推荐优先级', guide.priority_label, '依据当前分数区间自动归类。'),
                cls._source_detail('规则命中', '、'.join(guide.match_category_tags) or '暂无', '来自主题、学科、活跃度与窗口等规则。'),
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
                cls._source_detail('推荐结果数', '0 条', '当前规则增强服务下暂无明显高匹配结果。'),
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
                cls._source_detail('推荐结果数', f"{len(recommendations)} 条", '取当前推荐结果中的前 3 条高优先项。'),
                cls._source_detail('高频标签', '、'.join(list(dict.fromkeys(top_tags))[:4]) or '暂无', '来自推荐结果标签汇总。'),
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
                cls._source_detail('分析范围', scope_label, '来自管理员当前选择的院系范围。'),
                cls._source_detail('时间范围', time_label, '可选按年份缩小统计口径。'),
                cls._source_detail('成果总量', f'{achievement_total} 项', '来自学院看板实时聚合接口口径。'),
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
                    cls._source_detail('回退原因', reason or '当前问答链路处理失败', '不会影响主链路页面访问。'),
                ],
                'question_type': question_type,
                'failure_notice': '问答异常已被拦截，当前仅返回安全的回退说明。',
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
        elif question_type == 'achievement_summary':
            payload = cls._achievement_summary(teacher)
        elif question_type == 'guide_overview':
            payload = cls._guide_overview(teacher)
        elif question_type == 'academy_summary':
            payload = cls._academy_summary(request, department=department, year=year)
        else:
            payload = cls._guide_reason(teacher, guide_id or 0)

        payload.update(cls._base_meta())
        payload.setdefault('status', 'ok')
        payload['question_type'] = question_type
        if question_type != 'academy_summary':
            payload['teacher_snapshot'] = {
                'user_id': teacher.id,
                'teacher_name': teacher.real_name or teacher.username,
                'department': teacher.department or '',
                'title': teacher.title or '',
            }
        return payload
