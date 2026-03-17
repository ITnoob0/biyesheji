import base64
import json
import os
import sys
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


BASE_DIR = Path(__file__).resolve().parents[1]
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "core.settings")

import django

django.setup()

from django.conf import settings

from achievements.models import (
    AcademicService,
    IntellectualProperty,
    Paper,
    Project,
    TeachingAchievement,
)


def build_http_endpoint() -> str:
    explicit_url = os.environ.get("NEO4J_HTTP_URL", "").strip()
    if explicit_url:
        return explicit_url
    return "http://127.0.0.1:7474/db/neo4j/tx/commit"


def run_cypher(statements):
    endpoint = build_http_endpoint()
    payload = json.dumps({"statements": statements}).encode("utf-8")
    credentials = f"{settings.NEO4J_USER}:{settings.NEO4J_PASSWORD}".encode("utf-8")
    auth_header = base64.b64encode(credentials).decode("ascii")

    request = Request(
        endpoint,
        data=payload,
        headers={
            "Content-Type": "application/json",
            "Accept": "application/json;charset=UTF-8",
            "Authorization": f"Basic {auth_header}",
        },
        method="POST",
    )

    try:
        with urlopen(request, timeout=30) as response:
            body = response.read().decode("utf-8")
    except HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="ignore")
        raise RuntimeError(f"Neo4j HTTP error {exc.code}: {detail}") from exc
    except URLError as exc:
        raise RuntimeError(f"Neo4j connection failed: {exc}") from exc

    data = json.loads(body)
    if data.get("errors"):
        raise RuntimeError(f"Neo4j query failed: {data['errors']}")
    return data


def sync_papers() -> int:
    papers = list(
        Paper.objects.select_related("teacher")
        .prefetch_related("coauthors", "paperkeyword_set__keyword")
        .order_by("id")
    )

    for paper in papers:
        statements = [
            {
                "statement": """
                MERGE (t:Teacher {user_id: $teacher_user_id})
                SET t.name = $teacher_name

                MERGE (p:Paper {paper_id: $paper_id})
                SET p.title = $title

                MERGE (t)-[:PUBLISHED]->(p)
                """,
                "parameters": {
                    "teacher_user_id": int(paper.teacher_id),
                    "teacher_name": paper.teacher.real_name or paper.teacher.username,
                    "paper_id": str(paper.id),
                    "title": paper.title,
                },
            }
        ]

        for relation in paper.paperkeyword_set.all():
            statements.append(
                {
                    "statement": """
                    MATCH (t:Teacher {user_id: $teacher_user_id}), (p:Paper {paper_id: $paper_id})
                    MERGE (k:Keyword {name: $keyword_name})
                    MERGE (p)-[:HAS_KEYWORD]->(k)
                    MERGE (t)-[:RESEARCHES]->(k)
                    """,
                    "parameters": {
                        "teacher_user_id": int(paper.teacher_id),
                        "paper_id": str(paper.id),
                        "keyword_name": relation.keyword.name,
                    },
                }
            )

        for coauthor in paper.coauthors.all():
            statements.append(
                {
                    "statement": """
                    MATCH (p:Paper {paper_id: $paper_id})
                    MERGE (c:ExternalScholar {name: $coauthor_name})
                    MERGE (c)-[:CO_AUTHORED]->(p)
                    """,
                    "parameters": {
                        "paper_id": str(paper.id),
                        "coauthor_name": coauthor.name,
                    },
                }
            )

        run_cypher(statements)

    return len(papers)


def sync_projects() -> int:
    projects = list(Project.objects.select_related("teacher").order_by("id"))
    for project in projects:
        run_cypher(
            [
                {
                    "statement": """
                    MERGE (t:Teacher {user_id: $teacher_user_id})
                    SET t.name = $teacher_name

                    MERGE (p:Project {project_id: $project_id})
                    SET p.title = $title,
                        p.level = $level,
                        p.role = $role,
                        p.status = $status

                    MERGE (t)-[:UNDERTAKES_PROJECT]->(p)
                    """,
                    "parameters": {
                        "teacher_user_id": int(project.teacher_id),
                        "teacher_name": project.teacher.real_name or project.teacher.username,
                        "project_id": str(project.id),
                        "title": project.title,
                        "level": project.level,
                        "role": project.role,
                        "status": project.status,
                    },
                }
            ]
        )
    return len(projects)


