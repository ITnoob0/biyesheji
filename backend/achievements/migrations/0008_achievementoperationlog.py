from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('achievements', '0007_alter_paper_journal_level'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='AchievementOperationLog',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('achievement_type', models.CharField(choices=[('papers', '论文成果'), ('projects', '科研项目'), ('intellectual-properties', '知识产权'), ('teaching-achievements', '教学成果'), ('academic-services', '学术服务')], max_length=40)),
                ('achievement_id', models.IntegerField(blank=True, null=True)),
                ('action', models.CharField(choices=[('CREATE', '手工新增'), ('UPDATE', '编辑更新'), ('DELETE', '删除记录'), ('IMPORT', '批量导入')], max_length=20)),
                ('source', models.CharField(choices=[('manual', '手工维护'), ('bibtex', 'BibTeX 导入'), ('system', '系统生成')], default='manual', max_length=20)),
                ('summary', models.CharField(max_length=300)),
                ('changed_fields', models.JSONField(blank=True, default=list)),
                ('title_snapshot', models.CharField(blank=True, max_length=300)),
                ('detail_snapshot', models.CharField(blank=True, max_length=300)),
                ('snapshot_payload', models.JSONField(blank=True, default=dict)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('teacher', models.ForeignKey(on_delete=models.CASCADE, related_name='achievement_operation_logs', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'ordering': ('-created_at', '-id'),
            },
        ),
    ]
