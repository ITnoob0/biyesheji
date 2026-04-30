from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.test import APITestCase

from .models import EvaluationRuleCategory, EvaluationRuleItem, EvaluationRuleVersion


class EvaluationRuleApiTests(APITestCase):
    def setUp(self):
        user_model = get_user_model()
        self.system_admin = user_model.objects.create_superuser(
            id=1,
            username='admin',
            password='Admin123456',
            real_name='系统管理员',
        )
        self.college_admin = user_model.objects.create_user(
            id=200001,
            username='200001',
            password='College123456',
            real_name='学院管理员',
            department='计算机学院',
            is_staff=True,
        )
        self.teacher = user_model.objects.create_user(
            id=200002,
            username='200002',
            password='Teacher123456',
            real_name='普通教师',
            department='计算机学院',
            title='讲师',
        )
        self.active_version = EvaluationRuleVersion.objects.filter(
            status=EvaluationRuleVersion.STATUS_ACTIVE
        ).order_by('-id').first()
        self.project_category = EvaluationRuleCategory.objects.get(
            version=self.active_version,
            code='PROJECT',
        )

    def test_teacher_can_read_dashboard_in_readonly_mode(self):
        self.client.force_authenticate(self.teacher)

        response = self.client.get('/api/evaluation-rules/dashboard/')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertFalse(response.data['permissions']['can_edit'])
        self.assertEqual(response.data['permissions']['read_mode'], 'readonly')
        grouped_keys = {item['key'] for item in response.data['grouped_rules']}
        self.assertIn('PLATFORM_TEAM', grouped_keys)
        self.assertIn('SCI_POP_AWARD', grouped_keys)
        self.assertNotIn('EXCLUDED', grouped_keys)
        self.assertNotIn('COMMON_RULE', grouped_keys)

    def test_college_admin_can_read_dashboard_in_readonly_mode(self):
        self.client.force_authenticate(self.college_admin)

        response = self.client.get('/api/evaluation-rules/dashboard/')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertFalse(response.data['permissions']['can_edit'])
        self.assertEqual(response.data['permissions']['read_mode'], 'readonly')
        self.assertEqual(response.data['active_version']['id'], self.active_version.id)

    def test_teacher_cannot_create_rule_item(self):
        self.client.force_authenticate(self.teacher)

        response = self.client.post(
            '/api/evaluation-rules/items/',
            {
                'version': self.active_version.id,
                'category_ref': self.project_category.id,
                'rule_code': 'TEST-READONLY',
                'discipline': EvaluationRuleItem.DISCIPLINE_GENERAL,
                'entry_policy': EvaluationRuleItem.ENTRY_REQUIRED,
                'title': '教师越权创建规则',
                'score_text': '100',
                'sort_order': 999,
            },
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertFalse(EvaluationRuleItem.objects.filter(rule_code='TEST-READONLY').exists())

    def test_system_admin_can_create_category_and_rule_item(self):
        self.client.force_authenticate(self.system_admin)

        category_response = self.client.post(
            '/api/evaluation-rules/categories/',
            {
                'version': self.active_version.id,
                'code': 'TEST_CATEGORY',
                'name': '测试分类',
                'description': '用于测试管理员维护分类',
                'dimension_key': 'academic_output',
                'dimension_label': '学术产出与著作',
                'entry_enabled': True,
                'include_in_total': True,
                'include_in_radar': True,
                'sort_order': 990,
                'is_active': True,
            },
            format='json',
        )
        self.assertEqual(category_response.status_code, status.HTTP_201_CREATED)

        response = self.client.post(
            '/api/evaluation-rules/items/',
            {
                'version': self.active_version.id,
                'category_ref': category_response.data['id'],
                'rule_code': 'TEST-SYS-ADMIN',
                'discipline': EvaluationRuleItem.DISCIPLINE_GENERAL,
                'entry_policy': EvaluationRuleItem.ENTRY_REQUIRED,
                'title': '系统管理员测试规则',
                'description': '用于验证系统管理员可以维护评价规则。',
                'score_text': '100',
                'sort_order': 999,
                'is_active': True,
            },
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        created_item = EvaluationRuleItem.objects.get(rule_code='TEST-SYS-ADMIN')
        self.assertEqual(created_item.version_id, self.active_version.id)
        self.assertEqual(created_item.category_ref.code, 'TEST_CATEGORY')
        self.assertEqual(str(created_item.base_score), '100.00')

    def test_non_admin_item_list_hides_inactive_rules(self):
        hidden_item = EvaluationRuleItem.objects.create(
            version=self.active_version,
            category_ref=self.project_category,
            category=self.project_category.code,
            rule_code='TEST-HIDDEN',
            discipline=EvaluationRuleItem.DISCIPLINE_GENERAL,
            entry_policy=EvaluationRuleItem.ENTRY_REQUIRED,
            title='隐藏规则',
            score_text='50',
            base_score='50',
            include_in_total=True,
            include_in_radar=True,
            sort_order=998,
            is_active=False,
        )

        self.client.force_authenticate(self.teacher)
        teacher_response = self.client.get(f'/api/evaluation-rules/items/?version={self.active_version.id}')
        self.assertEqual(teacher_response.status_code, status.HTTP_200_OK)
        self.assertNotIn(hidden_item.id, [item['id'] for item in teacher_response.data])

        self.client.force_authenticate(self.system_admin)
        admin_response = self.client.get(f'/api/evaluation-rules/items/?version={self.active_version.id}')
        self.assertEqual(admin_response.status_code, status.HTTP_200_OK)
        self.assertIn(hidden_item.id, [item['id'] for item in admin_response.data])