def sync_intellectual_properties() -> int:
    records = list(IntellectualProperty.objects.select_related("teacher").order_by("id"))
    for item in records:
        run_cypher(
            [
                {
                    "statement": """
                    MERGE (t:Teacher {user_id: $teacher_user_id})
                    SET t.name = $teacher_name

                    MERGE (i:IntellectualProperty {ip_id: $ip_id})
                    SET i.title = $title,
                        i.ip_type = $ip_type,
                        i.registration_number = $registration_number

                    MERGE (t)-[:OWNS_IP]->(i)
                    """,
                    "parameters": {
                        "teacher_user_id": int(item.teacher_id),
                        "teacher_name": item.teacher.real_name or item.teacher.username,
                        "ip_id": str(item.id),
                        "title": item.title,
                        "ip_type": item.ip_type,
                        "registration_number": item.registration_number,
                    },
                }
            ]
        )
    return len(records)


def sync_teaching_achievements() -> int:
    records = list(TeachingAchievement.objects.select_related("teacher").order_by("id"))
    for item in records:
        run_cypher(
            [
                {
                    "statement": """
                    MERGE (t:Teacher {user_id: $teacher_user_id})
                    SET t.name = $teacher_name

                    MERGE (ta:TeachingAchievement {teaching_id: $teaching_id})
                    SET ta.title = $title,
                        ta.achievement_type = $achievement_type,
                        ta.level = $level

                    MERGE (t)-[:HAS_TEACHING_ACHIEVEMENT]->(ta)
                    """,
                    "parameters": {
                        "teacher_user_id": int(item.teacher_id),
                        "teacher_name": item.teacher.real_name or item.teacher.username,
                        "teaching_id": str(item.id),
                        "title": item.title,
                        "achievement_type": item.achievement_type,
                        "level": item.level,
                    },
                }
            ]
        )
    return len(records)


def sync_academic_services() -> int:
    records = list(AcademicService.objects.select_related("teacher").order_by("id"))
    for item in records:
        run_cypher(
            [
                {
                    "statement": """
                    MERGE (t:Teacher {user_id: $teacher_user_id})
                    SET t.name = $teacher_name

                    MERGE (s:AcademicService {service_id: $service_id})
                    SET s.title = $title,
                        s.service_type = $service_type,
                        s.organization = $organization

                    MERGE (t)-[:PROVIDES_SERVICE]->(s)
                    """,
                    "parameters": {
                        "teacher_user_id": int(item.teacher_id),
                        "teacher_name": item.teacher.real_name or item.teacher.username,
                        "service_id": str(item.id),
                        "title": item.title,
                        "service_type": item.service_type,
                        "organization": item.organization,
                    },
                }
            ]
        )
    return len(records)


def main() -> int:
    print(f"neo4j_http_endpoint={build_http_endpoint()}")
    run_cypher([{"statement": "MATCH (n) DETACH DELETE n"}])
    print("neo4j_clear=done")

    paper_count = sync_papers()
    project_count = sync_projects()
    ip_count = sync_intellectual_properties()
    teaching_count = sync_teaching_achievements()
    service_count = sync_academic_services()

    node_counts = run_cypher(
        [{"statement": "MATCH (n) RETURN labels(n) AS labels, count(n) AS count ORDER BY count DESC"}]
    )["results"][0]["data"]
    rel_counts = run_cypher(
        [{"statement": "MATCH ()-[r]->() RETURN type(r) AS relation, count(r) AS count ORDER BY count DESC"}]
    )["results"][0]["data"]

    print(f"neo4j_synced_papers={paper_count}")
    print(f"neo4j_synced_projects={project_count}")
    print(f"neo4j_synced_ips={ip_count}")
    print(f"neo4j_synced_teaching={teaching_count}")
    print(f"neo4j_synced_services={service_count}")
    print(f"neo4j_node_counts={node_counts}")
    print(f"neo4j_relation_counts={rel_counts}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
