"""
教师职称标准选项目录。

说明：
- 仅收录高校常见教师/专业技术职称，不包含行政职务。
- 后端作为权威来源，前端通过接口读取，避免手工输入导致脏数据。
"""

from __future__ import annotations

from typing import Final


TEACHER_PROFESSIONAL_TITLES: Final[tuple[str, ...]] = (
    "教授",
    "副教授",
    "讲师",
    "助教",
    "研究员",
    "副研究员",
    "助理研究员",
    "研究实习员",
)

_TEACHER_TITLE_SET: Final[set[str]] = set(TEACHER_PROFESSIONAL_TITLES)


def normalize_title(value: str | None) -> str:
    return (value or "").strip()


def is_valid_teacher_professional_title(value: str | None) -> bool:
    normalized = normalize_title(value)
    return bool(normalized) and normalized in _TEACHER_TITLE_SET


def get_teacher_professional_title_options() -> list[dict[str, str]]:
    return [{"label": item, "value": item} for item in TEACHER_PROFESSIONAL_TITLES]
