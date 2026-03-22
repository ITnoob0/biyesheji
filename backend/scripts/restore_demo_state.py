#!/usr/bin/env python
from __future__ import annotations

import os
import sys
import argparse
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parents[1]
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "core.settings")

import django

django.setup()

from django.core.management import call_command


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Restore demo state with safe defaults.")
    parser.add_argument(
        "--hard-reset-demo-data",
        action="store_true",
        help="删除并重建内置演示教师和演示指南，恢复到标准演示数据状态。",
    )
    parser.add_argument(
        "--reset-passwords",
        action="store_true",
        help="显式将内置演示账号密码重置为标准演示密码。",
    )
    parser.add_argument(
        "--print-accounts",
        action="store_true",
        help="打印当前演示账号说明；默认开启。",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    print("== Restore demo state ==")
    call_command("system_preflight")
    call_command("migrate")
    call_command(
        "init_demo_teachers",
        reset_demo_data=args.hard_reset_demo_data,
        reset_passwords=args.reset_passwords,
        print_accounts=True,
    )
    if args.hard_reset_demo_data:
        print("演示数据已恢复到标准状态，可继续启动服务或执行回归验证。")
    else:
        print("演示数据已完成安全同步：默认保留现有账号密码，可继续启动服务或执行回归验证。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
