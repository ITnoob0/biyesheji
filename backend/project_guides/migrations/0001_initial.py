from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='ProjectGuide',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('title', models.CharField(max_length=300, verbose_name='指南标题')),
                ('issuing_agency', models.CharField(max_length=200, verbose_name='发布单位')),
                ('guide_level', models.CharField(choices=[('NATIONAL', '国家级'), ('PROVINCIAL', '省部级'), ('MUNICIPAL', '市厅级'), ('ENTERPRISE', '企业合作')], default='PROVINCIAL', max_length=20, verbose_name='指南级别')),
                ('status', models.CharField(choices=[('DRAFT', '草稿'), ('OPEN', '申报中'), ('CLOSED', '已截止')], default='OPEN', max_length=20, verbose_name='状态')),
                ('application_deadline', models.DateField(blank=True, null=True, verbose_name='截止时间')),
                ('summary', models.TextField(verbose_name='指南摘要')),
                ('target_keywords', models.JSONField(blank=True, default=list, verbose_name='主题关键词')),
                ('target_disciplines', models.JSONField(blank=True, default=list, verbose_name='面向学科/方向')),
                ('support_amount', models.CharField(blank=True, max_length=100, verbose_name='资助强度')),
                ('eligibility_notes', models.TextField(blank=True, verbose_name='申报要求')),
                ('source_url', models.URLField(blank=True, verbose_name='来源链接')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('created_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='created_project_guides', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'verbose_name': '项目指南',
                'verbose_name_plural': '项目指南',
                'ordering': ('status', '-updated_at', '-created_at'),
            },
        ),
    ]
