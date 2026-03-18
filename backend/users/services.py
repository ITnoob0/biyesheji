from __future__ import annotations

from achievements.models import TeacherProfile


def get_teacher_profile(user):
    try:
        return user.profile
    except TeacherProfile.DoesNotExist:
        return None


def sync_teacher_profile(user, profile_data):
    TeacherProfile.objects.update_or_create(
        user=user,
        defaults={
            'department': profile_data.get('department', user.department or ''),
            'title': profile_data.get('title', user.title or ''),
            'discipline': profile_data.get('discipline', ''),
            'research_interests': profile_data.get('research_interests', ''),
            'h_index': profile_data.get('h_index', 0),
        },
    )


def update_teacher_account_and_profile(user, user_data, profile_data):
    for attr, value in user_data.items():
        setattr(user, attr, value)
    user.save()

    sync_teacher_profile(
        user,
        {
            'department': user.department or '',
            'title': user.title or '',
            'discipline': profile_data.get('discipline', ''),
            'research_interests': profile_data.get('research_interests', ''),
            'h_index': profile_data.get('h_index', 0),
        },
    )

    return user
