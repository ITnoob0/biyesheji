from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("achievements", "0016_remove_paper_citation_count"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="teacherprofile",
            name="h_index",
        ),
    ]
