from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("users", "0003_customuser_personal_center_fields"),
    ]

    operations = [
        migrations.AddField(
            model_name="customuser",
            name="contact_visibility",
            field=models.CharField(
                default="email_only",
                help_text="控制个人中心公开资料卡如何展示联系方式。",
                max_length=20,
                verbose_name="联系方式展示策略",
            ),
        ),
    ]
