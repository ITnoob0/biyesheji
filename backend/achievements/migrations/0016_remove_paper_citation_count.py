from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("achievements", "0015_delete_teachingachievement"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="paper",
            name="citation_count",
        ),
    ]
