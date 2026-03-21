#!/usr/bin/env python
from __future__ import annotations

import os
import sys
from importlib import import_module
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parents[1]
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

REQUIRED_DEPENDENCIES: tuple[tuple[str, str], ...] = (
    ("django", "Django"),
    ("rest_framework", "djangorestframework"),
    ("rest_framework_simplejwt", "djangorestframework-simplejwt"),
    ("corsheaders", "django-cors-headers"),
    ("pymysql", "PyMySQL"),
)


def check_dependencies() -> list[str]:
    missing: list[str] = []
    for module_name, package_name in REQUIRED_DEPENDENCIES:
        try:
            import_module(module_name)
        except Exception:
            missing.append(package_name)
    return missing


def main() -> int:
    missing = check_dependencies()
    if missing:
        print("[FAIL] 缺少关键依赖：{}".format(", ".join(missing)))
        print(
            "处理建议：先执行 `python -m pip install django djangorestframework "
            "djangorestframework-simplejwt django-cors-headers PyMySQL`，再继续运行本脚本。"
        )
        return 1

    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "core.settings")

    try:
        import django

        django.setup()
        from django.core.management import call_command
        from django.core.management.base import CommandError
    except Exception as exc:
        print(f"[FAIL] Django 环境初始化失败：{exc}")
        print("处理建议：请先确认依赖安装、数据库驱动和 backend/core/settings.py 配置无误。")
        return 1

    try:
        call_command("system_preflight")
    except CommandError:
        return 1
    except Exception as exc:
        print(f"[FAIL] 启动前检查执行失败：{exc}")
        print("处理建议：请先根据报错定位数据库连接、迁移状态或关键表结构问题。")
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
