from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('achievements', '0004_coauthor_internal_teacher'),
    ]

    operations = [
        migrations.AddField(
            model_name='paper',
            name='is_representative',
            field=models.BooleanField(default=False, verbose_name='是否代表作'),
        ),
        migrations.AddField(
            model_name='paper',
            name='pages',
            field=models.CharField(blank=True, max_length=50, verbose_name='页码范围'),
        ),
        migrations.AddField(
            model_name='paper',
            name='published_issue',
            field=models.CharField(blank=True, max_length=50, verbose_name='期号'),
        ),
        migrations.AddField(
            model_name='paper',
            name='published_volume',
            field=models.CharField(blank=True, max_length=50, verbose_name='卷号'),
        ),
        migrations.AddField(
            model_name='paper',
            name='source_url',
            field=models.URLField(blank=True, verbose_name='来源链接'),
        ),
    ]
