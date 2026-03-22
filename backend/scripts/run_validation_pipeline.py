#!/usr/bin/env python
from __future__ import annotations

import os
import shlex
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
BACKEND_DIR = REPO_ROOT / "backend"
FRONTEND_DIR = REPO_ROOT / "frontend"


@dataclass(frozen=True)
class ValidationStep:
    name: str
    cwd: Path
    command: tuple[str, ...]


def npm_command(*args: str) -> tuple[str, ...]:
    if os.name == "nt":
        return ("cmd", "/c", "npm", *args)
    return ("npm", *args)


STEPS: tuple[ValidationStep, ...] = (
    ValidationStep(
        name="backend.startup_preflight",
        cwd=BACKEND_DIR,
        command=(sys.executable, "scripts/startup_preflight.py"),
    ),
    ValidationStep(
        name="backend.manage_check",
        cwd=BACKEND_DIR,
        command=(sys.executable, "manage.py", "check"),
    ),
    ValidationStep(
        name="backend.key_tests",
        cwd=BACKEND_DIR,
        command=(
            sys.executable,
            "manage.py",
            "test",
            "--keepdb",
            "--noinput",
            "users",
            "achievements",
            "graph_engine",
            "project_guides",
            "ai_assistant",
        ),
    ),
    ValidationStep(
        name="backend.regression_chain",
        cwd=BACKEND_DIR,
        command=(sys.executable, "scripts/verify_development_16_24_regression.py"),
    ),
    ValidationStep(
        name="frontend.verify_baseline",
        cwd=FRONTEND_DIR,
        command=npm_command("run", "verify:baseline"),
    ),
)


def render_command(command: tuple[str, ...]) -> str:
    return " ".join(shlex.quote(part) for part in command)


def run_step(step: ValidationStep) -> int:
    print(f"[STEP] {step.name}")
    print(f"  cwd: {step.cwd}")
    print(f"  command: {render_command(step.command)}")
    completed = subprocess.run(step.command, cwd=step.cwd)
    if completed.returncode != 0:
        print(f"[FAIL] {step.name} exited with code {completed.returncode}")
        print("处理建议：请先查看该步骤上方日志，再定位依赖、迁移、数据库或测试失败原因。")
        return completed.returncode

    print(f"[PASS] {step.name}")
    print("")
    return 0


def main() -> int:
    print("== Minimum validation pipeline ==")
    print(f"Repository root: {REPO_ROOT}")
    print("")

    for step in STEPS:
        exit_code = run_step(step)
        if exit_code != 0:
            return exit_code

    print("[PASS] All validation steps completed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
