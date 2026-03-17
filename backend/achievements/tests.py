from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from rest_framework import status
from rest_framework.test import APITestCase

from .models import AcademicService, IntellectualProperty, Paper, Project, TeachingAchievement


class AchievementEntryApiTests(APITestCase):
    def setUp(self):
        user_model = get_user_model()
        self.user = user_model.objects.create_user(
            id=100004,
            username='100004',
            password='teacher123456',
            real_name='汪心蓝',
        )
        self.other_user = user_model.objects.create_user(
            id=100005,
            username='100005',
            password='teacher123456',
            real_name='测试教师',
        )
        self.client.force_authenticate(user=self.user)

    @patch('achievements.views.Neo4jEngine')
    @patch('achievements.views.AcademicAI')
    def test_paper_flow_keeps_working_with_keywords_and_coauthors(self, academic_ai_cls, neo4j_engine_cls):
        academic_ai_cls.return_value.extract_tags.return_value = ['教师画像', '智能辅助']

        payload = {
            'title': '高校教师科研画像平台设计',
            'abstract': '本文围绕高校教师科研画像平台的多源数据治理、成果录入与智能辅助机制展开研究。',
            'date_acquired': '2025-03-05',
            'paper_type': 'JOURNAL',
            'journal_name': '现代教育技术',
            'journal_level': '核心期刊',
            'citation_count': 9,
            'is_first_author': True,
            'doi': '10.1000/teacher-100004-paper',
            'coauthors': ['李晨', '周倩'],
        }

        response = self.client.post('/api/achievements/papers/', payload, format='json')

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Paper.objects.count(), 1)
        self.assertEqual(response.data['teacher'], 100004)
        self.assertEqual(response.data['teacher_name'], '汪心蓝')
        self.assertEqual(len(response.data['coauthor_details']), 2)
        self.assertEqual(response.data['keywords'], ['教师画像', '智能辅助'])
        neo4j_engine_cls.return_value.sync_paper_to_graph.assert_called_once()

    @patch('achievements.views.Neo4jEngine')
    @patch('achievements.views.AcademicAI')
    def test_paper_list_is_still_isolated_by_current_teacher(self, academic_ai_cls, neo4j_engine_cls):
        academic_ai_cls.return_value.extract_tags.return_value = []

        Paper.objects.create(
            teacher=self.user,
            title='我的论文',
            abstract='这是一个足够长的摘要，用来验证当前教师只能看到自己录入的论文数据。',
            date_acquired='2024-01-01',
            paper_type='JOURNAL',
            journal_name='测试期刊',
        )
        Paper.objects.create(
            teacher=self.other_user,
            title='其他教师的论文',
            abstract='这是另一个足够长的摘要，用来验证多账号场景下列表数据不会串到当前会话。',
            date_acquired='2024-01-02',
            paper_type='CONFERENCE',
            journal_name='测试会议',
        )

        response = self.client.get('/api/achievements/papers/')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['title'], '我的论文')
        self.assertEqual(response.data[0]['teacher'], 100004)

    @patch('achievements.views.Neo4jEngine')
    @patch('achievements.views.AcademicAI')
    def test_duplicate_doi_for_same_teacher_is_rejected(self, academic_ai_cls, neo4j_engine_cls):
        academic_ai_cls.return_value.extract_tags.return_value = []

        Paper.objects.create(
            teacher=self.user,
            title='已有论文',
            abstract='这是一个足够长的摘要，用来验证同一教师名下 DOI 重复时接口会正确拦截。',
            date_acquired='2024-01-01',
            paper_type='JOURNAL',
            journal_name='测试期刊',
            doi='10.1000/teacher-100004-duplicate',
        )

        payload = {
            'title': '重复 DOI 论文',
            'abstract': '这里是一段足够长的摘要，用来测试重复 DOI 校验是否对 100004 账号生效。',
            'date_acquired': '2025-03-05',
            'paper_type': 'JOURNAL',
            'journal_name': '现代教育技术',
            'doi': '10.1000/teacher-100004-duplicate',
            'coauthors': [],
        }

        response = self.client.post('/api/achievements/papers/', payload, format='json')

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('doi', response.data)

    def test_bibtex_preview_reports_ready_duplicate_and_invalid_entries(self):
        Paper.objects.create(
            teacher=self.user,
            title='已有 DOI 论文',
            abstract='这是一个足够长的摘要，用于验证 BibTeX 预览会识别当前教师下已经存在的 DOI。',
            date_acquired='2024-01-01',
            paper_type='JOURNAL',
            journal_name='测试期刊',
            doi='10.1000/existing-doi',
        )

        bibtex_content = """
@article{ready-entry,
  title = {BibTeX 可导入论文},
  author = {汪心蓝 and 李晨},
  journal = {现代教育技术},
  year = {2025},
  doi = {10.1000/new-doi},
  abstract = {围绕科研画像与成果中心联动展开研究。}
}

@article{duplicate-entry,
  title = {BibTeX 重复 DOI 论文},
  author = {汪心蓝 and 周倩},
  journal = {中国电化教育},
  year = {2024},
  doi = {10.1000/existing-doi}
}

@inproceedings{invalid-entry,
  author = {汪心蓝 and 吴楠},
  year = {2025}
}
"""

        upload = SimpleUploadedFile('papers.bib', bibtex_content.encode('utf-8'), content_type='text/plain')
        response = self.client.post('/api/achievements/papers/import/bibtex-preview/', {'file': upload})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['summary']['total_count'], 3)
        self.assertEqual(response.data['summary']['ready_count'], 1)
        self.assertEqual(response.data['summary']['duplicate_count'], 1)
        self.assertEqual(response.data['summary']['invalid_count'], 1)
        self.assertEqual(response.data['entries'][0]['preview_status'], 'ready')
        self.assertEqual(response.data['entries'][1]['preview_status'], 'duplicate')
        self.assertEqual(response.data['entries'][2]['preview_status'], 'invalid')
        self.assertEqual(response.data['entries'][0]['coauthors'], ['李晨'])

    @patch('achievements.views.Neo4jEngine')
    @patch('achievements.views.AcademicAI')
    def test_bibtex_confirm_import_reuses_existing_paper_write_flow(self, academic_ai_cls, neo4j_engine_cls):
        academic_ai_cls.return_value.extract_tags.return_value = ['BibTeX 导入', '画像联动']

        response = self.client.post(
            '/api/achievements/papers/import/bibtex-confirm/',
            {
                'entries': [
                    {
                        'source_index': 1,
                        'citation_key': 'imported-entry',
                        'entry_type': 'article',
                        'title': 'BibTeX 导入后的论文',
                        'abstract': '这是一个足够长的摘要，用于验证 BibTeX 确认导入仍然走现有论文写入链路。',
                        'date_acquired': '2025-05-01',
                        'paper_type': 'JOURNAL',
                        'journal_name': '现代教育技术',
                        'journal_level': '核心期刊',
                        'citation_count': 3,
                        'is_first_author': True,
                        'doi': '10.1000/imported-bibtex-paper',
                        'coauthors': ['李晨', '周倩'],
                        'preview_status': 'ready',
                        'issues': [],
                    },
                    {
                        'source_index': 2,
                        'citation_key': 'invalid-entry',
                        'entry_type': 'article',
                        'title': 'x',
                        'abstract': '',
                        'date_acquired': '2025-05-01',
                        'paper_type': 'JOURNAL',
                        'journal_name': '',
                        'journal_level': '',
                        'citation_count': 0,
                        'is_first_author': True,
                        'doi': '',
                        'coauthors': [],
                        'preview_status': 'invalid',
                        'issues': ['缺少期刊名称'],
                    },
                ]
            },
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['imported_count'], 1)
        self.assertEqual(response.data['failed_count'], 1)
        self.assertEqual(Paper.objects.filter(teacher=self.user, doi='10.1000/imported-bibtex-paper').count(), 1)

        imported_paper = Paper.objects.get(teacher=self.user, doi='10.1000/imported-bibtex-paper')
        self.assertEqual(imported_paper.coauthors.count(), 2)
        neo4j_engine_cls.return_value.sync_paper_to_graph.assert_called_once()

    @patch('achievements.views.Neo4jEngine')
    @patch('achievements.views.AcademicAI')
    def test_teacher_can_complete_full_achievement_entry_flow(self, academic_ai_cls, neo4j_engine_cls):
        academic_ai_cls.return_value.extract_tags.return_value = ['科研画像', '知识图谱']

        paper_response = self.client.post(
            '/api/achievements/papers/',
            {
                'title': '教师成果全链路治理研究',
                'abstract': '本文从成果录入、画像建模和图谱联动三个层面验证教师科研画像系统的可用性。',
                'date_acquired': '2025-04-01',
                'paper_type': 'JOURNAL',
                'journal_name': '软件导刊',
                'journal_level': '核心期刊',
                'citation_count': 5,
                'is_first_author': True,
                'doi': '10.1000/teacher-100004-full-flow',
                'coauthors': ['吴楠'],
            },
            format='json',
        )
        project_response = self.client.post(
            '/api/achievements/projects/',
            {
                'title': '教师科研画像关键技术研究',
                'date_acquired': '2025-01-10',
                'level': 'PROVINCIAL',
                'role': 'PI',
                'funding_amount': '25.00',
                'status': 'ONGOING',
            },
            format='json',
        )
        ip_response = self.client.post(
            '/api/achievements/intellectual-properties/',
            {
                'title': '教师画像分析系统',
                'date_acquired': '2025-02-11',
                'ip_type': 'SOFTWARE_COPYRIGHT',
                'registration_number': '2025SR100004',
                'is_transformed': False,
            },
            format='json',
        )
        teaching_response = self.client.post(
            '/api/achievements/teaching-achievements/',
            {
                'title': '数据智能课程教学改革',
                'date_acquired': '2025-03-01',
                'achievement_type': 'TEACHING_REFORM',
                'level': '校级',
            },
            format='json',
        )
        service_response = self.client.post(
            '/api/achievements/academic-services/',
            {
                'title': '人工智能论坛特邀报告',
                'date_acquired': '2025-03-03',
                'service_type': 'INVITED_TALK',
                'organization': '中国计算机学会',
            },
            format='json',
        )

        self.assertEqual(paper_response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(project_response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(ip_response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(teaching_response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(service_response.status_code, status.HTTP_201_CREATED)

        self.assertEqual(Paper.objects.filter(teacher_id=100004).count(), 1)
        self.assertEqual(Project.objects.filter(teacher_id=100004).count(), 1)
        self.assertEqual(IntellectualProperty.objects.filter(teacher_id=100004).count(), 1)
        self.assertEqual(TeachingAchievement.objects.filter(teacher_id=100004).count(), 1)
        self.assertEqual(AcademicService.objects.filter(teacher_id=100004).count(), 1)

        neo4j_engine_cls.return_value.sync_paper_to_graph.assert_called_once()
        neo4j_engine_cls.return_value.sync_project_to_graph.assert_called_once()
        neo4j_engine_cls.return_value.sync_intellectual_property_to_graph.assert_called_once()
        neo4j_engine_cls.return_value.sync_teaching_achievement_to_graph.assert_called_once()
        neo4j_engine_cls.return_value.sync_academic_service_to_graph.assert_called_once()

    @patch('achievements.views.Neo4jEngine')
    def test_new_achievement_types_are_listed_for_current_teacher_only(self, neo4j_engine_cls):
        project = Project.objects.create(
            teacher=self.user,
            title='项目 A',
            date_acquired='2025-01-10',
            level='PROVINCIAL',
            role='PI',
            funding_amount='25.00',
            status='ONGOING',
        )
        Project.objects.create(
            teacher=self.other_user,
            title='项目 B',
            date_acquired='2025-01-11',
            level='NATIONAL',
            role='CO_PI',
            funding_amount='10.00',
            status='ONGOING',
        )
        IntellectualProperty.objects.create(
            teacher=self.user,
            title='知识产权 A',
            date_acquired='2025-02-11',
            ip_type='SOFTWARE_COPYRIGHT',
            registration_number='IP-100004',
            is_transformed=True,
        )
        IntellectualProperty.objects.create(
            teacher=self.other_user,
            title='知识产权 B',
            date_acquired='2025-02-12',
            ip_type='PATENT_INVENTION',
            registration_number='IP-100005',
            is_transformed=False,
        )
        TeachingAchievement.objects.create(
            teacher=self.user,
            title='教学成果 A',
            date_acquired='2025-03-01',
            achievement_type='COURSE',
            level='省级',
        )
        TeachingAchievement.objects.create(
            teacher=self.other_user,
            title='教学成果 B',
            date_acquired='2025-03-02',
            achievement_type='COMPETITION',
            level='校级',
        )
        AcademicService.objects.create(
            teacher=self.user,
            title='学术服务 A',
            date_acquired='2025-03-03',
            service_type='EDITOR',
            organization='中国计算机学会',
        )
        AcademicService.objects.create(
            teacher=self.other_user,
            title='学术服务 B',
            date_acquired='2025-03-04',
            service_type='REVIEWER',
            organization='中国人工智能学会',
        )

        projects_response = self.client.get('/api/achievements/projects/')
        ips_response = self.client.get('/api/achievements/intellectual-properties/')
        teaching_response = self.client.get('/api/achievements/teaching-achievements/')
        services_response = self.client.get('/api/achievements/academic-services/')

        self.assertEqual(projects_response.status_code, status.HTTP_200_OK)
        self.assertEqual(ips_response.status_code, status.HTTP_200_OK)
        self.assertEqual(teaching_response.status_code, status.HTTP_200_OK)
        self.assertEqual(services_response.status_code, status.HTTP_200_OK)

        self.assertEqual([item['title'] for item in projects_response.data], [project.title])
        self.assertEqual([item['title'] for item in ips_response.data], ['知识产权 A'])
        self.assertEqual([item['title'] for item in teaching_response.data], ['教学成果 A'])
        self.assertEqual([item['title'] for item in services_response.data], ['学术服务 A'])

    @patch('achievements.views.Neo4jEngine')
    def test_new_achievement_types_can_be_deleted_and_sync_graph_cleanup(self, neo4j_engine_cls):
        project = Project.objects.create(
            teacher=self.user,
            title='待删除项目',
            date_acquired='2025-01-10',
            level='PROVINCIAL',
            role='PI',
            funding_amount='25.00',
            status='ONGOING',
        )
        ip_record = IntellectualProperty.objects.create(
            teacher=self.user,
            title='待删除知识产权',
            date_acquired='2025-02-11',
            ip_type='SOFTWARE_COPYRIGHT',
            registration_number='DEL-IP-100004',
            is_transformed=False,
        )
        teaching = TeachingAchievement.objects.create(
            teacher=self.user,
            title='待删除教学成果',
            date_acquired='2025-03-01',
            achievement_type='TEACHING_REFORM',
            level='校级',
        )
        service = AcademicService.objects.create(
            teacher=self.user,
            title='待删除学术服务',
            date_acquired='2025-03-03',
            service_type='INVITED_TALK',
            organization='中国计算机学会',
        )

        project_response = self.client.delete(f'/api/achievements/projects/{project.id}/')
        ip_response = self.client.delete(f'/api/achievements/intellectual-properties/{ip_record.id}/')
        teaching_response = self.client.delete(f'/api/achievements/teaching-achievements/{teaching.id}/')
        service_response = self.client.delete(f'/api/achievements/academic-services/{service.id}/')

        self.assertEqual(project_response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertEqual(ip_response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertEqual(teaching_response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertEqual(service_response.status_code, status.HTTP_204_NO_CONTENT)

        self.assertFalse(Project.objects.filter(id=project.id).exists())
        self.assertFalse(IntellectualProperty.objects.filter(id=ip_record.id).exists())
        self.assertFalse(TeachingAchievement.objects.filter(id=teaching.id).exists())
        self.assertFalse(AcademicService.objects.filter(id=service.id).exists())

        neo4j_engine_cls.return_value.delete_project_from_graph.assert_called_once_with(project.id)
        neo4j_engine_cls.return_value.delete_intellectual_property_from_graph.assert_called_once_with(ip_record.id)
        neo4j_engine_cls.return_value.delete_teaching_achievement_from_graph.assert_called_once_with(teaching.id)
        neo4j_engine_cls.return_value.delete_academic_service_from_graph.assert_called_once_with(service.id)

    def test_dashboard_stats_includes_multi_achievement_overview_and_recent_items(self):
        Paper.objects.create(
            teacher=self.user,
            title='画像论文',
            abstract='这是一个足够长的摘要，用于验证画像首页聚合不会只依赖单一论文卡片。',
            date_acquired='2025-04-01',
            paper_type='JOURNAL',
            journal_name='软件导刊',
            citation_count=6,
        )
        Project.objects.create(
            teacher=self.user,
            title='画像项目',
            date_acquired='2025-03-10',
            level='PROVINCIAL',
            role='PI',
            funding_amount='18.00',
            status='ONGOING',
        )
        IntellectualProperty.objects.create(
            teacher=self.user,
            title='画像知识产权',
            date_acquired='2025-03-12',
            ip_type='SOFTWARE_COPYRIGHT',
            registration_number='PORTRAIT-IP-001',
            is_transformed=True,
        )
        TeachingAchievement.objects.create(
            teacher=self.user,
            title='画像教学成果',
            date_acquired='2025-03-15',
            achievement_type='COURSE',
            level='省级',
        )
        AcademicService.objects.create(
            teacher=self.user,
            title='画像学术服务',
            date_acquired='2025-03-18',
            service_type='EDITOR',
            organization='中国计算机学会',
        )

        response = self.client.get('/api/achievements/dashboard-stats/')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['achievement_overview']['paper_count'], 1)
        self.assertEqual(response.data['achievement_overview']['project_count'], 1)
        self.assertEqual(response.data['achievement_overview']['intellectual_property_count'], 1)
        self.assertEqual(response.data['achievement_overview']['teaching_achievement_count'], 1)
        self.assertEqual(response.data['achievement_overview']['academic_service_count'], 1)
        self.assertEqual(response.data['achievement_overview']['total_achievements'], 5)
        self.assertTrue(any(item['type'] == 'project' for item in response.data['recent_achievements']))
        self.assertTrue(any(item['type'] == 'intellectual_property' for item in response.data['recent_achievements']))
        self.assertIn('source_note', response.data['data_meta'])
        self.assertEqual(response.data['data_meta']['acceptance_scope'], '本能力纳入当前阶段验收。')

    def test_radar_endpoint_returns_dimension_sources(self):
        Paper.objects.create(
            teacher=self.user,
            title='雷达论文',
            abstract='这是一个足够长的摘要，用于验证雷达能力维度来源说明接口返回结构。',
            date_acquired='2025-04-01',
            paper_type='JOURNAL',
            journal_name='测试期刊',
            citation_count=4,
        )
        Project.objects.create(
            teacher=self.user,
            title='雷达项目',
            date_acquired='2025-03-10',
            level='PROVINCIAL',
            role='PI',
            funding_amount='12.00',
            status='ONGOING',
        )

        response = self.client.get(f'/api/achievements/radar/{self.user.id}/')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['radar_dimensions']), 6)
        self.assertEqual(len(response.data['dimension_sources']), 6)
        self.assertTrue(any(item['name'] == '经费与项目攻关' for item in response.data['dimension_sources']))

    def test_admin_can_view_dashboard_stats_for_specified_teacher(self):
        user_model = get_user_model()
        admin = user_model.objects.create_superuser(
            id=1,
            username='admin',
            password='Admin123456',
            real_name='系统管理员',
        )
        Paper.objects.create(
            teacher=self.user,
            title='管理员视角论文',
            abstract='这是一个足够长的摘要，用于验证管理员查看指定教师画像时的聚合结果。',
            date_acquired='2025-04-01',
            paper_type='JOURNAL',
            journal_name='测试期刊',
            citation_count=3,
        )

        self.client.force_authenticate(user=admin)
        response = self.client.get('/api/achievements/dashboard-stats/', {'user_id': self.user.id})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['achievement_overview']['paper_count'], 1)
        self.assertEqual(response.data['achievement_overview']['total_achievements'], 1)

    def test_non_admin_cannot_access_academy_overview_dashboard(self):
        response = self.client.get('/api/achievements/academy-overview/')

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_admin_can_access_academy_overview_dashboard(self):
        user_model = get_user_model()
        admin = user_model.objects.create_superuser(
            id=1,
            username='admin',
            password='Admin123456',
            real_name='系统管理员',
        )

        Paper.objects.create(
            teacher=self.user,
            title='学院看板论文',
            abstract='这是一个足够长的摘要，用于验证学院级统计看板的论文聚合和趋势计算。',
            date_acquired='2025-04-01',
            paper_type='JOURNAL',
            journal_name='测试期刊',
            citation_count=3,
        )
        Project.objects.create(
            teacher=self.user,
            title='学院看板项目',
            date_acquired='2025-03-10',
            level='PROVINCIAL',
            role='PI',
            funding_amount='12.00',
            status='ONGOING',
        )

        self.client.force_authenticate(user=admin)
        response = self.client.get('/api/achievements/academy-overview/')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['statistics']), 5)
        self.assertTrue(response.data['yearly_trend'])
        self.assertTrue(response.data['department_distribution'])
        self.assertTrue(response.data['top_active_teachers'])
        self.assertIn('collaboration_overview', response.data)
        self.assertIn('data_meta', response.data)
