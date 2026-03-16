from django.conf import settings


class Neo4jEngine:
    def __init__(self):
        self.enabled = getattr(settings, 'ENABLE_NEO4J', False)
        self.driver = None

        if not self.enabled:
            return

        try:
            from neo4j import GraphDatabase
        except Exception:
            self.enabled = False
            return

        self.uri = getattr(settings, 'NEO4J_URI', 'bolt://localhost:7687').replace('neo4j://', 'bolt://')
        self.user = getattr(settings, 'NEO4J_USER', 'neo4j')
        self.password = getattr(settings, 'NEO4J_PASSWORD', '')
        self.driver = GraphDatabase.driver(self.uri, auth=(self.user, self.password))

    def close(self):
        if self.driver is not None:
            self.driver.close()

    def sync_paper_to_graph(self, paper_id, title, teacher, coauthors, keywords):
        if not self.enabled or self.driver is None:
            return

        query = """
        MERGE (t:Teacher {user_id: $teacher_user_id})
        SET t.name = $teacher_name

        MERGE (p:Paper {paper_id: $paper_id})
        SET p.title = $title

        MERGE (t)-[:PUBLISHED]->(p)

        WITH p, t
        OPTIONAL MATCH (p)-[oldKeywordRel:HAS_KEYWORD]->(:Keyword)
        DELETE oldKeywordRel

        WITH p, t
        OPTIONAL MATCH (:ExternalScholar)-[oldCoauthoredRel:CO_AUTHORED]->(p)
        DELETE oldCoauthoredRel

        FOREACH (keyword_name IN $keywords |
            MERGE (k:Keyword {name: keyword_name})
            MERGE (p)-[:HAS_KEYWORD]->(k)
            MERGE (t)-[:RESEARCHES]->(k)
        )

        FOREACH (coauthor_name IN $coauthors |
            MERGE (c:ExternalScholar {name: coauthor_name})
            MERGE (c)-[:CO_AUTHORED]->(p)
        )
        """

        safe_keywords = [keyword for keyword in keywords if keyword]
        safe_coauthors = [coauthor for coauthor in coauthors if coauthor]

        with self.driver.session() as session:
            session.run(
                query,
                paper_id=str(paper_id),
                title=title,
                teacher_user_id=int(teacher['user_id']),
                teacher_name=teacher['name'],
                coauthors=safe_coauthors,
                keywords=safe_keywords,
            )

    def delete_paper_from_graph(self, paper_id):
        if not self.enabled or self.driver is None:
            return

        query = """
        MATCH (p:Paper {paper_id: $paper_id})
        DETACH DELETE p
        """
        with self.driver.session() as session:
            session.run(query, paper_id=str(paper_id))
