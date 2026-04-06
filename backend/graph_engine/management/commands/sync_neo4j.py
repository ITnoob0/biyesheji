from django.core.management.base import BaseCommand
from django.conf import settings
from django.contrib.auth import get_user_model
from achievements.models import Paper, PaperKeyword
from achievements.visibility import APPROVED_STATUS
from neo4j import GraphDatabase
from typing import Any

User = get_user_model()

class Command(BaseCommand):
    help = "Sync MySQL academic data to Neo4j graph database."

    def handle(self, *args: Any, **options: Any) -> None:
        uri = getattr(settings, 'NEO4J_URI', 'neo4j://127.0.0.1:7687')
        user = getattr(settings, 'NEO4J_USER', 'neo4j')
        password = getattr(settings, 'NEO4J_PASSWORD', 'liujianlei')
        
        driver = GraphDatabase.driver(uri, auth=(user, password))
        
        with driver.session() as session:
            self.stdout.write("Cleaning up old data in Neo4j...")
            # 建议开发阶段开启：清空所有节点和关系，确保同步后数据的纯净
            session.run("MATCH (n) DETACH DELETE n")

            self.stdout.write("Syncing Teachers and Papers...")
            # 直接遍历论文，动态确保教师节点存在
            for paper in Paper.objects.filter(status=APPROVED_STATUS).select_related('teacher'):
                # 1. 确保主讲教师节点存在（即使没有 TeacherProfile）
                teacher_name = paper.teacher.get_full_name() or paper.teacher.username
                session.run(
                    "MERGE (t:Teacher {user_id: $user_id}) "
                    "SET t.name = $name",
                    user_id=paper.teacher.id,
                    name=teacher_name
                )

                # 2. 确保论文节点存在
                session.run(
                    "MERGE (p:Paper {paper_id: $paper_id}) "
                    "SET p.title = $title",
                    paper_id=paper.id,
                    title=paper.title
                )

                # 3. 建立发布关系
                session.run(
                    "MATCH (t:Teacher {user_id: $user_id}), (p:Paper {paper_id: $paper_id}) "
                    "MERGE (t)-[:PUBLISHED {is_first: $is_first}]->(p)",
                    user_id=paper.teacher.id,
                    paper_id=paper.id,
                    is_first=paper.is_first_author
                )

                # 4. 同步合作者
                for co in paper.coauthors.all():
                    if co.is_internal and co.internal_teacher:
                        co_name = co.internal_teacher.get_full_name() or co.internal_teacher.username
                        session.run(
                            "MERGE (t:Teacher {user_id: $user_id}) SET t.name = $name",
                            user_id=co.internal_teacher.id, name=co_name
                        )
                        session.run(
                            "MATCH (t:Teacher {user_id: $user_id}), (p:Paper {paper_id: $paper_id}) "
                            "MERGE (t)-[:CO_AUTHORED]->(p)",
                            user_id=co.internal_teacher.id, paper_id=paper.id
                        )
                    else:
                        session.run(
                            "MERGE (e:ExternalScholar {name: $name})",
                            name=co.name
                        )
                        session.run(
                            "MATCH (e:ExternalScholar {name: $name}), (p:Paper {paper_id: $paper_id}) "
                            "MERGE (e)-[:CO_AUTHORED]->(p)",
                            name=co.name, paper_id=paper.id
                        )

                # 5. 同步关键词
                for pk in PaperKeyword.objects.filter(paper=paper, paper__status=APPROVED_STATUS).select_related('keyword'):
                    session.run("MERGE (k:Keyword {name: $name})", name=pk.keyword.name)
                    session.run(
                        "MATCH (p:Paper {paper_id: $paper_id}), (k:Keyword {name: $name}) "
                        "MERGE (p)-[:HAS_KEYWORD]->(k)",
                        paper_id=paper.id, name=pk.keyword.name
                    )

        driver.close()
        self.stdout.write(self.style.SUCCESS("Neo4j sync completed successfully!"))