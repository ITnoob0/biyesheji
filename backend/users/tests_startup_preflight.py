from io import StringIO
from unittest.mock import patch

from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import TestCase

from core.startup_preflight import PreflightCheckResult, StartupPreflightService


class StartupPreflightServiceTests(TestCase):
    def test_run_checks_pass_in_current_test_environment(self):
        service = StartupPreflightService()

        results = service.run_checks()

        self.assertEqual([item.key for item in results], [
            "dependencies",
            "database_connection",
            "migration_state",
            "required_tables",
        ])
        self.assertTrue(all(item.passed for item in results))

    def test_required_table_names_cover_core_tables(self):
        tables = StartupPreflightService.get_required_table_names()

        self.assertIn("django_migrations", tables)
        self.assertIn("users_customuser", tables)
        self.assertIn("achievements_teacherprofile", tables)
        self.assertIn("achievements_paper", tables)
        self.assertIn("project_guides_projectguide", tables)


class SystemPreflightCommandTests(TestCase):
    def test_command_outputs_success_summary(self):
        stdout = StringIO()

        call_command("system_preflight", stdout=stdout)

        output = stdout.getvalue()
        self.assertIn("[PASS] 关键依赖已安装。", output)
        self.assertIn("推荐启动顺序：", output)
        self.assertIn("python scripts\\startup_preflight.py", output)
        self.assertIn("启动前检查通过", output)

    @patch("users.management.commands.system_preflight.StartupPreflightService.run_checks")
    def test_command_fails_with_actionable_message_when_check_fails(self, mocked_run_checks):
        mocked_run_checks.return_value = [
            PreflightCheckResult(
                key="dependencies",
                passed=True,
                summary="关键依赖已安装。",
            ),
            PreflightCheckResult(
                key="migration_state",
                passed=False,
                summary="检测到 2 个未执行迁移。",
                next_step="请执行 `python manage.py migrate`。",
                details=["users.0002_customuser_password_lifecycle"],
            ),
        ]

        stdout = StringIO()
        stderr = StringIO()

        with self.assertRaises(CommandError):
            call_command("system_preflight", stdout=stdout, stderr=stderr)

        error_output = stderr.getvalue()
        self.assertIn("[FAIL] 检测到 2 个未执行迁移。", error_output)
        self.assertIn("请执行 `python manage.py migrate`。", error_output)
