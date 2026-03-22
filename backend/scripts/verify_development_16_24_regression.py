#!/usr/bin/env python
from __future__ import annotations

import os
import sys
from uuid import uuid4
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parents[1]
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "core.settings")

import django

django.setup()

from django.core.management import call_command
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient


def assert_status(results: list[tuple[str, str]], label: str, actual: int, expected: int) -> None:
    results.append((label, f"{actual} == {expected}"))
    if actual != expected:
        raise AssertionError(f"{label} expected {expected}, got {actual}")


def assert_condition(results: list[tuple[str, str]], label: str, condition: bool, detail: str) -> None:
    if not condition:
        raise AssertionError(f"{label} failed: {detail}")
    results.append((label, detail))


def decode_json(response, label: str):
    try:
        return response.json()
    except Exception as exc:
        raise AssertionError(f"{label} did not return JSON: {exc}") from exc


def main() -> int:
    call_command("system_preflight")
    call_command("check")
    call_command("init_demo_teachers")

    user_model = get_user_model()
    teacher_user = user_model.objects.get(id=100001)
    admin_user = user_model.objects.get(username="admin")

    teacher_client = APIClient()
    teacher_client.force_authenticate(teacher_user)

    admin_client = APIClient()
    admin_client.force_authenticate(admin_user)

    results: list[tuple[str, str]] = []
    regression_token = uuid4().hex[:10]
    regression_doi = f"10.2026/demo-regression-main-chain-{regression_token}"
    regression_source_url = f"https://demo.local/papers/regression-main-chain-{regression_token}"

    assert_condition(
        results,
        "teacher.account_ready",
        teacher_user.is_active and teacher_user.has_usable_password(),
        "教师演示账号存在且数据库中保存了可用密码哈希",
    )

    teacher_me = teacher_client.get("/api/users/me/")
    assert_status(results, "teacher.me", teacher_me.status_code, 200)
    teacher_me_payload = decode_json(teacher_me, "teacher.me")
    assert_condition(
        results,
        "teacher.me.permission_scope",
        teacher_me_payload.get("permission_scope", {}).get("entry_role") == "teacher",
        "当前用户返回教师权限能力摘要",
    )

    teacher_profile_update = teacher_client.patch(
        "/api/users/me/",
        {
            "bio": "主链路回归脚本已更新该教师简介。",
            "contact_phone": "13900000001",
            "research_interests": "科研画像, 主链路回归",
        },
        format="json",
    )
    assert_status(results, "teacher.profile_update", teacher_profile_update.status_code, 200)
    teacher_profile_payload = decode_json(teacher_profile_update, "teacher.profile_update")
    assert_condition(
        results,
        "teacher.profile_update.fields",
        teacher_profile_payload.get("contact_phone") == "13900000001"
        and "主链路回归脚本" in teacher_profile_payload.get("bio", ""),
        "教师资料编辑后已回写关键字段",
    )

    paper_create = teacher_client.post(
        "/api/achievements/papers/",
        {
            "title": "主链路回归新增论文",
            "abstract": "这是一段足够长的摘要，用于验证教师成果新增、编辑、查询和画像联动主链路。",
            "date_acquired": "2026-03-20",
            "paper_type": "JOURNAL",
            "journal_name": "主链路验证期刊",
            "journal_level": "核心期刊",
            "published_volume": "12",
            "published_issue": "4",
            "pages": "21-29",
            "source_url": regression_source_url,
            "citation_count": 3,
            "is_first_author": True,
            "is_representative": True,
            "doi": regression_doi,
            "coauthors": ["回归合作者甲", "回归合作者乙"],
        },
        format="json",
    )
    assert_status(results, "teacher.paper_create", paper_create.status_code, 201)
    paper_payload = decode_json(paper_create, "teacher.paper_create")
    paper_id = paper_payload["id"]
    assert_condition(
        results,
        "teacher.paper_create.payload",
        paper_payload.get("teacher") == 100001 and paper_payload.get("is_representative") is True,
        "成果新增后返回教师归属与代表作标记",
    )

    paper_update = teacher_client.patch(
        f"/api/achievements/papers/{paper_id}/",
        {
            "title": "主链路回归更新论文",
            "abstract": "这是一段足够长的摘要，用于验证成果编辑主链路仍然稳定。",
            "date_acquired": "2026-03-21",
            "paper_type": "JOURNAL",
            "journal_name": "主链路验证期刊",
            "journal_level": "核心期刊",
            "published_volume": "12",
            "published_issue": "5",
            "pages": "30-38",
            "source_url": f"{regression_source_url}-updated",
            "citation_count": 5,
            "is_first_author": True,
            "is_representative": True,
            "doi": regression_doi,
            "coauthors": ["回归合作者甲"],
        },
        format="json",
    )
    assert_status(results, "teacher.paper_update", paper_update.status_code, 200)
    paper_update_payload = decode_json(paper_update, "teacher.paper_update")
    assert_condition(
        results,
        "teacher.paper_update.payload",
        paper_update_payload.get("title") == "主链路回归更新论文"
        and paper_update_payload.get("published_issue") == "5",
        "成果编辑后返回更新后的关键字段",
    )

    teacher_paper_search = teacher_client.get("/api/achievements/papers/", {"search": "主链路回归更新"})
    assert_status(results, "teacher.paper_search", teacher_paper_search.status_code, 200)
    teacher_paper_search_payload = decode_json(teacher_paper_search, "teacher.paper_search")
    assert_condition(
        results,
        "teacher.paper_search.payload",
        any(item.get("id") == paper_id for item in teacher_paper_search_payload),
        "成果查询可命中新建并更新后的论文",
    )

    teacher_paper_summary = teacher_client.get("/api/achievements/papers/summary/")
    assert_status(results, "teacher.paper_summary", teacher_paper_summary.status_code, 200)
    teacher_paper_summary_payload = decode_json(teacher_paper_summary, "teacher.paper_summary")
    assert_condition(
        results,
        "teacher.paper_summary.payload",
        teacher_paper_summary_payload.get("total_count", 0) >= 1
        and teacher_paper_summary_payload.get("representative_count", 0) >= 1,
        "成果统计摘要返回总量和代表作数量",
    )

    teacher_dashboard = teacher_client.get("/api/achievements/dashboard-stats/")
    assert_status(results, "teacher.dashboard", teacher_dashboard.status_code, 200)
    teacher_dashboard_payload = decode_json(teacher_dashboard, "teacher.dashboard")
    assert_condition(
        results,
        "teacher.dashboard.payload",
        bool(teacher_dashboard_payload.get("achievement_overview"))
        and bool(teacher_dashboard_payload.get("recent_achievements"))
        and bool(teacher_dashboard_payload.get("portrait_explanation")),
        "教师画像首页返回成果概览、近期成果和画像说明",
    )

    teacher_radar = teacher_client.get("/api/achievements/radar/100001/")
    assert_status(results, "teacher.radar", teacher_radar.status_code, 200)
    teacher_radar_payload = decode_json(teacher_radar, "teacher.radar")
    assert_condition(
        results,
        "teacher.radar.payload",
        len(teacher_radar_payload.get("radar_dimensions", [])) == 6
        and bool(teacher_radar_payload.get("dimension_insights")),
        "教师画像雷达返回 6 个维度和维度洞察",
    )

    teacher_papers = teacher_client.get("/api/achievements/papers/")
    assert_status(results, "teacher.papers", teacher_papers.status_code, 200)
    teacher_papers_payload = decode_json(teacher_papers, "teacher.papers")
    assert_condition(
        results,
        "teacher.papers.isolation",
        all(item.get("teacher") == 100001 for item in teacher_papers_payload),
        "教师成果列表仍保持当前教师隔离",
    )

    teacher_graph = teacher_client.get("/api/graph/topology/100001/")
    assert_status(results, "teacher.graph", teacher_graph.status_code, 200)
    teacher_graph_payload = decode_json(teacher_graph, "teacher.graph")
    assert_condition(
        results,
        "teacher.graph.payload",
        teacher_graph_payload.get("meta", {}).get("source") in {"neo4j", "mysql"}
        and "analysis" in teacher_graph_payload
        and "nodes" in teacher_graph_payload
        and "links" in teacher_graph_payload,
        "图谱接口返回数据来源、图结构和轻量分析摘要",
    )

    teacher_graph_other = teacher_client.get("/api/graph/topology/100002/")
    assert_status(results, "teacher.graph_other_forbidden", teacher_graph_other.status_code, 403)

    assert_status(
        results,
        "teacher.recommendations",
        teacher_client.get("/api/project-guides/recommendations/").status_code,
        200,
    )
    teacher_recommendations_payload = decode_json(
        teacher_client.get("/api/project-guides/recommendations/"),
        "teacher.recommendations.payload",
    )
    assert_condition(
        results,
        "teacher.recommendations.payload",
        bool(teacher_recommendations_payload.get("recommendations"))
        and teacher_recommendations_payload.get("teacher_snapshot", {}).get("user_id") == 100001,
        "推荐接口返回推荐结果和教师快照",
    )

    assert_status(
        results,
        "teacher.assistant",
        teacher_client.post("/api/ai-assistant/portrait-qa/", {"question_type": "portrait_summary"}, format="json").status_code,
        200,
    )
    teacher_assistant_payload = decode_json(
        teacher_client.post("/api/ai-assistant/portrait-qa/", {"question_type": "portrait_summary"}, format="json"),
        "teacher.assistant.payload",
    )
    assert_condition(
        results,
        "teacher.assistant.payload",
        teacher_assistant_payload.get("question_type") == "portrait_summary"
        and bool(teacher_assistant_payload.get("source_details")),
        "教师问答返回答案和来源说明",
    )

    assert_status(
        results,
        "teacher.academy_overview_forbidden",
        teacher_client.get("/api/achievements/academy-overview/").status_code,
        403,
    )
    guest_client = APIClient()
    guest_me = guest_client.get("/api/users/me/")
    assert_status(results, "guest.me_unauthorized", guest_me.status_code, 401)

    assert_condition(
        results,
        "admin.account_ready",
        admin_user.is_active and admin_user.has_usable_password(),
        "管理员演示账号存在且数据库中保存了可用密码哈希",
    )

    admin_me = admin_client.get("/api/users/me/")
    assert_status(results, "admin.me", admin_me.status_code, 200)
    admin_me_payload = decode_json(admin_me, "admin.me")
    assert_condition(
        results,
        "admin.me.permission_scope",
        admin_me_payload.get("permission_scope", {}).get("entry_role") == "admin",
        "当前用户返回管理员权限能力摘要",
    )

    admin_teacher_list = admin_client.get("/api/users/teachers/")
    assert_status(results, "admin.teacher_list", admin_teacher_list.status_code, 200)
    admin_teacher_list_payload = decode_json(admin_teacher_list, "admin.teacher_list")
    assert_condition(
        results,
        "admin.teacher_list.payload",
        len(admin_teacher_list_payload) >= 4 and all(not item.get("is_admin", False) for item in admin_teacher_list_payload),
        "教师管理列表返回教师账号且排除管理员账号",
    )

    admin_teacher_detail = admin_client.get("/api/users/teachers/100001/")
    assert_status(results, "admin.teacher_detail", admin_teacher_detail.status_code, 200)
    admin_teacher_detail_payload = decode_json(admin_teacher_detail, "admin.teacher_detail")
    assert_condition(
        results,
        "admin.teacher_detail.payload",
        admin_teacher_detail_payload.get("id") == 100001
        and admin_teacher_detail_payload.get("role_code") == "teacher",
        "管理员可查看指定教师详情",
    )

    admin_password_reset = admin_client.post("/api/users/teachers/100004/reset-password/")
    assert_status(results, "admin.password_reset", admin_password_reset.status_code, 200)
    admin_password_reset_payload = decode_json(admin_password_reset, "admin.password_reset")
    assert_condition(
        results,
        "admin.password_reset.payload",
        admin_password_reset_payload.get("temporary_password") == "teacher123456"
        and admin_password_reset_payload.get("password_reset_required") is True,
        "管理员重置教师密码后返回临时密码与安全状态",
    )

    assert_status(
        results,
        "admin.dashboard_target",
        admin_client.get("/api/achievements/dashboard-stats/", {"user_id": 100001}).status_code,
        200,
    )
    admin_dashboard_payload = decode_json(
        admin_client.get("/api/achievements/dashboard-stats/", {"user_id": 100001}),
        "admin.dashboard_target.payload",
    )
    assert_condition(
        results,
        "admin.dashboard_target.payload",
        admin_dashboard_payload.get("achievement_overview", {}).get("total_achievements", 0) >= 1
        and bool(admin_dashboard_payload.get("dimension_trend")),
        "管理员查看指定教师画像时返回聚合概览和趋势",
    )

    assert_status(
        results,
        "admin.graph_target",
        admin_client.get("/api/graph/topology/100001/").status_code,
        200,
    )
    admin_graph_payload = decode_json(
        admin_client.get("/api/graph/topology/100001/"),
        "admin.graph_target.payload",
    )
    assert_condition(
        results,
        "admin.graph_target.payload",
        bool(admin_graph_payload.get("meta")) and bool(admin_graph_payload.get("analysis")),
        "管理员可查看指定教师图谱与图分析结果",
    )

    assert_status(
        results,
        "admin.recommendations_target",
        admin_client.get("/api/project-guides/recommendations/", {"user_id": 100001}).status_code,
        200,
    )
    admin_recommendations_payload = decode_json(
        admin_client.get("/api/project-guides/recommendations/", {"user_id": 100001, "compare_user_id": 100004}),
        "admin.recommendations_target.payload",
    )
    assert_condition(
        results,
        "admin.recommendations_target.payload",
        bool(admin_recommendations_payload.get("recommendations"))
        and bool(admin_recommendations_payload.get("admin_analysis"))
        and bool(admin_recommendations_payload.get("comparison_summary")),
        "管理员推荐视图返回推荐结果、管理员分析和教师对比摘要",
    )

    assert_status(
        results,
        "admin.assistant_target",
        admin_client.post(
            "/api/ai-assistant/portrait-qa/",
            {"question_type": "portrait_summary", "user_id": 100001},
            format="json",
        ).status_code,
        200,
    )
    admin_assistant_payload = decode_json(
        admin_client.post(
            "/api/ai-assistant/portrait-qa/",
            {"question_type": "academy_summary", "department": "计算机学院", "year": 2025},
            format="json",
        ),
        "admin.assistant_target.payload",
    )
    assert_condition(
        results,
        "admin.assistant_target.payload",
        admin_assistant_payload.get("question_type") == "academy_summary"
        and bool(admin_assistant_payload.get("academy_snapshot")),
        "管理员问答支持学院统计说明",
    )

    assert_status(
        results,
        "admin.academy_overview",
        admin_client.get("/api/achievements/academy-overview/").status_code,
        200,
    )
    admin_academy_payload = decode_json(
        admin_client.get("/api/achievements/academy-overview/"),
        "admin.academy_overview.payload",
    )
    assert_condition(
        results,
        "admin.academy_overview.payload",
        bool(admin_academy_payload.get("statistics"))
        and bool(admin_academy_payload.get("filter_options"))
        and bool(admin_academy_payload.get("top_active_teachers")),
        "管理员学院看板返回统计、筛选项和教师排行",
    )

    print("Regression verification for developments 16-24 passed.")
    for label, detail in results:
        print(f"[OK] {label}: {detail}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
