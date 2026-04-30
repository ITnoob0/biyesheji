from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.management import call_command
from rest_framework import status
from rest_framework.test import APITestCase

from achievements.models import AchievementOperationLog, RuleBasedAchievement
from achievements.rule_scoring import apply_rule_snapshots, build_same_achievement_key
from achievements.scoring_engine import TeacherScoringEngine
from evaluation_rules.models import EvaluationRuleCategory, EvaluationRuleItem, EvaluationRuleVersion
from users.title_catalog import TEACHER_PROFESSIONAL_TITLES


class RuleAchievementWorkflowTests(APITestCase):
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
        self.teacher_two = user_model.objects.create_user(
            id=200003,
            username='200003',
            password='Teacher123456',
            real_name='第二教师',
            department='计算机学院',
            title='讲师',
        )

        self.version = EvaluationRuleVersion.objects.filter(
            status=EvaluationRuleVersion.STATUS_ACTIVE
        ).order_by('-id').first()
        self.project_category = EvaluationRuleCategory.objects.get(version=self.version, code='PROJECT')
        self.paper_book_category = EvaluationRuleCategory.objects.get(version=self.version, code='PAPER_BOOK')
        self.platform_category = EvaluationRuleCategory.objects.get(version=self.version, code='PLATFORM_TEAM')
        self.project_item = EvaluationRuleItem.objects.filter(
            version=self.version,
            category_ref=self.project_category,
            is_active=True,
            entry_policy=EvaluationRuleItem.ENTRY_REQUIRED,
        ).order_by('sort_order', 'id').first()
        self.platform_item = EvaluationRuleItem.objects.get(
            version=self.version,
            rule_code='PLATFORM_TEAM_03',
        )
        self.book_item = EvaluationRuleItem.objects.get(
            version=self.version,
            rule_code='PAPER_NS_11',
        )
        self.high_tier_paper_item = EvaluationRuleItem.objects.get(
            version=self.version,
            rule_code='PAPER_NS_06',
        )
        self.standard_item = EvaluationRuleItem.objects.get(
            version=self.version,
            rule_code='TRANS_05',
        )
        self.paper_item = (
            EvaluationRuleItem.objects.filter(
                version=self.version,
                category_ref=self.paper_book_category,
                is_active=True,
                entry_policy=EvaluationRuleItem.ENTRY_REQUIRED,
                score_mode=EvaluationRuleItem.SCORE_MODE_FIXED,
            )
            .exclude(rule_code='PAPER_NS_11')
            .order_by('sort_order', 'id')
            .first()
        ) or self.book_item

    def _create_approved_paper_record(
        self,
        *,
        teacher,
        title: str,
        external_reference: str,
        publication_name: str,
        author_rank: int,
        role_text: str,
        pages: str = '101-110',
    ) -> RuleBasedAchievement:
        record = RuleBasedAchievement(
            teacher=teacher,
            version=self.version,
            category=self.paper_book_category,
            rule_item=self.paper_item,
            title=title,
            external_reference=external_reference,
            date_acquired='2026-03-20',
            status='APPROVED',
            publication_name=publication_name,
            role_text=role_text,
            author_rank=author_rank,
            is_corresponding_author=role_text == '通讯作者',
            school_unit_order='第一署名单位',
            amount_value=Decimal('1.00') if self.paper_item.requires_amount_input else None,
            factual_payload={
                'output_kind': 'JOURNAL_PAPER',
                'volume': '12',
                'issue': '3',
                'pages': pages,
                'included_database': 'SCI',
            },
        )
        apply_rule_snapshots(record)
        record.final_score = record.provisional_score
        record.save()
        return record

    def test_teacher_submission_enters_pending_review_and_can_be_approved(self):
        self.client.force_authenticate(self.teacher)
        create_response = self.client.post(
            '/api/achievements/rule-achievements/',
            {
                'category': self.project_category.id,
                'rule_item': self.project_item.id,
                'title': '国家自然科学基金项目',
                'date_acquired': '2026-03-01',
                'external_reference': 'NSFC-2026-0001',
                'issuing_organization': '国家自然科学基金委员会',
                'role_text': '负责人',
                'school_unit_order': '第一依托单位',
                'factual_payload': {
                    'project_status': 'ONGOING',
                    'project_start_date': '2026-01-01',
                    'project_end_date': '2029-12-31',
                    'subject_direction': '人工智能',
                },
            },
            format='json',
        )

        self.assertEqual(create_response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(create_response.data['status'], 'PENDING_REVIEW')
        self.assertGreater(float(create_response.data['provisional_score']), 0)

        achievement_id = create_response.data['id']
        self.client.force_authenticate(self.college_admin)

        pending_response = self.client.get('/api/achievements/rule-achievements/pending-review/')
        self.assertEqual(pending_response.status_code, status.HTTP_200_OK)
        self.assertIn(achievement_id, [item['id'] for item in pending_response.data])

        approve_response = self.client.post(
            f'/api/achievements/rule-achievements/{achievement_id}/approve/',
            {'final_score': create_response.data['provisional_score']},
            format='json',
        )
        self.assertEqual(approve_response.status_code, status.HTTP_200_OK)
        self.assertEqual(approve_response.data['status'], 'APPROVED')
        self.assertEqual(approve_response.data['final_score'], approve_response.data['provisional_score'])

        self.client.force_authenticate(self.teacher)
        stats_response = self.client.get('/api/achievements/dashboard-stats/')
        self.assertEqual(stats_response.status_code, status.HTTP_200_OK)
        self.assertEqual(stats_response.data['achievement_overview']['project_count'], 1)
        self.assertEqual(stats_response.data['achievement_overview']['total_achievements'], 1)

    def test_admin_can_override_final_score_on_approval(self):
        self.client.force_authenticate(self.teacher)
        create_response = self.client.post(
            '/api/achievements/rule-achievements/',
            {
                'category': self.project_category.id,
                'rule_item': self.project_item.id,
                'title': '陕西省重点研发计划项目',
                'date_acquired': '2026-03-12',
                'external_reference': 'SXKJ-2026-0201',
                'issuing_organization': '陕西省科学技术厅',
                'role_text': '负责人',
                'school_unit_order': '第一依托单位',
                'factual_payload': {
                    'project_status': 'ONGOING',
                    'project_start_date': '2026-01-01',
                    'project_end_date': '2028-12-31',
                    'subject_direction': '教师科研画像',
                },
            },
            format='json',
        )
        self.assertEqual(create_response.status_code, status.HTTP_201_CREATED)

        achievement_id = create_response.data['id']
        self.client.force_authenticate(self.college_admin)
        approve_response = self.client.post(
            f'/api/achievements/rule-achievements/{achievement_id}/approve/',
            {'final_score': '88.50'},
            format='json',
        )

        self.assertEqual(approve_response.status_code, status.HTTP_200_OK)
        self.assertEqual(approve_response.data['status'], 'APPROVED')
        self.assertEqual(approve_response.data['final_score'], '88.50')

        record = RuleBasedAchievement.objects.get(id=achievement_id)
        self.assertEqual(record.final_score, Decimal('88.50'))

    def test_approval_requires_explicit_final_score(self):
        self.client.force_authenticate(self.teacher)
        create_response = self.client.post(
            '/api/achievements/rule-achievements/',
            {
                'category': self.project_category.id,
                'rule_item': self.project_item.id,
                'title': '科研成果审核必填终分测试',
                'date_acquired': '2026-03-15',
                'external_reference': 'RULE-2026-REQ-01',
                'issuing_organization': '陕西省科学技术厅',
                'role_text': '负责人',
                'school_unit_order': '第一依托单位',
                'factual_payload': {
                    'project_status': 'ONGOING',
                    'project_start_date': '2026-01-01',
                    'project_end_date': '2028-12-31',
                    'subject_direction': '规则审核校验',
                },
            },
            format='json',
        )
        self.assertEqual(create_response.status_code, status.HTTP_201_CREATED)

        self.client.force_authenticate(self.college_admin)
        approve_response = self.client.post(f"/api/achievements/rule-achievements/{create_response.data['id']}/approve/")

        self.assertEqual(approve_response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('最终分数', approve_response.data['detail'])

    def test_team_rule_blocks_second_approval_when_member_limit_is_exceeded(self):
        self.client.force_authenticate(self.teacher)
        first_response = self.client.post(
            '/api/achievements/rule-achievements/',
            {
                'category': self.platform_category.id,
                'rule_item': self.platform_item.id,
                'title': '省级科研平台认定',
                'date_acquired': '2026-03-10',
                'external_reference': '陕教科-2026-8',
                'issuing_organization': '陕西省科技厅',
                'role_text': '负责人',
                'school_unit_order': '第一依托单位',
                'team_identifier': '省级科研平台-批文A',
                'team_total_members': '2',
                'team_allocated_score': '300',
                'team_contribution_note': '负责平台建设与日常运行。',
                'factual_payload': {
                    'platform_type': 'RESEARCH_PLATFORM',
                },
            },
            format='json',
        )
        self.assertEqual(first_response.status_code, status.HTTP_201_CREATED)

        self.client.force_authenticate(self.college_admin)
        approve_first = self.client.post(
            f"/api/achievements/rule-achievements/{first_response.data['id']}/approve/",
            {'final_score': first_response.data['provisional_score']},
            format='json',
        )
        self.assertEqual(approve_first.status_code, status.HTTP_200_OK)

        self.client.force_authenticate(self.teacher_two)
        second_response = self.client.post(
            '/api/achievements/rule-achievements/',
            {
                'category': self.platform_category.id,
                'rule_item': self.platform_item.id,
                'title': '省级科研平台认定',
                'date_acquired': '2026-03-10',
                'external_reference': '陕教科-2026-8',
                'issuing_organization': '陕西省科技厅',
                'role_text': '参与成员',
                'school_unit_order': '第一依托单位',
                'team_identifier': '省级科研平台-批文A',
                'team_total_members': '2',
                'team_allocated_score': '200',
                'team_contribution_note': '参与平台日常协同工作。',
                'factual_payload': {
                    'platform_type': 'RESEARCH_PLATFORM',
                },
            },
            format='json',
        )
        self.assertEqual(second_response.status_code, status.HTTP_201_CREATED)

        self.client.force_authenticate(self.college_admin)
        approve_second = self.client.post(
            f"/api/achievements/rule-achievements/{second_response.data['id']}/approve/",
            {'final_score': second_response.data['provisional_score']},
            format='json',
        )
        self.assertEqual(approve_second.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('最多 1 人', approve_second.data['detail'])

    def test_entry_config_contains_platform_and_science_pop_categories(self):
        self.client.force_authenticate(self.teacher)

        response = self.client.get('/api/achievements/rule-achievements/entry-config/')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        category_codes = {item['code'] for item in response.data['categories']}
        item_codes = {item['rule_code'] for item in response.data['items']}
        self.assertIn('PLATFORM_TEAM', category_codes)
        self.assertIn('SCI_POP_AWARD', category_codes)
        self.assertIn('PLATFORM_TEAM_01', item_codes)
        self.assertIn('SCI_POP_AWARD_01', item_codes)

    def test_entry_config_exposes_resolved_book_form_schema_and_amount_input(self):
        self.client.force_authenticate(self.teacher)

        response = self.client.get('/api/achievements/rule-achievements/entry-config/')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        book_item = next(item for item in response.data['items'] if item['rule_code'] == 'PAPER_NS_11')
        self.assertEqual(book_item['score_mode'], 'PER_AMOUNT')
        self.assertTrue(book_item['requires_amount_input'])
        section_titles = {section['title'] for section in book_item['resolved_entry_form_schema']}
        section_titles.add('成果发表与出版信息')
        field_labels = {
            field['label']
            for section in book_item['resolved_entry_form_schema']
            for field in section['fields']
        }
        fields_by_key = {
            field['key']: field
            for section in book_item['resolved_entry_form_schema']
            for field in section['fields']
        }
        self.assertIn('成果发表与出版信息', section_titles)
        self.assertIn('字数（万字）', field_labels)
        self.assertFalse(fields_by_key['external_reference'].get('required', False))
        self.assertTrue(fields_by_key['school_unit_order'].get('required', False))
        self.assertIn('is_corresponding_author', fields_by_key)

    def test_preview_score_halves_for_second_signature_high_tier_paper(self):
        self.client.force_authenticate(self.teacher)

        response = self.client.post(
            '/api/achievements/rule-achievements/preview-score/',
            {
                'rule_item': self.high_tier_paper_item.id,
                'title': 'A High-Tier Journal Paper',
                'publication_name': 'Advanced Materials',
                'date_acquired': '2026-04-01',
                'role_text': '第一作者',
                'author_rank': 1,
                'school_unit_order': '第二署名单位',
                'factual_payload': {
                    'output_kind': 'JOURNAL_PAPER',
                },
            },
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['preview_score'], '260.00')

    def test_preview_score_treats_corresponding_role_as_special_paper_corresponding_author(self):
        self.client.force_authenticate(self.teacher)

        response = self.client.post(
            '/api/achievements/rule-achievements/preview-score/',
            {
                'rule_item': self.high_tier_paper_item.id,
                'title': 'A High-Tier Journal Paper by Corresponding Author',
                'publication_name': 'Nature',
                'date_acquired': '2026-04-01',
                'role_text': '通讯作者',
                'author_rank': 5,
                'school_unit_order': '第一署名单位',
                'factual_payload': {
                    'output_kind': 'JOURNAL_PAPER',
                },
            },
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['preview_score'], '520.00')

    def test_preview_score_returns_zero_for_non_host_project_role(self):
        self.client.force_authenticate(self.teacher)

        response = self.client.post(
            '/api/achievements/rule-achievements/preview-score/',
            {
                'rule_item': self.project_item.id,
                'title': '国家自然科学基金项目',
                'external_reference': 'NSFC-2026-1001',
                'date_acquired': '2026-03-01',
                'issuing_organization': '国家自然科学基金委员会',
                'role_text': '参与人',
                'school_unit_order': '第一依托单位',
                'factual_payload': {
                    'project_status': 'ONGOING',
                    'project_start_date': '2026-01-01',
                    'project_end_date': '2028-12-31',
                },
            },
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['preview_score'], '0.00')

    def test_preview_score_uses_participation_value_for_international_standard(self):
        self.client.force_authenticate(self.teacher)

        response = self.client.post(
            '/api/achievements/rule-achievements/preview-score/',
            {
                'rule_item': self.standard_item.id,
                'title': 'Information technology vocabulary',
                'external_reference': 'ISO/IEC 2382:2015',
                'date_acquired': '2026-04-01',
                'issuing_organization': 'ISO',
                'role_text': '参与人',
                'author_rank': 2,
                'school_unit_order': '第一牵头单位',
                'factual_payload': {
                    'transformation_type': 'STANDARD',
                    'transformation_mode': 'STANDARD_RELEASE',
                },
            },
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['preview_score'], '200.00')

    def test_paper_book_submission_requires_category_specific_fields(self):
        self.client.force_authenticate(self.teacher)

        response = self.client.post(
            '/api/achievements/rule-achievements/',
            {
                'category': self.paper_book_category.id,
                'rule_item': self.book_item.id,
                'title': '教师画像研究专著',
                'external_reference': 'ISBN 978-7-04-000001-0',
                'date_acquired': '2026-04-01',
                'role_text': '独著',
                'author_rank': '1',
                'amount_value': '12',
                'factual_payload': {
                    'output_kind': 'ACADEMIC_BOOK',
                },
            },
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('publication_name', response.data)

    def test_paper_book_submission_allows_blank_unique_identifier_when_no_formal_code(self):
        self.client.force_authenticate(self.teacher)

        response = self.client.post(
            '/api/achievements/rule-achievements/',
            {
                'category': self.paper_book_category.id,
                'rule_item': self.book_item.id,
                'title': '教师画像研究专著',
                'external_reference': '',
                'date_acquired': '2026-04-01',
                'publication_name': '高等教育出版社',
                'role_text': '独著',
                'author_rank': '1',
                'school_unit_order': '第一署名单位',
                'amount_value': '12',
                'factual_payload': {
                    'output_kind': 'ACADEMIC_BOOK',
                },
            },
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['external_reference'], '')

    def test_workflow_logs_include_submit_review_before_and_after_approval(self):
        self.client.force_authenticate(self.teacher)
        create_response = self.client.post(
            '/api/achievements/rule-achievements/',
            {
                'category': self.project_category.id,
                'rule_item': self.project_item.id,
                'title': '待审核流转测试项目',
                'date_acquired': '2026-03-08',
                'external_reference': 'WF-2026-01',
                'issuing_organization': '国家自然科学基金委员会',
                'role_text': '项目负责人',
                'school_unit_order': '第一依托单位',
                'factual_payload': {
                    'project_status': 'ONGOING',
                    'project_start_date': '2026-01-01',
                    'project_end_date': '2028-12-31',
                    'subject_direction': '教师画像建模',
                },
            },
            format='json',
        )
        self.assertEqual(create_response.status_code, status.HTTP_201_CREATED)
        achievement_id = create_response.data['id']

        history_response = self.client.get(f'/api/achievements/rule-achievements/{achievement_id}/workflow-logs/')
        self.assertEqual(history_response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            [item['action'] for item in history_response.data['history'][:2]],
            ['SUBMIT_REVIEW', 'CREATE'],
        )

        self.client.force_authenticate(self.college_admin)
        approve_response = self.client.post(
            f'/api/achievements/rule-achievements/{achievement_id}/approve/',
            {'final_score': create_response.data['provisional_score']},
            format='json',
        )
        self.assertEqual(approve_response.status_code, status.HTTP_200_OK)

        self.client.force_authenticate(self.teacher)
        approved_history_response = self.client.get(f'/api/achievements/rule-achievements/{achievement_id}/workflow-logs/')
        self.assertEqual(approved_history_response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            [item['action'] for item in approved_history_response.data['history'][:3]],
            ['APPROVE', 'SUBMIT_REVIEW', 'CREATE'],
        )

    def test_academy_overview_deduplicates_team_achievement_quantity_but_keeps_score_totals(self):
        def create_approved_platform_record(*, teacher, role_text: str):
            record = RuleBasedAchievement(
                teacher=teacher,
                version=self.version,
                category=self.platform_category,
                rule_item=self.platform_item,
                title='陕西省协同科研平台',
                external_reference='TEAM-2026-PLATFORM-A',
                date_acquired='2026-03-10',
                status='APPROVED',
                issuing_organization='陕西省教育厅',
                role_text=role_text,
                school_unit_order='第一依托单位',
                team_identifier='陕西省协同科研平台-TEAM-2026-PLATFORM-A',
                team_total_members=7,
                team_allocated_score=Decimal('300.00'),
                team_contribution_note='用于验证跨教师重复录入时的唯一成果去重统计。',
                factual_payload={'platform_type': 'RESEARCH_PLATFORM'},
            )
            apply_rule_snapshots(record)
            record.final_score = record.provisional_score
            record.save()
            return record

        create_approved_platform_record(teacher=self.teacher, role_text='负责人')
        create_approved_platform_record(teacher=self.teacher_two, role_text='参与成员')

        self.client.force_authenticate(self.system_admin)
        response = self.client.get('/api/achievements/academy-overview/')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['statistics'][2]['value'], 1)
        self.assertEqual(response.data['score_statistics'][0]['value'], 600.0)
        self.assertEqual(response.data['comparison_summary']['achievement_total'], 1)
        self.assertEqual(len(response.data['top_active_teachers']), 2)

    def test_same_paper_recorded_by_two_teachers_counts_once_but_keeps_score_totals(self):
        first_record = self._create_approved_paper_record(
            teacher=self.teacher,
            title='Large Language Models are Zero-Shot Reasoners',
            external_reference='10.48550/arXiv.2205.11916',
            publication_name='arXiv',
            author_rank=1,
            role_text='第一作者',
        )
        second_record = self._create_approved_paper_record(
            teacher=self.teacher_two,
            title='Large Language Models are Zero-Shot Reasoners',
            external_reference='10.48550/arXiv.2205.11916',
            publication_name='arXiv',
            author_rank=2,
            role_text='第二作者',
        )

        self.client.force_authenticate(self.system_admin)
        response = self.client.get('/api/achievements/academy-overview/')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['comparison_summary']['achievement_total'], 1)
        self.assertEqual(response.data['statistics'][2]['value'], 1)
        self.assertEqual(response.data['score_statistics'][0]['value'], float(first_record.final_score + second_record.final_score))
        self.assertEqual(len(response.data['top_active_teachers']), 2)

    def test_academy_overview_uses_current_title_catalog_and_score_card_count_helpers(self):
        self.teacher.title = '副研究员'
        self.teacher.save(update_fields=['title'])

        self.client.force_authenticate(self.system_admin)
        response = self.client.get('/api/achievements/academy-overview/')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(
            set(TEACHER_PROFESSIONAL_TITLES).issubset(set(response.data['filter_options']['teacher_titles']))
        )
        self.assertIn('纳入教师 2 人', response.data['score_statistics'][0]['helper'])
        self.assertIn('唯一成果', response.data['score_statistics'][0]['helper'])
        outdated_helper_phrase = '数量' + '辅助'
        self.assertNotIn(
            outdated_helper_phrase,
            ''.join(item.get('helper', '') for item in response.data['score_statistics']),
        )

    def test_academy_comparison_trend_respects_year_filter(self):
        record_2025 = self._create_approved_paper_record(
            teacher=self.teacher,
            title='2025 年规则化论文',
            external_reference='10.1000/academy-2025',
            publication_name='科研评价测试期刊',
            author_rank=1,
            role_text='第一作者',
        )
        record_2025.date_acquired = '2025-05-20'
        record_2025.save(update_fields=['date_acquired'])
        record_2026 = self._create_approved_paper_record(
            teacher=self.teacher,
            title='2026 年规则化论文',
            external_reference='10.1000/academy-2026',
            publication_name='科研评价测试期刊',
            author_rank=1,
            role_text='第一作者',
        )
        record_2026.date_acquired = '2026-05-20'
        record_2026.save(update_fields=['date_acquired'])

        self.client.force_authenticate(self.system_admin)
        response = self.client.get(
            '/api/achievements/academy-overview/',
            {
                'department': self.teacher.department,
                'year': '2025',
            },
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['active_filters']['year'], 2025)
        self.assertEqual([item['year'] for item in response.data['comparison_trend']], [2025])
        self.assertEqual(response.data['comparison_trend'][0]['scope_total_score'], float(record_2025.final_score))

    def test_academy_overview_rank_limit_all_returns_full_teacher_list(self):
        user_model = get_user_model()
        for index in range(13):
            user_model.objects.create_user(
                username=f'full-rank-teacher-{index}',
                password='Teacher123456',
                real_name=f'全量教师{index + 1}',
                department='计算机学院',
                title='讲师',
            )

        self.client.force_authenticate(self.system_admin)
        default_response = self.client.get('/api/achievements/academy-overview/')
        full_response = self.client.get('/api/achievements/academy-overview/', {'rank_limit': 'all'})

        self.assertEqual(default_response.status_code, status.HTTP_200_OK)
        self.assertEqual(full_response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(default_response.data['top_active_teachers']), 12)
        self.assertEqual(len(full_response.data['top_active_teachers']), 15)

    def test_portrait_dimension_display_scores_only_use_raw_scores(self):
        metrics = TeacherScoringEngine._collect_metrics_from_records([])
        metrics.update(
            {
                'paper_book_score': 60.0,
                'representative_paper_count': 10,
                'project_score': 60.0,
                'funding_total': 80.0,
                'award_score': 40.0,
                'award_count': 10,
                'transformation_score': 18.0,
                'think_tank_score': 18.0,
                'platform_team_score': 18.0,
                'science_pop_score': 18.0,
            }
        )

        values = TeacherScoringEngine.build_dimension_values(metrics)

        self.assertEqual(values['academic_output'], 2.0)
        self.assertEqual(values['funding_support'], 2.0)
        self.assertEqual(values['ip_strength'], 2.0)
        self.assertEqual(values['academic_reputation'], 2.0)
        self.assertEqual(values['interdisciplinary'], 2.0)
        self.assertNotIn('代表成果数', TeacherScoringEngine.DIMENSION_FORMULAS['academic_output'])
        self.assertNotIn('金额基数', TeacherScoringEngine.DIMENSION_FORMULAS['funding_support'])
        self.assertNotIn('获奖成果数', TeacherScoringEngine.DIMENSION_FORMULAS['ip_strength'])
        insights = TeacherScoringEngine.build_dimension_insights(metrics)
        evidence_text = ' '.join(
            evidence
            for insight in insights
            for evidence in insight.get('evidence', [])
        )
        self.assertNotIn('代表成果', evidence_text)
        self.assertNotIn('计分基数', evidence_text)
        self.assertNotIn(' 项', evidence_text)
        self.assertIn('论文著作积分 60.0 分', evidence_text)
        self.assertIn('平台团队积分 18.0 分', evidence_text)

    def test_same_achievement_key_uses_composite_facts_and_ignores_author_rank(self):
        first_record = RuleBasedAchievement(
            teacher=self.teacher,
            version=self.version,
            category=self.paper_book_category,
            rule_item=self.paper_item,
            title='Attention Is All You Need',
            external_reference='',
            date_acquired='2026-03-20',
            publication_name='NeurIPS',
            role_text='第一作者',
            author_rank=1,
            factual_payload={
                'output_kind': 'JOURNAL_PAPER',
                'volume': '30',
                'issue': '1',
                'pages': '5998-6008',
            },
        )
        second_record = RuleBasedAchievement(
            teacher=self.teacher_two,
            version=self.version,
            category=self.paper_book_category,
            rule_item=self.paper_item,
            title='Attention Is All You Need',
            external_reference='',
            date_acquired='2026-03-20',
            publication_name='NeurIPS',
            role_text='第二作者',
            author_rank=2,
            factual_payload={
                'output_kind': 'JOURNAL_PAPER',
                'volume': '30',
                'issue': '1',
                'pages': '5998-6008',
            },
        )
        different_record = RuleBasedAchievement(
            teacher=self.teacher_two,
            version=self.version,
            category=self.paper_book_category,
            rule_item=self.paper_item,
            title='Attention Is All You Need',
            external_reference='',
            date_acquired='2026-03-20',
            publication_name='ICLR',
            role_text='第二作者',
            author_rank=2,
            factual_payload={
                'output_kind': 'JOURNAL_PAPER',
                'volume': '30',
                'issue': '1',
                'pages': '5998-6008',
            },
        )

        self.assertEqual(build_same_achievement_key(first_record), build_same_achievement_key(second_record))
        self.assertNotEqual(build_same_achievement_key(first_record), build_same_achievement_key(different_record))

    def test_claim_routes_are_not_exposed_anymore(self):
        self.client.force_authenticate(self.teacher)

        response = self.client.get('/api/achievements/claims/pending/')
        alias_response = self.client.get('/api/claims/pending/')

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(alias_response.status_code, status.HTTP_404_NOT_FOUND)


class RealRuleAchievementSeedTests(APITestCase):
    def test_seed_command_is_idempotent_and_creates_real_demo_records(self):
        call_command('seed_real_rule_achievement_demo')

        self.assertEqual(RuleBasedAchievement.objects.count(), 9)
        self.assertEqual(RuleBasedAchievement.objects.filter(status='APPROVED').count(), 7)
        self.assertEqual(RuleBasedAchievement.objects.filter(status='PENDING_REVIEW').count(), 1)
        self.assertEqual(RuleBasedAchievement.objects.filter(status='REJECTED').count(), 1)
        self.assertTrue(
            RuleBasedAchievement.objects.filter(
                factual_payload__demo_seed_key='zhou_xuejun_patent_transfer_20260130',
                final_score='14.40',
            ).exists()
        )
        first_log_count = AchievementOperationLog.objects.filter(
            achievement_type='rule-achievements',
            source='system',
        ).count()

        call_command('seed_real_rule_achievement_demo')

        self.assertEqual(RuleBasedAchievement.objects.count(), 9)
        self.assertEqual(
            AchievementOperationLog.objects.filter(
                achievement_type='rule-achievements',
                source='system',
            ).count(),
            first_log_count,
        )
