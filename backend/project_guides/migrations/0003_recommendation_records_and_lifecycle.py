from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('project_guides', '0002_projectguide_rule_profile_and_tags'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AddField(
            model_name='projectguide',
            name='archived_at',
            field=models.DateTimeField(blank=True, null=True, verbose_name='归档时间'),
        ),
        migrations.AddField(
            model_name='projectguide',
            name='closed_at',
            field=models.DateTimeField(blank=True, null=True, verbose_name='关闭时间'),
        ),
        migrations.AddField(
            model_name='projectguide',
            name='lifecycle_note',
            field=models.CharField(blank=True, max_length=255, verbose_name='生命周期说明'),
        ),
        migrations.AddField(
            model_name='projectguide',
            name='published_at',
            field=models.DateTimeField(blank=True, null=True, verbose_name='发布时间'),
        ),
        migrations.AddField(
            model_name='projectguide',
            name='rule_config',
            field=models.JSONField(blank=True, default=dict, verbose_name='规则细化配置'),
        ),
        migrations.AlterField(
            model_name='projectguide',
            name='rule_profile',
            field=models.CharField(
                choices=[
                    ('BALANCED', '均衡规则'),
                    ('KEYWORD_FIRST', '主题优先'),
                    ('DISCIPLINE_FIRST', '学科优先'),
                    ('WINDOW_FIRST', '窗口优先'),
                    ('ACTIVITY_FIRST', '活跃度优先'),
                    ('PORTRAIT_FIRST', '画像联动优先'),
                    ('FOUNDATION_FIRST', '申报基础优先'),
                ],
                default='BALANCED',
                max_length=20,
                verbose_name='规则配置档位',
            ),
        ),
        migrations.AlterField(
            model_name='projectguide',
            name='status',
            field=models.CharField(
                choices=[
                    ('DRAFT', '草稿'),
                    ('OPEN', '申报中'),
                    ('CLOSED', '已截止'),
                    ('ARCHIVED', '已归档'),
                ],
                default='OPEN',
                max_length=20,
                verbose_name='状态',
            ),
        ),
        migrations.CreateModel(
            name='ProjectGuideFavorite',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('guide', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='favorites', to='project_guides.projectguide', verbose_name='项目指南')),
                ('teacher', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='project_guide_favorites', to=settings.AUTH_USER_MODEL, verbose_name='教师')),
            ],
            options={
                'verbose_name': '项目指南收藏',
                'verbose_name_plural': '项目指南收藏',
                'ordering': ('-updated_at', '-created_at'),
                'unique_together': {('teacher', 'guide')},
            },
        ),
        migrations.CreateModel(
            name='ProjectGuideRecommendationRecord',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('batch_token', models.CharField(db_index=True, max_length=36, verbose_name='推荐批次标识')),
                ('guide_title_snapshot', models.CharField(max_length=300, verbose_name='指南标题快照')),
                ('guide_status_snapshot', models.CharField(blank=True, max_length=20, verbose_name='指南状态快照')),
                ('rule_profile_snapshot', models.CharField(blank=True, max_length=20, verbose_name='规则档位快照')),
                ('recommendation_score', models.PositiveIntegerField(default=0, verbose_name='推荐得分')),
                ('priority_label', models.CharField(blank=True, max_length=20, verbose_name='关注等级')),
                ('recommendation_reasons', models.JSONField(blank=True, default=list, verbose_name='推荐理由快照')),
                ('explanation_dimensions', models.JSONField(blank=True, default=list, verbose_name='解释维度快照')),
                ('recommendation_labels', models.JSONField(blank=True, default=list, verbose_name='推荐标签快照')),
                ('matched_keywords', models.JSONField(blank=True, default=list, verbose_name='命中关键词快照')),
                ('matched_disciplines', models.JSONField(blank=True, default=list, verbose_name='命中学科快照')),
                ('portrait_dimension_links', models.JSONField(blank=True, default=list, verbose_name='画像联动快照')),
                ('is_favorited_snapshot', models.BooleanField(default=False, verbose_name='生成时是否已收藏')),
                ('feedback_signal', models.CharField(blank=True, choices=[('', '未反馈'), ('INTERESTED', '感兴趣'), ('NOT_RELEVANT', '暂不相关'), ('PLAN_TO_APPLY', '计划申报'), ('APPLIED', '已申报')], max_length=20, verbose_name='反馈信号')),
                ('feedback_note', models.TextField(blank=True, verbose_name='反馈备注')),
                ('generated_at', models.DateTimeField(auto_now_add=True, verbose_name='生成时间')),
                ('last_feedback_at', models.DateTimeField(blank=True, null=True, verbose_name='最后反馈时间')),
                ('guide', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='recommendation_records', to='project_guides.projectguide', verbose_name='项目指南')),
                ('requested_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='project_guide_recommendation_requests', to=settings.AUTH_USER_MODEL, verbose_name='触发账号')),
                ('teacher', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='project_guide_recommendation_records', to=settings.AUTH_USER_MODEL, verbose_name='目标教师')),
            ],
            options={
                'verbose_name': '项目指南推荐历史',
                'verbose_name_plural': '项目指南推荐历史',
                'ordering': ('-generated_at', '-id'),
            },
        ),
    ]
