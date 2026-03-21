#!/usr/bin/env python
from __future__ import annotations

import os
import sys
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parents[1]
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "core.settings")

import django

django.setup()

from django.core.management import call_command
from rest_framework.test import APIClient


def assert_status(results: list[tuple[str, int, int]], label: str, actual: int, expected: int) -> None:
    results.append((label, actual, expected))
    if actual != expected:
        raise AssertionError(f"{label} expected {expected}, got {actual}")


def main() -> int:
    call_command("system_preflight")
    call_command("check")
    call_command("init_demo_teachers")

    teacher_client = APIClient()
    teacher_login = teacher_client.post(
        "/api/token/",
        {"username": "100001", "password": "teacher123456"},
        format="json",
    )
    teacher_token = teacher_login.json()["access"]
    teacher_client.credentials(HTTP_AUTHORIZATION=f"Bearer {teacher_token}")

    admin_client = APIClient()
    admin_login = admin_client.post(
        "/api/token/",
        {"username": "admin", "password": "Admin123456"},
        format="json",
    )
    admin_token = admin_login.json()["access"]
    admin_client.credentials(HTTP_AUTHORIZATION=f"Bearer {admin_token}")

    results: list[tuple[str, int, int]] = []

    assert_status(results, "teacher.token", teacher_login.status_code, 200)
    assert_status(results, "teacher.me", teacher_client.get("/api/users/me/").status_code, 200)
    assert_status(results, "teacher.dashboard", teacher_client.get("/api/achievements/dashboard-stats/").status_code, 200)
    assert_status(results, "teacher.radar", teacher_client.get("/api/achievements/radar/100001/").status_code, 200)
    assert_status(results, "teacher.papers", teacher_client.get("/api/achievements/papers/").status_code, 200)
    assert_status(results, "teacher.graph", teacher_client.get("/api/graph/topology/100001/").status_code, 200)
    assert_status(
        results,
        "teacher.recommendations",
        teacher_client.get("/api/project-guides/recommendations/").status_code,
        200,
    )
    assert_status(
        results,
        "teacher.assistant",
        teacher_client.post("/api/ai-assistant/portrait-qa/", {"question_type": "portrait_summary"}, format="json").status_code,
        200,
    )
    assert_status(
        results,
        "teacher.academy_overview_forbidden",
        teacher_client.get("/api/achievements/academy-overview/").status_code,
        403,
    )

    assert_status(results, "admin.token", admin_login.status_code, 200)
    assert_status(results, "admin.me", admin_client.get("/api/users/me/").status_code, 200)
    assert_status(results, "admin.teacher_detail", admin_client.get("/api/users/teachers/100001/").status_code, 200)
    assert_status(
        results,
        "admin.dashboard_target",
        admin_client.get("/api/achievements/dashboard-stats/", {"user_id": 100001}).status_code,
        200,
    )
    assert_status(
        results,
        "admin.graph_target",
        admin_client.get("/api/graph/topology/100001/").status_code,
        200,
    )
    assert_status(
        results,
        "admin.recommendations_target",
        admin_client.get("/api/project-guides/recommendations/", {"user_id": 100001}).status_code,
        200,
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
    assert_status(
        results,
        "admin.academy_overview",
        admin_client.get("/api/achievements/academy-overview/").status_code,
        200,
    )

    print("Regression verification for developments 16-24 passed.")
    for label, actual, expected in results:
        print(f"[OK] {label}: {actual} == {expected}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
