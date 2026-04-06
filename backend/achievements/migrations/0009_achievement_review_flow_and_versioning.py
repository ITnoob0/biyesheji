from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('achievements', '0008_achievementoperationlog'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.RenameField(
            model_name='project',
            old_name='status',
            new_name='project_status',
        ),
        migrations.AddField(
            model_name='academicservice',
            name='status',
            field=models.CharField(
                choices=[
                    ('DRAFT', '草稿'),
                    ('PENDING_REVIEW', '待审核'),
                    ('APPROVED', '已通过'),
                    ('REJECTED', '已驳回'),
                ],
                default='DRAFT',
                max_length=20,
                verbose_name='审批状态',
            ),
        ),
        migrations.AddField(
            model_name='intellectualproperty',
            name='status',
            field=models.CharField(
                choices=[
                    ('DRAFT', '草稿'),
                    ('PENDING_REVIEW', '待审核'),
                    ('APPROVED', '已通过'),
                    ('REJECTED', '已驳回'),
                ],
                default='DRAFT',
                max_length=20,
                verbose_name='审批状态',
            ),
        ),
        migrations.AddField(
            model_name='paper',
            name='status',
            field=models.CharField(
                choices=[
                    ('DRAFT', '草稿'),
                    ('PENDING_REVIEW', '待审核'),
                    ('APPROVED', '已通过'),
                    ('REJECTED', '已驳回'),
                ],
                default='DRAFT',
                max_length=20,
                verbose_name='审批状态',
            ),
        ),
        migrations.AddField(
            model_name='project',
            name='status',
            field=models.CharField(
                choices=[
                    ('DRAFT', '草稿'),
                    ('PENDING_REVIEW', '待审核'),
                    ('APPROVED', '已通过'),
                    ('REJECTED', '已驳回'),
                ],
                default='DRAFT',
                max_length=20,
                verbose_name='审批状态',
            ),
        ),
        migrations.AddField(
            model_name='teachingachievement',
            name='status',
            field=models.CharField(
                choices=[
                    ('DRAFT', '草稿'),
                    ('PENDING_REVIEW', '待审核'),
                    ('APPROVED', '已通过'),
                    ('REJECTED', '已驳回'),
                ],
                default='DRAFT',
                max_length=20,
                verbose_name='审批状态',
            ),
        ),
        migrations.AddField(
            model_name='achievementoperationlog',
            name='change_details',
            field=models.JSONField(blank=True, default=list),
        ),
        migrations.AddField(
            model_name='achievementoperationlog',
            name='operator',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='achievement_review_logs',
                to=settings.AUTH_USER_MODEL,
            ),
        ),
        migrations.AddField(
            model_name='achievementoperationlog',
            name='review_comment',
            field=models.TextField(blank=True),
        ),
        migrations.AlterField(
            model_name='achievementoperationlog',
            name='action',
            field=models.CharField(
                choices=[
                    ('CREATE', '手工新增'),
                    ('UPDATE', '编辑更新'),
                    ('DELETE', '删除记录'),
                    ('IMPORT', '批量导入'),
                    ('SUBMIT_REVIEW', '提交审核'),
                    ('APPROVE', '审核通过'),
                    ('REJECT', '审核驳回'),
                ],
                max_length=20,
            ),
        ),
    ]
