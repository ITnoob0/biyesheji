from django.db import migrations, transaction


def normalize_teacher_usernames(apps, schema_editor):
    User = apps.get_model("users", "CustomUser")
    teachers = list(User.objects.filter(is_staff=False, is_superuser=False).order_by("id"))
    teachers_to_update = [teacher for teacher in teachers if teacher.username != str(teacher.id)]

    if not teachers_to_update:
        return

    with transaction.atomic():
        for teacher in teachers_to_update:
            teacher.username = f"__teacher_username_migration__{teacher.id}"
        User.objects.bulk_update(teachers_to_update, ["username"])

        for teacher in teachers_to_update:
            teacher.username = str(teacher.id)
        User.objects.bulk_update(teachers_to_update, ["username"])


class Migration(migrations.Migration):
    dependencies = [
        ("users", "0004_customuser_contact_visibility"),
    ]

    operations = [
        migrations.RunPython(normalize_teacher_usernames, migrations.RunPython.noop),
    ]
