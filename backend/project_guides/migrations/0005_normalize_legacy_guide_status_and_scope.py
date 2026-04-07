from django.db import migrations


def normalize_legacy_guide_status_and_scope(apps, schema_editor):
    project_guide_model = apps.get_model('project_guides', 'ProjectGuide')
    academy_model = apps.get_model('project_guides', 'Academy')
    recommendation_record_model = apps.get_model('project_guides', 'ProjectGuideRecommendationRecord')
    db_alias = schema_editor.connection.alias

    status_map = {'OPEN': 'ACTIVE', 'CLOSED': 'ARCHIVED'}
    for legacy_status, normalized_status in status_map.items():
        project_guide_model.objects.using(db_alias).filter(status=legacy_status).update(status=normalized_status)
        recommendation_record_model.objects.using(db_alias).filter(
            guide_status_snapshot=legacy_status
        ).update(guide_status_snapshot=normalized_status)

    # GLOBAL 指南不应绑定学院，统一清洗空值。
    project_guide_model.objects.using(db_alias).filter(scope='GLOBAL').exclude(academy_id=None).update(academy_id=None)

    academy_cache = {
        row['name']: row['id']
        for row in academy_model.objects.using(db_alias).values('id', 'name')
    }

    def resolve_academy_id(academy_name: str):
        academy_name = (academy_name or '').strip()
        if not academy_name:
            return None
        cached = academy_cache.get(academy_name)
        if cached:
            return cached
        academy = academy_model.objects.using(db_alias).create(name=academy_name)
        academy_cache[academy_name] = academy.id
        return academy.id

    # 历史学院管理员创建的数据在旧版中可能仍是 GLOBAL，这里做一次强制收口。
    academy_admin_global_guides = project_guide_model.objects.using(db_alias).filter(
        scope='GLOBAL',
        academy_id=None,
        created_by__is_staff=True,
        created_by__is_superuser=False,
    ).exclude(
        created_by__department__isnull=True,
    ).exclude(
        created_by__department='',
    )
    for row in academy_admin_global_guides.values('id', 'created_by__department'):
        academy_id = resolve_academy_id(row['created_by__department'])
        if academy_id:
            project_guide_model.objects.using(db_alias).filter(id=row['id']).update(
                scope='ACADEMY',
                academy_id=academy_id,
            )

    # 历史学院范围指南若未绑定学院，按创建人学院回填。
    academy_scope_without_college = project_guide_model.objects.using(db_alias).filter(
        scope='ACADEMY',
        academy_id=None,
        created_by__is_staff=True,
        created_by__is_superuser=False,
    ).exclude(
        created_by__department__isnull=True,
    ).exclude(
        created_by__department='',
    )
    for row in academy_scope_without_college.values('id', 'created_by__department'):
        academy_id = resolve_academy_id(row['created_by__department'])
        if academy_id:
            project_guide_model.objects.using(db_alias).filter(id=row['id']).update(academy_id=academy_id)


class Migration(migrations.Migration):
    dependencies = [
        ('project_guides', '0004_academy_projectguide_scope_alter_projectguide_status_and_more'),
    ]

    operations = [
        migrations.RunPython(normalize_legacy_guide_status_and_scope, migrations.RunPython.noop),
    ]
