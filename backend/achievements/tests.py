from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from .models import Paper


class PaperEntryApiTests(APITestCase):
    def setUp(self):
        user_model = get_user_model()
        self.user = user_model.objects.create_user(
            username='teacher_one',
            password='Admin123456',
            real_name='教师甲',
        )
        self.other_user = user_model.objects.create_user(
            username='teacher_two',
            password='Admin123456',
            real_name='教师乙',
        )
        self.client.force_authenticate(user=self.user)

    @patch('achievements.views.Neo4jEngine')
    @patch('achievements.views.AcademicAI')
    def test_create_paper_persists_coauthors_and_keywords(self, academic_ai_cls, neo4j_engine_cls):
        academic_ai_cls.return_value.extract_tags.return_value = ['人工智能', '知识图谱']

        payload = {
            'title': '高校教师科研画像研究',
            'abstract': '本文围绕高校教师科研画像构建与智能辅助场景展开分析。',
            'date_acquired': '2025-03-05',
            'paper_type': 'JOURNAL',
            'journal_name': '计算机工程',
            'journal_level': 'CCF-C',
            'citation_count': 12,
            'is_first_author': True,
            'doi': '10.1000/test-doi',
            'coauthors': ['张三', '李四'],
        }

        response = self.client.post(reverse('paper-list'), payload, format='json')

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Paper.objects.count(), 1)
        self.assertEqual(response.data['teacher'], self.user.id)
        self.assertEqual(len(response.data['coauthor_details']), 2)
        self.assertEqual(response.data['keywords'], ['人工智能', '知识图谱'])
        neo4j_engine_cls.return_value.sync_paper_to_graph.assert_called_once()

    @patch('achievements.views.Neo4jEngine')
    @patch('achievements.views.AcademicAI')
    def test_list_only_returns_current_user_papers(self, academic_ai_cls, neo4j_engine_cls):
        academic_ai_cls.return_value.extract_tags.return_value = []

        Paper.objects.create(
            teacher=self.user,
            title='我的论文',
            abstract='一个足够长的摘要用于通过校验。',
            date_acquired='2024-01-01',
            paper_type='JOURNAL',
            journal_name='测试期刊',
        )
        Paper.objects.create(
            teacher=self.other_user,
            title='别人的论文',
            abstract='另一个足够长的摘要用于通过校验。',
            date_acquired='2024-01-02',
            paper_type='CONFERENCE',
            journal_name='外部会议',
        )

        response = self.client.get(reverse('paper-list'))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['title'], '我的论文')

    @patch('achievements.views.Neo4jEngine')
    @patch('achievements.views.AcademicAI')
    def test_duplicate_doi_for_same_user_is_rejected(self, academic_ai_cls, neo4j_engine_cls):
        academic_ai_cls.return_value.extract_tags.return_value = []

        Paper.objects.create(
            teacher=self.user,
            title='已有论文',
            abstract='一个足够长的摘要用于通过校验。',
            date_acquired='2024-01-01',
            paper_type='JOURNAL',
            journal_name='测试期刊',
            doi='10.1000/duplicate',
        )

        payload = {
            'title': '重复 DOI 论文',
            'abstract': '本文摘要足够长，用来测试重复 DOI 校验逻辑。',
            'date_acquired': '2025-03-05',
            'paper_type': 'JOURNAL',
            'journal_name': '计算机工程',
            'doi': '10.1000/duplicate',
            'coauthors': [],
        }

        response = self.client.post(reverse('paper-list'), payload, format='json')

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('doi', response.data)
