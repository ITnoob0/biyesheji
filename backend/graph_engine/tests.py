from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import override_settings
from rest_framework.test import APITestCase

from achievements.models import (
    AcademicService,
    CoAuthor,
    IntellectualProperty,
    Paper,
    PaperKeyword,
    Project,
    ResearchKeyword,
    TeachingAchievement,
)


User = get_user_model()


@override_settings(ENABLE_NEO4J=False)
class GraphTopologyFallbackTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            id=100081,
            username='100081',
            password='teacher123456',
            real_name='测试教师',
        )
        self.client.force_authenticate(self.user)
        self.url = f'/api/graph/topology/{self.user.id}/'

    def test_relational_topology_includes_meta_and_detail_fields(self):
        paper = Paper.objects.create(
            teacher=self.user,
            title='高校教师科研画像数据融合方法研究',
            abstract='围绕画像建模与知识组织展开研究。',
            date_acquired='2026-03-01',
            doi='10.1234/portrait-fallback-test',
            paper_type='JOURNAL',
            journal_name='教育信息化研究',
            status='APPROVED',
        )
        CoAuthor.objects.create(paper=paper, name='校内合作者', is_internal=True)
        CoAuthor.objects.create(paper=paper, name='校外合作者', is_internal=False)
        keyword, _ = ResearchKeyword.objects.get_or_create(name='教师画像')
        PaperKeyword.objects.create(paper=paper, keyword=keyword)
        project = Project.objects.create(
            teacher=self.user,
            title='图谱与教师研究产出联动项目',
            date_acquired='2026-03-02',
            level='PROVINCIAL',
            role='PI',
            funding_amount='12.50',
            project_status='ONGOING',
            status='APPROVED',
        )
        ip = IntellectualProperty.objects.create(
            teacher=self.user,
            title='教师画像图谱系统软件著作权',
            date_acquired='2026-03-03',
            ip_type='SOFTWARE_COPYRIGHT',
            registration_number='IP-2026-001',
            is_transformed=False,
            status='APPROVED',
        )
        teaching = TeachingAchievement.objects.create(
            teacher=self.user,
            title='图谱与画像融合教改成果',
            date_acquired='2026-03-04',
            achievement_type='TEACHING_REFORM',
            level='校级',
            status='APPROVED',
        )
        service = AcademicService.objects.create(
            teacher=self.user,
            title='学术图数据治理专题论坛报告',
            date_acquired='2026-03-05',
            service_type='INVITED_TALK',
            organization='教育数据治理协作组织',
            status='APPROVED',
        )

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 200)
        self.assertIn('nodes', response.data)
        self.assertIn('links', response.data)
        self.assertIn('meta', response.data)

        meta = response.data['meta']
        self.assertEqual(meta['source'], 'mysql')
        self.assertTrue(meta['fallback_used'])
        self.assertGreaterEqual(meta['node_count'], 6)
        self.assertGreaterEqual(meta['link_count'], 5)
        self.assertIn('source_scope_note', meta)
        self.assertIn('degradation_note', meta)
        self.assertIn('interaction_note', meta)
        self.assertIn('analysis_level', meta)
        self.assertIn('fallback_tip', meta)

        self.assertTrue(any('nodeTypeLabel' in node for node in response.data['nodes']))
        self.assertTrue(any('detailLines' in node for node in response.data['nodes']))
        self.assertTrue(any(node.get('name') == paper.title for node in response.data['nodes']))
        self.assertTrue(any(node.get('recordType') == 'paper' and node.get('entityId') == paper.id for node in response.data['nodes']))
        self.assertTrue(any(node.get('recordType') == 'project' and node.get('entityId') == project.id for node in response.data['nodes']))
        self.assertTrue(any(node.get('recordType') == 'intellectual_property' and node.get('entityId') == ip.id for node in response.data['nodes']))
        self.assertTrue(any(node.get('recordType') == 'teaching_achievement' and node.get('entityId') == teaching.id for node in response.data['nodes']))
        self.assertTrue(any(node.get('recordType') == 'academic_service' and node.get('entityId') == service.id for node in response.data['nodes']))

        self.assertTrue(any('relationLabel' in link for link in response.data['links']))
        self.assertTrue(any('description' in link for link in response.data['links']))
        self.assertIn('analysis', response.data)
        self.assertIn('highlight_cards', response.data['analysis'])
        self.assertIn('scope_note', response.data['analysis'])
        self.assertIn('collaboration_overview', response.data['analysis'])
        self.assertIn('collaboration_circle_overview', response.data['analysis'])
        self.assertIn('collaborator_type_breakdown', response.data['analysis'])
        self.assertIn('theme_hotspots', response.data['analysis'])
        self.assertEqual(response.data['analysis']['collaborator_type_breakdown']['internal_count'], 1)
        self.assertEqual(response.data['analysis']['collaborator_type_breakdown']['external_count'], 1)
        self.assertEqual(response.data['analysis']['collaboration_circle_overview']['extended_collaborator_count'], 2)
        self.assertEqual(response.data['analysis']['theme_hotspots']['top_keywords'][0]['name'], '教师画像')

    def test_empty_relational_topology_keeps_compatible_response_shape(self):
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['nodes'], [])
        self.assertEqual(response.data['links'], [])
        self.assertIn('meta', response.data)
        self.assertEqual(response.data['meta']['source'], 'mysql')
        self.assertTrue(response.data['meta']['fallback_used'])
        self.assertIn('notice', response.data['meta'])
        self.assertIn('source_scope_note', response.data['meta'])
        self.assertIn('degradation_note', response.data['meta'])
        self.assertIn('interaction_note', response.data['meta'])
        self.assertIn('fallback_tip', response.data['meta'])
        self.assertEqual(response.data['analysis']['collaboration_overview']['paper_count'], 0)
        self.assertEqual(response.data['analysis']['collaboration_circle_overview']['core_collaborator_count'], 0)
        self.assertEqual(response.data['analysis']['theme_hotspots']['top_keywords'], [])

    def test_collaboration_circle_overview_uses_lightweight_thresholds(self):
        for index in range(3):
            paper = Paper.objects.create(
                teacher=self.user,
                title=f'合作圈层验证论文 {index + 1}',
                abstract='围绕合作圈层一期轻量阈值划分进行验证。',
                date_acquired=f'2026-03-0{index + 1}',
                doi=f'10.1234/circle-test-{index + 1}',
                paper_type='JOURNAL',
                journal_name='图谱分析验证期刊',
                status='APPROVED',
            )
            CoAuthor.objects.create(paper=paper, name='核心合作者', is_internal=False)
            if index < 2:
                CoAuthor.objects.create(paper=paper, name='活跃合作者', is_internal=True)
            if index == 0:
                CoAuthor.objects.create(paper=paper, name='扩展合作者', is_internal=False)

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 200)
        circle = response.data['analysis']['collaboration_circle_overview']
        self.assertEqual(circle['core_collaborator_count'], 1)
        self.assertEqual(circle['active_collaborator_count'], 1)
        self.assertEqual(circle['extended_collaborator_count'], 1)
        self.assertEqual(circle['core_collaborators'][0]['name'], '核心合作者')
        self.assertIn('轻量', circle['threshold_note'])

    @override_settings(ENABLE_NEO4J=True)
    def test_graph_still_falls_back_to_mysql_when_neo4j_runtime_is_unavailable(self):
        paper = Paper.objects.create(
            teacher=self.user,
            title='Neo4j 不可用时的回退验证论文',
            abstract='围绕图谱回退链路和轻量分析稳定性展开验证。',
            date_acquired='2026-03-03',
            doi='10.1234/graph-fallback-runtime',
            paper_type='JOURNAL',
            journal_name='教育信息化研究',
            status='APPROVED',
        )
        CoAuthor.objects.create(paper=paper, name='回退合作者', is_internal=False)

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['meta']['source'], 'mysql')
        self.assertTrue(response.data['meta']['fallback_used'])
        self.assertIn('MySQL', response.data['meta']['fallback_tip'])
        self.assertIn('degradation_note', response.data['meta'])
        self.assertTrue(response.data['nodes'])
        self.assertTrue(response.data['links'])

    def test_non_admin_cannot_access_other_teacher_topology(self):
        other_user = User.objects.create_user(
            id=100082,
            username='100082',
            password='teacher123456',
            real_name='其他教师',
        )

        response = self.client.get(f'/api/graph/topology/{other_user.id}/')

        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.data['detail'], '教师账号只能查看本人的学术图谱。')
        self.assertEqual(response.data['error']['status'], 403)
        self.assertTrue(response.data['request_id'])

    def test_admin_can_access_other_teacher_topology(self):
        admin = User.objects.create_superuser(
            id=1,
            username='admin',
            password='Admin123456',
            real_name='系统管理员',
        )
        other_user = User.objects.create_user(
            id=100083,
            username='100083',
            password='teacher123456',
            real_name='被查看教师',
        )
        paper = Paper.objects.create(
            teacher=other_user,
            title='管理员查看的图谱论文',
            abstract='围绕管理员查看指定教师学术图谱的权限边界进行验证。',
            date_acquired='2026-03-02',
            doi='10.1234/admin-graph-view',
            paper_type='JOURNAL',
            journal_name='教育信息化研究',
            status='APPROVED',
        )
        CoAuthor.objects.create(paper=paper, name='协作作者', is_internal=True)

        self.client.force_authenticate(admin)
        response = self.client.get(f'/api/graph/topology/{other_user.id}/')

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['meta']['source'], 'mysql')
        self.assertTrue(any(node.get('name') == paper.title for node in response.data['nodes']))

    @patch('graph_engine.signals.threading.Thread')
    def test_paper_save_signal_does_not_start_full_sync_by_default(self, thread_cls):
        Paper.objects.create(
            teacher=self.user,
            title='默认关闭信号同步的论文',
            abstract='围绕图谱同步链路收口进行验证，确认默认不会触发全量 Neo4j 重建。',
            date_acquired='2026-03-02',
            doi='10.1234/graph-signal-disabled',
            paper_type='JOURNAL',
            journal_name='教育信息化研究',
        )

        thread_cls.assert_not_called()
