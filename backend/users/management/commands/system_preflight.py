from django.core.management.base import BaseCommand, CommandError

from core.startup_preflight import StartupPreflightService


class Command(BaseCommand):
    help = "Run startup preflight checks for dependencies, MySQL connectivity, migrations, and required tables."

    def add_arguments(self, parser):
        parser.add_argument(
            "--database",
            default="default",
            help="Database alias to inspect. Defaults to 'default'.",
        )

    def handle(self, *args, **options):
        service = StartupPreflightService(using=options["database"])
        results = service.run_checks()
        failed_results = [item for item in results if not item.passed]

        for item in results:
            status_label = "PASS" if item.passed else "FAIL"
            write_method = self.stdout.write if item.passed else self.stderr.write
            write_method(f"[{status_label}] {item.summary}")

            for detail in item.details:
                write_method(f"  - {detail}")

            if item.next_step:
                write_method(f"  处理建议：{item.next_step}")

        self.stdout.write("")
        self.stdout.write("推荐启动顺序：")
        self.stdout.write("1. python scripts\\startup_preflight.py")
        self.stdout.write("2. python manage.py migrate")
        self.stdout.write("3. python scripts\\startup_preflight.py")
        self.stdout.write("4. python scripts\\restore_demo_state.py")
        self.stdout.write("5. python manage.py runserver")

        if failed_results:
            raise CommandError("启动前检查未通过，请先按上述建议处理后再继续执行迁移或启动。")

        self.stdout.write(self.style.SUCCESS("启动前检查通过，可继续执行迁移、初始化和服务启动。"))
