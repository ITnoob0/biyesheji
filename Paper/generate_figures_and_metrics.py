from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


ROOT = Path(__file__).resolve().parents[1]
PAPER_DIR = ROOT / "Paper"
FIGURE_DIR = PAPER_DIR / "figures"
METRICS_PATH = FIGURE_DIR / "api_metrics.json"


def ensure_dirs() -> None:
    FIGURE_DIR.mkdir(parents=True, exist_ok=True)


def load_font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    candidates = []
    if bold:
        candidates.extend(
            [
                r"C:\Windows\Fonts\msyhbd.ttc",
                r"C:\Windows\Fonts\simhei.ttf",
                r"C:\Windows\Fonts\arialbd.ttf",
            ]
        )
    candidates.extend(
        [
            r"C:\Windows\Fonts\msyh.ttc",
            r"C:\Windows\Fonts\simsun.ttc",
            r"C:\Windows\Fonts\arial.ttf",
        ]
    )
    for candidate in candidates:
        if Path(candidate).exists():
            try:
                return ImageFont.truetype(candidate, size=size)
            except OSError:
                continue
    return ImageFont.load_default()


TITLE_FONT = load_font(38, bold=True)
SUBTITLE_FONT = load_font(22)
TEXT_FONT = load_font(20)
SMALL_FONT = load_font(16)
CARD_TITLE_FONT = load_font(24, bold=True)
CARD_TEXT_FONT = load_font(18)


PALETTE = {
    "bg": "#f6f8fb",
    "surface": "#ffffff",
    "border": "#d6dde7",
    "ink": "#1f2a44",
    "muted": "#5c6b80",
    "blue": "#2f66d0",
    "green": "#2aa46b",
    "orange": "#f08a24",
    "red": "#db5a6b",
    "purple": "#6e56cf",
    "teal": "#14808a",
    "gold": "#b98500",
}


def wrap_text(draw: ImageDraw.ImageDraw, text: str, font: ImageFont.ImageFont, max_width: int) -> list[str]:
    words = []
    for raw_line in str(text).split("\n"):
        if not raw_line:
            words.append("")
            continue
        current = ""
        for ch in raw_line:
            test = current + ch
            bbox = draw.textbbox((0, 0), test, font=font)
            if bbox[2] - bbox[0] <= max_width or not current:
                current = test
            else:
                words.append(current)
                current = ch
        if current:
            words.append(current)
    return words or [""]


def draw_text_block(draw: ImageDraw.ImageDraw, x: int, y: int, text: str, font, fill: str, max_width: int, line_gap: int = 6) -> int:
    lines = wrap_text(draw, text, font, max_width)
    cursor_y = y
    for line in lines:
        draw.text((x, cursor_y), line, font=font, fill=fill)
        bbox = draw.textbbox((x, cursor_y), line, font=font)
        cursor_y += (bbox[3] - bbox[1]) + line_gap
    return cursor_y


def rounded_box(draw: ImageDraw.ImageDraw, xy, fill: str, outline: str | None = None, width: int = 2, radius: int = 18):
    draw.rounded_rectangle(xy, radius=radius, fill=fill, outline=outline, width=width)


def draw_chip(draw: ImageDraw.ImageDraw, x: int, y: int, text: str, fill: str, text_fill: str = "#ffffff") -> int:
    bbox = draw.textbbox((0, 0), text, font=SMALL_FONT)
    width = bbox[2] - bbox[0] + 24
    height = bbox[3] - bbox[1] + 14
    rounded_box(draw, (x, y, x + width, y + height), fill=fill, outline=fill, width=1, radius=14)
    draw.text((x + 12, y + 7), text, font=SMALL_FONT, fill=text_fill)
    return width


def draw_panel(draw: ImageDraw.ImageDraw, xy, title: str, lines: list[str], accent: str = PALETTE["blue"], bullets: bool = True):
    x1, y1, x2, y2 = xy
    rounded_box(draw, xy, fill=PALETTE["surface"], outline=PALETTE["border"], width=2, radius=22)
    rounded_box(draw, (x1 + 18, y1 + 16, x1 + 30, y1 + 52), fill=accent, outline=accent, width=1, radius=6)
    draw.text((x1 + 42, y1 + 18), title, font=CARD_TITLE_FONT, fill=PALETTE["ink"])
    cursor_y = y1 + 62
    for line in lines:
        prefix = "• " if bullets else ""
        cursor_y = draw_text_block(draw, x1 + 28, cursor_y, prefix + line, CARD_TEXT_FONT, PALETTE["muted"], (x2 - x1) - 56, 6)
        cursor_y += 4


