from __future__ import annotations

from django.contrib.auth import get_user_model
from rest_framework.exceptions import PermissionDenied

from achievements.scoring_engine import TeacherScoringEngine
from project_guides.models import ProjectGuide
from project_guides.services import ProjectGuideRecommendationService
from users.services import get_teacher_profile

from achievements.models import AcademicService, IntellectualProperty, Paper, Project, TeachingAchievement


class PortraitAssistantService:
    @staticmethod
    def resolve_target_teacher(request, user_id: int | None = None):
        target_user_id = user_id or request.user.id
        if request.user.id != target_user_id and not (request.user.is_staff or request.user.is_superuser):
            raise PermissionDenied('当前账号无权查看其他教师的问答结果。')

        return get_user_model().objects.get(id=target_user_id)

    @staticmethod
    def _base_meta():
        return {
            'scope_note': '当前为轻量智能问答演示链路，仅基于系统内真实教师资料、成果聚合、推荐结果和画像统计生成。',
            'non_coverage_note': '当前不支持复杂多轮问答、外部知识检索或开放领域问答。',
            'acceptance_scope': '本能力属于第三轮展示增强项，以单场景、可解释演示方式交付。',
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
            f"从画像维度看，当前最突出的能力是{top_dimensions[0]['name']}和{top_dimensions[1]['name']}。"
            f"{'研究兴趣主要包括' + profile.research_interests if profile and profile.research_interests else '当前研究兴趣信息仍可继续完善。'}"
        )

        return {
            'title': '教师科研画像总结',
            'answer': answer,
            'data_sources': [
                '教师基础资料',
                '实时画像评分引擎',
                '论文、项目、知识产权、教学成果、学术服务聚合统计',
            ],
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
        else:
            answer = (
                f"系统推荐“{guide.title}”，主要因为其主题与教师当前研究标签、学科方向和近期成果活跃度之间存在规则匹配。"
                f"当前推荐优先级为{guide.priority_label}，推荐分数为 {guide.recommendation_score}。"
                f"重点依据包括：{'；'.join(guide.recommendation_reasons[:3])}。"
            )
            reasons = guide.recommendation_reasons

        return {
            'title': '项目指南推荐原因说明',
            'answer': answer,
            'data_sources': [
                '推荐规则服务',
                '教师研究方向、学科和成果活跃度',
                '项目指南主题关键词与申报条件',
            ],
            'related_reasons': reasons,
            'guide_snapshot': {
                'guide_id': target_guide.id,
                'title': target_guide.title,
            },
        }

    @classmethod
    def build_answer(cls, teacher, question_type: str, guide_id: int | None = None):
        if question_type == 'portrait_summary':
            payload = cls._portrait_summary(teacher)
        elif question_type == 'achievement_summary':
            payload = cls._achievement_summary(teacher)
        else:
            payload = cls._guide_reason(teacher, guide_id or 0)

        payload.update(cls._base_meta())
        payload['teacher_snapshot'] = {
            'user_id': teacher.id,
            'teacher_name': teacher.real_name or teacher.username,
            'department': teacher.department or '',
            'title': teacher.title or '',
        }
        payload['question_type'] = question_type
        return payload
