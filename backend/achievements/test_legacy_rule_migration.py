from __future__ import annotations

from io import StringIO

from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.test import TestCase

from achievements.models import (
    AcademicService,
    IntellectualProperty,
    Paper,
    PaperKeyword,
    Project,
    ResearchKeyword,
    RuleBasedAchievement,
)


class LegacyRuleMigrationCommandTests(TestCase):
    def setUp(self):
        user_model = get_user_model()
        self.teacher = user_model.objects.create_user(
            username='teacher001',
            password='Teacher123456',
            real_name='教师一',
            department='计算机学院',
            title='讲师',
        )

    def test_command_migrates_supported_records_and_preserves_status(self):
        paper = Paper.objects.create(
            teacher=self.teacher,
            title='面向知识图谱的科研画像研究',
            date_acquired='2024-06-01',
            status='APPROVED',
            paper_type='JOURNAL',
            journal_name='计算机科学',
            journal_level='CCF-B',
            is_first_author=True,
            is_corresponding_author=True,
            doi='10.1234/example',
        )
        keyword = ResearchKeyword.objects.create(name='知识图谱')
        PaperKeyword.objects.create(paper=paper, keyword=keyword)
        paper.coauthors.create(name='张三', organization='延安大学')

        project = Project.objects.create(
            teacher=self.teacher,
            title='陕西省自然科学基础研究一般项目',
            date_acquired='2023-05-10',
            status='DRAFT',
            level='PROVINCIAL',
            role='PI',
            funding_amount='18.00',
            project_status='ONGOING',
        )

        ip = IntellectualProperty.objects.create(
            teacher=self.teacher,
            title='一种科研画像分析方法',
            date_acquired='2022-09-15',
            status='APPROVED',
            ip_type='PATENT_INVENTION',
            role='PI',
            registration_number='CN202210000001.X',
            is_transformed=False,
        )

        AcademicService.objects.create(
            teacher=self.teacher,
            title='某期刊审稿',
            date_acquired='2024-01-10',
            status='APPROVED',
            service_type='REVIEWER',
            organization='某学术期刊',
        )

        output = StringIO()
        call_command('migrate_legacy_achievements_to_rules', '--apply', stdout=output)

        self.assertEqual(RuleBasedAchievement.objects.count(), 3)

        migrated_paper = RuleBasedAchievement.objects.get(factual_payload__legacy_source_key=f'legacy-paper-{paper.id}')
        self.assertEqual(migrated_paper.rule_item.rule_code, 'PAPER_NS_08')
        self.assertEqual(migrated_paper.status, 'APPROVED')
        self.assertEqual(str(migrated_paper.final_score), '320.00')
        self.assertEqual(migrated_paper.keywords_text, '知识图谱')
        self.assertEqual(migrated_paper.coauthor_names, ['张三'])

        migrated_project = RuleBasedAchievement.objects.get(factual_payload__legacy_source_key=f'legacy-project-{project.id}')
        self.assertEqual(migrated_project.rule_item.rule_code, 'PROJECT_NS_11')
        self.assertEqual(migrated_project.status, 'DRAFT')
        self.assertEqual(str(migrated_project.final_score), '0.00')

        migrated_ip = RuleBasedAchievement.objects.get(
            factual_payload__legacy_source_key=f'legacy-intellectualproperty-{ip.id}'
        )
        self.assertEqual(migrated_ip.rule_item.rule_code, 'TRANS_02')
        self.assertEqual(str(migrated_ip.final_score), '200.00')

        self.assertIn('跳过 1 条', output.getvalue())

    def test_command_is_idempotent_for_same_legacy_source(self):
        Paper.objects.create(
            teacher=self.teacher,
            title='多模态科研画像论文',
            date_acquired='2024-03-01',
            status='APPROVED',
            paper_type='CONFERENCE',
            journal_name='学术会议',
            journal_level='会议论文',
        )

        call_command('migrate_legacy_achievements_to_rules', '--apply', stdout=StringIO())
        call_command('migrate_legacy_achievements_to_rules', '--apply', stdout=StringIO())

        self.assertEqual(RuleBasedAchievement.objects.count(), 1)

    def test_command_skips_unsupported_legacy_records(self):
        IntellectualProperty.objects.create(
            teacher=self.teacher,
            title='科研画像平台软件',
            date_acquired='2024-01-01',
            status='APPROVED',
            ip_type='SOFTWARE_COPYRIGHT',
            role='PI',
            registration_number='2024SR000001',
            is_transformed=True,
        )

        output = StringIO()
        call_command('migrate_legacy_achievements_to_rules', '--apply', stdout=output)

        self.assertEqual(RuleBasedAchievement.objects.count(), 0)
        self.assertIn('[skipped]', output.getvalue())
