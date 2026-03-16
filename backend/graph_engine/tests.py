from django.contrib.auth import get_user_model
from django.test import override_settings
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from achievements.models import CoAuthor, Paper, PaperKeyword, ResearchKeyword


@override_settings(ENABLE_NEO4J=False)
class AcademicGraphTopologyTests(APITestCase):
    def setUp(self):
        user_model = get_user_model()
        self.user = user_model.objects.create_user(
            username='teacher_graph',
            password='Admin123456',
            real_name='图谱教师',
        )
        self.client.force_authenticate(user=self.user)

    def test_topology_falls_back_to_relational_data(self):
        paper = Paper.objects.create(
            teacher=self.user,
            title='科研画像与知识图谱',
            abstract='这是一段足够长的摘要，用来验证学术社交拓扑图的关系库回退逻辑。',
            date_acquired='2025-03-05',
            paper_type='JOURNAL',
            journal_name='软件学报',
        )
        CoAuthor.objects.create(paper=paper, name='张三')
        keyword = ResearchKeyword.objects.create(name='知识图谱')
        PaperKeyword.objects.create(paper=paper, keyword=keyword)

        response = self.client.get(reverse('academic_graph_topology', kwargs={'user_id': self.user.id}))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(any(node['nodeType'] == 'CenterTeacher' for node in response.data['nodes']))
        self.assertTrue(any(node['nodeType'] == 'Paper' for node in response.data['nodes']))
        self.assertTrue(any(node['nodeType'] == 'ExternalScholar' for node in response.data['nodes']))
        self.assertTrue(any(node['nodeType'] == 'Keyword' for node in response.data['nodes']))
        self.assertTrue(any(link['name'] == 'published' for link in response.data['links']))
