from django.conf import settings
from django.contrib.auth import get_user_model
from rest_framework.exceptions import PermissionDenied
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from django.db.models import Count

from achievements.models import AcademicService, IntellectualProperty, Paper, PaperKeyword, Project, TeachingAchievement


NODE_TYPE_META = {
    'CenterTeacher': {'category': 0, 'symbol_size': 52, 'label': '中心教师'},
    'Paper': {'category': 1, 'symbol_size': 38, 'label': '论文'},
    'ExternalScholar': {'category': 2, 'symbol_size': 30, 'label': '合作学者'},
    'Keyword': {'category': 3, 'symbol_size': 24, 'label': '关键词'},
    'Project': {'category': 4, 'symbol_size': 34, 'label': '科研项目'},
    'IntellectualProperty': {'category': 5, 'symbol_size': 32, 'label': '知识产权'},
    'TeachingAchievement': {'category': 6, 'symbol_size': 32, 'label': '教学成果'},
    'AcademicService': {'category': 7, 'symbol_size': 30, 'label': '学术服务'},
}

RELATION_META = {
    'published': ('发表', '教师与论文成果的发表关系。'),
    'has_keyword': ('关键词', '论文与研究关键词之间的主题关联。'),
    'co-author': ('合作', '合作学者与论文之间的合作关系。'),
    'undertakes_project': ('承担项目', '教师与科研项目之间的承担关系。'),
    'owns_ip': ('知识产权', '教师与知识产权成果之间的归属关系。'),
    'has_teaching_achievement': ('教学成果', '教师与教学成果之间的关联关系。'),
    'provides_service': ('学术服务', '教师与学术服务事项之间的参与关系。'),
}