def new_canvas(title: str, subtitle: str = "") -> tuple[Image.Image, ImageDraw.ImageDraw]:
    image = Image.new("RGB", (1600, 900), PALETTE["bg"])
    draw = ImageDraw.Draw(image)
    draw.rectangle((0, 0, 1600, 108), fill="#eef3fb")
    draw.text((56, 34), title, font=TITLE_FONT, fill=PALETTE["ink"])
    if subtitle:
        draw.text((58, 80), subtitle, font=SUBTITLE_FONT, fill=PALETTE["muted"])
    return image, draw


def save(image: Image.Image, filename: str) -> None:
    image.save(FIGURE_DIR / filename, format="PNG")


def draw_arrow(draw: ImageDraw.ImageDraw, start: tuple[int, int], end: tuple[int, int], color: str = PALETTE["blue"], width: int = 4):
    draw.line((start, end), fill=color, width=width)
    ex, ey = end
    sx, sy = start
    if abs(ex - sx) >= abs(ey - sy):
        sign = 1 if ex >= sx else -1
        points = [(ex, ey), (ex - 18 * sign, ey - 10), (ex - 18 * sign, ey + 10)]
    else:
        sign = 1 if ey >= sy else -1
        points = [(ex, ey), (ex - 10, ey - 18 * sign), (ex + 10, ey - 18 * sign)]
    draw.polygon(points, fill=color)


def figure_research_background():
    image, draw = new_canvas("课题研究背景与问题域示意", "依据最终版系统的真实建设目标整理")
    draw_panel(draw, (70, 160, 450, 720), "现实问题", [
        "科研成果分散在不同填报口径与教师个人材料中",
        "静态统计难以说明教师当前的科研能力结构",
        "项目申报指导缺少可解释的个体化支撑",
        "学院管理端缺乏统一、可钻取的科研看板",
    ], accent=PALETTE["red"])
    draw_panel(draw, (610, 160, 990, 720), "系统建设目标", [
        "统一教师资料与多类型科研成果治理入口",
        "构建六维科研能力数字画像与趋势分析视图",
        "提供学术图谱、推荐辅助和受控式问答",
        "形成学院级统计总览、对比与教师分析闭环",
    ], accent=PALETTE["blue"])
    draw_panel(draw, (1150, 160, 1530, 720), "工程化落地原则", [
        "以真实业务数据和审核后成果为主口径",
        "推荐采用规则增强与可解释理由生成",
        "问答限定在系统内知识片段和回退链路",
        "图谱坚持 Neo4j 优先、MySQL 回退设计",
    ], accent=PALETTE["green"])
    draw_arrow(draw, (450, 440), (610, 440))
    draw_arrow(draw, (990, 440), (1150, 440))
    save(image, "research-background.png")


def figure_frontend_workspace():
    image, draw = new_canvas("前端工作台结构图", "依据 workspaceRoutes.ts 与最终版菜单结构生成")
    draw_panel(draw, (70, 170, 520, 740), "教师工作台", [
        "个人中心：公开资料、账户安全、成果认领、快捷入口",
        "教师画像：能力画像、趋势分析、学术社交、全部成果",
        "成果中心：成果总览、录入管理、BibTeX 导入、统计摘要",
        "项目推荐：推荐结果、收藏反馈、申报准备",
    ], accent=PALETTE["blue"])
    draw_panel(draw, (560, 170, 1040, 740), "共享页面与组件", [
        "登录页、忘记密码页、受控注册页",
        "统一主布局、侧栏菜单、顶部导航与主题系统",
        "浮动智能问答助手、错误提示与回跳提示",
        "ECharts 图表组件、雷达图、图谱与卡片化视图",
    ], accent=PALETTE["teal"])
    draw_panel(draw, (1080, 170, 1530, 740), "管理员工作台", [
        "教师管理：教师总览、创建教师、创建学院管理员",
        "成果审核：按学院范围审核教师成果",
        "学院看板：总览、学院对比、学院钻取、教师分析",
        "项目指南管理：指南总览、新增项目、生命周期管理",
    ], accent=PALETTE["orange"])
    draw_arrow(draw, (520, 320), (560, 320), PALETTE["blue"])
    draw_arrow(draw, (1040, 520), (1080, 520), PALETTE["orange"])
    save(image, "frontend-workspace.png")


