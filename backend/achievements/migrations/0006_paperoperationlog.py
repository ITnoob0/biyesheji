from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('achievements', '0005_paper_lifecycle_fields'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='PaperOperationLog',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('action', models.CharField(choices=[('CREATE', '手工新增'), ('UPDATE', '编辑更新'), ('DELETE', '删除记录'), ('IMPORT', 'BibTeX 导入')], max_length=20)),
                ('source', models.CharField(choices=[('manual', '手工维护'), ('bibtex', 'BibTeX 导入'), ('system', '系统生成')], default='manual', max_length=20)),
                ('summary', models.CharField(max_length=300)),
                ('changed_fields', models.JSONField(blank=True, default=list)),
                ('metadata_flags', models.JSONField(blank=True, default=list)),
                ('paper_title_snapshot', models.CharField(blank=True, max_length=300)),
                ('paper_doi_snapshot', models.CharField(blank=True, max_length=200)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('paper', models.ForeignKey(blank=True, null=True, on_delete=models.SET_NULL, related_name='operation_logs', to='achievements.paper')),
                ('teacher', models.ForeignKey(on_delete=models.CASCADE, related_name='paper_operation_logs', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'ordering': ('-created_at', '-id'),
            },
        ),
    ]
