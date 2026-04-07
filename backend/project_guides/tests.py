from datetime import timedelta

from django.contrib.auth import get_user_model
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from achievements.models import Paper, PaperKeyword, ResearchKeyword, TeacherProfile
from users.models import UserNotification

from .models import Academy, ProjectGuide, ProjectGuideFavorite, ProjectGuideRecommendationRecord


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
            status='APPROVED',
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
            'rule_profile': 'KEYWORD_FIRST',
            'application_deadline': '2026-05-31',
            'summary': '面向教育数字化、智能教学与评价改革方向征集重点项目。',
            'target_keywords': ['科研画像', '智能推荐'],
            'target_disciplines': ['教育数据智能', '教育技术学院'],
            'recommendation_tags': ['教育场景', '重点指南'],
            'support_amount': '20-30 万元',
            'eligibility_notes': '需具备近三年相关研究基础。',
            'source_url': 'https://example.com/guide',
        }

        response = self.client.post('/api/project-guides/', payload, format='json')

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(ProjectGuide.objects.count(), 1)
        self.assertEqual(response.data['created_by_name'], '系统管理员')
        self.assertEqual(response.data['rule_profile'], 'KEYWORD_FIRST')
        self.assertEqual(response.data['recommendation_tags'], ['教育场景', '重点指南'])

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

    def test_teacher_cannot_update_or_delete_project_guide(self):
        guide = ProjectGuide.objects.create(
            title='管理员创建的指南',
            issuing_agency='省教育厅',
            guide_level='PROVINCIAL',
            status='OPEN',
            summary='用于验证教师不能修改或删除指南。',
            target_keywords=['科研画像'],
            target_disciplines=['教育数据智能'],
            created_by=self.admin,
        )

        self.client.force_authenticate(self.teacher)
        update_response = self.client.patch(
            f'/api/project-guides/{guide.id}/',
            {'title': '越权修改的指南'},
            format='json',
        )
        delete_response = self.client.delete(f'/api/project-guides/{guide.id}/')

        self.assertEqual(update_response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(delete_response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertTrue(ProjectGuide.objects.filter(id=guide.id).exists())

    def test_teacher_recommendations_return_reasons_and_empty_state_metadata(self):
        ProjectGuide.objects.create(
            title='教育数据智能专项指南',
            issuing_agency='省教育厅',
            guide_level='PROVINCIAL',
            status='OPEN',
            rule_profile='KEYWORD_FIRST',
            application_deadline='2026-05-31',
            summary='围绕教育数据智能、科研画像和教学评价改革方向组织申报。',
            target_keywords=['科研画像', '教育数据智能', '智能推荐'],
            target_disciplines=['教育数据智能', '教育技术学院'],
            recommendation_tags=['画像重点', '适合教育场景'],
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
        self.assertIn('recommendation_labels', top_item)
        self.assertIn('explanation_dimensions', top_item)
        self.assertIn('priority_label', top_item)
        self.assertIn('recommendation_summary', top_item)
        self.assertIn('supporting_records', top_item)
        self.assertEqual(top_item['rule_profile'], 'KEYWORD_FIRST')
        self.assertTrue(any(item['key'] == 'keyword_match' for item in top_item['explanation_dimensions']))
        self.assertTrue(top_item['supporting_records'])
        self.assertIn('reason', top_item['supporting_records'][0])
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
            rule_profile='BALANCED',
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
        self.assertIn('admin_analysis', response.data)

    def test_admin_can_compare_recommendations_between_two_teachers(self):
        user_model = get_user_model()
        compare_teacher = user_model.objects.create_user(
            id=100021,
            username='100021',
            password='teacher123456',
            real_name='对比教师',
            department='教育技术学院',
            title='讲师',
            research_direction=['智能推荐'],
        )
        TeacherProfile.objects.create(
            user=compare_teacher,
            department='教育技术学院',
            discipline='智能推荐',
            title='讲师',
            research_interests='推荐系统, 教育评价',
            h_index=4,
        )

        ProjectGuide.objects.create(
            title='教师对比推荐指南',
            issuing_agency='省教育厅',
            guide_level='PROVINCIAL',
            status='OPEN',
            rule_profile='DISCIPLINE_FIRST',
            summary='用于验证管理员可查看两位教师的推荐差异。',
            target_keywords=['科研画像', '智能推荐'],
            target_disciplines=['教育数据智能', '智能推荐'],
            recommendation_tags=['对比分析'],
            created_by=self.admin,
        )

        self.client.force_authenticate(self.admin)
        response = self.client.get(
            '/api/project-guides/recommendations/',
            {'user_id': self.teacher.id, 'compare_user_id': compare_teacher.id},
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('comparison_teacher_snapshot', response.data)
        self.assertIn('comparison_summary', response.data)
        self.assertTrue(response.data['comparison_teacher_snapshot'])
        self.assertTrue(response.data['recommendations'])
        self.assertIn('compare_score', response.data['recommendations'][0])
        self.assertIn('compare_delta', response.data['recommendations'][0])
        self.assertIn('primary_better_count', response.data['comparison_summary'])
        self.assertIn('recommended_count', response.data['admin_analysis'])
        self.assertIn('top_labels', response.data['admin_analysis'])

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
        self.assertIn('error', response.data)
        self.assertTrue(response.data['error']['next_step'])
        self.assertTrue(response.data['request_id'])

    def test_teacher_cannot_use_compare_teacher_parameter(self):
        user_model = get_user_model()
        compare_teacher = user_model.objects.create_user(
            id=100022,
            username='100022',
            password='teacher123456',
            real_name='对比教师',
        )

        self.client.force_authenticate(self.teacher)
        response = self.client.get('/api/project-guides/recommendations/', {'compare_user_id': compare_teacher.id})

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertIn('error', response.data)
        self.assertTrue(response.data['request_id'])

    def test_admin_analysis_exposes_distribution_for_regression_verification(self):
        ProjectGuide.objects.create(
            title='重点指南 A',
            issuing_agency='省教育厅',
            guide_level='PROVINCIAL',
            status='OPEN',
            rule_profile='KEYWORD_FIRST',
            summary='用于验证管理员推荐分析分布字段。',
            target_keywords=['科研画像'],
            target_disciplines=['教育数据智能'],
            recommendation_tags=['画像重点'],
            created_by=self.admin,
        )
        ProjectGuide.objects.create(
            title='重点指南 B',
            issuing_agency='市教育局',
            guide_level='MUNICIPAL',
            status='OPEN',
            rule_profile='DISCIPLINE_FIRST',
            summary='用于验证管理员推荐分析分布字段。',
            target_keywords=['教育数据'],
            target_disciplines=['教育技术学院'],
            recommendation_tags=['学科贴合'],
            created_by=self.admin,
        )

        self.client.force_authenticate(self.admin)
        response = self.client.get('/api/project-guides/recommendations/', {'user_id': self.teacher.id})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('admin_analysis', response.data)
        self.assertGreaterEqual(response.data['admin_analysis']['recommended_count'], 1)
        self.assertTrue(response.data['admin_analysis']['priority_distribution'])
        self.assertTrue(response.data['admin_analysis']['rule_profile_distribution'])

    def test_teacher_can_persist_favorite_feedback_and_history(self):
        guide = ProjectGuide.objects.create(
            title='反馈收藏指南',
            issuing_agency='省教育厅',
            guide_level='PROVINCIAL',
            status='OPEN',
            rule_profile='PORTRAIT_FIRST',
            rule_config={'portrait_bonus': 6, 'keyword_bonus': 2},
            summary='用于验证推荐结果历史、收藏持久化和反馈信号采集。',
            target_keywords=['科研画像', '智能推荐'],
            target_disciplines=['教育数据智能'],
            recommendation_tags=['规则增强'],
            created_by=self.admin,
        )

        self.client.force_authenticate(self.teacher)
        recommendation_response = self.client.get('/api/project-guides/recommendations/')
        favorite_response = self.client.post(
            f'/api/project-guides/{guide.id}/favorite/',
            {'is_favorited': True},
            format='json',
        )
        feedback_response = self.client.post(
            f'/api/project-guides/{guide.id}/feedback/',
            {'feedback_signal': 'PLAN_TO_APPLY', 'feedback_note': '准备结合当前研究方向申报。'},
            format='json',
        )
        refreshed_recommendation_response = self.client.get('/api/project-guides/recommendations/')
        history_response = self.client.get('/api/project-guides/recommendation-history/')

        self.assertEqual(recommendation_response.status_code, status.HTTP_200_OK)
        self.assertTrue(recommendation_response.data['history_preview'])
        self.assertIn('favorites', recommendation_response.data)
        self.assertIn('portrait_link_summary', recommendation_response.data)
        self.assertTrue(recommendation_response.data['data_meta']['interaction_enabled'])
        self.assertTrue(any(item['portrait_dimension_links'] for item in recommendation_response.data['recommendations']))

        self.assertEqual(favorite_response.status_code, status.HTTP_200_OK)
        self.assertTrue(ProjectGuideFavorite.objects.filter(teacher=self.teacher, guide=guide).exists())
        self.assertIn(guide.id, favorite_response.data['favorite_ids'])

        self.assertEqual(feedback_response.status_code, status.HTTP_200_OK)
        self.assertEqual(feedback_response.data['feedback_signal'], 'PLAN_TO_APPLY')
        self.assertEqual(feedback_response.data['feedback_note'], '准备结合当前研究方向申报。')
        self.assertGreaterEqual(
            ProjectGuideRecommendationRecord.objects.filter(
                teacher=self.teacher,
                guide=guide,
                feedback_signal='PLAN_TO_APPLY',
            ).count(),
            1,
        )

        self.assertEqual(refreshed_recommendation_response.status_code, status.HTTP_200_OK)
        self.assertEqual(refreshed_recommendation_response.data['recommendations'][0]['latest_feedback_signal'], 'PLAN_TO_APPLY')
        self.assertEqual(refreshed_recommendation_response.data['recommendations'][0]['latest_feedback_note'], '准备结合当前研究方向申报。')
        self.assertIn('response_rate', refreshed_recommendation_response.data['feedback_summary'])
        self.assertGreaterEqual(refreshed_recommendation_response.data['feedback_summary']['responded_guide_count'], 1)
        self.assertGreaterEqual(refreshed_recommendation_response.data['feedback_summary']['plan_to_apply_count'], 1)
        self.assertTrue(refreshed_recommendation_response.data['feedback_summary']['recent_feedback_items'])
        self.assertIn('feedback_ranking_boundary', refreshed_recommendation_response.data['data_meta'])

        self.assertEqual(history_response.status_code, status.HTTP_200_OK)
        self.assertTrue(history_response.data['history'])
        self.assertIn('distribution', history_response.data['feedback_summary'])
        self.assertTrue(history_response.data['feedback_summary']['recent_feedback_items'])

    def test_admin_self_recommendation_can_toggle_favorite_and_feedback(self):
        guide = ProjectGuide.objects.create(
            title='管理员自用收藏指南',
            issuing_agency='省教育厅',
            guide_level='PROVINCIAL',
            status='OPEN',
            rule_profile='BALANCED',
            summary='用于验证管理员在给自己推荐场景下可进行收藏与反馈。',
            target_keywords=['科研画像'],
            target_disciplines=['教育数据智能'],
            created_by=self.admin,
        )

        self.client.force_authenticate(self.admin)
        recommendation_response = self.client.get('/api/project-guides/recommendations/')
        favorite_response = self.client.post(
            f'/api/project-guides/{guide.id}/favorite/',
            {'is_favorited': True},
            format='json',
        )
        feedback_response = self.client.post(
            f'/api/project-guides/{guide.id}/feedback/',
            {'feedback_signal': 'INTERESTED', 'feedback_note': '管理员自用视角测试反馈。'},
            format='json',
        )
        refreshed_recommendation_response = self.client.get('/api/project-guides/recommendations/')

        self.assertEqual(recommendation_response.status_code, status.HTTP_200_OK)
        self.assertTrue(recommendation_response.data['data_meta']['interaction_enabled'])

        self.assertEqual(favorite_response.status_code, status.HTTP_200_OK)
        self.assertTrue(ProjectGuideFavorite.objects.filter(teacher=self.admin, guide=guide).exists())
        self.assertIn(guide.id, favorite_response.data['favorite_ids'])

        self.assertEqual(feedback_response.status_code, status.HTTP_200_OK)
        self.assertEqual(feedback_response.data['feedback_signal'], 'INTERESTED')
        self.assertEqual(feedback_response.data['feedback_note'], '管理员自用视角测试反馈。')

        self.assertEqual(refreshed_recommendation_response.status_code, status.HTTP_200_OK)
        self.assertIn(guide.id, refreshed_recommendation_response.data['favorites']['guide_ids'])
        self.assertIn('feedback_summary', refreshed_recommendation_response.data)

    def test_admin_analysis_includes_feedback_response_summary(self):
        guide = ProjectGuide.objects.create(
            title='管理员反馈摘要指南',
            issuing_agency='省教育厅',
            guide_level='PROVINCIAL',
            status='OPEN',
            rule_profile='KEYWORD_FIRST',
            summary='用于验证管理员可以看到教师推荐响应分析摘要。',
            target_keywords=['科研画像', '智能推荐'],
            target_disciplines=['教育数据智能'],
            created_by=self.admin,
        )

        self.client.force_authenticate(self.teacher)
        self.client.get('/api/project-guides/recommendations/')
        self.client.post(
            f'/api/project-guides/{guide.id}/feedback/',
            {'feedback_signal': 'INTERESTED', 'feedback_note': '与当前方向较贴合。'},
            format='json',
        )

        self.client.force_authenticate(self.admin)
        response = self.client.get('/api/project-guides/recommendations/', {'user_id': self.teacher.id})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('admin_analysis', response.data)
        self.assertGreaterEqual(response.data['admin_analysis']['responded_guide_count'], 1)
        self.assertGreaterEqual(response.data['admin_analysis']['positive_feedback_count'], 1)
        self.assertIn('response_rate', response.data['admin_analysis'])

    def test_admin_can_view_lifecycle_summary_and_archive_guide(self):
        guide = ProjectGuide.objects.create(
            title='生命周期指南',
            issuing_agency='科技部',
            guide_level='NATIONAL',
            status='OPEN',
            rule_profile='FOUNDATION_FIRST',
            rule_config={'activity_bonus': 4},
            summary='用于验证项目指南生命周期管理增强。',
            target_keywords=['科研画像'],
            target_disciplines=['教育数据智能'],
            lifecycle_note='已发布待归档',
            created_by=self.admin,
        )

        self.client.force_authenticate(self.admin)
        archive_response = self.client.patch(
            f'/api/project-guides/{guide.id}/',
            {'status': 'ARCHIVED'},
            format='json',
        )
        summary_response = self.client.get('/api/project-guides/summary/')

        self.assertEqual(archive_response.status_code, status.HTTP_200_OK)
        guide.refresh_from_db()
        self.assertEqual(guide.status, 'ARCHIVED')
        self.assertIsNotNone(guide.archived_at)

        self.assertEqual(summary_response.status_code, status.HTTP_200_OK)
        self.assertGreaterEqual(summary_response.data['archived_count'], 1)
        self.assertGreaterEqual(summary_response.data['config_coverage_count'], 1)
        self.assertIn('FOUNDATION_FIRST', summary_response.data['rule_profile_distribution'])


class ProjectGuideAdminRbacPushTests(APITestCase):
    def setUp(self):
        user_model = get_user_model()
        self.system_admin = user_model.objects.create_superuser(
            id=120001,
            username='pg-system-admin',
            password='Admin123456',
            real_name='系统管理员PG',
        )
        self.college_admin_x = user_model.objects.create_user(
            id=120002,
            username='pg-college-admin-x',
            password='Admin123456',
            real_name='学院管理员X',
            department='学院X',
            is_staff=True,
        )
        self.college_admin_y = user_model.objects.create_user(
            id=120003,
            username='pg-college-admin-y',
            password='Admin123456',
            real_name='学院管理员Y',
            department='学院Y',
            is_staff=True,
        )
        self.teacher_x = user_model.objects.create_user(
            id=120010,
            username='120010',
            password='teacher123456',
            real_name='教师X1',
            department='学院X',
            research_direction=['人工智能', '教育数据'],
            title='副教授',
        )
        self.teacher_y = user_model.objects.create_user(
            id=120011,
            username='120011',
            password='teacher123456',
            real_name='教师Y1',
            department='学院Y',
            research_direction=['计算机视觉'],
            title='讲师',
        )

    def _guide_payload(self, **overrides):
        payload = {
            'title': '项目指南默认标题',
            'issuing_agency': '省教育厅',
            'guide_level': 'PROVINCIAL',
            'status': 'DRAFT',
            'scope': 'GLOBAL',
            'summary': '用于测试项目指南 RBAC 与推送行为的默认摘要内容。',
            'target_keywords': ['人工智能'],
            'target_disciplines': ['计算机科学'],
            'recommendation_tags': ['测试'],
        }
        payload.update(overrides)
        return payload

    def test_case_1_system_admin_global_lifecycle_and_targeted_push(self):
        self.client.force_authenticate(self.system_admin)
        create_response = self.client.post(
            '/api/project-guides/',
            self._guide_payload(title='全局指南草稿', status='DRAFT', scope='GLOBAL'),
            format='json',
        )
        self.assertEqual(create_response.status_code, status.HTTP_201_CREATED)
        guide_id = create_response.data['id']

        patch_response = self.client.patch(
            f'/api/project-guides/{guide_id}/',
            {'status': 'URGENT', 'target_keywords': ['人工智能', '教育数据']},
            format='json',
        )
        self.assertEqual(patch_response.status_code, status.HTTP_200_OK)
        self.assertEqual(patch_response.data['status'], 'URGENT')

        push_response = self.client.post(f'/api/project-guides/{guide_id}/targeted_push/', {}, format='json')
        self.assertEqual(push_response.status_code, status.HTTP_200_OK)
        self.assertIn('matched_count', push_response.data)
        self.assertGreaterEqual(push_response.data['matched_count'], 1)
        self.assertGreaterEqual(
            UserNotification.objects.filter(
                recipient=self.teacher_x,
                category=UserNotification.CATEGORY_PROJECT_GUIDE_PUSH,
            ).count(),
            1,
        )

    def test_case_2_college_admin_scope_forced_to_academy(self):
        self.client.force_authenticate(self.college_admin_x)
        response = self.client.post(
            '/api/project-guides/',
            self._guide_payload(title='学院管理员创建指南', scope='GLOBAL', status='ACTIVE'),
            format='json',
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        guide = ProjectGuide.objects.get(id=response.data['id'])
        self.assertEqual(guide.scope, ProjectGuide.SCOPE_ACADEMY)
        self.assertIsNotNone(guide.academy_id)
        self.assertEqual(guide.academy.name, '学院X')

    def test_case_3_cross_academy_data_isolation(self):
        academy_x = Academy.objects.create(name='学院X')
        academy_y = Academy.objects.create(name='学院Y')
        global_guide = ProjectGuide.objects.create(
            title='全局可见指南',
            issuing_agency='科技部',
            guide_level='NATIONAL',
            status='ACTIVE',
            scope='GLOBAL',
            summary='全局指南',
            created_by=self.system_admin,
        )
        guide_a1 = ProjectGuide.objects.create(
            title='学院X指南A1',
            issuing_agency='学院X科研办',
            guide_level='PROVINCIAL',
            status='ACTIVE',
            scope='ACADEMY',
            academy=academy_x,
            summary='学院X指南',
            created_by=self.college_admin_x,
        )
        guide_b1 = ProjectGuide.objects.create(
            title='学院Y指南B1',
            issuing_agency='学院Y科研办',
            guide_level='PROVINCIAL',
            status='ACTIVE',
            scope='ACADEMY',
            academy=academy_y,
            summary='学院Y指南',
            created_by=self.college_admin_y,
        )

        self.client.force_authenticate(self.college_admin_y)
        list_response = self.client.get('/api/project-guides/')
        self.assertEqual(list_response.status_code, status.HTTP_200_OK)
        returned_ids = {item['id'] for item in list_response.data}
        self.assertIn(global_guide.id, returned_ids)
        self.assertIn(guide_b1.id, returned_ids)
        self.assertNotIn(guide_a1.id, returned_ids)

        delete_response = self.client.delete(f'/api/project-guides/{guide_a1.id}/')
        self.assertIn(delete_response.status_code, [status.HTTP_403_FORBIDDEN, status.HTTP_404_NOT_FOUND])
        self.assertTrue(ProjectGuide.objects.filter(id=guide_a1.id).exists())

    def test_case_4_archived_guide_cannot_trigger_targeted_push(self):
        self.client.force_authenticate(self.system_admin)
        guide = ProjectGuide.objects.create(
            title='已归档指南',
            issuing_agency='省教育厅',
            guide_level='PROVINCIAL',
            status='ARCHIVED',
            scope='GLOBAL',
            summary='归档后禁止推送',
            created_by=self.system_admin,
        )
        response = self.client.post(f'/api/project-guides/{guide.id}/targeted_push/', {}, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_lifecycle_filters_by_deadline_and_updated_at(self):
        self.client.force_authenticate(self.system_admin)
        today = timezone.now().date()

        old_guide = ProjectGuide.objects.create(
            title='生命周期旧指南',
            issuing_agency='省教育厅',
            guide_level='PROVINCIAL',
            status='ACTIVE',
            scope='GLOBAL',
            application_deadline=today - timedelta(days=10),
            summary='用于验证生命周期旧数据筛选。',
            created_by=self.system_admin,
        )
        recent_guide = ProjectGuide.objects.create(
            title='生命周期新指南',
            issuing_agency='省教育厅',
            guide_level='PROVINCIAL',
            status='ACTIVE',
            scope='GLOBAL',
            application_deadline=today + timedelta(days=30),
            summary='用于验证生命周期新数据筛选。',
            created_by=self.system_admin,
        )
        ProjectGuide.objects.filter(id=old_guide.id).update(updated_at=timezone.now() - timedelta(days=40))

        response = self.client.get(
            '/api/project-guides/',
            {
                'status': 'ACTIVE',
                'deadline_from': str(today),
                'updated_from': str(today - timedelta(days=7)),
            },
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        returned_titles = {item['title'] for item in response.data}
        self.assertIn(recent_guide.title, returned_titles)
        self.assertNotIn(old_guide.title, returned_titles)

    def test_lifecycle_summary_contains_overdue_active_count(self):
        self.client.force_authenticate(self.system_admin)
        today = timezone.now().date()
        ProjectGuide.objects.create(
            title='已超期未归档指南',
            issuing_agency='省教育厅',
            guide_level='PROVINCIAL',
            status='ACTIVE',
            scope='GLOBAL',
            application_deadline=today - timedelta(days=1),
            summary='用于验证超期统计。',
            created_by=self.system_admin,
        )
        ProjectGuide.objects.create(
            title='正常进行指南',
            issuing_agency='省教育厅',
            guide_level='PROVINCIAL',
            status='ACTIVE',
            scope='GLOBAL',
            application_deadline=today + timedelta(days=10),
            summary='用于验证超期统计。',
            created_by=self.system_admin,
        )
        response = self.client.get('/api/project-guides/summary/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertGreaterEqual(response.data['overdue_active_count'], 1)


class ProjectRecommendationThreeRoleFlowTests(APITestCase):
    def setUp(self):
        user_model = get_user_model()
        self.system_admin = user_model.objects.create_superuser(
            id=130001,
            username='rec-system-admin',
            password='Admin123456',
            real_name='系统管理员推荐',
        )
        self.college_admin_ai = user_model.objects.create_user(
            id=130002,
            username='rec-college-admin-ai',
            password='Admin123456',
            real_name='学院管理员AI',
            is_staff=True,
            department='人工智能学院',
            title='教授',
        )
        self.college_admin_cs = user_model.objects.create_user(
            id=130003,
            username='rec-college-admin-cs',
            password='Admin123456',
            real_name='学院管理员CS',
            is_staff=True,
            department='计算机学院',
            title='教授',
        )
        self.teacher_ai_1 = user_model.objects.create_user(
            id=130010,
            username='130010',
            password='Teacher123456',
            real_name='AI教师甲',
            department='人工智能学院',
            title='副教授',
            research_direction=['知识图谱', '智能推荐'],
        )
        self.teacher_ai_2 = user_model.objects.create_user(
            id=130011,
            username='130011',
            password='Teacher123456',
            real_name='AI教师乙',
            department='人工智能学院',
            title='讲师',
            research_direction=['智能推荐'],
        )
        self.teacher_cs_1 = user_model.objects.create_user(
            id=130012,
            username='130012',
            password='Teacher123456',
            real_name='CS教师甲',
            department='计算机学院',
            title='副教授',
            research_direction=['计算机视觉'],
        )

        TeacherProfile.objects.create(
            user=self.teacher_ai_1,
            department='人工智能学院',
            discipline='人工智能',
            title='副教授',
            research_interests='知识图谱, 智能推荐',
            h_index=12,
        )
        TeacherProfile.objects.create(
            user=self.teacher_ai_2,
            department='人工智能学院',
            discipline='人工智能',
            title='讲师',
            research_interests='智能推荐',
            h_index=5,
        )
        TeacherProfile.objects.create(
            user=self.teacher_cs_1,
            department='计算机学院',
            discipline='计算机科学',
            title='副教授',
            research_interests='计算机视觉',
            h_index=9,
        )

        self.academy_ai = Academy.objects.create(name='人工智能学院')
        self.academy_cs = Academy.objects.create(name='计算机学院')

        self.global_active_guide = ProjectGuide.objects.create(
            title='全校智能申报指南',
            issuing_agency='科技处',
            guide_level='NATIONAL',
            status='ACTIVE',
            scope='GLOBAL',
            summary='全校范围内可申报的智能方向项目指南。',
            target_keywords=['智能推荐', '知识图谱'],
            target_disciplines=['人工智能', '计算机科学'],
            created_by=self.system_admin,
        )
        self.ai_college_guide = ProjectGuide.objects.create(
            title='人工智能学院专项指南',
            issuing_agency='人工智能学院科研办',
            guide_level='PROVINCIAL',
            status='URGENT',
            scope='ACADEMY',
            academy=self.academy_ai,
            summary='仅面向人工智能学院的专项申报指南。',
            target_keywords=['知识图谱'],
            target_disciplines=['人工智能'],
            created_by=self.college_admin_ai,
        )
        self.cs_college_guide = ProjectGuide.objects.create(
            title='计算机学院专项指南',
            issuing_agency='计算机学院科研办',
            guide_level='PROVINCIAL',
            status='ACTIVE',
            scope='ACADEMY',
            academy=self.academy_cs,
            summary='仅面向计算机学院的专项申报指南。',
            target_keywords=['计算机视觉'],
            target_disciplines=['计算机科学'],
            created_by=self.college_admin_cs,
        )
        ProjectGuide.objects.create(
            title='历史归档指南',
            issuing_agency='科技处',
            guide_level='MUNICIPAL',
            status='ARCHIVED',
            scope='GLOBAL',
            summary='已归档指南，不应参与当前推荐。',
            target_keywords=['历史'],
            target_disciplines=['历史学'],
            created_by=self.system_admin,
        )

        for teacher, title_suffix, keyword in [
            (self.teacher_ai_1, 'A1', '智能推荐'),
            (self.teacher_ai_2, 'A2', '知识图谱'),
            (self.teacher_cs_1, 'C1', '计算机视觉'),
        ]:
            paper = Paper.objects.create(
                teacher=teacher,
                title=f'推荐测试论文-{title_suffix}',
                abstract=f'围绕{keyword}方向开展研究。',
                date_acquired='2025-06-01',
                paper_type='JOURNAL',
                journal_name='科研管理研究',
                citation_count=3,
                doi=f'10.1000/rec-flow-{title_suffix.lower()}',
                status='APPROVED',
            )
            keyword_obj, _ = ResearchKeyword.objects.get_or_create(name=keyword)
            PaperKeyword.objects.create(paper=paper, keyword=keyword_obj)

    def test_teacher_recommendation_full_flow(self):
        self.client.force_authenticate(self.teacher_ai_1)
        rec_response = self.client.get('/api/project-guides/recommendations/')
        self.assertEqual(rec_response.status_code, status.HTTP_200_OK)
        self.assertTrue(rec_response.data['recommendations'])

        titles = {item['title'] for item in rec_response.data['recommendations']}
        self.assertIn(self.global_active_guide.title, titles)
        self.assertIn(self.ai_college_guide.title, titles)
        self.assertNotIn(self.cs_college_guide.title, titles)
        self.assertNotIn('历史归档指南', titles)

        favorite_response = self.client.post(
            f'/api/project-guides/{self.global_active_guide.id}/favorite/',
            {'is_favorited': True},
            format='json',
        )
        self.assertEqual(favorite_response.status_code, status.HTTP_200_OK)
        self.assertIn(self.global_active_guide.id, favorite_response.data['favorite_ids'])

        feedback_response = self.client.post(
            f'/api/project-guides/{self.global_active_guide.id}/feedback/',
            {'feedback_signal': 'INTERESTED', 'feedback_note': '当前方向与本人研究较贴合。'},
            format='json',
        )
        self.assertEqual(feedback_response.status_code, status.HTTP_200_OK)
        self.assertEqual(feedback_response.data['feedback_signal'], 'INTERESTED')

        history_response = self.client.get('/api/project-guides/recommendation-history/')
        self.assertEqual(history_response.status_code, status.HTTP_200_OK)
        self.assertTrue(history_response.data['history'])

        forbidden_response = self.client.get(
            '/api/project-guides/recommendations/',
            {'user_id': self.teacher_ai_2.id},
        )
        self.assertEqual(forbidden_response.status_code, status.HTTP_403_FORBIDDEN)

    def test_college_admin_recommendation_scope_flow(self):
        self.client.force_authenticate(self.college_admin_ai)
        in_scope_response = self.client.get(
            '/api/project-guides/recommendations/',
            {'user_id': self.teacher_ai_1.id},
        )
        self.assertEqual(in_scope_response.status_code, status.HTTP_200_OK)
        self.assertIn('admin_analysis', in_scope_response.data)

        titles = {item['title'] for item in in_scope_response.data['recommendations']}
        self.assertIn(self.global_active_guide.title, titles)
        self.assertIn(self.ai_college_guide.title, titles)
        self.assertNotIn(self.cs_college_guide.title, titles)

        compare_response = self.client.get(
            '/api/project-guides/recommendations/',
            {'user_id': self.teacher_ai_1.id, 'compare_user_id': self.teacher_ai_2.id},
        )
        self.assertEqual(compare_response.status_code, status.HTTP_200_OK)
        self.assertIn('comparison_summary', compare_response.data)
        self.assertTrue(compare_response.data['comparison_teacher_snapshot'])

        out_scope_response = self.client.get(
            '/api/project-guides/recommendations/',
            {'user_id': self.teacher_cs_1.id},
        )
        self.assertEqual(out_scope_response.status_code, status.HTTP_403_FORBIDDEN)

    def test_system_admin_recommendation_global_flow(self):
        self.client.force_authenticate(self.system_admin)
        response = self.client.get(
            '/api/project-guides/recommendations/',
            {'user_id': self.teacher_cs_1.id, 'compare_user_id': self.teacher_ai_1.id},
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('admin_analysis', response.data)
        self.assertTrue(response.data['comparison_teacher_snapshot'])
        self.assertIn('comparison_summary', response.data)
        self.assertEqual(response.data['teacher_snapshot']['user_id'], self.teacher_cs_1.id)
        self.assertEqual(response.data['comparison_teacher_snapshot']['user_id'], self.teacher_ai_1.id)
