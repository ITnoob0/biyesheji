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

    def _run(self, query, **params):
        if not self.enabled or self.driver is None:
            return
        with self.driver.session() as session:
            session.run(query, **params)

    def sync_paper_to_graph(self, paper_id, title, teacher, coauthors, keywords):
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

        self._run(
            query,
            paper_id=str(paper_id),
            title=title,
            teacher_user_id=int(teacher['user_id']),
            teacher_name=teacher['name'],
            coauthors=[coauthor for coauthor in coauthors if coauthor],
            keywords=[keyword for keyword in keywords if keyword],
        )

    def delete_paper_from_graph(self, paper_id):
        self._run("MATCH (p:Paper {paper_id: $paper_id}) DETACH DELETE p", paper_id=str(paper_id))

    def sync_project_to_graph(self, project_id, title, teacher, level, role, status):
        query = """
        MERGE (t:Teacher {user_id: $teacher_user_id})
        SET t.name = $teacher_name

        MERGE (p:Project {project_id: $project_id})
        SET p.title = $title,
            p.level = $level,
            p.role = $role,
            p.status = $status

        MERGE (t)-[:UNDERTAKES_PROJECT]->(p)
        """
        self._run(
            query,
            project_id=str(project_id),
            title=title,
            teacher_user_id=int(teacher['user_id']),
            teacher_name=teacher['name'],
            level=level,
            role=role,
            status=status,
        )

    def delete_project_from_graph(self, project_id):
        self._run("MATCH (p:Project {project_id: $project_id}) DETACH DELETE p", project_id=str(project_id))

    def sync_intellectual_property_to_graph(self, ip_id, title, teacher, ip_type, registration_number):
        query = """
        MERGE (t:Teacher {user_id: $teacher_user_id})
        SET t.name = $teacher_name

        MERGE (i:IntellectualProperty {ip_id: $ip_id})
        SET i.title = $title,
            i.ip_type = $ip_type,
            i.registration_number = $registration_number

        MERGE (t)-[:OWNS_IP]->(i)
        """
        self._run(
            query,
            ip_id=str(ip_id),
            title=title,
            teacher_user_id=int(teacher['user_id']),
            teacher_name=teacher['name'],
            ip_type=ip_type,
            registration_number=registration_number,
        )

    def delete_intellectual_property_from_graph(self, ip_id):
        self._run("MATCH (i:IntellectualProperty {ip_id: $ip_id}) DETACH DELETE i", ip_id=str(ip_id))
    def sync_academic_service_to_graph(self, service_id, title, teacher, service_type, organization):
        query = """
        MERGE (t:Teacher {user_id: $teacher_user_id})
        SET t.name = $teacher_name

        MERGE (s:AcademicService {service_id: $service_id})
        SET s.title = $title,
            s.service_type = $service_type,
            s.organization = $organization

        MERGE (t)-[:PROVIDES_SERVICE]->(s)
        """
        self._run(
            query,
            service_id=str(service_id),
            title=title,
            teacher_user_id=int(teacher['user_id']),
            teacher_name=teacher['name'],
            service_type=service_type,
            organization=organization,
        )

    def delete_academic_service_from_graph(self, service_id):
        self._run(
            "MATCH (s:AcademicService {service_id: $service_id}) DETACH DELETE s",
            service_id=str(service_id),
        )
