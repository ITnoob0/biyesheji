from __future__ import annotations

import re

from django.conf import settings
from django.contrib.auth import get_user_model

from achievements.academy_dashboard_analysis import build_scope_querysets
from achievements.models import AcademicService, IntellectualProperty, Paper, Project
from achievements.portrait_analysis import build_snapshot_boundary
from achievements.scoring_engine import TeacherScoringEngine
from achievements.visibility import APPROVED_STATUS
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
    def _base_meta() -> dict:
        return {
            "scope_note": "当前为受控的轻量智能辅助链路，仅基于系统内真实教师资料、成果聚合、推荐结果和学院统计生成，不调用外部知识。",
            "non_coverage_note": "当前不支持开放领域问答、外部知识检索或面向全网资料的通用回答。",
            "acceptance_scope": "本能力属于当前阶段增强项，以模板化、可解释、可回退的问答辅助方式交付。",
            "boundary_notes": [
                "答案只使用当前系统已有资料和统计结果。",
                "当数据缺失时，系统会明确提示信息不足，而不是虚构补全。",
                "问答异常时会优先回退为安全说明模式，不影响主业务页面使用。",
            ],
        }

    @staticmethod
    def _teacher_snapshot(teacher) -> dict:
        return {
            "user_id": teacher.id,
            "teacher_name": teacher.real_name or teacher.username,
            "department": teacher.department or "",
            "title": teacher.title or "",
        }

    @staticmethod
    def _evidence_link(label: str, page: str, section: str | None = None, **kwargs) -> dict:
        payload = {"label": label, "page": page}
        if section:
            payload["section"] = section
        for key, value in kwargs.items():
            if value is not None and value != "":
                payload[key] = value
        return payload

    @staticmethod
    def _source_detail(
        label: str,
        value: str,
        note: str,
        link: dict | None = None,
        *,
        module: str = "",
        module_label: str = "",
        page_label: str = "",
        availability_status: str = "ok",
        availability_label: str = "可验证",
        verification_text: str = "",
    ) -> dict:
        payload = {
            "label": label,
            "value": value,
            "note": note,
            "module": module,
            "module_label": module_label,
            "page_label": page_label,
            "availability_status": availability_status,
            "availability_label": availability_label,
            "verification_text": verification_text,
        }
        if link:
            payload["link"] = link
        return payload

    @staticmethod
    def _collect_metrics(teacher) -> dict:
        papers = Paper.objects.filter(teacher=teacher, status=APPROVED_STATUS)
        projects = Project.objects.filter(teacher=teacher, status=APPROVED_STATUS)
        ips = IntellectualProperty.objects.filter(teacher=teacher, status=APPROVED_STATUS)
        services = AcademicService.objects.filter(teacher=teacher, status=APPROVED_STATUS)
        paper_count = papers.count()
        project_count = projects.count()
        ip_count = ips.count()
        service_count = services.count()
        return {
            "paper_count": paper_count,
            "project_count": project_count,
            "ip_count": ip_count,
            "service_count": service_count,
            "total_achievements": paper_count + project_count + ip_count + service_count,
            "representative_paper_count": papers.filter(is_representative=True).count(),
        }

    @staticmethod
    def _collect_recent_records(teacher, limit: int = 5) -> list[dict]:
        records: list[dict] = []
        for paper in Paper.objects.filter(teacher=teacher, status=APPROVED_STATUS).order_by("-date_acquired", "-created_at")[:limit]:
            records.append({"type": "paper", "title": paper.title, "date": paper.date_acquired.isoformat()})
        for project in Project.objects.filter(teacher=teacher, status=APPROVED_STATUS).order_by("-date_acquired", "-created_at")[:limit]:
            records.append({"type": "project", "title": project.title, "date": project.date_acquired.isoformat()})
        for ip in IntellectualProperty.objects.filter(teacher=teacher, status=APPROVED_STATUS).order_by("-date_acquired", "-created_at")[:limit]:
            records.append({"type": "ip", "title": ip.title, "date": ip.date_acquired.isoformat()})
        for service in AcademicService.objects.filter(teacher=teacher, status=APPROVED_STATUS).order_by("-date_acquired", "-created_at")[:limit]:
            records.append({"type": "service", "title": service.title, "date": service.date_acquired.isoformat()})
        records.sort(key=lambda item: item["date"], reverse=True)
        return records[:limit]

    @staticmethod
    def _resolve_profile_missing_fields(teacher, profile) -> list[str]:
        fields = []
        if not (teacher.department or (profile and profile.department)):
            fields.append("院系")
        if not (teacher.title or (profile and profile.title)):
            fields.append("职称")
        if not (profile and profile.discipline):
            fields.append("学科")
        if not (profile and profile.research_interests):
            fields.append("研究兴趣")
        if not teacher.research_direction:
            fields.append("研究方向")
        if not teacher.bio:
            fields.append("个人简介")
        return fields

    @staticmethod
    def _resolve_graph_status(metrics: dict) -> str:
        if metrics.get("total_achievements", 0) <= 0:
            return "no_data"
        if not getattr(settings, "ENABLE_NEO4J", False):
            return "mysql_fallback"
        return "neo4j_preferred"

    @staticmethod
    def _resolve_recommendation_status(teacher) -> tuple[str, dict | None]:
        open_total = ProjectGuide.objects.filter(status__in=ProjectGuide.ACTIVE_PUSH_STATUSES).count()
        if open_total <= 0:
            return "no_open_guides", None
        result = ProjectGuideRecommendationService.build_recommendations(teacher)
        if not (result.get("recommendations") or []):
            return "no_match", result
        return "available", result

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
        extra_degraded_flags: list[str] | None = None,
        extra_unavailable_flags: list[str] | None = None,
    ) -> dict:
        degraded_flags = list(extra_degraded_flags or [])
        unavailable_flags = list(extra_unavailable_flags or [])

        if snapshot_boundary and snapshot_boundary.get("persistence_status") == "not_persisted":
            degraded_flags.append("教师画像历史快照尚未持久化，当前说明基于运行时分析结果。")
        if recommendation_status == "no_open_guides":
            degraded_flags.append("当前没有开放中的项目指南，推荐链路只保留边界说明。")
        elif recommendation_status == "no_match":
            degraded_flags.append("当前没有明显高匹配指南，推荐链路会回退为规则说明。")
        if graph_status == "mysql_fallback":
            degraded_flags.append("图谱当前按 MySQL 回退链路解释，复杂图计算不在当前问答范围内。")
        elif graph_status == "neo4j_preferred":
            degraded_flags.append("图谱遵循 Neo4j 优先、MySQL 回退的混合链路。")
        elif graph_status == "no_data":
            unavailable_flags.append("当前成果数据不足，无法形成可验证的图谱证据。")

        if metrics and metrics.get("total_achievements", 0) <= 0:
            unavailable_flags.append("当前尚无成果入库，部分画像和推荐说明只能返回边界提示。")
        elif metrics and metrics.get("total_achievements", 0) < 2:
            degraded_flags.append("当前成果样本较少，部分趋势与联动解释仅供辅助参考。")

        if missing_profile_fields:
            degraded_flags.append(f"教师基础档案仍缺少：{'、'.join(missing_profile_fields[:4])}。")

        return {
            "answer_mode": "系统内真实数据模板化问答",
            "scope_label": "仅使用系统内真实资料、成果、推荐结果、图谱链路说明和学院统计。",
            "verification_note": "请回到对应业务页面继续核验。" if not academy_mode else "请回到学院看板中的真实统计区继续核验。",
            "degraded_flags": degraded_flags,
            "unavailable_flags": unavailable_flags,
        }

    @classmethod
    def _wrap_response(cls, *, question_type: str, teacher=None, academy_snapshot: dict | None = None, **payload) -> dict:
        base = cls._base_meta()
        response = {
            "status": payload.pop("status", "ok"),
            "question_type": question_type,
            **base,
            **payload,
        }
        if teacher is not None:
            response["teacher_snapshot"] = cls._teacher_snapshot(teacher)
        if academy_snapshot is not None:
            response["academy_snapshot"] = academy_snapshot
        return response

    @classmethod
    def build_failure_payload(
        cls,
        question_type: str,
        *,
        teacher=None,
        reason: str = "",
        unavailable_flags: list[str] | None = None,
        degraded_flags: list[str] | None = None,
    ) -> dict:
        metrics = cls._collect_metrics(teacher) if teacher is not None else None
        profile = get_teacher_profile(teacher) if teacher is not None else None
        missing_fields = cls._resolve_profile_missing_fields(teacher, profile) if teacher is not None else []
        source_governance = cls._build_source_governance(
            metrics=metrics,
            snapshot_boundary=None,
            recommendation_status=None,
            graph_status=None,
            missing_profile_fields=missing_fields,
            extra_degraded_flags=degraded_flags,
            extra_unavailable_flags=unavailable_flags,
        )
        return cls._wrap_response(
            status="fallback",
            question_type=question_type,
            teacher=teacher,
            title="问答结果已降级为说明模式",
            answer="当前智能辅助结果暂时无法完整生成，系统已回退为基础说明模式。你仍可继续使用画像、成果、推荐和学院看板等页面。",
            data_sources=["系统内既有页面与实时聚合结果"],
            source_details=[
                cls._source_detail(
                    "回退原因",
                    reason or "当前问答链路处理失败",
                    "不会影响主业务页面访问。",
                    cls._evidence_link("查看助手页面", "assistant", section="assistant-answer", note="当前为安全回退说明。"),
                    module="assistant",
                    module_label="问答模块",
                    page_label="智能问答页",
                    availability_status="fallback",
                    availability_label="已降级",
                    verification_text="可回到画像、成果、推荐或看板页面继续核验。",
                )
            ],
            failure_notice="问答异常已被拦截，当前仅返回安全的回退说明。",
            related_reasons=[reason] if reason else [],
            source_governance=source_governance,
        )

    @classmethod
    def _build_portrait_summary(cls, teacher, metrics: dict, radar: dict, profile) -> dict:
        dims = sorted(radar.get("radar_dimensions") or [], key=lambda item: item.get("value", 0), reverse=True)
        top_dims = dims[:2] or [{"name": "学术产出"}, {"name": "学术活跃"}]
        answer = (
            f"{teacher.real_name or teacher.username} 当前来自 {teacher.department or '未填写院系'}，"
            f"职称为 {teacher.title or '未填写职称'}。系统已汇总其成果 {metrics['total_achievements']} 项，"
            f"其中论文 {metrics['paper_count']} 篇、项目 {metrics['project_count']} 项、知识产权 {metrics['ip_count']} 项、学术服务 {metrics['service_count']} 项。"
            f"从画像维度看，当前更突出的能力是 {top_dims[0]['name']} 和 {top_dims[1]['name']}。"
            f"{('研究兴趣主要包括 ' + profile.research_interests) if profile and profile.research_interests else '当前研究兴趣信息仍可继续完善。'}"
        )
        return {
            "title": "教师科研画像总结",
            "answer": answer,
            "data_sources": ["教师基础资料", "实时画像评分引擎", "多成果聚合统计"],
            "source_details": [
                cls._source_detail(
                    "教师资料",
                    teacher.real_name or teacher.username,
                    "来自当前系统中的教师基础档案。",
                    cls._evidence_link("回到画像说明区", "portrait", section="portrait-explanation", note="当前摘要以实时聚合画像为准。"),
                    module="portrait",
                    module_label="画像模块",
                    page_label="教师画像主页",
                    verification_text="可在画像说明区核验当前教师资料与画像口径。",
                ),
                cls._source_detail(
                    "成果总量",
                    f"{metrics['total_achievements']} 项",
                    "来自论文、项目、知识产权和学术服务实时聚合。",
                    cls._evidence_link("查看支撑成果区", "portrait", section="portrait-achievements", note="当前仅回跳到权限范围内的真实成果证据区。"),
                    module="achievement",
                    module_label="成果模块",
                    page_label="教师画像主页 / 代表性成果区",
                    verification_text="可回到画像页代表性成果区继续核验累计成果来源。",
                ),
            ],
            "related_reasons": [f"当前总分 {radar.get('total_score', 0)}", f"代表作 {metrics['representative_paper_count']} 篇"],
        }

    @classmethod
    def _build_portrait_dimension_reason(cls, teacher, radar: dict) -> dict:
        dims = sorted(radar.get("radar_dimensions") or [], key=lambda item: item.get("value", 0), reverse=True)
        top_dims = dims[:2]
        reasons = [item.get("formula_note") or f"{item.get('name')} 当前得分 {item.get('value', 0)}" for item in top_dims]
        answer = "当前画像并不是凭空生成，而是依据既有成果与教师资料做维度聚合。" + "；".join(reasons)
        return {
            "title": "教师画像如何形成",
            "answer": answer,
            "data_sources": ["画像维度评分结果", "画像维度证据摘要"],
            "source_details": [
                cls._source_detail(
                    top_dims[0].get("name", "画像维度") if top_dims else "画像维度",
                    f"评分 {top_dims[0].get('value', 0) if top_dims else 0}",
                    "来自当前画像维度计算与证据摘要。",
                    cls._evidence_link(
                        "回到该维度证据区",
                        "portrait",
                        section="portrait-dimensions",
                        dimension_key=top_dims[0].get("key") if top_dims else None,
                        note="当前维度说明仍以实时评分与证据标签为准。",
                    ),
                    module="portrait",
                    module_label="画像模块",
                    page_label="教师画像主页",
                    verification_text="可在画像维度证据区核验维度得分和支撑说明。",
                )
            ],
            "related_reasons": reasons or ["当前暂无可展示的维度证据。"],
        }

    @classmethod
    def _build_portrait_data_governance(cls, teacher, metrics: dict, profile, snapshot_boundary: dict | None, recommendation_status: str, graph_status: str) -> dict:
        missing_fields = cls._resolve_profile_missing_fields(teacher, profile)
        governance = cls._build_source_governance(
            metrics=metrics,
            snapshot_boundary=snapshot_boundary,
            recommendation_status=recommendation_status,
            graph_status=graph_status,
            missing_profile_fields=missing_fields,
        )
        return {
            "title": "画像数据口径与治理说明",
            "answer": "当前画像数据来自系统内教师资料、成果聚合、画像评分与推荐结果；若资料缺失或样本偏少，系统会明确提示边界。",
            "data_sources": ["教师档案", "成果聚合", "画像评分", "推荐结果"],
            "source_details": [
                cls._source_detail(
                    "画像主链路",
                    "教师资料 + 成果聚合 + 评分引擎",
                    "当前画像说明仅基于系统内真实数据。",
                    cls._evidence_link("查看画像说明", "portrait", section="portrait-explanation", note="可回到画像主页核验口径。"),
                    module="portrait",
                    module_label="画像模块",
                    page_label="教师画像主页",
                    verification_text="可在画像说明区核验当前画像来源和边界。",
                )
            ],
            "related_reasons": [f"缺失字段：{'、'.join(missing_fields)}" if missing_fields else "教师基础档案完整度良好。"],
            "source_governance": governance,
        }

    @classmethod
    def _build_achievement_summary(cls, teacher, metrics: dict, recent_records: list[dict]) -> dict:
        record_text = "；".join(item["title"] for item in recent_records[:3]) if recent_records else "暂无近期成果记录。"
        return {
            "title": "成果结构概览",
            "answer": (
                f"当前累计成果 {metrics['total_achievements']} 项，其中论文 {metrics['paper_count']} 篇、项目 {metrics['project_count']} 项、"
                f"知识产权 {metrics['ip_count']} 项、学术服务 {metrics['service_count']} 项。近期成果线索包括：{record_text}"
            ),
            "data_sources": ["成果聚合统计", "近期成果记录"],
            "source_details": [
                cls._source_detail(
                    "成果统计",
                    f"总成果 {metrics['total_achievements']} 项",
                    "来自当前账号权限范围内的真实成果记录。",
                    cls._evidence_link("查看成果列表", "achievement-entry", section="achievement-records", note="可回到成果模块核验原始记录。"),
                    module="achievement",
                    module_label="成果模块",
                    page_label="成果录入页",
                    verification_text="可在成果列表中核验每一条原始记录。",
                )
            ],
            "related_reasons": [record_text],
        }

    @classmethod
    def _guide_item_id(cls, item) -> int | None:
        if isinstance(item, dict):
            return item.get("id")
        return getattr(item, "id", None)

    @classmethod
    def _guide_item_reasons(cls, item) -> list[str]:
        if isinstance(item, dict):
            return list(item.get("reason_lines") or item.get("match_reasons") or [])
        return []

    @classmethod
    def _select_guide(cls, teacher, recommendation_result: dict | None, guide_id: int | None = None):
        if guide_id:
            return ProjectGuide.objects.filter(id=guide_id).first()
        recommendations = (recommendation_result or {}).get("recommendations") or []
        if recommendations:
            first_id = cls._guide_item_id(recommendations[0])
            if first_id:
                guide = ProjectGuide.objects.filter(id=first_id).first()
                if guide is not None:
                    return guide
        return ProjectGuide.objects.filter(status__in=ProjectGuide.ACTIVE_PUSH_STATUSES).order_by("-updated_at", "-created_at").first()

    @classmethod
    def _build_guide_reason(cls, teacher, guide, recommendation_result: dict | None) -> dict:
        reasons = []
        for item in (recommendation_result or {}).get("recommendations") or []:
            if cls._guide_item_id(item) == guide.id:
                reasons = cls._guide_item_reasons(item)
                break
        if not reasons:
            reasons = [
                f"指南主题与教师研究方向存在匹配：{'、'.join((guide.target_keywords or [])[:3]) or '待补充'}",
                f"指南面向学科：{'、'.join((guide.target_disciplines or [])[:3]) or '待补充'}",
            ]
        return {
            "title": "推荐理由说明",
            "answer": f"当前重点推荐《{guide.title}》。主要原因是：" + "；".join(reasons[:3]),
            "data_sources": ["项目指南", "推荐规则结果"],
            "guide_snapshot": {"guide_id": guide.id, "title": guide.title},
            "source_details": [
                cls._source_detail(
                    "推荐项目",
                    guide.title,
                    "来自系统内项目指南与推荐链路。",
                    cls._evidence_link("回到推荐详情", "recommendations", section="recommendation-evidence", guide_id=guide.id, note="可回到推荐模块核验该项目详情。"),
                    module="recommendation",
                    module_label="推荐模块",
                    page_label="项目推荐页",
                    verification_text="可回到推荐页查看项目级证据。",
                )
            ],
            "related_reasons": reasons[:4],
        }

    @classmethod
    def _build_guide_overview(cls, teacher, recommendation_result: dict | None) -> dict:
        recommendations = (recommendation_result or {}).get("recommendations") or []
        favorites = ((recommendation_result or {}).get("favorites") or {}).get("guide_ids") or []
        data_meta = (recommendation_result or {}).get("data_meta") or {}
        return {
            "title": "推荐结果概览",
            "answer": (
                f"当前可用推荐 {len(recommendations)} 项，收藏 {len(favorites)} 项。"
                f"当前推荐策略为 {data_meta.get('current_strategy', '规则增强推荐')}。"
            ),
            "data_sources": ["推荐结果", "收藏记录", "推荐策略配置"],
            "source_details": [
                cls._source_detail(
                    "推荐统计",
                    f"推荐 {len(recommendations)} 项 / 收藏 {len(favorites)} 项",
                    "来自当前账号权限范围内的推荐结果。",
                    cls._evidence_link("查看推荐结果", "recommendations", section="recommendation-evidence", note="可回到推荐页查看项目级证据。"),
                    module="recommendation",
                    module_label="推荐模块",
                    page_label="项目推荐页",
                    verification_text="可回到推荐页继续核验推荐记录。",
                )
            ],
            "related_reasons": [data_meta.get("current_strategy", "规则增强推荐")],
        }

    @classmethod
    def _build_achievement_recommendation_link(cls, teacher, metrics: dict, recommendation_result: dict | None) -> dict:
        guide = cls._select_guide(teacher, recommendation_result)
        if guide is None:
            return cls.build_failure_payload(
                "achievement_recommendation_link",
                teacher=teacher,
                reason="当前没有可用的项目指南或推荐结果。",
                unavailable_flags=["当前暂无可解释的推荐链路。"],
            )
        reasons = [
            f"论文 {metrics['paper_count']} 篇可作为当前申报基础。",
            f"项目 {metrics['project_count']} 项与指南方向形成支撑。",
            f"代表作 {metrics['representative_paper_count']} 篇可增强成果展示。",
        ]
        return {
            "title": "成果与推荐的联动说明",
            "answer": f"当前成果基础与《{guide.title}》存在联动。" + "；".join(reasons),
            "data_sources": ["成果聚合", "推荐结果"],
            "guide_snapshot": {"guide_id": guide.id, "title": guide.title},
            "source_details": [
                cls._source_detail(
                    "联动指南",
                    guide.title,
                    "来自当前推荐结果与成果基础联动分析。",
                    cls._evidence_link("回到推荐详情", "recommendations", section="recommendation-evidence", guide_id=guide.id, note="可回到推荐模块核验该项目详情。"),
                    module="recommendation",
                    module_label="推荐模块",
                    page_label="项目推荐页",
                    verification_text="可回到推荐页查看项目级证据。",
                )
            ],
            "related_reasons": reasons,
        }

    @classmethod
    def _build_achievement_portrait_link(cls, teacher, metrics: dict, radar: dict) -> dict | None:
        if metrics["total_achievements"] <= 0:
            return None
        top_dim = sorted(radar.get("radar_dimensions") or [], key=lambda item: item.get("value", 0), reverse=True)
        top_dim_name = top_dim[0].get("name", "画像维度") if top_dim else "画像维度"
        reasons = [
            f"论文 {metrics['paper_count']} 篇直接支撑画像中的学术产出。",
            f"项目 {metrics['project_count']} 项与知识产权 {metrics['ip_count']} 项共同支撑综合能力判断。",
            f"当前最突出维度为 {top_dim_name}。",
        ]
        return {
            "title": "成果与画像的联动说明",
            "answer": "当前画像并非独立生成，而是由成果结构、活跃度和基础资料共同驱动。" + "；".join(reasons),
            "data_sources": ["成果聚合统计", "画像评分结果"],
            "source_details": [
                cls._source_detail(
                    "画像联动维度",
                    top_dim_name,
                    "来自当前画像评分与成果聚合的联动解释。",
                    cls._evidence_link("回到画像维度证据区", "portrait", section="portrait-dimensions", dimension_key=top_dim[0].get("key") if top_dim else None, note="可回到画像页核验维度证据。"),
                    module="portrait",
                    module_label="画像模块",
                    page_label="教师画像主页",
                    verification_text="可在画像维度证据区核验联动来源。",
                )
            ],
            "related_reasons": reasons,
        }

    @classmethod
    def _build_graph_status_answer(cls, teacher, metrics: dict, graph_status: str) -> dict:
        if graph_status == "neo4j_preferred":
            answer = "当前图谱优先走 Neo4j，同时保留 MySQL 回退链路。"
        elif graph_status == "mysql_fallback":
            answer = "当前图谱已回退为 MySQL 关系链路，仍可用于教师、成果和合作关系的轻量解释。"
        else:
            answer = "当前成果样本不足，暂时无法形成稳定图谱。"
        governance = cls._build_source_governance(metrics=metrics, graph_status=graph_status)
        return {
            "title": "图谱链路状态说明",
            "answer": answer,
            "data_sources": ["学术图谱链路", "成果聚合统计"],
            "source_details": [
                cls._source_detail(
                    "图谱状态",
                    graph_status,
                    "来自当前图谱配置与成果样本判断。",
                    cls._evidence_link("查看图谱页面", "portrait", section="portrait-graph", note="可回到图谱页面查看真实节点与关系。"),
                    module="graph",
                    module_label="图谱模块",
                    page_label="教师画像主页 / 学术图谱",
                    verification_text="可在图谱页面核验当前展示与回退状态。",
                )
            ],
            "related_reasons": governance["degraded_flags"] or governance["unavailable_flags"],
            "source_governance": governance,
        }

    @classmethod
    def _build_academy_summary(cls, request, department: str = "", year: int | None = None) -> dict:
        ensure_admin_user(request.user, ACADEMY_SCOPE_MESSAGE)
        user_model = get_user_model()
        teachers = user_model.objects.filter(is_superuser=False)
        if getattr(request.user, "is_staff", False) and not getattr(request.user, "is_superuser", False):
            teachers = teachers.filter(is_staff=False, department=request.user.department)
        if department:
            teachers = teachers.filter(department=department)
        teacher_ids = list(teachers.values_list("id", flat=True))
        querysets = build_scope_querysets(teacher_ids, year, "all")
        paper_total = querysets["paper"].count()
        project_total = querysets["project"].count()
        ip_total = querysets["ip"].count()
        service_total = querysets["service"].count()
        achievement_total = paper_total + project_total + ip_total + service_total
        scope_label = department or "全校"
        time_label = f"{year} 年" if year else "当前全量时间范围"
        academy_snapshot = {
            "department": department,
            "year": year,
            "teacher_total": teachers.count(),
            "achievement_total": achievement_total,
        }
        return cls._wrap_response(
            question_type="academy_summary",
            academy_snapshot=academy_snapshot,
            title="学院统计概览",
            answer=(
                f"{scope_label}在{time_label}下共覆盖教师 {teachers.count()} 人，累计成果 {achievement_total} 项，"
                f"其中论文 {paper_total} 篇、项目 {project_total} 项、知识产权 {ip_total} 项、学术服务 {service_total} 项。"
                "该回答仅用于管理辅助说明，仍基于当前系统中的实时聚合结果。"
            ),
            data_sources=["学院看板实时聚合数据", "教师、成果与合作记录"],
            source_details=[
                cls._source_detail(
                    "分析范围",
                    scope_label,
                    "来自管理员当前选择的院系范围。",
                    cls._evidence_link("回到学院看板", "academy-dashboard", section="academy-ranking", department=department, year=year, note="当前学院问答只回跳到管理员可访问的真实统计区。"),
                    module="academy",
                    module_label="学院看板",
                    page_label="学院管理看板",
                    verification_text="可在学院看板中继续核验统计口径和明细。",
                )
            ],
            related_reasons=[f"时间范围：{time_label}", f"教师数：{teachers.count()}"],
            source_governance=cls._build_source_governance(academy_mode=True),
        )

    @classmethod
    def build_answer(
        cls,
        request,
        teacher,
        question_type: str,
        guide_id: int | None = None,
        department: str = "",
        year: int | None = None,
    ) -> dict:
        if question_type == "academy_summary":
            return cls._build_academy_summary(request, department=department, year=year)

        metrics = cls._collect_metrics(teacher)
        radar = TeacherScoringEngine.get_comprehensive_radar_data(teacher)
        profile = get_teacher_profile(teacher)
        recent_records = cls._collect_recent_records(teacher)
        snapshot_boundary = build_snapshot_boundary(teacher)
        recommendation_status, recommendation_result = cls._resolve_recommendation_status(teacher)
        graph_status = cls._resolve_graph_status(metrics)

        if question_type == "portrait_summary":
            payload = cls._build_portrait_summary(teacher, metrics, radar, profile)
        elif question_type == "portrait_dimension_reason":
            payload = cls._build_portrait_dimension_reason(teacher, radar)
        elif question_type == "portrait_data_governance":
            payload = cls._build_portrait_data_governance(
                teacher,
                metrics,
                profile,
                snapshot_boundary,
                recommendation_status,
                graph_status,
            )
        elif question_type == "achievement_summary":
            payload = cls._build_achievement_summary(teacher, metrics, recent_records)
        elif question_type == "achievement_portrait_link":
            payload = cls._build_achievement_portrait_link(teacher, metrics, radar)
            if payload is None:
                return cls.build_failure_payload(
                    question_type,
                    teacher=teacher,
                    reason="当前教师暂无可用于联动分析的成果数据。",
                    unavailable_flags=["当前尚无成果入库，无法说明成果与画像联动关系。"],
                )
        elif question_type == "achievement_recommendation_link":
            payload = cls._build_achievement_recommendation_link(teacher, metrics, recommendation_result)
            if payload.get("status") == "fallback":
                return payload
        elif question_type == "guide_reason":
            guide = cls._select_guide(teacher, recommendation_result, guide_id=guide_id)
            if guide is None:
                return cls.build_failure_payload(
                    question_type,
                    teacher=teacher,
                    reason="未找到指定的项目指南。",
                    unavailable_flags=["当前无法说明推荐理由。"],
                )
            payload = cls._build_guide_reason(teacher, guide, recommendation_result)
        elif question_type == "guide_overview":
            payload = cls._build_guide_overview(teacher, recommendation_result)
        elif question_type == "graph_status":
            payload = cls._build_graph_status_answer(teacher, metrics, graph_status)
        else:
            return cls.build_failure_payload(question_type, teacher=teacher, reason=f"暂未支持的问题类型：{question_type}")

        if "source_governance" not in payload:
            payload["source_governance"] = cls._build_source_governance(
                metrics=metrics,
                snapshot_boundary=snapshot_boundary,
                recommendation_status=recommendation_status,
                graph_status=graph_status,
                missing_profile_fields=cls._resolve_profile_missing_fields(teacher, profile),
            )
        return cls._wrap_response(question_type=question_type, teacher=teacher, **payload)


