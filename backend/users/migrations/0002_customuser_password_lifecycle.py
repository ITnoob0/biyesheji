from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("users", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="customuser",
            name="password_reset_required",
            field=models.BooleanField(
                default=False,
                help_text="管理员初始化或重置密码后，提醒用户登录后尽快修改密码。",
                verbose_name="需修改密码",
            ),
        ),
        migrations.AddField(
            model_name="customuser",
            name="password_updated_at",
            field=models.DateTimeField(blank=True, null=True, verbose_name="密码更新时间"),
        ),
    ]
