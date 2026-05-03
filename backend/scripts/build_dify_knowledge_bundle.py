"""Build Dify knowledge-base bundles for the AI assistant.

Run from the repository root:

    python backend/scripts/build_dify_knowledge_bundle.py

Default behavior generates a user-facing bundle:

    documents/dify-user-facing-knowledge-base-bundle.md

Optional internal bundle for defense/demo evidence:

    python backend/scripts/build_dify_knowledge_bundle.py --mode internal
    python backend/scripts/build_dify_knowledge_bundle.py --mode all

Design note:
- The user-facing bundle avoids exposing words such as demo data, test data,
  conservative mapping, fallback mode, or unfinished platform details.
- The internal bundle is for defense, administrator verification, and developer
  troubleshooting.
"""

from __future__ import annotations

import argparse
from datetime import datetime
from pathlib import Path
from typing import Iterable

ROOT_DIR = Path(__file__).resolve().parents[2]
DOCUMENTS_DIR = ROOT_DIR / "documents"

USER_FACING_OUTPUT = DOCUMENTS_DIR / "dify-user-facing-knowledge-base-bundle.md"
INTERNAL_OUTPUT = DOCUMENTS_DIR / "dify-internal-demo-evidence-bundle.md"

USER_FACING_FILES = [
    {
        "path": DOCUMENTS_DIR / "research-evaluation-core-rules-final.md",
        "title": "核心科研能力评价规则",
        "priority": "P0",
        "domain": "research_evaluation",
        "note": "面向用户解释成果录入范围、评价规则、积分认定和成果边界的最高优先级依据。",
    },
    {
        "path": DOCUMENTS_DIR / "research-evaluation-source.txt",
        "title": "规则来源与政策依据",
        "priority": "P0",
        "domain": "policy_source",
        "note": "面向用户解释规则来源、政策依据、通用认定原则和争议处理依据。",
    },
]

INTERNAL_FILES = [
    {
        "path": DOCUMENTS_DIR / "rule-achievement-real-demo-sources.md",
        "title": "真实演示成果来源",
        "priority": "P2_INTERNAL",
        "domain": "demo_sources",
        "note": "仅用于答辩说明、管理员核验和开发调试，不建议导入普通用户主知识库。",
    },
    {
        "path": DOCUMENTS_DIR / "dify-ai-assistant-project-context.md",
        "title": "Dify AI 助手项目上下文",
        "priority": "P2_INTERNAL",
        "domain": "dify_integration",
        "note": "用于开发者理解前后端接入、输入变量、页面上下文和异常处理。",
    },
    {
        "path": DOCUMENTS_DIR / "dify-ai-assistant-rag-playbook.md",
        "title": "Dify RAG 配置与知识库增强手册",
        "priority": "P2_INTERNAL",
        "domain": "dify_rag_playbook",
        "note": "用于配置 Dify 知识库切分、检索参数、提示词和验收问题。",
    },
    {
        "path": DOCUMENTS_DIR / "dify-knowledge-base-upload-manifest.md",
        "title": "Dify 知识库导入清单",
        "priority": "P2_INTERNAL",
        "domain": "dify_manifest",
        "note": "用于维护知识库导入顺序和文档优先级。",
    },
]

USER_FACING_GUIDE = """
## 面向用户的回答口径

你是高校教师科研画像与智能辅助系统的智能问答助手。回答时应保持正式、稳定、产品化表达。

### 回答原则

1. 优先依据本知识库中的核心科研能力评价规则和政策依据回答。
2. 涉及成果认定时，先给结论，再给依据，再给用户下一步可操作建议。
3. 不向普通用户暴露演示数据、测试数据、保守映射、开发调试、回退模式、平台未完成等内部表述。
4. 当材料不足时，不说“系统没有开发完成”，应说“当前材料不足以完成自动认定，请补充成果名称、类别、时间、证明材料等信息，系统将依据规则继续匹配”。
5. 不编造未收录的规则、分值、政策文件或最终认定结论。
6. 涉及正式评价时，应表达为“系统依据当前科研评价规则提供辅助判断，最终以学校科研管理部门或学术委员会审核为准”。

### 推荐回答结构

结论：该成果在当前规则下属于……，可按……方向进行认定/需要补充材料后认定。

依据：根据核心科研能力评价规则，……

建议：请补充或核验……

### 不推荐表达

- 这是演示数据。
- 这是测试数据。
- 系统还没完成。
- 当前只能保守映射。
- 平台能力有限。

### 推荐替代表达

- 系统将依据当前科研评价规则进行匹配。
- 当前材料还不足以完成自动认定，建议补充证明材料。
- 该结论为系统辅助判断，正式结果以审核为准。
""".strip()

INTERNAL_GUIDE = """
## 内部使用说明

本包用于答辩说明、管理员核验和开发调试。可以包含演示来源、配置手册、导入清单和项目上下文。

不要把本内部包作为普通教师用户主知识库直接导入生产型 Dify Chat App，避免助手向用户输出演示、测试、保守映射或开发调试口径。
""".strip()


def read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return path.read_text(encoding="utf-8-sig")


def make_header(title: str, guide: str) -> str:
    generated_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    return "\n".join(
        [
            f"# {title}",
            "",
            f"生成时间：{generated_at}",
            "",
            "本文件由 `backend/scripts/build_dify_knowledge_bundle.py` 自动生成。",
            "",
            guide,
            "",
        ]
    )


def make_section(item: dict[str, object]) -> str:
    path = item["path"]
    if not isinstance(path, Path):
        raise TypeError("source file path must be a Path")

    rel_path = path.relative_to(ROOT_DIR).as_posix()
    title = str(item["title"])
    priority = str(item["priority"])
    domain = str(item["domain"])
    note = str(item["note"])

    if not path.exists():
        return "\n".join(
            [
                "---",
                "",
                f"# {title}",
                "",
                f"source_file: `{rel_path}`",
                f"priority: `{priority}`",
                f"domain: `{domain}`",
                "status: `missing`",
                "",
                f"> 缺失说明：{note}",
                "",
                "该文件不存在，请补齐后重新生成知识库整合包。",
                "",
            ]
        )

    content = read_text(path).strip()
    return "\n".join(
        [
            "---",
            "",
            f"# {title}",
            "",
            f"source_file: `{rel_path}`",
            f"priority: `{priority}`",
            f"domain: `{domain}`",
            "status: `included`",
            "",
            f"> 用途：{note}",
            "",
            content,
            "",
        ]
    )


def write_bundle(output_file: Path, title: str, guide: str, files: Iterable[dict[str, object]]) -> None:
    DOCUMENTS_DIR.mkdir(parents=True, exist_ok=True)
    parts = [make_header(title, guide)]
    parts.extend(make_section(item) for item in files)
    output_file.write_text("\n".join(parts).strip() + "\n", encoding="utf-8")
    print(f"Generated {output_file.relative_to(ROOT_DIR).as_posix()}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build Dify knowledge-base bundles.")
    parser.add_argument(
        "--mode",
        choices=("user", "internal", "all"),
        default="user",
        help="Bundle type to generate. Default: user.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    if args.mode in {"user", "all"}:
        write_bundle(
            USER_FACING_OUTPUT,
            "高校教师科研画像系统 Dify 用户问答知识库",
            USER_FACING_GUIDE,
            USER_FACING_FILES,
        )

    if args.mode in {"internal", "all"}:
        write_bundle(
            INTERNAL_OUTPUT,
            "高校教师科研画像系统 Dify 内部核验知识库",
            INTERNAL_GUIDE,
            INTERNAL_FILES,
        )


if __name__ == "__main__":
    main()
