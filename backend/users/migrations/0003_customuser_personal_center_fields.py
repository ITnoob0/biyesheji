from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("users", "0002_customuser_password_lifecycle"),
    ]

    operations = [
        migrations.AddField(
            model_name="customuser",
            name="avatar_url",
            field=models.URLField(blank=True, null=True, verbose_name="头像地址"),
        ),
        migrations.AddField(
            model_name="customuser",
            name="contact_phone",
            field=models.CharField(blank=True, max_length=30, null=True, verbose_name="联系电话"),
        ),
    ]