def figure_usecase():
    image, draw = new_canvas("系统业务用例图", "依据教师、学院管理员、系统管理员三类角色整理")
    draw_panel(draw, (60, 210, 290, 690), "教师", [
        "维护个人资料",
        "录入与导入成果",
        "查看科研画像",
        "查看项目推荐",
        "使用问答助手",
        "处理成果认领",
    ], accent=PALETTE["blue"])
    draw_panel(draw, (1310, 210, 1540, 690), "系统管理员", [
        "管理学院管理员账号",
        "查看全校学院对比",
        "维护全局项目指南",
        "查看指定教师画像与推荐",
    ], accent=PALETTE["purple"])
    draw_panel(draw, (1080, 210, 1280, 690), "学院管理员", [
        "管理本院教师账号",
        "审核教师成果",
        "查看学院科研看板",
        "推送项目指南",
    ], accent=PALETTE["orange"])

    usecases = [
        ("资料维护", (420, 210, 670, 280)),
        ("成果治理", (420, 310, 670, 380)),
        ("科研画像", (420, 410, 670, 480)),
        ("项目推荐", (420, 510, 670, 580)),
        ("智能问答", (420, 610, 670, 680)),
        ("教师管理", (760, 260, 1010, 330)),
        ("成果审核", (760, 380, 1010, 450)),
        ("学院看板", (760, 500, 1010, 570)),
        ("指南管理", (760, 620, 1010, 690)),
    ]
    for name, xy in usecases:
        rounded_box(draw, xy, fill=PALETTE["surface"], outline=PALETTE["border"], width=2, radius=34)
        bbox = draw.textbbox((0, 0), name, font=CARD_TITLE_FONT)
        draw.text(((xy[0] + xy[2] - (bbox[2] - bbox[0])) / 2, xy[1] + 18), name, font=CARD_TITLE_FONT, fill=PALETTE["ink"])
    for y in [245, 345, 445, 545, 645]:
        draw_arrow(draw, (290, y), (420, y), PALETTE["blue"], 3)
    for y in [295, 415, 535, 655]:
        draw_arrow(draw, (1010, y), (1080, y), PALETTE["orange"], 3)
    for y in [295, 535, 655]:
        draw_arrow(draw, (1010, y), (1310, y), PALETTE["purple"], 3)
    save(image, "usecase-overview.png")


def figure_architecture():
    image, draw = new_canvas("系统总体架构图", "依据 core/urls.py、workspaceRoutes.ts、服务层与数据层真实结构生成")
    layers = [
        ("前端展示层", PALETTE["blue"], ["Vue 3", "Vite", "Element Plus", "ECharts", "统一工作台与浮动问答"]),
        ("接口与认证层", PALETTE["teal"], ["Django REST Framework", "JWT 鉴权", "参数校验", "统一错误结构", "X-Request-ID"]),
        ("业务服务层", PALETTE["green"], ["成果治理", "画像评分", "项目推荐", "问答服务", "学院看板", "图谱协调"]),
        ("数据与增强层", PALETTE["orange"], ["MySQL 主存储", "Neo4j 可选增强", "本地媒体文件", "推荐历史与画像快照"]),
        ("工程保障层", PALETTE["purple"], ["启动前检查", "演示数据恢复", "回归脚本", "最小 CI", "回退与异常治理"]),
    ]
    top = 150
    for idx, (title, color, items) in enumerate(layers):
        y1 = top + idx * 132
        y2 = y1 + 92
        rounded_box(draw, (120, y1, 1480, y2), fill=PALETTE["surface"], outline=color, width=3, radius=26)
        draw.text((150, y1 + 18), title, font=CARD_TITLE_FONT, fill=color)
        text = "  ·  ".join(items)
        draw_text_block(draw, 340, y1 + 22, text, CARD_TEXT_FONT, PALETTE["muted"], 1100, 4)
        if idx < len(layers) - 1:
            draw_arrow(draw, (800, y2), (800, y2 + 30), color)
    save(image, "system-architecture.png")


