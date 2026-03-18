from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.test import APITestCase

from achievements.models import Paper, PaperKeyword, ResearchKeyword, TeacherProfile

from .models import ProjectGuide


class ProjectGuideApiTests(APITestCase):
    def setUp(self):
        user_model = get_user_model()
        self.admin = user_model.objects.create_superuser(
            id=1,
            username='admin',
            password='Admin123456',
            real_name='系统管理员',
        )
        self.teacher = user_model.objects.create_user(
            id=100004,
            username='100004',
            password='teacher123456',
            real_name='汪心蕾',
            department='教育技术学院',
            title='副教授',
            research_direction=['教育数据智能', '科研画像'],
            bio='聚焦教育数据智能与科研画像分析。',
        )
        TeacherProfile.objects.create(
            user=self.teacher,
            department='教育技术学院',
            discipline='教育数据智能',
            title='副教授',
            research_interests='科研画像, 智能推荐, 教育评价',
            h_index=8,
        )

        paper = Paper.objects.create(
            teacher=self.teacher,
            title='教师科研画像推荐方法研究',
            abstract='围绕教师科研画像、智能推荐与知识组织的关系展开研究。',
            date_acquired='2025-03-12',
            paper_type='JOURNAL',
            journal_name='现代教育技术',
            citation_count=5,
            doi='10.1000/guide-rec-100004',
        )
        for keyword in ['科研画像', '智能推荐', '教育数据']:
            keyword_obj, _ = ResearchKeyword.objects.get_or_create(name=keyword)
            PaperKeyword.objects.create(paper=paper, keyword=keyword_obj)

    def test_admin_can_create_project_guide(self):
        self.client.force_authenticate(self.admin)

        payload = {
            'title': '教育数字化转型重点项目申报指南',
            'issuing_agency': '省教育厅',
            'guide_level': 'PROVINCIAL',
            'status': 'OPEN',
            'application_deadline': '2026-05-31',
            'summary': '面向教育数字化、智能教学与评价改革方向征集重点项目。',
            'target_keywords': ['科研画像', '智能推荐'],
            'target_disciplines': ['教育数据智能', '教育技术学院'],
            'support_amount': '20-30 万元',
            'eligibility_notes': '需具备近三年相关研究基础。',
            'source_url': 'https://example.com/guide',
        }

        response = self.client.post('/api/project-guides/', payload, format='json')

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(ProjectGuide.objects.count(), 1)
        self.assertEqual(response.data['created_by_name'], '系统管理员')

    def test_teacher_cannot_create_project_guide(self):
        self.client.force_authenticate(self.teacher)

        response = self.client.post(
            '/api/project-guides/',
            {
                'title': '不应允许教师创建的指南',
                'issuing_agency': '某单位',
                'summary': '这条数据不应被普通教师创建成功。',
                'target_keywords': ['科研画像'],
                'target_disciplines': ['教育数据智能'],
            },
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_teacher_recommendations_return_reasons_and_empty_state_metadata(self):
        ProjectGuide.objects.create(
            title='教育数据智能专项指南',
            issuing_agency='省教育厅',
            guide_level='PROVINCIAL',
            status='OPEN',
            application_deadline='2026-05-31',
            summary='围绕教育数据智能、科研画像和教学评价改革方向组织申报。',
            target_keywords=['科研画像', '教育数据智能', '智能推荐'],
            target_disciplines=['教育数据智能', '教育技术学院'],
            support_amount='30 万元',
            eligibility_notes='申报人需近三年有相关论文成果。',
            created_by=self.admin,
        )
        ProjectGuide.objects.create(
            title='无关的企业合作指南',
            issuing_agency='某企业',
            guide_level='ENTERPRISE',
            status='OPEN',
            summary='面向机械制造产线升级项目。',
            target_keywords=['机械制造'],
            target_disciplines=['机械工程'],
            created_by=self.admin,
        )

        self.client.force_authenticate(self.teacher)
        response = self.client.get('/api/project-guides/recommendations/')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertGreaterEqual(len(response.data['recommendations']), 1)
        top_item = response.data['recommendations'][0]
        self.assertTrue(top_item['recommendation_reasons'])
        self.assertIn('match_category_tags', top_item)
        self.assertIn('priority_label', top_item)
        self.assertIn('recommendation_summary', top_item)
        self.assertIn('teacher_snapshot', response.data)
        self.assertIn('data_meta', response.data)
        self.assertIn('empty_state', response.data)
        self.assertIn('sorting_note', response.data['data_meta'])
        self.assertIn('current_strategy', response.data['data_meta'])
        self.assertEqual(top_item['title'], '教育数据智能专项指南')

    def test_teacher_sees_only_open_guides_in_list(self):
        ProjectGuide.objects.create(
            title='开放指南',
            issuing_agency='省科技厅',
            guide_level='PROVINCIAL',
            status='OPEN',
            summary='开放可见指南。',
            target_keywords=['科研画像'],
            target_disciplines=['教育数据智能'],
            created_by=self.admin,
        )
        ProjectGuide.objects.create(
            title='草稿指南',
            issuing_agency='省科技厅',
            guide_level='PROVINCIAL',
            status='DRAFT',
            summary='教师不应看到的草稿指南。',
            target_keywords=['科研画像'],
            target_disciplines=['教育数据智能'],
            created_by=self.admin,
        )

        self.client.force_authenticate(self.teacher)
        response = self.client.get('/api/project-guides/')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual([item['title'] for item in response.data], ['开放指南'])

    def test_admin_can_request_recommendations_for_specified_teacher(self):
        ProjectGuide.objects.create(
            title='管理员指定教师推荐指南',
            issuing_agency='省教育厅',
            guide_level='PROVINCIAL',
            status='OPEN',
            summary='用于验证管理员可以按教师查看项目推荐。',
            target_keywords=['科研画像'],
            target_disciplines=['教育数据智能'],
            created_by=self.admin,
        )

        self.client.force_authenticate(self.admin)
        response = self.client.get('/api/project-guides/recommendations/', {'user_id': self.teacher.id})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['teacher_snapshot']['user_id'], self.teacher.id)
        self.assertTrue(response.data['recommendations'])

    def test_teacher_cannot_request_other_teacher_recommendations(self):
        user_model = get_user_model()
        other_teacher = user_model.objects.create_user(
            id=100020,
            username='100020',
            password='teacher123456',
            real_name='其他教师',
            department='计算机学院',
            title='讲师',
        )

        self.client.force_authenticate(self.teacher)
        response = self.client.get('/api/project-guides/recommendations/', {'user_id': other_teacher.id})

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
