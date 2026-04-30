from __future__ import annotations


STANDARD_COLLEGES = [
    "文学院",
    "政法与公共管理学院",
    "历史文化学院",
    "鲁迅艺术学院",
    "经管学院",
    "体育学院",
    "外国语学院",
    "数学与计算机科学学院",
    "物理与电子信息学院",
    "化学与化工学院",
    "生命科学学院",
    "石油学院",
    "建筑工程学院",
    "教育科学学院",
    "马克思主义学院",
    "医学院",
    "继续教育学院",
]

COLLEGE_ALIASES = {
    "信息工程学院": "数学与计算机科学学院",
    "人工智能学院": "数学与计算机科学学院",
    "计算机学院": "数学与计算机科学学院",
    "软件学院": "数学与计算机科学学院",
    "数学与计算机学院": "数学与计算机科学学院",
    "数学计算机科学学院": "数学与计算机科学学院",
    "物电学院": "物理与电子信息学院",
    "物理学院": "物理与电子信息学院",
    "电子信息学院": "物理与电子信息学院",
    "政法学院": "政法与公共管理学院",
    "公共管理学院": "政法与公共管理学院",
    "教育学院": "教育科学学院",
    "教育技术学院": "教育科学学院",
    "经济管理学院": "经管学院",
    "经济与管理学院": "经管学院",
    "化工学院": "化学与化工学院",
    "化学学院": "化学与化工学院",
    "建筑学院": "建筑工程学院",
    "土木工程学院": "建筑工程学院",
}


def normalize_college_name(value: str | None) -> str:
    name = (value or "").strip()
    if not name:
        return ""
    return COLLEGE_ALIASES.get(name, name)


def is_standard_college_name(value: str | None) -> bool:
    return normalize_college_name(value) in STANDARD_COLLEGES


def ensure_standard_colleges() -> None:
    from .models import College

    for index, name in enumerate(STANDARD_COLLEGES, start=1):
        College.objects.get_or_create(
            name=name,
            defaults={
                "sort_order": index,
                "is_active": True,
            },
        )
