from io import StringIO

from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.test import TestCase

from achievements.models import Paper
from project_guides.models import ProjectGuide
from users.management.commands.init_demo_teachers import Command as InitDemoTeachersCommand


class DemoInitializationCommandTests(TestCase):
    def test_existing_demo_account_passwords_are_preserved_by_default(self):
        call_command("init_demo_teachers")
        user_model = get_user_model()
        teacher = user_model.objects.get(id=100001)
        admin = user_model.objects.get(username="admin")

        teacher.set_password("TeacherKeepMe123!")
        teacher.password_reset_required = False
        teacher.save(update_fields=["password", "password_reset_required"])

        admin.set_password("AdminKeepMe123!")
        admin.save(update_fields=["password"])

        call_command("init_demo_teachers")

        teacher.refresh_from_db()
        admin.refresh_from_db()
        self.assertTrue(teacher.check_password("TeacherKeepMe123!"))
        self.assertTrue(admin.check_password("AdminKeepMe123!"))

    def test_reset_demo_data_restores_standard_demo_teachers_and_guides(self):
        call_command("init_demo_teachers")
        user_model = get_user_model()
        demo_teacher = user_model.objects.get(id=100001)
        Paper.objects.create(
            teacher=demo_teacher,
            title="应被重置删除的临时论文",
            abstract="用于验证重置演示数据时，会删除内置演示教师名下的临时脏数据。",
            date_acquired="2026-03-01",
            paper_type="JOURNAL",
            journal_name="测试期刊",
            doi="10.2026/demo-reset-extra-paper",
        )

        call_command("init_demo_teachers", reset_demo_data=True)

        restored_teacher = user_model.objects.get(id=100001)
        self.assertTrue(restored_teacher.check_password(InitDemoTeachersCommand.DEMO_ACCOUNT_PASSWORD))
        self.assertTrue(restored_teacher.password_reset_required)
        self.assertFalse(Paper.objects.filter(doi="10.2026/demo-reset-extra-paper").exists())
        self.assertEqual(ProjectGuide.objects.filter(source_url__startswith="https://demo.local/guides/").count(), 4)

    def test_explicit_reset_passwords_restores_standard_demo_passwords(self):
        call_command("init_demo_teachers")
        user_model = get_user_model()
        teacher = user_model.objects.get(id=100001)
        admin = user_model.objects.get(username="admin")

        teacher.set_password("TeacherKeepMe123!")
        teacher.password_reset_required = False
        teacher.save(update_fields=["password", "password_reset_required"])
        admin.set_password("AdminKeepMe123!")
        admin.save(update_fields=["password"])

        call_command("init_demo_teachers", reset_passwords=True)

        teacher.refresh_from_db()
        admin.refresh_from_db()
        self.assertTrue(teacher.check_password(InitDemoTeachersCommand.DEMO_ACCOUNT_PASSWORD))
        self.assertTrue(teacher.password_reset_required)
        self.assertTrue(admin.check_password(InitDemoTeachersCommand.DEMO_ACCOUNT_PASSWORD))

    def test_print_accounts_outputs_demo_account_summary(self):
        stdout = StringIO()

        call_command("init_demo_teachers", print_accounts=True, stdout=stdout)

        output = stdout.getvalue()
        self.assertIn("演示账号清单", output)
        self.assertIn("管理员账号：admin", output)
        self.assertIn("教师账号密码", output)
        self.assertIn("教师账号：100001", output)
