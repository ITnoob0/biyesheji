from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.conf import settings
from neo4j import GraphDatabase

class AcademicGraphTopologyView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, user_id: int) -> Response:
        uri = getattr(settings, 'NEO4J_URI', 'bolt://localhost:7687')
        user = getattr(settings, 'NEO4J_USER', 'neo4j')
        password = getattr(settings, 'NEO4J_PASSWORD', 'password')
        driver = GraphDatabase.driver(uri, auth=(user, password))
        
        with driver.session() as session:
            # 修改后的 Cypher 查询：确保获取所有关联节点和它们所属的论文 ID
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
                return Response({"nodes": [], "links": []})

            nodes = []
            links = []
            node_map = {}

            # 1. 中心教师
            t = record['t']
            t_id = f"teacher_{user_id}"
            nodes.append({"id": t_id, "name": t['name'], "category": 0, "symbolSize": 50, "nodeType": "CenterTeacher"})
            node_map[t_id] = True

            # 2. 论文节点 (与教师连线)
            for p in record['papers']:
                if p:
                    p_id = f"paper_{p['paper_id']}"
                    if p_id not in node_map:
                        nodes.append({"id": p_id, "name": p['title'], "category": 1, "symbolSize": 40, "nodeType": "Paper"})
                        node_map[p_id] = True
                    links.append({"source": t_id, "target": p_id, "name": "published"})

            # 3. 关键词节点 (与论文连线)
            for k in record['keywords']:
                if k:
                    k_id = f"keyword_{k['name']}"
                    if k_id not in node_map:
                        nodes.append({"id": k_id, "name": k['name'], "category": 3, "symbolSize": 25, "nodeType": "Keyword"})
                        node_map[k_id] = True
            
            for item in record['p_k_links']:
                if item['p_id'] and item['k_name']:
                    links.append({"source": f"paper_{item['p_id']}", "target": f"keyword_{item['k_name']}", "name": "has_keyword"})

            # 4. 外部学者节点 (与论文连线) - 核心修复位置
            for e in record['scholars']:
                if e:
                    e_id = f"scholar_{e['name']}"
                    if e_id not in node_map:
                        nodes.append({"id": e_id, "name": e['name'], "category": 2, "symbolSize": 35, "nodeType": "ExternalScholar"})
                        node_map[e_id] = True

            for item in record['p_e_links']:
                if item['p_id'] and item['e_name']:
                    links.append({"source": f"scholar_{item['e_name']}", "target": f"paper_{item['p_id']}", "name": "co-author"})

            driver.close()
            return Response({"nodes": nodes, "links": links})