class AssistantChatService:
    @staticmethod
    def resolve_chat_teacher(request):
        return request.user

    @staticmethod
    def _tokenize(text: str) -> list[str]:
        chinese_tokens = re.findall(r"[\u4e00-\u9fff]{2,}", text or "")
        english_tokens = re.findall(r"[A-Za-z][A-Za-z\\-]{1,}", (text or "").lower())
        return [token.strip().lower() for token in chinese_tokens + english_tokens if token.strip()]

    @classmethod
    def _collect_sources(cls, teacher, context_hint: str = "") -> list[dict]:
        metrics = PortraitAssistantService._collect_metrics(teacher)
        profile = get_teacher_profile(teacher)
        recommendation_status, recommendation_result = PortraitAssistantService._resolve_recommendation_status(teacher)
        recent_records = PortraitAssistantService._collect_recent_records(teacher, limit=5)
        recommendations = (recommendation_result or {}).get("recommendations") or []

        sources = [
            {
                "id": "S1",
                "title": "教师画像基础信息",
                "module": "portrait",
                "snippet": (
                    f"教师：{teacher.real_name or teacher.username}；院系：{teacher.department or '未填写'}；"
                    f"职称：{teacher.title or '未填写'}；学科：{profile.discipline if profile else '未填写'}；"
                    f"研究兴趣：{profile.research_interests if profile and profile.research_interests else '未填写'}。"
                ),
                "link": PortraitAssistantService._evidence_link("查看画像主页", "portrait", section="portrait-explanation", note="当前回答来源于系统内教师画像与资料快照。"),
            },
            {
                "id": "S2",
                "title": "成果聚合统计",
                "module": "achievement",
                "snippet": (
                    f"成果总数 {metrics.get('total_achievements', 0)}；论文 {metrics.get('paper_count', 0)}；"
                    f"项目 {metrics.get('project_count', 0)}；知识产权 {metrics.get('ip_count', 0)}；学术服务 {metrics.get('service_count', 0)}。"
                ),
                "link": PortraitAssistantService._evidence_link("查看成果证据", "achievement-entry", section="achievement-records", note="可回跳到成果列表核验当前统计口径。"),
            },
            {
                "id": "S3",
                "title": "推荐结果概览",
                "module": "recommendation",
                "snippet": (
                    f"当前可用推荐 {len(recommendations)} 项；推荐状态 {recommendation_status}；"
                    f"推荐策略：{((recommendation_result or {}).get('data_meta') or {}).get('current_strategy', '规则增强推荐')}。"
                ),
                "link": PortraitAssistantService._evidence_link("查看推荐结果", "recommendations", section="recommendation-evidence", note="可回到推荐页查看项目级证据。"),
            },
        ]

        if recent_records:
            recent_titles = "；".join(item["title"] for item in recent_records[:3])
            sources.append(
                {
                    "id": "S4",
                    "title": "近期成果线索",
                    "module": "achievement",
                    "snippet": f"近期成果包括：{recent_titles}。",
                    "link": PortraitAssistantService._evidence_link("查看成果列表", "achievement-entry", section="achievement-records", note="可回到成果模块查看原始记录。"),
                }
            )

        if context_hint:
            sources.append(
                {
                    "id": "S5",
                    "title": "当前提问上下文",
                    "module": "assistant",
                    "snippet": f"当前对话来自上下文入口：{context_hint}。",
                    "link": PortraitAssistantService._evidence_link("查看助手页面", "assistant", section="assistant-answer", note="当前问题由跨模块联动带入。"),
                }
            )

        return sources

    @classmethod
    def _rank_sources(cls, question: str, sources: list[dict], limit: int) -> list[dict]:
        question_tokens = set(cls._tokenize(question))
        ranked = []
        for item in sources:
            snippet_tokens = set(cls._tokenize(f"{item['title']} {item['snippet']}"))
            score = len(question_tokens & snippet_tokens)
            ranked.append({**item, "score": score})
        ranked.sort(key=lambda item: (item["score"], item["id"]), reverse=True)
        top = [item for item in ranked if item["score"] > 0][:limit]
        return top or ranked[:limit]

    @staticmethod
    def _build_answer(question: str, sources: list[dict]) -> str:
        if not sources:
            return "当前没有检索到可验证的系统内证据，建议补充教师资料或成果后再提问。"
        lines = [f"已基于系统内证据检索到 {len(sources)} 条相关信息，先给出可核验摘要："]
        for item in sources[:3]:
            lines.append(f"- [{item['id']}] {item['title']}：{item['snippet']}")
        lines.append(f"围绕你的问题“{question}”，建议优先回到上述证据页面继续核验与细化。")
        return "\n".join(lines)

    @classmethod
    def build_chat_answer(cls, request, *, message: str, context_hint: str = "", limit: int = 4) -> dict:
        teacher = cls.resolve_chat_teacher(request)
        sources = cls._rank_sources(message, cls._collect_sources(teacher, context_hint=context_hint), limit)
        answer_text = cls._build_answer(message, sources)
        meta = PortraitAssistantService._base_meta()
        status = "ok" if sources else "fallback"
        return {
            "status": status,
            "title": "AI 助手回答",
            "answer": answer_text,
            "assistant_mode": "rag-chat",
            "model": "rules-fallback",
            "question": message,
            "context_hint": context_hint,
            "scope_note": meta["scope_note"],
            "non_coverage_note": meta["non_coverage_note"],
            "acceptance_scope": meta["acceptance_scope"],
            "boundary_notes": meta["boundary_notes"],
            "teacher_snapshot": PortraitAssistantService._teacher_snapshot(teacher),
            "sources": sources,
        }
