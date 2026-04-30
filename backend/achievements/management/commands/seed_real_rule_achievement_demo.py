from __future__ import annotations

from django.core.management.base import BaseCommand, CommandError

from achievements.real_rule_achievement_seed import DEMO_PASSWORD, RealRuleAchievementDemoSeeder


class Command(BaseCommand):
    help = '注入一组基于公开来源整理的真实规则化科研成果演示数据，用于教师录入、学院审核和积分统计联调。'

    def handle(self, *args, **options):
        try:
            result = RealRuleAchievementDemoSeeder(stdout=self.stdout).run()
        except RuntimeError as exc:
            raise CommandError(str(exc)) from exc

        self.stdout.write(
            self.style.SUCCESS(
                '真实规则成果演示数据已同步完成：'
                f"用户新增 {result['users_created']}，用户更新 {result['users_updated']}，"
                f"成果新增 {result['achievements_created']}，成果更新 {result['achievements_updated']}，"
                f"新增流程日志 {result['logs_created']}。"
            )
        )
        self.stdout.write(
            self.style.WARNING(
                f'演示账号统一密码：{DEMO_PASSWORD}。学院管理员与教师可直接登录验证“录入 -> 审核 -> 生效计分”链路。'
            )
        )
