from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.conf import settings
from neo4j import GraphDatabase
from typing import Any, Dict

class AcademicGraphTopologyView(APIView):
	"""
	获取指定教师的2跳学术社交图谱，返回 ECharts Graph series 格式
	"""
	permission_classes = [IsAuthenticated]

	def get(self, request, user_id: int) -> Response:
		uri = getattr(settings, 'NEO4J_URI', 'bolt://localhost:7687')
		user = getattr(settings, 'NEO4J_USER', 'neo4j')
		password = getattr(settings, 'NEO4J_PASSWORD', 'password')
		driver = GraphDatabase.driver(uri, auth=(user, password))
		with driver.session() as session:
			cypher = '''
			MATCH (t:Teacher {user_id: $user_id})
			OPTIONAL MATCH (t)-[pub:PUBLISHED]->(p:Paper)
			OPTIONAL MATCH (t)-[co:CO_AUTHORED]->(p)
			OPTIONAL MATCH (p)-[kw:HAS_KEYWORD]->(k:Keyword)
			OPTIONAL MATCH (e:ExternalScholar)-[eco:CO_AUTHORED]->(p)
			RETURN t, collect(DISTINCT p) AS papers, collect(DISTINCT k) AS keywords,
				   collect(DISTINCT e) AS external_scholars,
				   collect(DISTINCT pub) AS published_edges,
				   collect(DISTINCT co) AS coauthored_edges,
				   collect(DISTINCT eco) AS external_coauthored_edges,
				   collect(DISTINCT kw) AS keyword_edges
			'''
			result = session.run(cypher, user_id=user_id)
			record = result.single()
			nodes = []
			links = []
			node_map = {}
			# 教师节点
			t = record['t']
			teacher_id = f"teacher_{t['user_id']}"
			nodes.append({
				"id": teacher_id,
				"name": t['name'],
				"category": 0,
				"symbolSize": 50,
				"nodeType": "CenterTeacher"
			})
			node_map[teacher_id] = True
			# 论文节点
			for p in record['papers']:
				pid = f"paper_{p['paper_id']}"
				if pid not in node_map:
					nodes.append({
						"id": pid,
						"name": p['title'],
						"category": 1,
						"symbolSize": 40,
						"nodeType": "Paper"
					})
					node_map[pid] = True
				links.append({
					"source": teacher_id,
					"target": pid,
					"name": "published"
				})
			# 关键词节点
			for k in record['keywords']:
				kid = f"keyword_{k['name']}"
				if kid not in node_map:
					nodes.append({
						"id": kid,
						"name": k['name'],
						"category": 3,
						"symbolSize": 30,
						"nodeType": "Keyword"
					})
					node_map[kid] = True
			for p in record['papers']:
				pid = f"paper_{p['paper_id']}"
				for k in record['keywords']:
					kid = f"keyword_{k['name']}"
					links.append({
						"source": pid,
						"target": kid,
						"name": "has_keyword"
					})
			# 外部学者节点
			for e in record['external_scholars']:
				eid = f"external_{e['name']}"
				if eid not in node_map:
					nodes.append({
						"id": eid,
						"name": e['name'],
						"category": 2,
						"symbolSize": 35,
						"nodeType": "ExternalScholar"
					})
					node_map[eid] = True
			for p in record['papers']:
				pid = f"paper_{p['paper_id']}"
				for e in record['external_scholars']:
					eid = f"external_{e['name']}"
					links.append({
						"source": eid,
						"target": pid,
						"name": "co-author"
					})
			# 返回 ECharts 格式
			driver.close()
			return Response({"nodes": nodes, "links": links})
