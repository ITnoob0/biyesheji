"""
同步 MySQL 数据到 Neo4j 图数据库
用法：python manage.py sync_neo4j
"""
from django.core.management.base import BaseCommand
from django.conf import settings
from achievements.models import TeacherProfile, Paper, CoAuthor, PaperKeyword, ResearchKeyword
from neo4j import GraphDatabase
from typing import Any

class Command(BaseCommand):
    """
    Django 管理命令：同步学术数据到 Neo4j 图数据库
    """
    help = "Sync MySQL academic data to Neo4j graph database."

    def handle(self, *args: Any, **options: Any) -> None:
        uri = getattr(settings, 'NEO4J_URI', 'bolt://localhost:7687')
        user = getattr(settings, 'NEO4J_USER', 'neo4j')
        password = getattr(settings, 'NEO4J_PASSWORD', 'password')
        driver = GraphDatabase.driver(uri, auth=(user, password))
        self.stdout.write(self.style.SUCCESS(f"Connecting to Neo4j at {uri} as {user}"))
        with driver.session() as session:
            # 同步教师节点
            for tp in TeacherProfile.objects.select_related('user'):
                session.run(
                    "MERGE (t:Teacher {user_id: $user_id, name: $name})",
                    user_id=tp.user.id,
                    name=tp.user.get_full_name() or tp.user.username
                )
            # 同步论文节点
            for paper in Paper.objects.all():
                session.run(
                    "MERGE (p:Paper {paper_id: $paper_id, title: $title})",
                    paper_id=paper.id,
                    title=paper.title
                )
                # 教师与论文关系
                session.run(
                    "MATCH (t:Teacher {user_id: $user_id}), (p:Paper {paper_id: $paper_id}) "
                    "MERGE (t)-[:PUBLISHED {is_first: $is_first}]->(p)",
                    user_id=paper.teacher.id,
                    paper_id=paper.id,
                    is_first=paper.is_first_author
                )
                # 合作者节点与关系
                for co in paper.coauthors.all():
                    if co.is_internal and co.internal_teacher:
                        session.run(
                            "MERGE (t:Teacher {user_id: $user_id, name: $name})",
                            user_id=co.internal_teacher.id,
                            name=co.internal_teacher.get_full_name() or co.internal_teacher.username
                        )
                        session.run(
                            "MATCH (t:Teacher {user_id: $user_id}), (p:Paper {paper_id: $paper_id}) "
                            "MERGE (t)-[:CO_AUTHORED]->(p)",
                            user_id=co.internal_teacher.id,
                            paper_id=paper.id
                        )
                    else:
                        session.run(
                            "MERGE (e:ExternalScholar {name: $name})",
                            name=co.name
                        )
                        session.run(
                            "MATCH (e:ExternalScholar {name: $name}), (p:Paper {paper_id: $paper_id}) "
                            "MERGE (e)-[:CO_AUTHORED]->(p)",
                            name=co.name,
                            paper_id=paper.id
                        )
                # 关键词节点与关系
                for pk in PaperKeyword.objects.filter(paper=paper):
                    kw = pk.keyword
                    session.run(
                        "MERGE (k:Keyword {name: $name})",
                        name=kw.name
                    )
                    session.run(
                        "MATCH (p:Paper {paper_id: $paper_id}), (k:Keyword {name: $name}) "
                        "MERGE (p)-[:HAS_KEYWORD]->(k)",
                        paper_id=paper.id,
                        name=kw.name
                    )
        driver.close()
        self.stdout.write(self.style.SUCCESS("Neo4j sync completed."))
