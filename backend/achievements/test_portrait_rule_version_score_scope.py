from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.test import APITestCase

from evaluation_rules.models import EvaluationRuleCategory, EvaluationRuleItem, EvaluationRuleVersion

from .models import RuleBasedAchievement


class PortraitRuleVersionScoreScopeTests(APITestCase):
    def setUp(self):
        user_model = get_user_model()
        self.teacher = user_model.objects.create_user(
            id=100901,
            username='100901',
            password='teacher123456',
            real_name='规则版本画像教师',
            department='人工智能学院',
        )
        self.active_version = EvaluationRuleVersion.objects.create(
            code='ACTIVE-2026',
            name='2026 启用规则',
            status=EvaluationRuleVersion.STATUS_ACTIVE,
        )
        self.archived_version = EvaluationRuleVersion.objects.create(
            code='ARCHIVED-2022',
            name='2022 历史规则',
            status=EvaluationRuleVersion.STATUS_ARCHIVED,
        )
        self.active_category = self._create_category(self.active_version, 'PROJECT', '科研项目')
        self.archived_category = self._create_category(self.archived_version, 'PAPER_BOOK', '论文著作')
        self.active_item = self._create_item(self.active_version, self.active_category, '省部级重点研发项目')
        self.archived_item = self._create_item(self.archived_version, self.archived_category, 'CSSCI 来源期刊论文')
        self.active_record = self._create_record(
            version=self.active_version,
            category=self.active_category,
            rule_item=self.active_item,
            title='陕西省重点研发计划“黄土高原生态遥感智能监测”',
            final_score='80.00',
        )
        self.archived_record = self._create_record(
            version=self.archived_version,
            category=self.archived_category,
            rule_item=self.archived_item,
            title='黄土丘陵区乡村振兴数字治理机制研究',
            final_score='35.50',
        )
        self.client.force_authenticate(self.teacher)

    def _create_category(self, version, code, name):
        return EvaluationRuleCategory.objects.create(
            version=version,
            code=code,
            name=name,
            dimension_key=code.lower(),
            dimension_label=name,
        )

    def _create_item(self, version, category, title):
        return EvaluationRuleItem.objects.create(
            version=version,
            category_ref=category,
            category=category.code,
            title=title,
            rule_code=f'{version.code}-{category.code}',
            score_mode=EvaluationRuleItem.SCORE_MODE_FIXED,
            base_score='10.00',
        )

    def _create_record(self, *, version, category, rule_item, title, final_score):
        return RuleBasedAchievement.objects.create(
            teacher=self.teacher,
            version=version,
            category=category,
            rule_item=rule_item,
            title=title,
            date_acquired='2026-04-20',
            status='APPROVED',
            provisional_score=final_score,
            final_score=final_score,
            category_code_snapshot=category.code,
            category_name_snapshot=category.name,
            rule_title_snapshot=rule_item.title,
            rule_code_snapshot=rule_item.rule_code,
        )

    def test_dashboard_total_is_direct_sum_across_rule_versions(self):
        response = self.client.get('/api/achievements/dashboard-stats/')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['achievement_overview']['total_score'], 115.5)
        self.assertEqual(response.data['calculation_summary']['total_score'], 115.5)
        self.assertEqual(response.data['calculation_summary']['weight_mode'], 'direct_rule_score_sum')
        self.assertTrue(response.data['rule_version_scope']['is_all_versions'])

    def test_dashboard_can_filter_single_rule_version_without_recalculating_old_score(self):
        response = self.client.get(
            '/api/achievements/dashboard-stats/',
            {'rule_version': self.archived_version.id},
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['achievement_overview']['total_score'], 35.5)
        self.assertEqual(response.data['rule_version_scope']['selected_rule_version_id'], self.archived_version.id)
        self.assertFalse(response.data['rule_version_scope']['is_all_versions'])

    def test_approved_historical_rule_version_record_is_frozen(self):
        response = self.client.patch(
            f'/api/achievements/rule-achievements/{self.archived_record.id}/',
            {'title': '历史规则成果不应被改写'},
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_409_CONFLICT)
        self.assertEqual(response.data['error']['code'], 'rule_achievement_version_frozen')
