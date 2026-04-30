from __future__ import annotations

from django.core.management.base import BaseCommand, CommandError

from achievements.legacy_rule_migration import LegacyAchievementRuleMigrator


class Command(BaseCommand):
    help = '将旧成果模型中的历史数据批量自动映射迁移到规则化成果体系。'

    def add_arguments(self, parser):
        parser.add_argument(
            '--apply',
            action='store_true',
            help='实际写入数据库；不传时仅做干跑预览。',
        )
        parser.add_argument(
            '--teacher-id',
            type=int,
            default=None,
            help='仅迁移指定教师的历史成果。',
        )

    def handle(self, *args, **options):
        migrator = LegacyAchievementRuleMigrator(
            apply_changes=bool(options['apply']),
            teacher_id=options.get('teacher_id'),
            stdout=self.stdout,
        )
        try:
            result = migrator.run()
        except RuntimeError as exc:
            raise CommandError(str(exc)) from exc

        summary = result['summary']
        if options['apply']:
            self.stdout.write(
                self.style.SUCCESS(
                    f"历史成果迁移完成：新增 {summary['created']} 条，已存在 {summary['existing']} 条，跳过 {summary['skipped']} 条。"
                )
            )
        else:
            self.stdout.write(
                self.style.WARNING(
                    f"历史成果迁移干跑完成：预计新增 {summary['created']} 条，已存在 {summary['existing']} 条，跳过 {summary['skipped']} 条。"
                )
            )