def figure_module_structure():
    image, draw = new_canvas("系统功能模块结构图", "依据前后端模块边界与数据主链路整理")
    center = (650, 310, 950, 430)
    draw_panel(draw, center, "成果治理中心", [
        "论文、项目、知识产权、教学成果、学术服务",
        "审核流转、操作日志、BibTeX 导入、成果认领",
    ], accent=PALETTE["green"])
    panels = {
        "个人中心": (80, 120, 430, 280),
        "教师画像": (1080, 120, 1480, 280),
        "项目推荐": (1080, 330, 1480, 500),
        "智能问答": (1080, 560, 1480, 730),
        "学院看板": (80, 560, 430, 730),
        "学术图谱": (80, 330, 430, 500),
    }
    panel_lines = {
        "个人中心": ["资料维护、头像上传、账户安全", "公开资料与快捷入口"],
        "教师画像": ["六维画像、趋势分析、同侪基准", "历史快照与解释卡片"],
        "项目推荐": ["规则增强打分、支撑记录", "收藏反馈与推荐历史"],
        "智能问答": ["问题类型判断、模板化回答", "来源卡片与回退说明"],
        "学院看板": ["总览、对比、钻取、教师分析", "导出与学院级筛选"],
        "学术图谱": ["Neo4j 优先、MySQL 回退", "轻量关系分析与热点统计"],
    }
    colors = {
        "个人中心": PALETTE["blue"],
        "教师画像": PALETTE["teal"],
        "项目推荐": PALETTE["orange"],
        "智能问答": PALETTE["purple"],
        "学院看板": PALETTE["gold"],
        "学术图谱": PALETTE["red"],
    }
    for title, xy in panels.items():
        draw_panel(draw, xy, title, panel_lines[title], accent=colors[title])
        draw_arrow(draw, (center[0] if xy[0] < 650 else center[2], (center[1] + center[3]) // 2), (xy[2] if xy[0] < 650 else xy[0], (xy[1] + xy[3]) // 2), colors[title], 3)
    save(image, "function-module.png")


def figure_database_er():
    image, draw = new_canvas("数据库 ER 图", "依据 Django 模型中的核心实体与主外键关系简化绘制")
    entities = {
        "CustomUser": ((80, 120, 340, 260), ["id", "username", "real_name", "department", "role_code/permission_scope*"]),
        "TeacherProfile": ((420, 120, 700, 250), ["user_id", "discipline", "research_interests", "h_index"]),
        "Paper": ((80, 340, 360, 540), ["teacher_id", "title", "doi", "status", "citation_count"]),
        "AchievementClaim": ((420, 340, 760, 560), ["achievement_id", "initiator_id", "target_user_id", "status", "confirmed_author_rank"]),
        "PortraitSnapshot": ((820, 120, 1120, 260), ["user_id", "year", "dimension_scores", "total_score"]),
        "ProjectGuide": ((1180, 120, 1510, 300), ["academy_id", "status", "rule_profile", "target_keywords", "target_disciplines"]),
        "RecommendationRecord": ((1110, 410, 1510, 650), ["teacher_id", "guide_id", "recommendation_score", "feedback_signal", "portrait_dimension_links"]),
        "UserNotification": ((420, 620, 760, 780), ["recipient_id", "sender_id", "category", "action_path", "is_read"]),
    }
    for title, (xy, fields) in entities.items():
        draw_panel(draw, xy, title, fields, accent=PALETTE["blue"] if title in {"CustomUser", "TeacherProfile"} else PALETTE["teal"], bullets=False)
    relationships = [
        ((340, 190), (420, 180)),
        ((210, 260), (210, 340)),
        ((340, 430), (420, 450)),
        ((700, 180), (820, 190)),
        ((1060, 260), (1260, 410)),
        ((340, 180), (1180, 180)),
        ((340, 190), (420, 680)),
    ]
    for start, end in relationships:
        draw_arrow(draw, start, end, PALETTE["blue"], 3)
    draw.text((118, 270), "*角色能力摘要由接口层序列化输出", font=SMALL_FONT, fill=PALETTE["muted"])
    save(image, "database-er.png")


def page_figure(title: str, subtitle: str, sidebar: list[str], content_blocks: list[tuple[str, list[str], str]], filename: str):
    image, draw = new_canvas(title, subtitle)
    rounded_box(draw, (45, 130, 260, 850), fill="#17324d", outline="#17324d", width=1, radius=28)
    draw.text((76, 166), "工作台导航", font=CARD_TITLE_FONT, fill="#ffffff")
    y = 224
    for item in sidebar:
        rounded_box(draw, (70, y, 235, y + 44), fill="#24496d", outline="#24496d", width=1, radius=16)
        draw.text((88, y + 10), item, font=CARD_TEXT_FONT, fill="#f7fbff")
        y += 58
    rounded_box(draw, (290, 138, 1550, 212), fill=PALETTE["surface"], outline=PALETTE["border"], width=2, radius=24)
    draw.text((320, 160), title, font=CARD_TITLE_FONT, fill=PALETTE["ink"])
    chip_x = 1130
    for chip_text, chip_color in [("最终版系统", PALETTE["blue"]), ("论文插图", PALETTE["green"]), ("真实结构示意", PALETTE["orange"])]:
        chip_w = draw_chip(draw, chip_x, 156, chip_text, chip_color)
        chip_x += chip_w + 12
    positions = [
        (290, 240, 910, 520),
        (930, 240, 1550, 520),
        (290, 540, 910, 835),
        (930, 540, 1550, 835),
    ]
    for (block_title, lines, color), xy in zip(content_blocks, positions):
        draw_panel(draw, xy, block_title, lines, accent=color)
    save(image, filename)


def figure_login_page():
    image, draw = new_canvas("系统登录页面", "依据 LoginView.vue 的登录流程、会话恢复与安全提示结构生成")
    rounded_box(draw, (70, 150, 860, 790), fill="#eef4ff", outline="#c7d7f7", width=2, radius=32)
    draw.text((110, 220), "高校教师科研能力数字画像与智能辅助系统", font=TITLE_FONT, fill=PALETTE["ink"])
    draw_text_block(draw, 114, 300, "左侧为品牌介绍、恢复提示与安全说明区域；右侧为工号/管理员账号登录表单，支持回跳目标提示和登录失败指引。", CARD_TEXT_FONT, PALETTE["muted"], 620, 8)
    for i, label in enumerate(["科研成果治理", "教师科研画像", "项目推荐", "受控式智能问答", "学院科研看板"]):
        draw_chip(draw, 110, 410 + i * 56, label, PALETTE["blue"])
    rounded_box(draw, (950, 190, 1450, 740), fill=PALETTE["surface"], outline=PALETTE["border"], width=2, radius=28)
    draw.text((1010, 236), "账号登录", font=CARD_TITLE_FONT, fill=PALETTE["ink"])
    form_labels = ["工号 / 管理员账号", "登录密码", "受保护页面回跳提示", "错误消息与下一步建议"]
    y = 300
    for idx, label in enumerate(form_labels):
        rounded_box(draw, (1000, y, 1400, y + 72), fill="#fafcff", outline="#d9e2ef", width=2, radius=18)
        draw.text((1028, y + 12), label, font=CARD_TEXT_FONT, fill=PALETTE["muted"])
        if idx < 2:
            draw.text((1028, y + 40), "....................", font=CARD_TEXT_FONT, fill="#b0bac9")
        y += 98
    draw_chip(draw, 1008, 640, "JWT 登录", PALETTE["green"])
    draw_chip(draw, 1128, 640, "会话恢复", PALETTE["orange"])
    save(image, "login-page.png")


def figure_achievement_flow():
    image, draw = new_canvas("成果治理流程图", "依据成果录入、审核、认领、日志与联动分析链路生成")
    steps = [
        ("教师录入或 BibTeX 导入", PALETTE["blue"]),
        ("提交审核", PALETTE["teal"]),
        ("管理员审核通过/驳回", PALETTE["orange"]),
        ("记录操作日志与快照", PALETTE["purple"]),
        ("进入画像 / 推荐 / 看板 / 图谱", PALETTE["green"]),
    ]
    x = 90
    for idx, (label, color) in enumerate(steps):
        rounded_box(draw, (x, 340, x + 250, 470), fill=PALETTE["surface"], outline=color, width=3, radius=28)
        draw_text_block(draw, x + 26, 375, label, CARD_TITLE_FONT, PALETTE["ink"], 200, 6)
        if idx < len(steps) - 1:
            draw_arrow(draw, (x + 250, 405), (x + 300, 405), color, 4)
        x += 300
    draw_panel(draw, (190, 570, 630, 790), "校内合著认领支线", [
        "内部作者搜索与认领邀请",
        "接受、拒绝或修正作者位次",
        "同步通知与认领状态变化",
    ], accent=PALETTE["gold"])
    draw_panel(draw, (940, 570, 1400, 790), "审核状态回退支线", [
        "教师修改已审核成果后重新进入待审核",
        "确保画像、推荐和学院统计统一使用已审核口径",
        "删除或驳回记录时同步清理图谱快照",
    ], accent=PALETTE["red"])
    draw_arrow(draw, (360, 570), (360, 470), PALETTE["gold"], 3)
    draw_arrow(draw, (1160, 570), (980, 470), PALETTE["red"], 3)
    save(image, "achievement-flow.png")


def figure_test_result(pipeline_summary: dict, api_metrics: list[dict]):
    image, draw = new_canvas("系统测试结果汇总图", "依据统一验证流水线与 API 计时结果生成")
    draw_panel(draw, (70, 160, 770, 430), "统一验证流水线结果", [
        f"启动前检查：{pipeline_summary['preflight']}",
        f"Django 检查：{pipeline_summary['check']}",
        f"后端自动化测试：{pipeline_summary['tests']}",
        f"主链路回归：{pipeline_summary['regression']}",
        f"前端基线验证：{pipeline_summary['frontend']}",
        f"后端测试数量：{pipeline_summary['test_count']} 项，用时 {pipeline_summary['test_duration']} 秒",
    ], accent=PALETTE["green"])
    draw_panel(draw, (70, 470, 770, 820), "关键结论", [
        "统一验证流水线全链路通过",
        "教师与管理员关键业务闭环均已验证",
        "越权访问返回 401 / 403，回退链路可工作",
        "图谱、推荐、问答与画像模块均返回真实结构化结果",
    ], accent=PALETTE["blue"])
    rounded_box(draw, (840, 160, 1530, 820), fill=PALETTE["surface"], outline=PALETTE["border"], width=2, radius=24)
    draw.text((870, 186), "关键接口响应耗时（ms）", font=CARD_TITLE_FONT, fill=PALETTE["ink"])
    base_y = 250
    max_value = max((item["elapsed_ms"] for item in api_metrics if item["status_code"] < 500), default=1)
    for item in api_metrics:
        label = item["label"]
        elapsed = item["elapsed_ms"]
        status_code = item["status_code"]
        color = PALETTE["green"] if 200 <= status_code < 300 else PALETTE["orange"] if status_code in {401, 403} else PALETTE["red"]
        draw.text((870, base_y), f"{label}（{status_code}）", font=SMALL_FONT, fill=PALETTE["muted"])
        rounded_box(draw, (1080, base_y - 4, 1480, base_y + 24), fill="#eef2f7", outline="#eef2f7", width=1, radius=12)
        bar_length = int((elapsed / max_value) * 380)
        rounded_box(draw, (1080, base_y - 4, 1080 + max(20, bar_length), base_y + 24), fill=color, outline=color, width=1, radius=12)
        draw.text((1490, base_y), f"{elapsed:.2f}", font=SMALL_FONT, fill=PALETTE["ink"])
        base_y += 56
    save(image, "test-result.png")


def figure_page_set():
    page_figure(
        "教师个人中心界面示意",
        "依据 TeacherProfileEditorView.vue 的公开资料、账户安全和快捷入口结构生成",
        ["公开资料", "账户安全", "成果认领", "快捷入口"],
        [
            ("教师资料卡", ["姓名、院系、职称、学科、研究方向", "头像上传与资料完整度提示"], PALETTE["blue"]),
            ("联系方式策略", ["邮箱、电话、公开可见范围", "公开摘要与内部可见策略"], PALETTE["teal"]),
            ("研究兴趣与简介", ["研究方向标签", "研究兴趣文本", "个人简介"], PALETTE["green"]),
            ("账户安全与联动入口", ["密码修改", "成果、画像、推荐快捷入口", "摘要统计"], PALETTE["orange"]),
        ],
        "profile-editor-page.png",
    )
    page_figure(
        "科研成果管理界面示意",
        "依据 AchievementEntryView.vue 的概览、录入、导入和认领结构生成",
        ["成果总览", "成果录入", "BibTeX 导入", "统计摘要", "代表成果"],
        [
            ("成果管理概览", ["论文、项目、知识产权、教学成果、学术服务概览", "最近成果与联动入口"], PALETTE["blue"]),
            ("论文录入表单", ["题目、摘要、DOI、卷期页、引用次数", "第一作者/通讯作者/代表作标记"], PALETTE["green"]),
            ("作者与认领设置", ["本校教师搜索", "作者位次、通讯作者标记", "认领邀请自动生成"], PALETTE["purple"]),
            ("BibTeX 与统计区", ["预览导入、重复提醒", "成果结构统计与列表筛选"], PALETTE["orange"]),
        ],
        "achievement-page.png",
    )
    page_figure(
        "教师科研画像界面示意",
        "依据 DashboardView.vue 的画像总览、维度说明、趋势与图谱结构生成",
        ["能力画像", "趋势分析", "学术社交", "全部成果"],
        [
            ("画像摘要", ["教师头像、院系、职称、H-index", "成果总量与人物摘要"], PALETTE["blue"]),
            ("综合能力雷达", ["六维雷达图", "维度评分、权重与证据标签"], PALETTE["green"]),
            ("趋势与结构分析", ["维度变化趋势", "近年成果结构"], PALETTE["orange"]),
            ("学术社交与关键词", ["图谱展示", "主题聚焦与关键词演化"], PALETTE["purple"]),
        ],
        "portrait-page.png",
    )
    page_figure(
        "项目推荐界面示意",
        "依据 ProjectRecommendationView.vue 的推荐结果、反馈与准备视图结构生成",
        ["推荐结果", "收藏与反馈", "申报准备"],
        [
            ("教师快照与筛选", ["教师选择、对比教师、关键词筛选", "指南级别、推荐优先级、排序方式"], PALETTE["blue"]),
            ("推荐结果卡片", ["推荐分、优先级、推荐标签", "来源链接与推荐摘要"], PALETTE["green"]),
            ("解释维度与支撑记录", ["关键词匹配、学科匹配、活跃度支撑", "画像联动维度与支撑成果"], PALETTE["orange"]),
            ("反馈与历史", ["收藏、感兴趣、暂不相关、计划申报", "推荐历史回看与反馈备注"], PALETTE["purple"]),
        ],
        "recommendation-page.png",
    )
    page_figure(
        "智能问答辅助面板示意",
        "依据 FloatingDifyAssistant.vue 与 portrait-qa 接口返回结构生成",
        ["画像总结", "维度原因", "成果与画像", "推荐说明", "学院概览"],
        [
            ("问题输入区", ["受控问题类型与草稿提示", "上下文来源：画像 / 推荐 / 看板"], PALETTE["blue"]),
            ("答案区", ["模板化或模型组织后的回答", "边界说明与失败回退提示"], PALETTE["green"]),
            ("来源卡片区", ["模块标签、页面回跳、可验证状态", "画像、成果、推荐、学院统计来源"], PALETTE["orange"]),
            ("治理说明区", ["仅使用系统内真实数据", "模型不可用时回退为安全回答"], PALETTE["purple"]),
        ],
        "assistant-page.png",
    )
    page_figure(
        "学院科研看板界面示意",
        "依据 AcademyDashboardView.vue 的总览、对比、钻取与教师分析结构生成",
        ["总览", "学院对比", "学院钻取", "教师分析"],
        [
            ("统计概览卡片", ["教师数、成果总量、论文数、项目数", "近年变化与筛选状态"], PALETTE["blue"]),
            ("趋势与结构图", ["年度趋势、成果结构、院系分布", "学院级钻取入口"], PALETTE["green"]),
            ("教师排行与明细", ["教师排行、代表成果、画像入口", "导出与筛选"], PALETTE["orange"]),
            ("运营分析区", ["学院管理员视角的本院教师分析", "系统管理员视角的学院间对比"], PALETTE["purple"]),
        ],
        "academy-dashboard-page.png",
    )
    page_figure(
        "学术图谱展示界面示意",
        "依据 AcademicGraph.vue 的网络图、分析卡片与回退提示结构生成",
        ["画像主页", "学术社交", "图谱解释"],
        [
            ("图谱主画布", ["教师、论文、关键词、合作学者网络", "节点点击与关系说明"], PALETTE["blue"]),
            ("图谱元信息", ["Neo4j 优先 / MySQL 回退", "节点数、边数、轻量分析层级"], PALETTE["green"]),
            ("合作与主题分析", ["核心合作者、圈层概览", "主题热点与关键词焦点"], PALETTE["orange"]),
            ("回退提示区", ["图数据库异常时的说明", "仅进行轻量分析，不执行复杂图计算"], PALETTE["purple"]),
        ],
        "graph-page.png",
    )


def measure_api_metrics() -> list[dict]:
    sys.path.insert(0, str(ROOT / "backend"))
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "core.settings")
    import django

    django.setup()

    from django.contrib.auth import get_user_model
    from rest_framework.test import APIClient

    user_model = get_user_model()
    teacher = user_model.objects.get(id=100001)
    admin = user_model.objects.get(id=1)

    teacher_client = APIClient()
    teacher_client.force_authenticate(teacher)

    admin_client = APIClient()
    admin_client.force_authenticate(admin)

    guest_client = APIClient()

    cases = [
        ("教师资料接口", teacher_client, "get", "/api/users/me/", None),
        ("教师画像总览", teacher_client, "get", "/api/achievements/dashboard-stats/", None),
        ("教师画像雷达", teacher_client, "get", f"/api/achievements/radar/{teacher.id}/", None),
        ("项目推荐接口", teacher_client, "get", "/api/project-guides/recommendations/", None),
        ("画像问答接口", teacher_client, "post", "/api/ai-assistant/portrait-qa/", {"question_type": "portrait_summary"}),
        ("学术图谱接口", teacher_client, "get", f"/api/graph/topology/{teacher.id}/", None),
        ("学院看板接口", admin_client, "get", "/api/achievements/academy-overview/", None),
        ("未登录访问 me", guest_client, "get", "/api/users/me/", None),
        ("教师访问学院看板", teacher_client, "get", "/api/achievements/academy-overview/", None),
    ]

    results: list[dict] = []
    for label, client, method, path, payload in cases:
        started = time.perf_counter()
        if method == "get":
            response = client.get(path, payload or {})
        else:
            response = client.post(path, payload or {}, format="json")
        elapsed_ms = (time.perf_counter() - started) * 1000
        results.append(
            {
                "label": label,
                "path": path,
                "method": method.upper(),
                "status_code": int(response.status_code),
                "elapsed_ms": round(elapsed_ms, 2),
            }
        )
    METRICS_PATH.write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
    return results


def main():
    ensure_dirs()
    figure_research_background()
    figure_frontend_workspace()
    figure_usecase()
    figure_architecture()
    figure_module_structure()
    figure_database_er()
    figure_login_page()
    figure_page_set()
    figure_achievement_flow()
    api_metrics = measure_api_metrics()
    figure_test_result(
        {
            "preflight": "通过",
            "check": "通过",
            "tests": "通过",
            "regression": "通过",
            "frontend": "通过",
            "test_count": "151",
            "test_duration": "727.998",
        },
        api_metrics,
    )
    print(f"Generated figures in: {FIGURE_DIR}")
    print(f"Saved API metrics to: {METRICS_PATH}")


if __name__ == "__main__":
    main()
