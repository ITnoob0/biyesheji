from django.conf import settings
from django.contrib.auth import get_user_model
from rest_framework.exceptions import PermissionDenied
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from achievements.models import Paper


class AcademicGraphTopologyView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, user_id: int) -> Response:
        if request.user.id != user_id and not (request.user.is_staff or request.user.is_superuser):
            raise PermissionDenied('You do not have permission to view this graph.')

        neo4j_topology = self._build_neo4j_topology(user_id)
        if neo4j_topology is not None:
            return Response(neo4j_topology)

        return Response(self._build_relational_topology(user_id))

    def _build_neo4j_topology(self, user_id: int):
        if not getattr(settings, 'ENABLE_NEO4J', False):
            return None

        try:
            from neo4j import GraphDatabase
        except Exception:
            return None

        uri = getattr(settings, 'NEO4J_URI', 'bolt://localhost:7687')
        user = getattr(settings, 'NEO4J_USER', 'neo4j')
        password = getattr(settings, 'NEO4J_PASSWORD', 'password')
        driver = None

        try:
            driver = GraphDatabase.driver(uri, auth=(user, password))

            with driver.session() as session:
                cypher = '''
                MATCH (t:Teacher {user_id: $user_id})
                OPTIONAL MATCH (t)-[:PUBLISHED]->(p:Paper)
                OPTIONAL MATCH (p)-[:HAS_KEYWORD]->(k:Keyword)
                OPTIONAL MATCH (e:ExternalScholar)-[:CO_AUTHORED]->(p)
                RETURN t,
                       collect(DISTINCT p) AS papers,
                       collect(DISTINCT k) AS keywords,
                       collect(DISTINCT e) AS scholars,
                       collect(DISTINCT {p_id: p.paper_id, k_name: k.name}) AS p_k_links,
                       collect(DISTINCT {p_id: p.paper_id, e_name: e.name}) AS p_e_links
                '''
                result = session.run(cypher, user_id=user_id)
                record = result.single()

                if not record or not record['t']:
                    return None

                nodes = []
                links = []
                node_map = {}

                teacher = record['t']
                teacher_id = f'teacher_{user_id}'
                nodes.append(
                    {
                        'id': teacher_id,
                        'name': teacher['name'],
                        'category': 0,
                        'symbolSize': 50,
                        'nodeType': 'CenterTeacher',
                    }
                )
                node_map[teacher_id] = True

                for paper in record['papers']:
                    if paper:
                        paper_id = f"paper_{paper['paper_id']}"
                        if paper_id not in node_map:
                            nodes.append(
                                {
                                    'id': paper_id,
                                    'name': paper['title'],
                                    'category': 1,
                                    'symbolSize': 40,
                                    'nodeType': 'Paper',
                                }
                            )
                            node_map[paper_id] = True
                        links.append({'source': teacher_id, 'target': paper_id, 'name': 'published'})

                for keyword in record['keywords']:
                    if keyword:
                        keyword_id = f"keyword_{keyword['name']}"
                        if keyword_id not in node_map:
                            nodes.append(
                                {
                                    'id': keyword_id,
                                    'name': keyword['name'],
                                    'category': 3,
                                    'symbolSize': 25,
                                    'nodeType': 'Keyword',
                                }
                            )
                            node_map[keyword_id] = True

                for item in record['p_k_links']:
                    if item['p_id'] and item['k_name']:
                        links.append(
                            {
                                'source': f"paper_{item['p_id']}",
                                'target': f"keyword_{item['k_name']}",
                                'name': 'has_keyword',
                            }
                        )

                for scholar in record['scholars']:
                    if scholar:
                        scholar_id = f"scholar_{scholar['name']}"
                        if scholar_id not in node_map:
                            nodes.append(
                                {
                                    'id': scholar_id,
                                    'name': scholar['name'],
                                    'category': 2,
                                    'symbolSize': 35,
                                    'nodeType': 'ExternalScholar',
                                }
                            )
                            node_map[scholar_id] = True

                for item in record['p_e_links']:
                    if item['p_id'] and item['e_name']:
                        links.append(
                            {
                                'source': f"scholar_{item['e_name']}",
                                'target': f"paper_{item['p_id']}",
                                'name': 'co-author',
                            }
                        )

                if len(nodes) <= 1:
                    return None

                return {'nodes': nodes, 'links': links}
        except Exception:
            return None
        finally:
            if driver is not None:
                driver.close()

    def _build_relational_topology(self, user_id: int):
        user_model = get_user_model()
        try:
            teacher = user_model.objects.get(id=user_id)
        except user_model.DoesNotExist:
            return {'nodes': [], 'links': []}

        papers = list(
            Paper.objects.filter(teacher=teacher)
            .prefetch_related('coauthors', 'paperkeyword_set__keyword')
            .order_by('-date_acquired', '-created_at')
        )

        if not papers:
            return {'nodes': [], 'links': []}

        nodes = []
        links = []
        node_ids = set()

        teacher_node_id = f'teacher_{teacher.id}'
        teacher_name = teacher.real_name or teacher.username
        nodes.append(
            {
                'id': teacher_node_id,
                'name': teacher_name,
                'category': 0,
                'symbolSize': 52,
                'nodeType': 'CenterTeacher',
            }
        )
        node_ids.add(teacher_node_id)

        for paper in papers:
            paper_node_id = f'paper_{paper.id}'
            if paper_node_id not in node_ids:
                nodes.append(
                    {
                        'id': paper_node_id,
                        'name': paper.title,
                        'category': 1,
                        'symbolSize': 38,
                        'nodeType': 'Paper',
                    }
                )
                node_ids.add(paper_node_id)

            links.append({'source': teacher_node_id, 'target': paper_node_id, 'name': 'published'})

            for coauthor in paper.coauthors.all():
                scholar_node_id = f'coauthor_{coauthor.id}'
                if scholar_node_id not in node_ids:
                    nodes.append(
                        {
                            'id': scholar_node_id,
                            'name': coauthor.name,
                            'category': 2,
                            'symbolSize': 30,
                            'nodeType': 'ExternalScholar',
                        }
                    )
                    node_ids.add(scholar_node_id)

                links.append({'source': scholar_node_id, 'target': paper_node_id, 'name': 'co-author'})

            for relation in paper.paperkeyword_set.all():
                keyword = relation.keyword
                keyword_node_id = f'keyword_{keyword.id}'
                if keyword_node_id not in node_ids:
                    nodes.append(
                        {
                            'id': keyword_node_id,
                            'name': keyword.name,
                            'category': 3,
                            'symbolSize': 24,
                            'nodeType': 'Keyword',
                        }
                    )
                    node_ids.add(keyword_node_id)

                links.append({'source': paper_node_id, 'target': keyword_node_id, 'name': 'has_keyword'})

        return {'nodes': nodes, 'links': links}
