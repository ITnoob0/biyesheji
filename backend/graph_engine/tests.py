from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import override_settings
from rest_framework.test import APITestCase

from achievements.models import CoAuthor, Paper, PaperKeyword, ResearchKeyword


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
        )
        CoAuthor.objects.create(paper=paper, name='校内合作者', is_internal=True)
        CoAuthor.objects.create(paper=paper, name='校外合作者', is_internal=False)
        keyword, _ = ResearchKeyword.objects.get_or_create(name='教师画像')
        PaperKeyword.objects.create(paper=paper, keyword=keyword)

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 200)
        self.assertIn('nodes', response.data)
        self.assertIn('links', response.data)
        self.assertIn('meta', response.data)

        meta = response.data['meta']
        self.assertEqual(meta['source'], 'mysql')
        self.assertTrue(meta['fallback_used'])
        self.assertGreaterEqual(meta['node_count'], 2)
        self.assertGreaterEqual(meta['link_count'], 1)

        self.assertTrue(any('nodeTypeLabel' in node for node in response.data['nodes']))
        self.assertTrue(any('detailLines' in node for node in response.data['nodes']))
        self.assertTrue(any(node.get('name') == '高校教师科研画像数据融合方法研究' for node in response.data['nodes']))

        self.assertTrue(any('relationLabel' in link for link in response.data['links']))
        self.assertTrue(any('description' in link for link in response.data['links']))
        self.assertIn('analysis', response.data)
        self.assertIn('highlight_cards', response.data['analysis'])
        self.assertIn('scope_note', response.data['analysis'])
        self.assertIn('collaboration_overview', response.data['analysis'])
        self.assertIn('collaborator_type_breakdown', response.data['analysis'])
        self.assertIn('theme_hotspots', response.data['analysis'])
        self.assertEqual(response.data['analysis']['collaborator_type_breakdown']['internal_count'], 1)
        self.assertEqual(response.data['analysis']['collaborator_type_breakdown']['external_count'], 1)
        self.assertEqual(response.data['analysis']['theme_hotspots']['top_keywords'][0]['name'], '教师画像')
        self.assertIn('analysis_level', response.data['meta'])
        self.assertIn('fallback_tip', response.data['meta'])

    def test_empty_relational_topology_keeps_compatible_response_shape(self):
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['nodes'], [])
        self.assertEqual(response.data['links'], [])
        self.assertIn('meta', response.data)
        self.assertEqual(response.data['meta']['source'], 'mysql')
        self.assertTrue(response.data['meta']['fallback_used'])
        self.assertIn('notice', response.data['meta'])
        self.assertIn('fallback_tip', response.data['meta'])
        self.assertEqual(response.data['analysis']['collaboration_overview']['paper_count'], 0)
        self.assertEqual(response.data['analysis']['theme_hotspots']['top_keywords'], [])

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
        )
        CoAuthor.objects.create(paper=paper, name='回退合作者', is_internal=False)

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['meta']['source'], 'mysql')
        self.assertTrue(response.data['meta']['fallback_used'])
        self.assertIn('MySQL', response.data['meta']['fallback_tip'])
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

    @patch('graph_engine.signals.threading.Thread')
    def test_paper_save_signal_does_not_start_full_sync_by_default(self, thread_cls):
        Paper.objects.create(
            teacher=self.user,
            title='默认关闭信号同步的论文',
            abstract='围绕第二轮图谱链路收口进行验证，确认默认不会触发全量 Neo4j 重建。',
            date_acquired='2026-03-02',
            doi='10.1234/graph-signal-disabled',
            paper_type='JOURNAL',
            journal_name='教育信息化研究',
        )

        thread_cls.assert_not_called()
