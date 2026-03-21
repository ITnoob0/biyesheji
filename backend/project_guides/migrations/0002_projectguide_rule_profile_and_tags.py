from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('project_guides', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='projectguide',
            name='recommendation_tags',
            field=models.JSONField(blank=True, default=list, verbose_name='推荐标签'),
        ),
        migrations.AddField(
            model_name='projectguide',
            name='rule_profile',
            field=models.CharField(
                choices=[
                    ('BALANCED', '均衡规则'),
                    ('KEYWORD_FIRST', '主题优先'),
                    ('DISCIPLINE_FIRST', '学科优先'),
                    ('WINDOW_FIRST', '窗口优先'),
                    ('ACTIVITY_FIRST', '活跃度优先'),
                ],
                default='BALANCED',
                max_length=20,
                verbose_name='规则配置档位',
            ),
        ),
    ]
