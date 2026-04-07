from unittest.mock import patch

from datetime import timedelta

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from .models import (
    AcademicService,
    AchievementClaim,
    IntellectualProperty,
    Paper,
    PaperOperationLog,
    Project,
    TeachingAchievement,
)


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
        graph_sync_service.sync_paper.assert_not_called()

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
        graph_sync_service.sync_paper.assert_not_called()

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

        graph_sync_service.sync_paper.assert_not_called()
        graph_sync_service.sync_project.assert_not_called()
        graph_sync_service.sync_intellectual_property.assert_not_called()
        graph_sync_service.sync_teaching_achievement.assert_not_called()
        graph_sync_service.sync_academic_service.assert_not_called()

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
            status='APPROVED',
        )
        Project.objects.create(
            teacher=self.user,
            title='画像项目',
            date_acquired='2025-03-10',
            level='PROVINCIAL',
            role='PI',
            funding_amount='18.00',
            project_status='ONGOING',
            status='APPROVED',
        )
        IntellectualProperty.objects.create(
            teacher=self.user,
            title='画像知识产权',
            date_acquired='2025-03-12',
            ip_type='SOFTWARE_COPYRIGHT',
            registration_number='PORTRAIT-IP-001',
            is_transformed=True,
            status='APPROVED',
        )
        TeachingAchievement.objects.create(
            teacher=self.user,
            title='画像教学成果',
            date_acquired='2025-03-15',
            achievement_type='COURSE',
            level='省级',
            status='APPROVED',
        )
        AcademicService.objects.create(
            teacher=self.user,
            title='画像学术服务',
            date_acquired='2025-03-18',
            service_type='EDITOR',
            organization='中国计算机学会',
            status='APPROVED',
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

    def test_all_achievements_endpoint_returns_representative_first_and_then_by_date(self):
        Paper.objects.create(
            teacher=self.user,
            title='代表作论文',
            abstract='用于验证全部成果接口的代表作排序。',
            date_acquired='2024-03-01',
            paper_type='JOURNAL',
            journal_name='测试期刊',
            citation_count=12,
            is_first_author=True,
            is_representative=True,
            status='APPROVED',
        )
        Paper.objects.create(
            teacher=self.user,
            title='普通论文',
            abstract='用于验证非代表作排序。',
            date_acquired='2025-01-15',
            paper_type='JOURNAL',
            journal_name='测试期刊',
            citation_count=3,
            is_first_author=False,
            is_representative=False,
            status='APPROVED',
        )
        Project.objects.create(
            teacher=self.user,
            title='科研项目A',
            date_acquired='2024-12-20',
            level='PROVINCIAL',
            role='PI',
            funding_amount='18.00',
            project_status='ONGOING',
            status='APPROVED',
        )

        response = self.client.get(f'/api/achievements/all-achievements/{self.user.id}/')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['teacher_id'], self.user.id)
        self.assertEqual(response.data['achievement_total'], 3)
        self.assertEqual(response.data['records'][0]['title'], '代表作论文')
        self.assertEqual(response.data['records'][0]['is_representative'], True)
        self.assertEqual(response.data['records'][1]['title'], '普通论文')
        self.assertEqual(response.data['records'][1]['author_rank_category'], 'participating')
        self.assertEqual(response.data['records'][2]['title'], '科研项目A')
        self.assertEqual(response.data['records'][2]['type_label'], '科研项目')

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
            status='APPROVED',
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
            status='APPROVED',
        )
        Project.objects.create(
            teacher=self.user,
            title='学院看板项目',
            date_acquired='2025-03-10',
            level='PROVINCIAL',
            role='PI',
            funding_amount='12.00',
            project_status='ONGOING',
            status='APPROVED',
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
            status='APPROVED',
        )
        Paper.objects.create(
            teacher=teacher_out_scope,
            title='2024 年院系外论文',
            abstract='这是另一个足够长的摘要，用于验证过滤条件不会误包含其他教师数据。',
            date_acquired='2024-03-01',
            paper_type='JOURNAL',
            journal_name='测试期刊',
            status='APPROVED',
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
            status='APPROVED',
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

    def test_academy_dashboard_supports_drilldown_rank_switch_and_comparison_trend(self):
        user_model = get_user_model()
        admin = user_model.objects.create_superuser(
            id=3,
            username='admin3',
            password='Admin123456',
            real_name='系统管理员三号',
        )
        teacher_a = user_model.objects.create_user(
            id=100093,
            username='100093',
            password='teacher123456',
            real_name='高被引教师',
            department='人工智能学院',
            title='教授',
        )
        teacher_b = user_model.objects.create_user(
            id=100094,
            username='100094',
            password='teacher123456',
            real_name='项目教师',
            department='人工智能学院',
            title='教授',
        )

        paper_a = Paper.objects.create(
            teacher=teacher_a,
            title='高被引论文',
            abstract='这是一个足够长的摘要，用于验证学院看板支持按引用排行和教师钻取。',
            date_acquired='2025-05-01',
            paper_type='JOURNAL',
            journal_name='测试期刊',
            citation_count=15,
            status='APPROVED',
        )
        paper_a.coauthors.create(name='合作作者甲')
        Paper.objects.create(
            teacher=teacher_a,
            title='上一年论文',
            abstract='这是另一个足够长的摘要，用于形成范围对比趋势。',
            date_acquired='2024-05-01',
            paper_type='JOURNAL',
            journal_name='测试期刊',
            citation_count=5,
            status='APPROVED',
        )
        Project.objects.create(
            teacher=teacher_b,
            title='重点项目',
            date_acquired='2025-06-01',
            level='PROVINCIAL',
            role='PI',
            funding_amount='20.00',
            project_status='ONGOING',
            status='APPROVED',
        )

        self.client.force_authenticate(user=admin)
        response = self.client.get(
            '/api/achievements/academy-overview/',
            {
                'department': '人工智能学院',
                'teacher_id': teacher_a.id,
                'teacher_title': '教授',
                'achievement_type': 'paper',
                'rank_by': 'citation_total',
                'has_collaboration': 'true',
            },
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['active_filters']['achievement_type'], 'paper')
        self.assertEqual(response.data['active_filters']['rank_by'], 'citation_total')
        self.assertTrue(response.data['active_filters']['has_collaboration'])
        self.assertIn('achievement_types', response.data['filter_options'])
        self.assertIn('ranking_modes', response.data['filter_options'])
        self.assertTrue(response.data['comparison_trend'])
        self.assertEqual(response.data['ranking_meta']['current_rank_by'], 'citation_total')
        self.assertEqual(response.data['top_active_teachers'][0]['rank_label'], '总被引')
        self.assertIn('selected_department_summary', response.data['drilldown'])
        self.assertIn('selected_teacher_summary', response.data['drilldown'])
        self.assertEqual(response.data['drilldown']['selected_teacher_summary']['user_id'], teacher_a.id)
        self.assertTrue(response.data['drilldown']['teacher_recent_achievements'])

    def test_academy_dashboard_export_returns_csv_for_selected_target(self):
        user_model = get_user_model()
        admin = user_model.objects.create_superuser(
            id=4,
            username='admin4',
            password='Admin123456',
            real_name='系统管理员四号',
        )
        teacher = user_model.objects.create_user(
            id=100095,
            username='100095',
            password='teacher123456',
            real_name='导出教师',
            department='人工智能学院',
            title='讲师',
        )
        Paper.objects.create(
            teacher=teacher,
            title='导出论文',
            abstract='这是一个足够长的摘要，用于验证学院级看板导出增强链路。',
            date_acquired='2025-07-01',
            paper_type='JOURNAL',
            journal_name='测试期刊',
            citation_count=2,
        )

        self.client.force_authenticate(user=admin)
        response = self.client.get(
            '/api/achievements/academy-overview/export/',
            {'department': '人工智能学院', 'export_target': 'departments'},
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('text/csv', response['Content-Type'])
        content = response.content.decode('utf-8')
        self.assertIn('院系', content)
        self.assertIn('人工智能学院', content)


class PaperGovernanceApiTests(APITestCase):
    def setUp(self):
        user_model = get_user_model()
        self.user = user_model.objects.create_user(
            id=100120,
            username='100120',
            password='teacher123456',
            real_name='成果治理教师',
        )
        self.client.force_authenticate(user=self.user)

    def test_bibtex_revalidate_supports_fix_after_preview(self):
        invalid_payload = {
            'entries': [
                {
                    'source_index': 1,
                    'citation_key': 'draft-entry',
                    'entry_type': 'article',
                    'title': '',
                    'abstract': '',
                    'date_acquired': '',
                    'paper_type': 'JOURNAL',
                    'journal_name': '',
                    'journal_level': '',
                    'published_volume': '',
                    'published_issue': '',
                    'pages': '',
                    'source_url': '',
                    'citation_count': 0,
                    'is_first_author': True,
                    'is_representative': False,
                    'doi': '',
                    'coauthors': [],
                    'preview_status': 'invalid',
                    'issues': [],
                    'issue_details': [],
                }
            ]
        }
        invalid_response = self.client.post('/api/achievements/papers/import/bibtex-revalidate/', invalid_payload, format='json')
        self.assertEqual(invalid_response.status_code, status.HTTP_200_OK)
        self.assertEqual(invalid_response.data['summary']['invalid_count'], 1)

        fixed_payload = invalid_payload.copy()
        fixed_payload['entries'] = [
            {
                **invalid_payload['entries'][0],
                'title': 'BibTeX 修订后的论文',
                'journal_name': '测试期刊',
                'date_acquired': '2025-04-01',
                'doi': '10.1000/bibtex-revalidate',
            }
        ]
        fixed_response = self.client.post('/api/achievements/papers/import/bibtex-revalidate/', fixed_payload, format='json')
        self.assertEqual(fixed_response.status_code, status.HTTP_200_OK)
        self.assertEqual(fixed_response.data['summary']['ready_count'], 1)
        self.assertEqual(fixed_response.data['entries'][0]['preview_status'], 'ready')

    @patch('achievements.views.AcademicGraphSyncService')
    @patch('achievements.views.AcademicAI')
    def test_paper_history_governance_and_compare_endpoints_work(self, academic_ai_cls, graph_sync_service):
        academic_ai_cls.return_value.extract_tags.return_value = ['成果治理', '操作历史']

        create_response = self.client.post(
            '/api/achievements/papers/',
            {
                'title': '治理主论文',
                'abstract': '用于验证治理中心下的历史记录、元数据告警与结构化对比接口。',
                'date_acquired': '2025-04-01',
                'paper_type': 'JOURNAL',
                'journal_name': '治理期刊',
                'citation_count': 5,
                'doi': '10.1000/governance-main',
                'coauthors': ['李晨'],
            },
            format='json',
        )
        second_paper = Paper.objects.create(
            teacher=self.user,
            title='治理对比论文',
            abstract='用于对比的第二篇论文，补齐了更多治理字段。',
            date_acquired='2025-05-01',
            paper_type='CONFERENCE',
            journal_name='治理会议',
            journal_level='CCF-B',
            pages='10-18',
            source_url='https://example.com/governance-compare',
            citation_count=11,
            doi='10.1000/governance-compare',
        )

        paper_id = create_response.data['id']
        update_response = self.client.patch(
            f'/api/achievements/papers/{paper_id}/',
            {
                'title': '治理主论文（修订版）',
                'abstract': '用于验证治理中心下的历史记录、元数据告警与结构化对比接口，已补充修订说明。',
                'date_acquired': '2025-04-02',
                'paper_type': 'JOURNAL',
                'journal_name': '治理期刊',
                'journal_level': '',
                'citation_count': 6,
                'doi': '10.1000/governance-main',
                'coauthors': ['李晨', '王敏'],
            },
            format='json',
        )
        self.assertEqual(update_response.status_code, status.HTTP_200_OK)

        history_response = self.client.get(f'/api/achievements/papers/{paper_id}/history/')
        governance_response = self.client.get('/api/achievements/papers/governance/')
        compare_response = self.client.get(
            '/api/achievements/papers/compare/',
            {'left_id': paper_id, 'right_id': second_paper.id},
        )

        self.assertEqual(history_response.status_code, status.HTTP_200_OK)
        self.assertGreaterEqual(len(history_response.data['history']), 2)
        self.assertEqual(history_response.data['history'][0]['action'], 'UPDATE')
        self.assertEqual(history_response.data['history'][1]['action'], 'CREATE')

        self.assertEqual(governance_response.status_code, status.HTTP_200_OK)
        self.assertIn('summary', governance_response.data)
        self.assertIn('recent_operations', governance_response.data)
        self.assertTrue(governance_response.data['compare_candidates'])

        self.assertEqual(compare_response.status_code, status.HTTP_200_OK)
        self.assertIn('comparison_rows', compare_response.data)
        self.assertIn('summary', compare_response.data)
        self.assertEqual(compare_response.data['summary']['shared_coauthors'], [])
        graph_sync_service.sync_paper.assert_not_called()

    @patch('achievements.views.AcademicGraphSyncService')
    def test_export_representative_batch_and_cleanup_apply_work(self, graph_sync_service):
        paper_a = Paper.objects.create(
            teacher=self.user,
            title='待清洗论文 A',
            abstract='用于验证批量标准化清洗与导出治理结果的论文记录。',
            date_acquired='2025-01-10',
            paper_type='JOURNAL',
            journal_name='导出期刊',
            doi=' 10.1000/NEEDS-CLEANUP ',
            source_url=' https://example.com/a ',
            pages=' 1-9 ',
        )
        paper_b = Paper.objects.create(
            teacher=self.user,
            title='待运营论文 B',
            abstract='用于验证代表作批量运营与治理日志生成。',
            date_acquired='2025-02-10',
            paper_type='JOURNAL',
            journal_name='导出期刊',
            doi='10.1000/b',
        )

        representative_response = self.client.post(
            '/api/achievements/papers/representative/batch-update/',
            {'paper_ids': [paper_a.id, paper_b.id], 'is_representative': True},
            format='json',
        )
        cleanup_response = self.client.post(
            '/api/achievements/papers/cleanup-apply/',
            {'paper_ids': [paper_a.id], 'action': 'normalize_text_fields'},
            format='json',
        )
        export_response = self.client.get('/api/achievements/papers/export/')

        self.assertEqual(representative_response.status_code, status.HTTP_200_OK)
        self.assertEqual(representative_response.data['updated_count'], 2)
        self.assertEqual(cleanup_response.status_code, status.HTTP_200_OK)
        self.assertEqual(cleanup_response.data['updated_count'], 1)

        paper_a.refresh_from_db()
        paper_b.refresh_from_db()
        self.assertTrue(paper_a.is_representative)
        self.assertTrue(paper_b.is_representative)
        self.assertEqual(paper_a.doi, '10.1000/needs-cleanup')
        self.assertEqual(paper_a.source_url, 'https://example.com/a')
        self.assertEqual(paper_a.pages, '1-9')

        self.assertEqual(export_response.status_code, status.HTTP_200_OK)
        self.assertIn('text/csv', export_response['Content-Type'])
        self.assertIn('标题', export_response.content.decode('utf-8'))
        self.assertGreaterEqual(PaperOperationLog.objects.filter(teacher=self.user).count(), 3)


class TeacherPortraitApiTests(APITestCase):
    def setUp(self):
        user_model = get_user_model()
        self.user = user_model.objects.create_user(
            id=100140,
            username='100140',
            password='teacher123456',
            real_name='画像深化教师',
            department='人工智能学院',
            title='副教授',
        )
        self.client.force_authenticate(user=self.user)

        paper_a = Paper.objects.create(
            teacher=self.user,
            title='2024 阶段论文',
            abstract='这是一个足够长的摘要，用于验证教师画像阶段对比能力和结构化解释字段。',
            date_acquired='2024-04-01',
            paper_type='JOURNAL',
            journal_name='画像期刊',
            citation_count=4,
            doi='10.1000/portrait-2024',
        )
        paper_a.coauthors.create(name='阶段合作者甲')
        paper_b = Paper.objects.create(
            teacher=self.user,
            title='2025 阶段论文',
            abstract='这是另一个足够长的摘要，用于验证教师画像报告导出和趋势承接能力。',
            date_acquired='2025-05-01',
            paper_type='CONFERENCE',
            journal_name='画像会议',
            citation_count=11,
            doi='10.1000/portrait-2025',
        )
        paper_b.coauthors.create(name='阶段合作者乙')

        Project.objects.create(
            teacher=self.user,
            title='画像阶段项目',
            date_acquired='2025-03-01',
            level='PROVINCIAL',
            role='PI',
            funding_amount='18.00',
            status='ONGOING',
        )
        IntellectualProperty.objects.create(
            teacher=self.user,
            title='画像分析软件',
            date_acquired='2025-02-10',
            ip_type='SOFTWARE_COPYRIGHT',
            registration_number='2025SR140000',
            is_transformed=True,
        )
        TeachingAchievement.objects.create(
            teacher=self.user,
            title='画像课程改革',
            date_acquired='2025-01-15',
            achievement_type='TEACHING_REFORM',
            level='校级',
        )
        AcademicService.objects.create(
            teacher=self.user,
            title='画像论坛报告',
            date_acquired='2024-06-15',
            service_type='INVITED_TALK',
            organization='中国计算机学会',
        )

    def test_dashboard_stats_includes_snapshot_boundary_and_stage_comparison(self):
        response = self.client.get('/api/achievements/dashboard-stats/')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('weight_spec', response.data)
        self.assertIn('calculation_summary', response.data)
        self.assertIn('stage_comparison', response.data)
        self.assertIn('snapshot_boundary', response.data)
        self.assertTrue(response.data['stage_comparison']['available'])
        self.assertEqual(response.data['snapshot_boundary']['persistence_status'], 'not_persisted')
        self.assertEqual(response.data['snapshot_boundary']['snapshot_version'], 'portrait-runtime-v1')
        self.assertEqual(response.data['snapshot_boundary']['generation_trigger'], 'dashboard_request')
        self.assertEqual(response.data['snapshot_boundary']['freeze_status'], 'response_scoped')
        self.assertTrue(response.data['stage_comparison']['structured_summary'])
        self.assertTrue(response.data['stage_comparison']['changed_dimensions'][0]['change_summary'])
        self.assertTrue(response.data['stage_comparison']['changed_dimensions'][0]['drivers'])
        self.assertIn('weight_logic_summary', response.data['portrait_explanation'])
        self.assertIn('snapshot_version_note', response.data['portrait_explanation'])

    def test_radar_endpoint_includes_weight_spec_and_calculation_summary(self):
        response = self.client.get(f'/api/achievements/radar/{self.user.id}/')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['weight_spec']), 6)
        self.assertIn('formula_note', response.data['calculation_summary'])
        self.assertIn('strongest_dimension', response.data['calculation_summary'])

    def test_portrait_report_supports_json_and_markdown_export(self):
        json_response = self.client.get(f'/api/achievements/portrait-report/{self.user.id}/')
        markdown_response = self.client.get(
            f'/api/achievements/portrait-report/{self.user.id}/',
            {'export': 'markdown'},
        )

        self.assertEqual(json_response.status_code, status.HTTP_200_OK)
        self.assertIn('report_title', json_response.data)
        self.assertTrue(json_response.data['highlights'])
        self.assertTrue(json_response.data['sections'])
        self.assertIn('snapshot_boundary', json_response.data)
        self.assertIn('snapshot_digest', json_response.data)
        self.assertEqual(json_response.data['snapshot_boundary']['generation_trigger'], 'report_request')
        self.assertEqual(json_response.data['snapshot_digest']['version'], 'portrait-runtime-v1')

        self.assertEqual(markdown_response.status_code, status.HTTP_200_OK)
        self.assertIn('text/markdown', markdown_response['Content-Type'])
        self.assertIn('教师画像分析报告', markdown_response.content.decode('utf-8'))
        self.assertIn('快照摘要', markdown_response.content.decode('utf-8'))
        self.assertIn('变化说明', markdown_response.content.decode('utf-8'))


