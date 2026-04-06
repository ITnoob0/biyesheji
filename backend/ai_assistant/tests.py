from django.contrib.auth import get_user_model
from django.test import override_settings
from rest_framework import status
from rest_framework.test import APITestCase
from unittest.mock import patch

from achievements.models import Paper, TeacherProfile
from project_guides.models import ProjectGuide


class PortraitAssistantApiTests(APITestCase):
    def setUp(self):
        user_model = get_user_model()
        self.teacher = user_model.objects.create_user(
            id=100031,
            username='100031',
            password='teacher123456',
            real_name='问答教师',
            department='计算机学院',
            title='副教授',
            research_direction=['知识图谱', '科研画像'],
        )
        TeacherProfile.objects.create(
            user=self.teacher,
            department='计算机学院',
            discipline='人工智能',
            title='副教授',
            research_interests='知识图谱, 科研画像',
            h_index=5,
        )
        self.admin = user_model.objects.create_superuser(
            id=1,
            username='admin',
            password='Admin123456',
            real_name='系统管理员',
        )

        Paper.objects.create(
            teacher=self.teacher,
            title='科研画像问答支撑论文',
            abstract='这是一个足够长的摘要，用于支持第三轮的轻量智能问答演示链路。',
            date_acquired='2025-05-01',
            paper_type='JOURNAL',
            journal_name='软件导刊',
            citation_count=8,
            doi='10.1000/assistant-portrait-paper',
            status='APPROVED',
        )
        self.guide = ProjectGuide.objects.create(
            title='科研画像智能分析专项指南',
            issuing_agency='省教育厅',
            guide_level='PROVINCIAL',
            status='OPEN',
            summary='围绕科研画像、智能分析和教师评价方向组织申报。',
            target_keywords=['科研画像', '知识图谱'],
            target_disciplines=['人工智能', '计算机学院'],
            support_amount='20 万元',
            created_by=self.admin,
        )

    def test_teacher_can_request_portrait_summary(self):
        self.client.force_authenticate(self.teacher)
        response = self.client.post(
            '/api/ai-assistant/portrait-qa/',
            {
                'question_type': 'portrait_summary',
            },
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['question_type'], 'portrait_summary')
        self.assertIn('answer', response.data)
        self.assertIn('系统内真实教师资料', response.data['scope_note'])
        self.assertTrue(response.data['source_details'])

    def test_teacher_can_request_guide_reason(self):
        self.client.force_authenticate(self.teacher)
        response = self.client.post(
            '/api/ai-assistant/portrait-qa/',
            {
                'question_type': 'guide_reason',
                'guide_id': self.guide.id,
            },
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['question_type'], 'guide_reason')
        self.assertEqual(response.data['guide_snapshot']['guide_id'], self.guide.id)
        self.assertTrue(response.data['data_sources'])
        self.assertTrue(response.data['related_reasons'])
        self.assertEqual(response.data['source_details'][0]['link']['page'], 'recommendations')
        self.assertEqual(response.data['source_details'][0]['link']['guide_id'], self.guide.id)

    def test_teacher_can_request_portrait_dimension_reason(self):
        self.client.force_authenticate(self.teacher)
        response = self.client.post(
            '/api/ai-assistant/portrait-qa/',
            {
                'question_type': 'portrait_dimension_reason',
            },
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['question_type'], 'portrait_dimension_reason')
        self.assertTrue(response.data['related_reasons'])
        self.assertTrue(response.data['source_details'])
        self.assertEqual(response.data['source_details'][0]['link']['page'], 'portrait')
        self.assertEqual(response.data['source_details'][0]['link']['section'], 'portrait-dimensions')

    def test_teacher_can_request_portrait_data_governance(self):
        self.client.force_authenticate(self.teacher)
        response = self.client.post(
            '/api/ai-assistant/portrait-qa/',
            {
                'question_type': 'portrait_data_governance',
            },
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['question_type'], 'portrait_data_governance')
        self.assertIn('source_governance', response.data)
        self.assertEqual(response.data['source_details'][0]['module_label'], '画像模块')
        self.assertTrue(response.data['source_governance']['verification_note'])

    def test_teacher_can_request_achievement_recommendation_link(self):
        self.client.force_authenticate(self.teacher)
        response = self.client.post(
            '/api/ai-assistant/portrait-qa/',
            {
                'question_type': 'achievement_recommendation_link',
            },
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['question_type'], 'achievement_recommendation_link')
        self.assertEqual(response.data['guide_snapshot']['guide_id'], self.guide.id)
        self.assertTrue(response.data['related_reasons'])
        self.assertEqual(response.data['source_details'][0]['link']['page'], 'recommendations')

    def test_teacher_can_request_graph_status(self):
        self.client.force_authenticate(self.teacher)
        response = self.client.post(
            '/api/ai-assistant/portrait-qa/',
            {
                'question_type': 'graph_status',
            },
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['question_type'], 'graph_status')
        self.assertEqual(response.data['source_details'][0]['link']['page'], 'portrait')
        self.assertEqual(response.data['source_details'][0]['link']['section'], 'portrait-graph')
        self.assertTrue(response.data['source_governance']['degraded_flags'])

    def test_teacher_can_request_guide_overview(self):
        self.client.force_authenticate(self.teacher)
        response = self.client.post(
            '/api/ai-assistant/portrait-qa/',
            {
                'question_type': 'guide_overview',
            },
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['question_type'], 'guide_overview')
        self.assertIn('推荐', response.data['title'])

    def test_admin_can_request_academy_summary(self):
        self.client.force_authenticate(self.admin)
        response = self.client.post(
            '/api/ai-assistant/portrait-qa/',
            {
                'question_type': 'academy_summary',
                'department': '计算机学院',
                'year': 2025,
            },
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['question_type'], 'academy_summary')
        self.assertEqual(response.data['academy_snapshot']['department'], '计算机学院')
        self.assertEqual(response.data['academy_snapshot']['year'], 2025)
        self.assertEqual(response.data['source_details'][0]['link']['page'], 'academy-dashboard')

    def test_admin_can_request_other_teacher_answer(self):
        self.client.force_authenticate(self.admin)
        response = self.client.post(
            '/api/ai-assistant/portrait-qa/',
            {
                'question_type': 'portrait_summary',
                'user_id': self.teacher.id,
            },
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['question_type'], 'portrait_summary')
        self.assertEqual(response.data['teacher_snapshot']['user_id'], self.teacher.id)
        self.assertTrue(response.data['source_details'])

    def test_non_admin_cannot_request_other_teacher_answer(self):
        other_teacher = get_user_model().objects.create_user(
            id=100032,
            username='100032',
            password='teacher123456',
            real_name='其他教师',
        )

        self.client.force_authenticate(self.teacher)
        response = self.client.post(
            '/api/ai-assistant/portrait-qa/',
            {
                'question_type': 'portrait_summary',
                'user_id': other_teacher.id,
            },
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_non_admin_cannot_request_academy_summary(self):
        self.client.force_authenticate(self.teacher)
        response = self.client.post(
            '/api/ai-assistant/portrait-qa/',
            {
                'question_type': 'academy_summary',
            },
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertIn('error', response.data)
        self.assertTrue(response.data['error']['next_step'])
        self.assertTrue(response.data['request_id'])

    def test_data_poor_teacher_gets_fallback_for_achievement_portrait_link(self):
        poor_teacher = get_user_model().objects.create_user(
            id=100033,
            username='100033',
            password='teacher123456',
            real_name='样本不足教师',
        )

        self.client.force_authenticate(poor_teacher)
        response = self.client.post(
            '/api/ai-assistant/portrait-qa/',
            {
                'question_type': 'achievement_portrait_link',
            },
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['status'], 'fallback')
        self.assertEqual(response.data['question_type'], 'achievement_portrait_link')
        self.assertTrue(response.data['failure_notice'])
        self.assertTrue(response.data['source_governance']['unavailable_flags'])

    @patch('ai_assistant.views.PortraitAssistantService.build_answer')
    def test_assistant_returns_fallback_payload_when_answer_generation_fails(self, build_answer):
        build_answer.side_effect = RuntimeError('temporary failure')

        self.client.force_authenticate(self.teacher)
        response = self.client.post(
            '/api/ai-assistant/portrait-qa/',
            {
                'question_type': 'portrait_summary',
            },
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['status'], 'fallback')
        self.assertIn('failure_notice', response.data)
        self.assertIn('temporary failure', response.data['source_details'][0]['value'])
        self.assertIn('受控的轻量智能辅助链路', response.data['scope_note'])

    def test_teacher_can_use_chat_assistant(self):
        self.client.force_authenticate(self.teacher)
        response = self.client.post(
            '/api/ai-assistant/chat/',
            {
                'message': '结合我的成果和推荐，下一步申报建议是什么？',
                'context_hint': 'recommendation',
            },
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn(response.data['status'], ['ok', 'fallback'])
        self.assertEqual(response.data['assistant_mode'], 'rag-chat')
        self.assertTrue(response.data['answer'])
        self.assertTrue(response.data['sources'])
        self.assertEqual(response.data['teacher_snapshot']['user_id'], self.teacher.id)

    def test_chat_assistant_rejects_target_user_id(self):
        self.client.force_authenticate(self.admin)
        response = self.client.post(
            '/api/ai-assistant/chat/',
            {
                'message': '请总结当前教师画像。',
                'user_id': self.teacher.id,
            },
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('user_id', response.data)

    @override_settings(DIFY_BASE_URL='', DIFY_API_KEY='')
    def test_dify_chat_returns_fallback_when_unconfigured(self):
        self.client.force_authenticate(self.teacher)
        response = self.client.post(
            '/api/ai-assistant/dify-chat/',
            {
                'message': '请给我一个本周科研任务建议。',
            },
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['assistant_mode'], 'dify-proxy')
        self.assertEqual(response.data['status'], 'fallback')
        self.assertIn('暂未完成配置', response.data['answer'])