class AcademicGraphTopologyView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, user_id: int) -> Response:
        if request.user.id != user_id and not (request.user.is_staff or request.user.is_superuser):
            raise PermissionDenied('You do not have permission to view this graph.')

        neo4j_topology = self._build_neo4j_topology(user_id)
        if neo4j_topology is not None:
            return Response(neo4j_topology)

        return Response(self._build_relational_topology(user_id))

    def _build_meta(self, source: str, fallback_used: bool, node_count: int, link_count: int, notice: str):
        return {
            'source': source,
            'fallback_used': fallback_used,
            'node_count': node_count,
            'link_count': link_count,
            'notice': notice,
        }

    def _make_node(self, node_id: str, name: str, node_type: str, detail_lines=None, **extra):
        meta = NODE_TYPE_META.get(node_type, {'category': 8, 'symbol_size': 28, 'label': node_type})
        return {
            'id': node_id,
            'name': name,
            'category': meta['category'],
            'symbolSize': meta['symbol_size'],
            'nodeType': node_type,
            'nodeTypeLabel': meta['label'],
            'detailLines': detail_lines or [],
            **extra,
        }

    def _make_link(self, source: str, target: str, relation_name: str):
        label, description = RELATION_META.get(relation_name, (relation_name, '当前关系用于描述图谱中的实体连接。'))
        return {
            'source': source,
            'target': target,
            'name': relation_name,
            'relationLabel': label,
            'description': description,
        }

    def _build_analysis(self, teacher):
        paper_queryset = Paper.objects.filter(teacher=teacher)
        collaborator_ranking = list(
            paper_queryset
            .filter(coauthors__isnull=False)
            .values('coauthors__name')
            .annotate(count=Count('coauthors__id'))
            .order_by('-count', 'coauthors__name')[:5]
        )
        keyword_ranking = list(
            PaperKeyword.objects.filter(paper__teacher=teacher)
            .values('keyword__name')
            .annotate(count=Count('keyword_id'))
            .order_by('-count', 'keyword__name')[:5]
        )

        top_collaborators = [
            {
                'name': item['coauthors__name'],
                'count': item['count'],
            }
            for item in collaborator_ranking
            if item['coauthors__name']
        ]
        top_keywords = [
            {
                'name': item['keyword__name'],
                'count': item['count'],
            }
            for item in keyword_ranking
            if item['keyword__name']
        ]

        highlight_cards = [
            {
                'title': '合作最活跃学者',
                'value': top_collaborators[0]['name'] if top_collaborators else '暂无',
                'detail': (
                    f"共同关联 {top_collaborators[0]['count']} 篇论文"
                    if top_collaborators
                    else '录入合作作者后会自动形成分析结果。'
                ),
            },
            {
                'title': '高频研究主题',
                'value': top_keywords[0]['name'] if top_keywords else '暂无',
                'detail': (
                    f"在关键词中出现 {top_keywords[0]['count']} 次"
                    if top_keywords
                    else '录入论文摘要并提取关键词后会自动形成主题分析。'
                ),
            },
        ]

        return {
            'top_collaborators': top_collaborators,
            'top_keywords': top_keywords,
            'network_overview': {
                'paper_count': paper_queryset.count(),
                'collaborator_total': len(top_collaborators),
                'keyword_total': len(top_keywords),
            },
            'highlight_cards': highlight_cards,
            'scope_note': '当前属于轻量图分析展示，侧重合作与主题热点，不构成完整图挖掘平台。',
        }

    def _finalize_response(self, teacher, nodes, links, source: str, fallback_used: bool, notice: str):
        return {
            'nodes': nodes,
            'links': links,
            'meta': self._build_meta(source, fallback_used, len(nodes), len(links), notice),
            'analysis': self._build_analysis(teacher) if teacher else {
                'top_collaborators': [],
                'top_keywords': [],
                'network_overview': {
                    'paper_count': 0,
                    'collaborator_total': 0,
                    'keyword_total': 0,
                },
                'highlight_cards': [],
                'scope_note': '当前无可用数据，尚未形成轻量图分析结果。',
            },
        }

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
                OPTIONAL MATCH (t)-[:UNDERTAKES_PROJECT]->(pr:Project)
                OPTIONAL MATCH (t)-[:OWNS_IP]->(ip:IntellectualProperty)
                OPTIONAL MATCH (t)-[:HAS_TEACHING_ACHIEVEMENT]->(ta:TeachingAchievement)
                OPTIONAL MATCH (t)-[:PROVIDES_SERVICE]->(svc:AcademicService)
                RETURN t,
                       collect(DISTINCT p) AS papers,
                       collect(DISTINCT k) AS keywords,
                       collect(DISTINCT e) AS scholars,
                       collect(DISTINCT pr) AS projects,
                       collect(DISTINCT ip) AS ips,
                       collect(DISTINCT ta) AS teachings,
                       collect(DISTINCT svc) AS services,
                       collect(DISTINCT {p_id: p.paper_id, k_name: k.name}) AS p_k_links,
                       collect(DISTINCT {p_id: p.paper_id, e_name: e.name}) AS p_e_links
                '''
                record = session.run(cypher, user_id=user_id).single()

                if not record or not record['t']:
                    return None

                nodes = []
                links = []
                node_map = set()

                def add_node(node):
                    if not node['id'] or node['id'] in node_map:
                        return
                    nodes.append(node)
                    node_map.add(node['id'])

                teacher_node = record['t']
                user_model = get_user_model()
                teacher = user_model.objects.filter(id=user_id).first()
                teacher_id = f'teacher_{user_id}'
                add_node(
                    self._make_node(
                        teacher_id,
                        teacher_node.get('name', f'教师 {user_id}'),
                        'CenterTeacher',
                        detail_lines=['图谱中心节点', '当前教师画像的核心主体'],
                    )
                )

                for paper in record['papers']:
                    if not paper:
                        continue
                    paper_id = f"paper_{paper['paper_id']}"
                    add_node(
                        self._make_node(
                            paper_id,
                            paper.get('title', '未命名论文'),
                            'Paper',
                            detail_lines=['论文成果节点'],
                        )
                    )
                    links.append(self._make_link(teacher_id, paper_id, 'published'))

                for keyword in record['keywords']:
                    if not keyword:
                        continue
                    add_node(
                        self._make_node(
                            f"keyword_{keyword['name']}",
                            keyword['name'],
                            'Keyword',
                            detail_lines=['研究主题关键词'],
                        )
                    )

                for item in record['p_k_links']:
                    if item['p_id'] and item['k_name']:
                        links.append(self._make_link(f"paper_{item['p_id']}", f"keyword_{item['k_name']}", 'has_keyword'))

                for scholar in record['scholars']:
                    if not scholar:
                        continue
                    add_node(
                        self._make_node(
                            f"scholar_{scholar['name']}",
                            scholar['name'],
                            'ExternalScholar',
                            detail_lines=['外部合作学者节点'],
                        )
                    )

                for item in record['p_e_links']:
                    if item['p_id'] and item['e_name']:
                        links.append(self._make_link(f"scholar_{item['e_name']}", f"paper_{item['p_id']}", 'co-author'))

                for project in record['projects']:
                    if not project:
                        continue
                    project_id = f"project_{project['project_id']}"
                    add_node(
                        self._make_node(
                            project_id,
                            project.get('title', '未命名项目'),
                            'Project',
                            detail_lines=[
                                f"项目级别：{project.get('level', '未知')}",
                                f"承担角色：{project.get('role', '未知')}",
                                f"项目状态：{project.get('status', '未知')}",
                            ],
                        )
                    )
                    links.append(self._make_link(teacher_id, project_id, 'undertakes_project'))

                for ip in record['ips']:
                    if not ip:
                        continue
                    ip_id = f"ip_{ip['ip_id']}"
                    add_node(
                        self._make_node(
                            ip_id,
                            ip.get('title', '未命名知识产权'),
                            'IntellectualProperty',
                            detail_lines=[
                                f"成果类型：{ip.get('ip_type', '未知')}",
                                f"登记号：{ip.get('registration_number', '未知')}",
                            ],
                        )
                    )
                    links.append(self._make_link(teacher_id, ip_id, 'owns_ip'))

                for teaching in record['teachings']:
                    if not teaching:
                        continue
                    teaching_id = f"teaching_{teaching['teaching_id']}"
                    add_node(
                        self._make_node(
                            teaching_id,
                            teaching.get('title', '未命名教学成果'),
                            'TeachingAchievement',
                            detail_lines=[
                                f"成果类型：{teaching.get('achievement_type', '未知')}",
                                f"级别：{teaching.get('level', '未知')}",
                            ],
                        )
                    )
                    links.append(self._make_link(teacher_id, teaching_id, 'has_teaching_achievement'))

                for service in record['services']:
                    if not service:
                        continue
                    service_id = f"service_{service['service_id']}"
                    add_node(
                        self._make_node(
                            service_id,
                            service.get('title', '未命名学术服务'),
                            'AcademicService',
                            detail_lines=[
                                f"服务类型：{service.get('service_type', '未知')}",
                                f"服务机构：{service.get('organization', '未知')}",
                            ],
                        )
                    )
                    links.append(self._make_link(teacher_id, service_id, 'provides_service'))

                if len(nodes) <= 1:
                    return None

                return self._finalize_response(
                    teacher,
                    nodes,
                    links,
                    source='neo4j',
                    fallback_used=False,
                    notice='当前图谱由 Neo4j 实时读取；若图数据库不可用，系统会自动回退到 MySQL 关系数据。',
                )
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
            return self._finalize_response(
                None,
                [],
                [],
                source='mysql',
                fallback_used=True,
                notice='未找到目标教师，图谱数据为空。',
            )

        papers = list(
            Paper.objects.filter(teacher=teacher)
            .prefetch_related('coauthors', 'paperkeyword_set__keyword')
            .order_by('-date_acquired', '-created_at')
        )
        projects = list(Project.objects.filter(teacher=teacher).order_by('-date_acquired', '-created_at'))
        ips = list(IntellectualProperty.objects.filter(teacher=teacher).order_by('-date_acquired', '-created_at'))
        teachings = list(TeachingAchievement.objects.filter(teacher=teacher).order_by('-date_acquired', '-created_at'))
        services = list(AcademicService.objects.filter(teacher=teacher).order_by('-date_acquired', '-created_at'))

        if not any([papers, projects, ips, teachings, services]):
            return self._finalize_response(
                teacher,
                [],
                [],
                source='mysql',
                fallback_used=True,
                notice='当前教师暂无可构成图谱的成果数据，请先录入论文、项目、知识产权、教学成果或学术服务。',
            )

        nodes = []
        links = []
        node_ids = set()

        def add_node(node):
            if node['id'] in node_ids:
                return
            nodes.append(node)
            node_ids.add(node['id'])

        teacher_node_id = f'teacher_{teacher.id}'
        teacher_name = teacher.real_name or teacher.username
        add_node(
            self._make_node(
                teacher_node_id,
                teacher_name,
                'CenterTeacher',
                detail_lines=['图谱中心节点', '当前教师画像的核心主体'],
            )
        )

        for paper in papers:
            paper_node_id = f'paper_{paper.id}'
            add_node(
                self._make_node(
                    paper_node_id,
                    paper.title,
                    'Paper',
                    detail_lines=[
                        f'论文类型：{paper.get_paper_type_display()}',
                        f'期刊/会议：{paper.journal_name}',
                        f'发表时间：{paper.date_acquired.isoformat()}',
                    ],
                )
            )
            links.append(self._make_link(teacher_node_id, paper_node_id, 'published'))

            for coauthor in paper.coauthors.all():
                scholar_node_id = f'coauthor_{coauthor.id}'
                add_node(
                    self._make_node(
                        scholar_node_id,
                        coauthor.name,
                        'ExternalScholar',
                        detail_lines=['合作网络节点', f'关联论文：{paper.title}'],
                    )
                )
                links.append(self._make_link(scholar_node_id, paper_node_id, 'co-author'))

            for relation in paper.paperkeyword_set.all():
                keyword = relation.keyword
                keyword_node_id = f'keyword_{keyword.id}'
                add_node(
                    self._make_node(
                        keyword_node_id,
                        keyword.name,
                        'Keyword',
                        detail_lines=['研究主题关键词', f'来源论文：{paper.title}'],
                    )
                )
                links.append(self._make_link(paper_node_id, keyword_node_id, 'has_keyword'))

        for project in projects:
            project_node_id = f'project_{project.id}'
            add_node(
                self._make_node(
                    project_node_id,
                    project.title,
                    'Project',
                    detail_lines=[
                        f'项目级别：{project.get_level_display()}',
                        f'承担角色：{project.get_role_display()}',
                        f'经费：{project.funding_amount} 万元',
                    ],
                )
            )
            links.append(self._make_link(teacher_node_id, project_node_id, 'undertakes_project'))

        for ip in ips:
            ip_node_id = f'ip_{ip.id}'
            add_node(
                self._make_node(
                    ip_node_id,
                    ip.title,
                    'IntellectualProperty',
                    detail_lines=[
                        f'成果类型：{ip.get_ip_type_display()}',
                        f'登记号：{ip.registration_number}',
                        '已转化' if ip.is_transformed else '未转化',
                    ],
                )
            )
            links.append(self._make_link(teacher_node_id, ip_node_id, 'owns_ip'))

        for teaching in teachings:
            teaching_node_id = f'teaching_{teaching.id}'
            add_node(
                self._make_node(
                    teaching_node_id,
                    teaching.title,
                    'TeachingAchievement',
                    detail_lines=[
                        f'成果类型：{teaching.get_achievement_type_display()}',
                        f'级别：{teaching.level}',
                    ],
                )
            )
            links.append(self._make_link(teacher_node_id, teaching_node_id, 'has_teaching_achievement'))

        for service in services:
            service_node_id = f'service_{service.id}'
            add_node(
                self._make_node(
                    service_node_id,
                    service.title,
                    'AcademicService',
                    detail_lines=[
                        f'服务类型：{service.get_service_type_display()}',
                        f'服务机构：{service.organization}',
                    ],
                )
            )
            links.append(self._make_link(teacher_node_id, service_node_id, 'provides_service'))

        return self._finalize_response(
            teacher,
            nodes,
            links,
            source='mysql',
            fallback_used=True,
            notice='当前图谱已自动回退到 MySQL 关系数据展示，图数据库不可用时页面主体仍可正常使用。',
        )