class AchievementReviewFlowApiTests(APITestCase):
    def setUp(self):
        user_model = get_user_model()
        self.system_admin = user_model.objects.create_superuser(
            id=901001,
            username='sysadmin-review',
            password='Admin123456',
            real_name='系统管理员审批',
            department='科研管理中心',
        )
        self.college_admin = user_model.objects.create_user(
            id=901002,
            username='college-admin-review',
            password='Admin123456',
            real_name='学院管理员审批',
            department='人工智能学院',
            title='学院管理员',
            is_staff=True,
        )
        self.teacher = user_model.objects.create_user(
            id=901003,
            username='901003',
            password='teacher123456',
            real_name='本院教师',
            department='人工智能学院',
            title='讲师',
        )
        self.other_teacher = user_model.objects.create_user(
            id=901004,
            username='901004',
            password='teacher123456',
            real_name='外院教师',
            department='计算机学院',
            title='讲师',
        )

    def create_paper(self, teacher, title='待审核论文', status='DRAFT'):
        return Paper.objects.create(
            teacher=teacher,
            title=title,
            abstract='这是一个足够长的摘要，用于验证成果审批流与版本管理功能。',
            date_acquired='2025-05-01',
            paper_type='JOURNAL',
            journal_name='审批测试期刊',
            status=status,
        )

    def create_project(self, teacher, title='待审核项目', status='DRAFT'):
        return Project.objects.create(
            teacher=teacher,
            title=title,
            date_acquired='2025-05-02',
            level='PROVINCIAL',
            role='PI',
            funding_amount='10.00',
            project_status='ONGOING',
            status=status,
        )

    def create_ip(self, teacher, title='待审核知识产权', status='DRAFT'):
        return IntellectualProperty.objects.create(
            teacher=teacher,
            title=title,
            date_acquired='2025-05-03',
            ip_type='SOFTWARE_COPYRIGHT',
            registration_number=f'IP-{teacher.id}-{title}',
            is_transformed=False,
            status=status,
        )

    def create_teaching(self, teacher, title='待审核教学成果', status='DRAFT'):
        return TeachingAchievement.objects.create(
            teacher=teacher,
            title=title,
            date_acquired='2025-05-04',
            achievement_type='COURSE',
            level='校级',
            status=status,
        )

    def create_service(self, teacher, title='待审核学术服务', status='DRAFT'):
        return AcademicService.objects.create(
            teacher=teacher,
            title=title,
            date_acquired='2025-05-05',
            service_type='INVITED_TALK',
            organization='测试机构',
            status=status,
        )

    def test_teacher_can_submit_paper_for_review(self):
        paper = self.create_paper(self.teacher)
        self.client.force_authenticate(user=self.teacher)

        response = self.client.post(f'/api/achievements/papers/{paper.id}/submit-review/', format='json')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        paper.refresh_from_db()
        self.assertEqual(paper.status, 'PENDING_REVIEW')

    def test_teacher_create_all_achievement_types_defaults_to_pending_review(self):
        self.client.force_authenticate(user=self.teacher)

        responses = [
            self.client.post(
                '/api/achievements/papers/',
                {
                    'title': '待审论文',
                    'abstract': '这是一个足够长的摘要，用于验证首轮提交自动进入待审核。',
                    'date_acquired': '2025-06-01',
                    'paper_type': 'JOURNAL',
                    'journal_name': '测试期刊',
                    'coauthors': [],
                },
                format='json',
            ),
            self.client.post(
                '/api/achievements/projects/',
                {
                    'title': '待审项目',
                    'date_acquired': '2025-06-02',
                    'level': 'PROVINCIAL',
                    'role': 'PI',
                    'funding_amount': '10.00',
                    'project_status': 'ONGOING',
                },
                format='json',
            ),
            self.client.post(
                '/api/achievements/intellectual-properties/',
                {
                    'title': '待审知识产权',
                    'date_acquired': '2025-06-03',
                    'ip_type': 'SOFTWARE_COPYRIGHT',
                    'registration_number': 'IP-PENDING-001',
                    'is_transformed': False,
                },
                format='json',
            ),
            self.client.post(
                '/api/achievements/teaching-achievements/',
                {
                    'title': '待审教学成果',
                    'date_acquired': '2025-06-04',
                    'achievement_type': 'COURSE',
                    'level': '校级',
                },
                format='json',
            ),
            self.client.post(
                '/api/achievements/academic-services/',
                {
                    'title': '待审学术服务',
                    'date_acquired': '2025-06-05',
                    'service_type': 'INVITED_TALK',
                    'organization': '测试机构',
                },
                format='json',
            ),
        ]

        for response in responses:
            self.assertEqual(response.status_code, status.HTTP_201_CREATED)
            self.assertEqual(response.data['status'], 'PENDING_REVIEW')

    def test_admin_without_teacher_id_can_list_scoped_teacher_achievements(self):
        own_college_project = self.create_project(self.teacher, title='本院项目', status='PENDING_REVIEW')
        self.create_project(self.other_teacher, title='外院项目', status='PENDING_REVIEW')

        self.client.force_authenticate(user=self.college_admin)
        college_response = self.client.get('/api/achievements/projects/')
        self.assertEqual(college_response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(college_response.data), 1)
        self.assertEqual(college_response.data[0]['id'], own_college_project.id)

        self.client.force_authenticate(user=self.system_admin)
        system_response = self.client.get('/api/achievements/projects/')
        self.assertEqual(system_response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(system_response.data), 2)

    def test_college_admin_only_sees_pending_papers_in_own_college(self):
        self.create_paper(self.teacher, title='本院待审核', status='PENDING_REVIEW')
        self.create_paper(self.other_teacher, title='外院待审核', status='PENDING_REVIEW')
        self.client.force_authenticate(user=self.college_admin)

        response = self.client.get('/api/achievements/papers/pending-review/')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['title'], '本院待审核')

    def test_reject_requires_reason_and_logs_comment(self):
        paper = self.create_paper(self.teacher, status='PENDING_REVIEW')
        self.client.force_authenticate(user=self.college_admin)

        invalid_response = self.client.post(f'/api/achievements/papers/{paper.id}/reject/', {}, format='json')
        valid_response = self.client.post(
            f'/api/achievements/papers/{paper.id}/reject/',
            {'reason': '期刊级别与附件证明不一致，请补充说明。'},
            format='json',
        )

        self.assertEqual(invalid_response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(valid_response.status_code, status.HTTP_200_OK)
        paper.refresh_from_db()
        self.assertEqual(paper.status, 'REJECTED')

    def test_teacher_editing_approved_paper_resets_status_to_pending_review(self):
        paper = self.create_paper(self.teacher, status='APPROVED')
        self.client.force_authenticate(user=self.teacher)

        response = self.client.patch(
            f'/api/achievements/papers/{paper.id}/',
            {
                'title': '已通过论文（修订版）',
                'abstract': paper.abstract,
                'date_acquired': '2025-05-01',
                'paper_type': 'JOURNAL',
                'journal_name': '审批测试期刊',
                'coauthors': [],
            },
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        paper.refresh_from_db()
        self.assertEqual(paper.status, 'PENDING_REVIEW')

    def test_college_admin_can_view_pending_review_for_all_achievement_types(self):
        self.create_paper(self.teacher, title='本院待审核论文', status='PENDING_REVIEW')
        self.create_project(self.teacher, title='本院待审核项目', status='PENDING_REVIEW')
        self.create_ip(self.teacher, title='本院待审核知识产权', status='PENDING_REVIEW')
        self.create_teaching(self.teacher, title='本院待审核教学成果', status='PENDING_REVIEW')
        self.create_service(self.teacher, title='本院待审核学术服务', status='PENDING_REVIEW')

        self.create_project(self.other_teacher, title='外院待审核项目', status='PENDING_REVIEW')
        self.create_ip(self.other_teacher, title='外院待审核知识产权', status='PENDING_REVIEW')

        endpoint_map = {
            'papers': '/api/achievements/papers/pending-review/',
            'projects': '/api/achievements/projects/pending-review/',
            'intellectual_properties': '/api/achievements/intellectual-properties/pending-review/',
            'teaching_achievements': '/api/achievements/teaching-achievements/pending-review/',
            'academic_services': '/api/achievements/academic-services/pending-review/',
        }

        self.client.force_authenticate(user=self.college_admin)
        results = {key: self.client.get(url) for key, url in endpoint_map.items()}

        for key, response in results.items():
            self.assertEqual(response.status_code, status.HTTP_200_OK, msg=f'{key} pending-review 接口未返回 200')
            self.assertEqual(len(response.data), 1, msg=f'{key} 未按学院范围过滤待审核列表')

        self.assertEqual(results['papers'].data[0]['title'], '本院待审核论文')
        self.assertEqual(results['projects'].data[0]['title'], '本院待审核项目')
        self.assertEqual(results['intellectual_properties'].data[0]['title'], '本院待审核知识产权')
        self.assertEqual(results['teaching_achievements'].data[0]['title'], '本院待审核教学成果')
        self.assertEqual(results['academic_services'].data[0]['title'], '本院待审核学术服务')

    def test_college_admin_can_approve_non_paper_achievements(self):
        project = self.create_project(self.teacher, status='PENDING_REVIEW')
        ip_record = self.create_ip(self.teacher, status='PENDING_REVIEW')
        teaching = self.create_teaching(self.teacher, status='PENDING_REVIEW')
        service = self.create_service(self.teacher, status='PENDING_REVIEW')

        endpoint_pairs = [
            (project, f'/api/achievements/projects/{project.id}/approve/'),
            (ip_record, f'/api/achievements/intellectual-properties/{ip_record.id}/approve/'),
            (teaching, f'/api/achievements/teaching-achievements/{teaching.id}/approve/'),
            (service, f'/api/achievements/academic-services/{service.id}/approve/'),
        ]

        self.client.force_authenticate(user=self.college_admin)
        for instance, endpoint in endpoint_pairs:
            response = self.client.post(endpoint, {}, format='json')
            self.assertEqual(response.status_code, status.HTTP_200_OK, msg=f'审批通过失败: {endpoint}')
            instance.refresh_from_db()
            self.assertEqual(instance.status, 'APPROVED')

    def test_college_admin_reject_requires_reason_for_non_paper_achievements(self):
        project = self.create_project(self.teacher, status='PENDING_REVIEW')
        ip_record = self.create_ip(self.teacher, status='PENDING_REVIEW')
        teaching = self.create_teaching(self.teacher, status='PENDING_REVIEW')
        service = self.create_service(self.teacher, status='PENDING_REVIEW')

        endpoint_pairs = [
            (project, f'/api/achievements/projects/{project.id}/reject/'),
            (ip_record, f'/api/achievements/intellectual-properties/{ip_record.id}/reject/'),
            (teaching, f'/api/achievements/teaching-achievements/{teaching.id}/reject/'),
            (service, f'/api/achievements/academic-services/{service.id}/reject/'),
        ]

        self.client.force_authenticate(user=self.college_admin)
        for instance, endpoint in endpoint_pairs:
            invalid_response = self.client.post(endpoint, {}, format='json')
            self.assertEqual(invalid_response.status_code, status.HTTP_400_BAD_REQUEST)

            valid_response = self.client.post(endpoint, {'reason': '材料缺失，请补充后重提。'}, format='json')
            self.assertEqual(valid_response.status_code, status.HTTP_200_OK)
            instance.refresh_from_db()
            self.assertEqual(instance.status, 'REJECTED')


class PaperClaimOrderConfirmationApiTests(APITestCase):
    def setUp(self):
        user_model = get_user_model()
        self.teacher_a = user_model.objects.create_user(
            id=904001,
            username='904001',
            password='teacher123456',
            real_name='TeacherA',
            department='人工智能学院',
            title='副教授',
        )
        self.teacher_b = user_model.objects.create_user(
            id=904002,
            username='904002',
            password='teacher123456',
            real_name='TeacherB',
            department='人工智能学院',
            title='讲师',
        )
        self.teacher_c = user_model.objects.create_user(
            id=904003,
            username='904003',
            password='teacher123456',
            real_name='TeacherC',
            department='人工智能学院',
            title='讲师',
        )

    def _create_paper(self, actor, payload):
        self.client.force_authenticate(user=actor)
        response = self.client.post('/api/achievements/papers/', payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        return Paper.objects.get(id=response.data['id'])

    def test_case_1_standard_claim_flow(self):
        paper = self._create_paper(
            self.teacher_a,
            {
                'title': 'Standard claim paper',
                'abstract': 'Long enough abstract for standard internal claim workflow testing.',
                'date_acquired': '2025-08-01',
                'paper_type': 'JOURNAL',
                'journal_name': 'Claim Journal',
                'is_first_author': True,
                'is_corresponding_author': False,
                'coauthor_records': [
                    {'name': self.teacher_b.real_name, 'user_id': self.teacher_b.id, 'order': 2, 'is_corresponding': False}
                ],
            },
        )
        claim = AchievementClaim.objects.get(achievement=paper, target_user=self.teacher_b)
        self.assertEqual(claim.status, 'PENDING')
        self.assertEqual(claim.proposed_order, 2)

        self.client.force_authenticate(user=self.teacher_b)
        accept_response = self.client.post(
            f'/api/claims/{claim.id}/accept/',
            {'actual_order': 2, 'actual_is_corresponding': False},
            format='json',
        )
        self.assertEqual(accept_response.status_code, status.HTTP_200_OK)
        claim.refresh_from_db()
        self.assertEqual(claim.status, 'ACCEPTED')
        self.assertEqual(claim.actual_order, 2)
        self.assertFalse(claim.confirmed_is_corresponding)
        self.assertEqual(paper.coauthors.get(internal_teacher=self.teacher_b).author_rank, 2)

    def test_case_2_student_first_teacher_corresponding(self):
        paper = self._create_paper(
            self.teacher_a,
            {
                'title': 'Student first author case',
                'abstract': 'Long enough abstract for student first and teacher corresponding author scenario.',
                'date_acquired': '2025-08-02',
                'paper_type': 'JOURNAL',
                'journal_name': 'Corresponding Journal',
                'is_first_author': False,
                'is_corresponding_author': True,
                'coauthor_records': [
                    {'name': 'StudentOne', 'order': 1, 'is_corresponding': False},
                    {'name': self.teacher_b.real_name, 'user_id': self.teacher_b.id, 'order': 3, 'is_corresponding': False},
                ],
            },
        )
        claim = AchievementClaim.objects.get(achievement=paper, target_user=self.teacher_b)
        self.assertEqual(claim.status, 'PENDING')
        self.assertEqual(claim.proposed_order, 3)
        self.assertFalse(claim.proposed_is_corresponding)

        paper.status = 'APPROVED'
        paper.save(update_fields=['status'])
        self.client.force_authenticate(user=self.teacher_a)
        all_response = self.client.get(f'/api/achievements/all-achievements/{self.teacher_a.id}/')
        self.assertEqual(all_response.status_code, status.HTTP_200_OK)
        target = next(item for item in all_response.data['records'] if item['id'] == paper.id)
        self.assertIn('通讯作者', target['author_rank_label'])

    def test_case_3_claim_accept_with_order_correction_to_conflict(self):
        paper = self._create_paper(
            self.teacher_a,
            {
                'title': 'Conflict claim paper',
                'abstract': 'Long enough abstract for conflict scenario where claim target corrects order and corresponding.',
                'date_acquired': '2025-08-03',
                'paper_type': 'JOURNAL',
                'journal_name': 'Conflict Journal',
                'coauthor_records': [
                    {'name': self.teacher_c.real_name, 'user_id': self.teacher_c.id, 'order': 3, 'is_corresponding': False}
                ],
            },
        )
        claim = AchievementClaim.objects.get(achievement=paper, target_user=self.teacher_c)

        self.client.force_authenticate(user=self.teacher_c)
        response = self.client.post(
            f'/api/achievements/claims/{claim.id}/accept/',
            {'actual_order': 2, 'actual_is_corresponding': True},
            format='json',
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        claim.refresh_from_db()
        self.assertEqual(claim.status, 'CONFLICT')
        self.assertEqual(claim.actual_order, 2)
        self.assertTrue(claim.confirmed_is_corresponding)
        coauthor = paper.coauthors.get(internal_teacher=self.teacher_c)
        self.assertEqual(coauthor.author_rank, 2)
        self.assertTrue(coauthor.is_corresponding)

    def test_case_4_second_author_teacher_records_and_first_author_claims(self):
        paper = self._create_paper(
            self.teacher_b,
            {
                'title': 'Second author uploads for first author',
                'abstract': 'Long enough abstract for second-author teacher submission and first-author teacher claim confirmation.',
                'date_acquired': '2025-08-04',
                'paper_type': 'JOURNAL',
                'journal_name': 'Shared Journal',
                'is_first_author': False,
                'is_corresponding_author': False,
                'coauthor_records': [
                    {'name': self.teacher_a.real_name, 'user_id': self.teacher_a.id, 'order': 1, 'is_corresponding': False},
                    {'name': self.teacher_b.real_name, 'user_id': self.teacher_b.id, 'order': 2, 'is_corresponding': False},
                ],
            },
        )
        claim = AchievementClaim.objects.get(achievement=paper, target_user=self.teacher_a)
        self.assertEqual(claim.status, 'PENDING')
        self.assertEqual(claim.proposed_order, 1)

        paper.status = 'APPROVED'
        paper.save(update_fields=['status'])

        self.client.force_authenticate(user=self.teacher_b)
        owner_all_response = self.client.get(f'/api/achievements/all-achievements/{self.teacher_b.id}/')
        self.assertEqual(owner_all_response.status_code, status.HTTP_200_OK)
        owner_target = next(item for item in owner_all_response.data['records'] if item['id'] == paper.id)
        self.assertEqual(owner_target['author_rank_label'], '第2作者')

        self.client.force_authenticate(user=self.teacher_a)
        accept_response = self.client.post(
            f'/api/achievements/claims/{claim.id}/accept/',
            {'actual_order': 1, 'actual_is_corresponding': False},
            format='json',
        )
        self.assertEqual(accept_response.status_code, status.HTTP_200_OK)
        claim.refresh_from_db()
        self.assertEqual(claim.status, 'ACCEPTED')

        a_all_response = self.client.get(f'/api/achievements/all-achievements/{self.teacher_a.id}/')
        self.assertEqual(a_all_response.status_code, status.HTTP_200_OK)
        a_target = next(item for item in a_all_response.data['records'] if item['id'] == paper.id)
        self.assertEqual(a_target['author_rank_label'], '第1作者')


class AchievementClaimFlowApiTests(APITestCase):
    def setUp(self):
        user_model = get_user_model()
        self.teacher_a = user_model.objects.create_user(
            id=902001,
            username='902001',
            password='teacher123456',
            real_name='张老师',
            department='人工智能学院',
            title='副教授',
        )
        self.teacher_b = user_model.objects.create_user(
            id=902002,
            username='902002',
            password='teacher123456',
            real_name='李晨',
            department='人工智能学院',
            title='讲师',
        )
        self.teacher_c = user_model.objects.create_user(
            id=902003,
            username='902003',
            password='teacher123456',
            real_name='王刚',
            department='计算机学院',
            title='讲师',
        )
        self.college_admin = user_model.objects.create_user(
            id=902004,
            username='college-admin-claim',
            password='Admin123456',
            real_name='学院管理员认领',
            department='人工智能学院',
            title='学院管理员',
            is_staff=True,
        )

    def _create_approved_paper(self):
        return Paper.objects.create(
            teacher=self.teacher_a,
            title='跨学院协同论文',
            abstract='这是一个足够长的摘要，用于验证校内合著者成果认领机制在审批通过后的画像聚合效果。',
            date_acquired='2025-04-18',
            paper_type='JOURNAL',
            journal_name='测试期刊',
            citation_count=12,
            is_first_author=True,
            status='APPROVED',
        )

    def test_create_paper_auto_generates_pending_claim_for_internal_coauthor(self):
        self.client.force_authenticate(user=self.teacher_a)
        response = self.client.post(
            '/api/achievements/papers/',
            {
                'title': '自动识别认领论文',
                'abstract': '这是一个足够长的摘要，用于验证论文录入后会按合著者姓名自动生成认领邀请。',
                'date_acquired': '2025-04-01',
                'paper_type': 'JOURNAL',
                'journal_name': '测试期刊',
                'coauthors': ['李晨', '外部合作者'],
            },
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        claim = AchievementClaim.objects.filter(target_user=self.teacher_b).first()
        self.assertIsNotNone(claim)
        self.assertEqual(claim.status, 'PENDING')
        self.assertEqual(claim.initiator_id, self.teacher_a.id)

    def test_accept_claim_updates_status_and_all_achievements_contains_claimed_paper(self):
        paper = self._create_approved_paper()
        AchievementClaim.objects.create(
            achievement=paper,
            initiator=self.teacher_a,
            target_user=self.teacher_b,
            status='PENDING',
        )

        self.client.force_authenticate(user=self.teacher_b)
        pending_response = self.client.get('/api/achievements/claims/pending/')
        self.assertEqual(pending_response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(pending_response.data['records']), 1)

        claim_id = pending_response.data['records'][0]['id']
        accept_response = self.client.post(f'/api/achievements/claims/{claim_id}/accept/', format='json')
        self.assertEqual(accept_response.status_code, status.HTTP_200_OK)

        all_response = self.client.get(f'/api/achievements/all-achievements/{self.teacher_b.id}/')
        self.assertEqual(all_response.status_code, status.HTTP_200_OK)
        self.assertTrue(any(item['title'] == paper.title for item in all_response.data['records']))

        dashboard_response = self.client.get('/api/achievements/dashboard-stats/')
        self.assertEqual(dashboard_response.status_code, status.HTTP_200_OK)
        self.assertEqual(dashboard_response.data['achievement_overview']['paper_count'], 1)

    def test_reject_claim_marks_status_rejected(self):
        paper = self._create_approved_paper()
        claim = AchievementClaim.objects.create(
            achievement=paper,
            initiator=self.teacher_a,
            target_user=self.teacher_b,
            status='PENDING',
        )

        self.client.force_authenticate(user=self.teacher_b)
        response = self.client.post(f'/api/achievements/claims/{claim.id}/reject/', format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        claim.refresh_from_db()
        self.assertEqual(claim.status, 'REJECTED')

    def test_college_admin_unclaimed_tracking_is_scoped_to_own_college(self):
        paper = self._create_approved_paper()
        claim_in_college = AchievementClaim.objects.create(
            achievement=paper,
            initiator=self.teacher_a,
            target_user=self.teacher_b,
            status='PENDING',
        )
        claim_other_college = AchievementClaim.objects.create(
            achievement=paper,
            initiator=self.teacher_a,
            target_user=self.teacher_c,
            status='PENDING',
        )
        old_time = timezone.now() - timedelta(days=8)
        AchievementClaim.objects.filter(id__in=[claim_in_college.id, claim_other_college.id]).update(created_at=old_time)

        self.client.force_authenticate(user=self.college_admin)
        response = self.client.get('/api/achievements/claims/college-unclaimed/', {'days_threshold': 7})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['records']), 1)
        self.assertEqual(response.data['records'][0]['target_user_name'], '李晨')
