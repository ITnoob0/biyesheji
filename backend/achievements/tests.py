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

    @patch('achievements.views.AcademicGraphSyncService')
    @patch('achievements.views.AcademicAI')
    def test_paper_flow_keeps_working_with_keywords_and_coauthors(self, academic_ai_cls, graph_sync_service):
        academic_ai_cls.return_value.extract_tags.return_value = ['教师画像', '智能辅助']

        payload = {
            'title': '高校教师科研画像平台设计',
            'abstract': '本文围绕高校教师科研画像平台的多源数据治理、成果录入与智能辅助机制展开研究。',
            'date_acquired': '2025-03-05',
            'paper_type': 'JOURNAL',
            'journal_name': '现代教育技术',
            'journal_level': '核心期刊',
            'published_volume': '18',
            'published_issue': '3',
            'pages': '22-30',
            'source_url': 'https://example.com/papers/teacher-100004-paper',
            'citation_count': 9,
            'is_first_author': True,
            'is_representative': True,
            'doi': '10.1000/teacher-100004-paper',
            'coauthors': ['李晨', '周倩'],
        }

        response = self.client.post('/api/achievements/papers/', payload, format='json')

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Paper.objects.count(), 1)
        self.assertEqual(response.data['teacher'], 100004)
        self.assertEqual(response.data['teacher_name'], '汪心蓝')
        self.assertEqual(response.data['published_volume'], '18')
        self.assertTrue(response.data['is_representative'])
        self.assertEqual(response.data['publication_year'], 2025)
        self.assertEqual(len(response.data['coauthor_details']), 2)
        self.assertEqual(response.data['keywords'], ['教师画像', '智能辅助'])
        graph_sync_service.sync_paper.assert_called_once()

    @patch('achievements.views.AcademicGraphSyncService')
    @patch('achievements.views.AcademicAI')
    def test_paper_list_is_still_isolated_by_current_teacher(self, academic_ai_cls, graph_sync_service):
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

    @patch('achievements.views.AcademicGraphSyncService')
    @patch('achievements.views.AcademicAI')
    def test_duplicate_doi_for_same_teacher_is_rejected(self, academic_ai_cls, graph_sync_service):
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

    @patch('achievements.views.AcademicGraphSyncService')
    @patch('achievements.views.AcademicAI')
    def test_teacher_cannot_update_or_delete_other_teachers_paper(self, academic_ai_cls, graph_sync_service):
        academic_ai_cls.return_value.extract_tags.return_value = []

        other_paper = Paper.objects.create(
            teacher=self.other_user,
            title='其他教师的论文',
            abstract='这是一个足够长的摘要，用来验证当前教师无法编辑或删除其他账号的论文记录。',
            date_acquired='2024-01-02',
            paper_type='JOURNAL',
            journal_name='测试期刊',
            doi='10.1000/other-user-paper',
        )

        update_response = self.client.patch(
            f'/api/achievements/papers/{other_paper.id}/',
            {
                'title': '越权修改',
                'abstract': '这是一个足够长的摘要，用来验证越权修改会被拒绝。',
                'date_acquired': '2024-02-02',
                'paper_type': 'JOURNAL',
                'journal_name': '测试期刊',
                'doi': '10.1000/other-user-paper',
                'coauthors': [],
            },
            format='json',
        )
        delete_response = self.client.delete(f'/api/achievements/papers/{other_paper.id}/')

        self.assertEqual(update_response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(delete_response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertTrue(Paper.objects.filter(id=other_paper.id).exists())

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

    def test_bibtex_preview_marks_title_journal_year_duplicate_even_without_doi(self):
        Paper.objects.create(
            teacher=self.user,
            title='同名论文',
            abstract='这是一个足够长的摘要，用于验证 BibTeX 预览会识别题目、期刊与年份的高度重复记录。',
            date_acquired='2024-01-01',
            paper_type='JOURNAL',
            journal_name='现代教育技术',
        )

        bibtex_content = """
@article{similar-entry,
  title = {同名论文},
  author = {汪心蓝 and 李晨},
  journal = {现代教育技术},
  year = {2024},
  abstract = {围绕重复录入提示进行测试。}
}
"""

        upload = SimpleUploadedFile('papers.bib', bibtex_content.encode('utf-8'), content_type='text/plain')
        response = self.client.post('/api/achievements/papers/import/bibtex-preview/', {'file': upload})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['entries'][0]['preview_status'], 'duplicate')
        self.assertTrue(any('高度重复' in issue for issue in response.data['entries'][0]['issues']))

    def test_bibtex_preview_marks_batch_duplicate_doi_entries(self):
        bibtex_content = """
@article{first-entry,
  title = {批次重复 DOI 论文一},
  author = {汪心蓝 and 李晨},
  journal = {现代教育技术},
  year = {2025},
  doi = {10.1000/batch-duplicate-doi},
  abstract = {用于验证批次内 DOI 重复提示。}
}

@article{second-entry,
  title = {批次重复 DOI 论文二},
  author = {汪心蓝 and 周倩},
  journal = {中国电化教育},
  year = {2025},
  doi = {10.1000/batch-duplicate-doi},
  abstract = {用于验证批次内 DOI 重复提示。}
}
"""

        upload = SimpleUploadedFile('batch-duplicate.bib', bibtex_content.encode('utf-8'), content_type='text/plain')
        response = self.client.post('/api/achievements/papers/import/bibtex-preview/', {'file': upload})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['summary']['duplicate_count'], 1)
        self.assertEqual(response.data['entries'][0]['preview_status'], 'ready')
        self.assertEqual(response.data['entries'][1]['preview_status'], 'duplicate')
        self.assertTrue(any('当前批次中存在重复 DOI' in issue for issue in response.data['entries'][1]['issues']))

    @patch('achievements.views.AcademicGraphSyncService')
    @patch('achievements.views.AcademicAI')
    def test_bibtex_confirm_import_reuses_existing_paper_write_flow(self, academic_ai_cls, graph_sync_service):
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
        graph_sync_service.sync_paper.assert_called_once()

    @patch('achievements.views.AcademicGraphSyncService')
    @patch('achievements.views.AcademicAI')
    def test_bibtex_confirm_skips_duplicate_doi_entries_instead_of_importing(self, academic_ai_cls, graph_sync_service):
        academic_ai_cls.return_value.extract_tags.return_value = ['BibTeX 导入']

        Paper.objects.create(
            teacher=self.user,
            title='已有 DOI 论文',
            abstract='这是一个足够长的摘要，用于验证确认导入时会跳过重复 DOI。',
            date_acquired='2024-01-01',
            paper_type='JOURNAL',
            journal_name='测试期刊',
            doi='10.1000/existing-confirm-doi',
        )

        response = self.client.post(
            '/api/achievements/papers/import/bibtex-confirm/',
            {
                'entries': [
                    {
                        'source_index': 1,
                        'citation_key': 'duplicate-entry',
                        'entry_type': 'article',
                        'title': '重复 DOI 导入论文',
                        'abstract': '这是一个足够长的摘要，用于验证确认导入时会跳过重复 DOI。',
                        'date_acquired': '2025-05-01',
                        'paper_type': 'JOURNAL',
                        'journal_name': '现代教育技术',
                        'journal_level': '核心期刊',
                        'citation_count': 3,
                        'is_first_author': True,
                        'doi': '10.1000/existing-confirm-doi',
                        'coauthors': ['李晨'],
                        'preview_status': 'duplicate',
                        'issues': ['当前账号下已存在相同 DOI 的论文。'],
                    }
                ]
            },
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['imported_count'], 0)
        self.assertEqual(response.data['skipped_count'], 1)
        self.assertEqual(response.data['failed_count'], 0)
        self.assertIn('重复记录已跳过', response.data['skipped_entries'][0]['issue_summary'])
        self.assertEqual(Paper.objects.filter(teacher=self.user, doi='10.1000/existing-confirm-doi').count(), 1)
        graph_sync_service.sync_paper.assert_not_called()

    @patch('achievements.views.AcademicGraphSyncService')
    @patch('achievements.views.AcademicAI')
    def test_teacher_can_complete_full_achievement_entry_flow(self, academic_ai_cls, graph_sync_service):
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

        graph_sync_service.sync_paper.assert_called_once()
        graph_sync_service.sync_project.assert_called_once()
        graph_sync_service.sync_intellectual_property.assert_called_once()
        graph_sync_service.sync_teaching_achievement.assert_called_once()
        graph_sync_service.sync_academic_service.assert_called_once()

    @patch('achievements.views.AcademicGraphSyncService')
    def test_new_achievement_types_are_listed_for_current_teacher_only(self, graph_sync_service):
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

    @patch('achievements.views.AcademicGraphSyncService')
    def test_new_achievement_types_can_be_deleted_and_sync_graph_cleanup(self, graph_sync_service):
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

        graph_sync_service.delete_project.assert_called_once_with(project.id)
        graph_sync_service.delete_intellectual_property.assert_called_once_with(ip_record.id)
        graph_sync_service.delete_teaching_achievement.assert_called_once_with(teaching.id)
        graph_sync_service.delete_academic_service.assert_called_once_with(service.id)

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
        self.assertTrue(response.data['dimension_trend'])
        self.assertTrue(response.data['recent_structure'])
        self.assertIn('overview', response.data['portrait_explanation'])
        self.assertIn('snapshot_boundary_note', response.data['portrait_explanation'])
        self.assertTrue(any(item['key'] == 'academic_output' for item in response.data['dimension_insights']))
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
        self.assertEqual(len(response.data['dimension_insights']), 6)
        self.assertTrue(any(item['name'] == '经费与项目攻关' for item in response.data['dimension_sources']))
        self.assertTrue(any(item['level'] in ['优势维度', '稳定维度', '成长维度'] for item in response.data['dimension_insights']))

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

    def test_admin_can_list_papers_for_specified_teacher(self):
        user_model = get_user_model()
        admin = user_model.objects.create_superuser(
            id=1,
            username='admin',
            password='Admin123456',
            real_name='系统管理员',
        )
        Paper.objects.create(
            teacher=self.user,
            title='管理员查看的论文',
            abstract='这是一个足够长的摘要，用于验证管理员可以按教师过滤论文列表。',
            date_acquired='2025-04-01',
            paper_type='JOURNAL',
            journal_name='测试期刊',
        )
        Paper.objects.create(
            teacher=self.other_user,
            title='其他教师的论文',
            abstract='这是另一个足够长的摘要，用于验证 teacher_id 过滤只返回目标教师数据。',
            date_acquired='2025-04-02',
            paper_type='CONFERENCE',
            journal_name='测试会议',
        )

        self.client.force_authenticate(user=admin)
        response = self.client.get('/api/achievements/papers/', {'teacher_id': self.user.id})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['teacher'], self.user.id)
        self.assertEqual(response.data[0]['title'], '管理员查看的论文')

    @patch('achievements.views.AcademicGraphSyncService')
    @patch('achievements.views.AcademicAI')
    def test_admin_cannot_create_update_or_delete_teacher_paper_via_teacher_self_service_endpoint(
        self,
        academic_ai_cls,
        graph_sync_service,
    ):
        academic_ai_cls.return_value.extract_tags.return_value = []
        user_model = get_user_model()
        admin = user_model.objects.create_superuser(
            id=1,
            username='admin',
            password='Admin123456',
            real_name='系统管理员',
        )
        paper = Paper.objects.create(
            teacher=self.user,
            title='教师自助成果',
            abstract='这是一个足够长的摘要，用于验证管理员不能通过教师成果自助入口代替教师维护成果。',
            date_acquired='2025-01-01',
            paper_type='JOURNAL',
            journal_name='测试期刊',
            doi='10.1000/teacher-self-service-paper',
        )

        self.client.force_authenticate(user=admin)
        create_response = self.client.post(
            '/api/achievements/papers/',
            {
                'title': '管理员越权新增论文',
                'abstract': '这是一个足够长的摘要，用于验证管理员不能通过教师自助入口新增成果。',
                'date_acquired': '2025-02-01',
                'paper_type': 'JOURNAL',
                'journal_name': '测试期刊',
                'doi': '10.1000/admin-create-denied',
                'coauthors': [],
            },
            format='json',
        )
        update_response = self.client.patch(
            f'/api/achievements/papers/{paper.id}/',
            {
                'title': '管理员越权修改',
                'abstract': '这是一个足够长的摘要，用于验证管理员不能通过教师自助入口修改成果。',
                'date_acquired': '2025-01-03',
                'paper_type': 'JOURNAL',
                'journal_name': '测试期刊',
                'doi': '10.1000/teacher-self-service-paper',
                'coauthors': [],
            },
            format='json',
        )
        delete_response = self.client.delete(f'/api/achievements/papers/{paper.id}/')

        self.assertEqual(create_response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(update_response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(delete_response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(create_response.data['detail'], '成果录入和维护仅限教师本人操作，管理员当前仅可查看与验证。')
        self.assertTrue(Paper.objects.filter(id=paper.id).exists())
        self.assertEqual(Paper.objects.filter(doi='10.1000/admin-create-denied').count(), 0)
        graph_sync_service.sync_paper.assert_not_called()
        graph_sync_service.delete_paper.assert_not_called()

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
        self.assertIn('filter_options', response.data)
        self.assertIn('active_filters', response.data)
        self.assertIn('trend_summary', response.data)
        self.assertIn('comparison_summary', response.data)
        self.assertIn('realtime_metrics', response.data['data_meta'])
        self.assertIn('offline_candidate_metrics', response.data['data_meta'])

    @patch('achievements.views.AcademicGraphSyncService')
    @patch('achievements.views.AcademicAI')
    def test_teacher_can_search_and_update_paper_records(self, academic_ai_cls, graph_sync_service):
        academic_ai_cls.return_value.extract_tags.return_value = ['科研画像']

        paper = Paper.objects.create(
            teacher=self.user,
            title='待更新论文',
            abstract='这是一个足够长的摘要，用于验证论文编辑和搜索链路在第二轮开发后仍可正常使用。',
            date_acquired='2025-01-01',
            paper_type='JOURNAL',
            journal_name='教育技术研究',
            doi='10.1000/paper-edit-search',
        )
        Paper.objects.create(
            teacher=self.user,
            title='无关论文',
            abstract='这是另一个足够长的摘要，用于验证搜索结果会按关键词过滤。',
            date_acquired='2025-01-02',
            paper_type='CONFERENCE',
            journal_name='测试会议',
            doi='10.1000/paper-search-other',
        )

        update_response = self.client.patch(
            f'/api/achievements/papers/{paper.id}/',
            {
                'title': '已更新论文',
                'abstract': '这是一个足够长的摘要，用于验证论文编辑在当前教师名下可以正确更新。',
                'date_acquired': '2025-01-03',
                'paper_type': 'CONFERENCE',
                'journal_name': '教育技术论坛',
                'journal_level': 'CCF-C',
                'citation_count': 4,
                'is_first_author': False,
                'doi': '10.1000/paper-edit-search',
                'coauthors': ['李晨'],
            },
            format='json',
        )
        search_response = self.client.get('/api/achievements/papers/', {'search': '已更新'})

        self.assertEqual(update_response.status_code, status.HTTP_200_OK)
        paper.refresh_from_db()
        self.assertEqual(paper.title, '已更新论文')
        self.assertEqual(paper.paper_type, 'CONFERENCE')
        self.assertEqual(paper.coauthors.count(), 1)

        self.assertEqual(search_response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(search_response.data), 1)
        self.assertEqual(search_response.data[0]['title'], '已更新论文')

    def test_teacher_can_filter_sort_and_summarize_papers(self):
        Paper.objects.create(
            teacher=self.user,
            title='代表作论文',
            abstract='这是一个足够长的摘要，用于验证成果中心支持代表作筛选、统计和近年成果展示。',
            date_acquired='2026-02-01',
            paper_type='JOURNAL',
            journal_name='测试期刊 A',
            journal_level='SCI',
            pages='1-8',
            source_url='https://example.com/a',
            citation_count=12,
            is_representative=True,
            doi='10.1000/summary-a',
        )
        Paper.objects.create(
            teacher=self.user,
            title='普通论文',
            abstract='这是另一个足够长的摘要，用于验证按年份过滤和元数据缺失统计。',
            date_acquired='2024-05-10',
            paper_type='CONFERENCE',
            journal_name='测试会议 B',
            citation_count=2,
            doi='',
        )
        Paper.objects.create(
            teacher=self.user,
            title='高被引论文',
            abstract='这是第三个足够长的摘要，用于验证按引用次数排序。',
            date_acquired='2025-06-01',
            paper_type='JOURNAL',
            journal_name='测试期刊 C',
            journal_level='核心期刊',
            pages='33-40',
            source_url='https://example.com/c',
            citation_count=20,
            doi='10.1000/summary-c',
        )

        representative_response = self.client.get(
            '/api/achievements/papers/',
            {'is_representative': 'true', 'sort_by': 'citation_desc'},
        )
        yearly_response = self.client.get('/api/achievements/papers/', {'year': 2024})
        summary_response = self.client.get('/api/achievements/papers/summary/')

        self.assertEqual(representative_response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(representative_response.data), 1)
        self.assertEqual(representative_response.data[0]['title'], '代表作论文')

        self.assertEqual(yearly_response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(yearly_response.data), 1)
        self.assertEqual(yearly_response.data[0]['title'], '普通论文')

        self.assertEqual(summary_response.status_code, status.HTTP_200_OK)
        self.assertEqual(summary_response.data['total_count'], 3)
        self.assertEqual(summary_response.data['representative_count'], 1)
        self.assertEqual(summary_response.data['missing_doi_count'], 1)
        self.assertTrue(any(item['paper_type'] == 'JOURNAL' for item in summary_response.data['type_distribution']))
        self.assertTrue(any(item['year'] == 2026 for item in summary_response.data['yearly_distribution']))
        self.assertEqual(summary_response.data['recent_records'][0]['title'], '代表作论文')

    @patch('achievements.views.AcademicGraphSyncService')
    def test_teacher_can_search_projects_by_title_or_status(self, graph_sync_service):
        Project.objects.create(
            teacher=self.user,
            title='画像平台二期项目',
            date_acquired='2025-02-01',
            level='PROVINCIAL',
            role='PI',
            funding_amount='12.00',
            status='ONGOING',
        )
        Project.objects.create(
            teacher=self.user,
            title='已结题项目',
            date_acquired='2025-02-02',
            level='NATIONAL',
            role='CO_PI',
            funding_amount='18.00',
            status='COMPLETED',
        )

        response = self.client.get('/api/achievements/projects/', {'search': 'ONGOING'})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['title'], '画像平台二期项目')

    def test_admin_can_filter_academy_dashboard_by_department_and_year(self):
        user_model = get_user_model()
        admin = user_model.objects.create_superuser(
            id=1,
            username='admin',
            password='Admin123456',
            real_name='系统管理员',
        )
        teacher_in_scope = user_model.objects.create_user(
            id=100090,
            username='100090',
            password='teacher123456',
            real_name='院系内教师',
            department='人工智能学院',
            title='讲师',
        )
        teacher_out_scope = user_model.objects.create_user(
            id=100091,
            username='100091',
            password='teacher123456',
            real_name='院系外教师',
            department='计算机学院',
            title='讲师',
        )

        Paper.objects.create(
            teacher=teacher_in_scope,
            title='2025 年院系内论文',
            abstract='这是一个足够长的摘要，用于验证学院看板支持按院系和年份过滤。',
            date_acquired='2025-03-01',
            paper_type='JOURNAL',
            journal_name='测试期刊',
        )
        Paper.objects.create(
            teacher=teacher_out_scope,
            title='2024 年院系外论文',
            abstract='这是另一个足够长的摘要，用于验证过滤条件不会误包含其他教师数据。',
            date_acquired='2024-03-01',
            paper_type='JOURNAL',
            journal_name='测试期刊',
        )

        self.client.force_authenticate(user=admin)
        response = self.client.get(
            '/api/achievements/academy-overview/',
            {'department': '人工智能学院', 'year': 2025},
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['active_filters']['department'], '人工智能学院')
        self.assertEqual(response.data['active_filters']['year'], 2025)
        self.assertEqual(response.data['statistics'][1]['value'], 1)
        self.assertEqual(len(response.data['top_active_teachers']), 1)
        self.assertEqual(response.data['top_active_teachers'][0]['user_id'], teacher_in_scope.id)

    def test_academy_dashboard_includes_extended_filter_and_ranking_fields(self):
        user_model = get_user_model()
        admin = user_model.objects.create_superuser(
            id=2,
            username='admin2',
            password='Admin123456',
            real_name='系统管理员二号',
        )
        teacher = user_model.objects.create_user(
            id=100092,
            username='100092',
            password='teacher123456',
            real_name='合作教师',
            department='人工智能学院',
            title='副教授',
        )
        paper = Paper.objects.create(
            teacher=teacher,
            title='合作论文',
            abstract='这是一个足够长的摘要，用于验证学院看板扩展字段保持稳定返回。',
            date_acquired='2025-06-01',
            paper_type='JOURNAL',
            journal_name='测试期刊',
            citation_count=7,
        )
        paper.coauthors.create(name='校外合作者')

        self.client.force_authenticate(user=admin)
        response = self.client.get('/api/achievements/academy-overview/', {'teacher_title': '副教授', 'has_collaboration': 'true'})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['active_filters']['teacher_title'], '副教授')
        self.assertTrue(response.data['active_filters']['has_collaboration'])
        self.assertIn('teacher_titles', response.data['filter_options'])
        self.assertIn('department_breakdown', response.data)
        self.assertIn('latest_active_year', response.data['top_active_teachers'][0])
