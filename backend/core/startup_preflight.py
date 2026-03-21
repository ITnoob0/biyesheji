from __future__ import annotations

from dataclasses import dataclass, field
from importlib import import_module

from django.apps import apps
from django.contrib.auth import get_user_model
from django.db import connections
from django.db.migrations.executor import MigrationExecutor


REQUIRED_DEPENDENCIES: tuple[tuple[str, str], ...] = (
    ("django", "Django"),
    ("rest_framework", "djangorestframework"),
    ("rest_framework_simplejwt", "djangorestframework-simplejwt"),
    ("corsheaders", "django-cors-headers"),
    ("pymysql", "PyMySQL"),
)


@dataclass(slots=True)
class PreflightCheckResult:
    key: str
    passed: bool
    summary: str
    next_step: str = ""
    details: list[str] = field(default_factory=list)


class StartupPreflightService:
    def __init__(self, using: str = "default") -> None:
        self.using = using

    def run_checks(self) -> list[PreflightCheckResult]:
        return [
            self.check_dependencies(),
            self.check_database_connection(),
            self.check_migration_state(),
            self.check_required_tables(),
        ]

    def check_dependencies(self) -> PreflightCheckResult:
        missing: list[str] = []
        for module_name, package_name in REQUIRED_DEPENDENCIES:
            try:
                import_module(module_name)
            except Exception:
                missing.append(package_name)

        if missing:
            return PreflightCheckResult(
                key="dependencies",
                passed=False,
                summary=f"缺少关键依赖：{', '.join(missing)}。",
                next_step=(
                    "请先安装缺失依赖，再继续执行迁移或启动。"
                    " 示例：python -m pip install django djangorestframework "
                    "djangorestframework-simplejwt django-cors-headers PyMySQL"
                ),
                details=["当前检查只覆盖后端启动与数据库连接必需的关键依赖。"],
            )

        installed = ", ".join(package_name for _, package_name in REQUIRED_DEPENDENCIES)
        return PreflightCheckResult(
            key="dependencies",
            passed=True,
            summary="关键依赖已安装。",
            details=[f"已确认关键依赖可导入：{installed}。"],
        )

    def check_database_connection(self) -> PreflightCheckResult:
        connection = connections[self.using]
        settings_dict = connection.settings_dict

        try:
            connection.ensure_connection()
            with connection.cursor() as cursor:
                cursor.execute("SELECT 1")
                cursor.fetchone()
        except Exception as exc:
            return PreflightCheckResult(
                key="database_connection",
                passed=False,
                summary=f"MySQL 连接不可用：{exc}",
                next_step=(
                    "请确认 MySQL 服务已启动，并核对 backend/core/settings.py 中的 "
                    "NAME、USER、PASSWORD、HOST、PORT 配置。"
                ),
                details=[
                    f"当前连接目标：{settings_dict.get('HOST', '')}:{settings_dict.get('PORT', '')}",
                    f"当前数据库：{settings_dict.get('NAME', '')}",
                ],
            )

        return PreflightCheckResult(
            key="database_connection",
            passed=True,
            summary="MySQL 连接可用。",
            details=[
                f"连接目标：{settings_dict.get('HOST', '')}:{settings_dict.get('PORT', '')}",
                f"数据库：{settings_dict.get('NAME', '')}",
            ],
        )

    def check_migration_state(self) -> PreflightCheckResult:
        connection = connections[self.using]

        try:
            executor = MigrationExecutor(connection)
            targets = executor.loader.graph.leaf_nodes()
            plan = executor.migration_plan(targets)
        except Exception as exc:
            return PreflightCheckResult(
                key="migration_state",
                passed=False,
                summary=f"无法检查迁移状态：{exc}",
                next_step="请先修复数据库连接或迁移元数据问题，再重新执行启动前检查。",
            )

        if plan:
            pending = [f"{migration.app_label}.{migration.name}" for migration, _ in plan]
            return PreflightCheckResult(
                key="migration_state",
                passed=False,
                summary=f"检测到 {len(pending)} 个未执行迁移。",
                next_step="请执行 `python manage.py migrate` 后重新运行启动前检查。",
                details=pending[:10]
                + (["..."] if len(pending) > 10 else []),
            )

        return PreflightCheckResult(
            key="migration_state",
            passed=True,
            summary="所有迁移均已执行。",
        )

    def check_required_tables(self) -> PreflightCheckResult:
        connection = connections[self.using]
        table_names = set(connection.introspection.table_names())
        required_tables = self.get_required_table_names()
        missing_tables = [table for table in required_tables if table not in table_names]

        if missing_tables:
            return PreflightCheckResult(
                key="required_tables",
                passed=False,
                summary=f"缺少必要表结构：{', '.join(missing_tables)}。",
                next_step=(
                    "请先执行 `python manage.py migrate`，若仍缺表，再检查数据库是否连接到了正确实例。"
                ),
            )

        return PreflightCheckResult(
            key="required_tables",
            passed=True,
            summary="必要表结构已存在。",
            details=required_tables,
        )

    @staticmethod
    def get_required_table_names() -> list[str]:
        user_table = get_user_model()._meta.db_table
        teacher_profile_table = apps.get_model("achievements", "TeacherProfile")._meta.db_table
        paper_table = apps.get_model("achievements", "Paper")._meta.db_table
        guide_table = apps.get_model("project_guides", "ProjectGuide")._meta.db_table
        return [
            "django_migrations",
            user_table,
            teacher_profile_table,
            paper_table,
            guide_table,
        ]
