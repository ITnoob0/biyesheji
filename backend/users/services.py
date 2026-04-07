from __future__ import annotations

import csv
import io
import logging
import re
import zipfile
from pathlib import Path
from urllib.parse import urlparse
from uuid import uuid4
from xml.etree import ElementTree as ET
from xml.sax.saxutils import escape

from django.conf import settings
from django.core.files.storage import default_storage
from django.utils import timezone

from achievements.models import TeacherProfile

from .models import UserNotification
from .access import is_admin_user, is_college_admin_user, is_system_admin_user


DEFAULT_PASSWORD_SECURITY_NOTICE = "请妥善保管工号与密码，建议使用高强度密码并定期更新。"
TEMPORARY_PASSWORD_SECURITY_NOTICE = "当前密码为管理员初始化或重置后的临时密码，请登录后尽快修改。"
INACTIVE_ACCOUNT_SECURITY_NOTICE = "当前账户已停用，请联系管理员恢复后再继续使用。"
logger = logging.getLogger(__name__)
CONTACT_VISIBILITY_LABELS = {
    "email_only": "仅公开邮箱",
    "phone_only": "仅公开电话",
    "both": "公开邮箱和电话",
    "internal_only": "联系方式仅内部可见",
}


def get_teacher_profile(user):
    try:
        return user.profile
    except TeacherProfile.DoesNotExist:
        return None


def sync_teacher_profile(user, profile_data):
    TeacherProfile.objects.update_or_create(
        user=user,
        defaults={
            "department": profile_data.get("department", user.department or ""),
            "title": profile_data.get("title", user.title or ""),
            "discipline": profile_data.get("discipline", ""),
            "research_interests": profile_data.get("research_interests", ""),
            "h_index": profile_data.get("h_index", 0),
        },
    )


def update_teacher_account_and_profile(user, user_data, profile_data):
    for attr, value in user_data.items():
        setattr(user, attr, value)
    user.save()

    sync_teacher_profile(
        user,
        {
            "department": user.department or "",
            "title": user.title or "",
            "discipline": profile_data.get("discipline", ""),
            "research_interests": profile_data.get("research_interests", ""),
            "h_index": profile_data.get("h_index", 0),
        },
    )

    return user


def set_user_password(user, raw_password: str, *, require_password_change: bool) -> None:
    user.set_password(raw_password)
    user.password_reset_required = require_password_change
    user.password_updated_at = timezone.now()
    user.save(update_fields=["password", "password_reset_required", "password_updated_at"])


def set_user_active_status(user, *, is_active: bool) -> None:
    user.is_active = is_active
    user.save(update_fields=["is_active"])


def get_user_role_code(user) -> str:
    if is_system_admin_user(user):
        return "admin"
    if is_college_admin_user(user):
        return "college_admin"
    return "teacher"


def get_user_role_label(user) -> str:
    return "系统管理员" if is_admin_user(user) else "教师账户"


def get_user_account_status_label(user) -> str:
    return "账户可用" if getattr(user, "is_active", False) else "账户停用"


def get_user_password_status_label(user) -> str:
    return "待修改密码" if getattr(user, "password_reset_required", False) else "状态正常"


def get_user_contact_visibility_label(user) -> str:
    return CONTACT_VISIBILITY_LABELS.get(getattr(user, "contact_visibility", "email_only"), "仅公开邮箱")


def get_user_next_action_hint(user) -> str:
    if not getattr(user, "is_active", True):
        return "当前账户已停用，需由管理员恢复启用后才能继续登录和修改密码。"
    if getattr(user, "password_reset_required", False):
        return "当前密码为初始化或重置后的临时密码，请登录后尽快前往个人中心修改密码。"
    return "当前账户状态正常，可继续维护资料、成果和密码。"


def build_public_contact_channels(user) -> list[dict]:
    channels = []
    visibility = getattr(user, "contact_visibility", "email_only")
    email = (getattr(user, "email", "") or "").strip()
    phone = (getattr(user, "contact_phone", "") or "").strip()

    if visibility in {"email_only", "both"} and email:
        channels.append({"key": "email", "label": "联系邮箱", "value": email})
    if visibility in {"phone_only", "both"} and phone:
        channels.append({"key": "phone", "label": "联系电话", "value": phone})

    return channels


def get_user_permission_scope(user) -> dict:
    admin = is_admin_user(user)

    if admin:
        return {
            "entry_role": "admin",
            "scope_summary": "管理员可管理教师账户、项目指南和学院看板，并可查看指定教师的画像、图谱、推荐与问答结果。",
            "allowed_actions": [
                "管理教师账户",
                "重置教师密码",
                "维护项目指南",
                "查看学院级统计看板",
                "查看指定教师画像、图谱、推荐与问答结果",
            ],
            "restricted_actions": [
                "不通过教师成果入口直接代教师新增、修改或删除成果",
            ],
            "future_extension_hint": "后续如扩展多角色，应继续优先在统一权限入口中集中扩展，而不是在页面和接口中散落判断。",
        }

    return {
        "entry_role": "teacher",
        "scope_summary": "教师可维护本人资料与成果，并查看本人的画像、图谱、推荐与问答结果，不能访问管理员入口或其他教师数据。",
        "allowed_actions": [
            "维护本人资料",
            "修改本人密码",
            "录入、编辑和删除本人成果",
            "查看本人的画像、图谱、推荐与问答结果",
        ],
        "restricted_actions": [
            "不能访问管理员入口",
            "不能管理教师账户",
            "不能查看其他教师的数据",
            "不能使用学院级统计和教师对比能力",
        ],
        "future_extension_hint": "后续如扩展多角色，应继续优先在统一权限入口中集中扩展，而不是在页面和接口中散落判断。",
    }


def get_user_role_label(user) -> str:
    if is_system_admin_user(user):
        return "系统管理员"
    if is_college_admin_user(user):
        return "学院管理员"
    return "教师账户"


def get_user_permission_scope(user) -> dict:
    if is_system_admin_user(user):
        return {
            "entry_role": "admin",
            "scope_summary": "系统管理员可在全校范围管理教师账户、查看学院看板、维护项目指南，并查看教师画像、成果与管理分析结果。",
            "allowed_actions": [
                "管理教师账户",
                "重置教师密码",
                "维护项目指南",
                "查看学院看板",
                "查看指定教师画像与成果",
            ],
            "restricted_actions": [
                "不通过教师成果入口直接代教师新增、修改或删除成果",
            ],
            "future_extension_hint": "后续如继续扩展管理角色，应优先在统一权限入口中扩展，而不是在页面和接口中分散判断。",
        }

    if is_college_admin_user(user):
        return {
            "entry_role": "college_admin",
            "scope_summary": "学院管理员保留教师本人账户能力，并可在本学院范围内查看教师信息、学院看板和项目指南管理结果，不具备全校管理范围。",
            "allowed_actions": [
                "查看本学院教师信息",
                "查看本学院学院看板",
                "管理本学院教师账户",
                "查看本学院教师画像与成果",
            ],
            "restricted_actions": [
                "不能查看其他学院教师数据",
                "不能访问系统管理员全校范围管理能力",
            ],
            "future_extension_hint": "如后续继续扩展学院管理员能力，应继续保持学院范围约束，不上收为全校管理权限。",
        }

    return {
        "entry_role": "teacher",
        "scope_summary": "教师可维护本人资料与成果，并查看本人的画像、图谱、推荐与问答结果，不可访问管理员入口或其他教师数据。",
        "allowed_actions": [
            "维护本人资料",
            "修改本人密码",
            "录入、编辑和删除本人成果",
            "查看本人画像、图谱、推荐与问答结果",
        ],
        "restricted_actions": [
            "不能访问管理员入口",
            "不能管理教师账户",
            "不能查看其他教师数据",
            "不能使用学院级统计和教师对比能力",
        ],
        "future_extension_hint": "后续如扩展更多角色，应继续优先在统一权限入口中集中扩展，而不是在页面和接口中分散判断。",
    }


def get_user_security_notice(user) -> str:
    if not user.is_active:
        return INACTIVE_ACCOUNT_SECURITY_NOTICE
    if getattr(user, "password_reset_required", False):
        return TEMPORARY_PASSWORD_SECURITY_NOTICE
    return DEFAULT_PASSWORD_SECURITY_NOTICE


def store_user_avatar_upload(*, user, uploaded_file, request) -> str:
    avatar_dir = Path("avatars")
    extension = Path(uploaded_file.name).suffix.lower() or ".bin"
    generated_name = avatar_dir / f"user_{user.id}_{timezone.now().strftime('%Y%m%d%H%M%S')}_{uuid4().hex[:8]}{extension}"

    old_avatar_url = getattr(user, "avatar_url", "") or ""
    parsed_url = urlparse(old_avatar_url)
    if parsed_url.path.startswith(settings.MEDIA_URL):
        old_relative_path = parsed_url.path.removeprefix(settings.MEDIA_URL)
        old_storage_path = str(Path(old_relative_path))
        if old_storage_path and default_storage.exists(old_storage_path):
            default_storage.delete(old_storage_path)

    stored_path = default_storage.save(str(generated_name), uploaded_file)
    return request.build_absolute_uri(f"{settings.MEDIA_URL}{stored_path}")


def build_teacher_management_summary(queryset) -> dict:
    total_count = queryset.count()
    active_count = queryset.filter(is_active=True).count()
    inactive_count = queryset.filter(is_active=False).count()
    password_reset_required_count = queryset.filter(password_reset_required=True).count()
    stable_password_count = max(total_count - password_reset_required_count, 0)

    return {
        "total_count": total_count,
        "active_count": active_count,
        "inactive_count": inactive_count,
        "password_reset_required_count": password_reset_required_count,
        "stable_password_count": stable_password_count,
        "recovery_guidance": "账户停用后，教师将无法继续登录或修改密码；恢复启用后可继续使用原密码登录。若管理员执行了密码重置，教师登录后需尽快修改临时密码。",
        "future_extension_hint": "后续如扩展多角色，应继续在统一权限入口和账户生命周期摘要中集中扩展，不应散落到各个页面自行判断。",
    }


def log_account_lifecycle_event(*, actor, target, action: str, detail: str = "") -> None:
    actor_name = getattr(actor, "username", "unknown")
    target_name = getattr(target, "username", "unknown")
    logger.info(
        "account_lifecycle action=%s actor=%s target=%s detail=%s",
        action,
        actor_name,
        target_name,
        detail or "-",
    )


def create_user_notification(
    *,
    recipient,
    title: str,
    category: str,
    content: str = "",
    sender=None,
    action_path: str = "",
    action_query: dict | None = None,
    payload: dict | None = None,
) -> UserNotification:
    return UserNotification.objects.create(
        recipient=recipient,
        sender=sender,
        category=category,
        title=title,
        content=content,
        action_path=action_path,
        action_query=action_query or {},
        payload=payload or {},
    )


def bulk_create_user_notifications(
    *,
    recipients,
    title: str,
    category: str,
    content_builder=None,
    sender=None,
    action_path: str = "",
    action_query_builder=None,
    payload_builder=None,
) -> int:
    records = []
    for recipient in recipients:
        content = content_builder(recipient) if callable(content_builder) else ""
        action_query = action_query_builder(recipient) if callable(action_query_builder) else {}
        payload = payload_builder(recipient) if callable(payload_builder) else {}
        records.append(
            UserNotification(
                recipient=recipient,
                sender=sender,
                category=category,
                title=title,
                content=content or "",
                action_path=action_path or "",
                action_query=action_query or {},
                payload=payload or {},
            )
        )
    if records:
        UserNotification.objects.bulk_create(records)
    return len(records)


def parse_bulk_account_import_file(uploaded_file) -> list[dict]:
    filename = (getattr(uploaded_file, "name", "") or "").strip().lower()
    if not filename:
        raise ValueError("上传文件缺少文件名，请使用 .xlsx 或 .csv 模板。")

    raw_bytes = uploaded_file.read()
    if not raw_bytes:
        raise ValueError("上传文件为空，请检查后重试。")

    if filename.endswith(".csv"):
        rows = _parse_csv_rows(raw_bytes)
    elif filename.endswith(".xlsx"):
        rows = _parse_xlsx_rows(raw_bytes)
    else:
        raise ValueError("仅支持 .xlsx 或 .csv 文件。")

    return _normalize_import_rows(rows)


def build_bulk_import_template_xlsx(*, is_system_admin: bool, college_name: str = "") -> tuple[str, bytes]:
    if is_system_admin:
        filename = "college-admin-bulk-import-template.xlsx"
        rows = [
            ["工号", "姓名", "学院", "固定说明（无需填写）"],
            ["", "", "", "固定为学院管理员"],
        ]
    else:
        fixed_college = (college_name or "当前学院").strip()
        filename = "teacher-bulk-import-template.xlsx"
        rows = [
            ["工号", "姓名", "学院固定说明（无需填写）", "职称固定说明（无需填写）"],
            ["", "", f"固定为当前学院：{fixed_college}", "固定为讲师"],
        ]

    workbook_bytes = _build_minimal_xlsx(rows)
    return filename, workbook_bytes


def _parse_csv_rows(raw_bytes: bytes) -> list[list[str]]:
    decoded = None
    for encoding in ("utf-8-sig", "utf-8", "gbk"):
        try:
            decoded = raw_bytes.decode(encoding)
            break
        except UnicodeDecodeError:
            continue
    if decoded is None:
        raise ValueError("CSV 编码无法识别，请使用 UTF-8 或 GBK 编码后重试。")

    reader = csv.reader(io.StringIO(decoded))
    rows: list[list[str]] = []
    for row in reader:
        cleaned = [(cell or "").strip() for cell in row]
        if any(cleaned):
            rows.append(cleaned)
    return rows


def _build_minimal_xlsx(rows: list[list[str]]) -> bytes:
    content_types = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
  <Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
  <Default Extension="xml" ContentType="application/xml"/>
  <Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>
  <Override PartName="/xl/worksheets/sheet1.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>
</Types>"""
    rels = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/>
</Relationships>"""
    workbook = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"
          xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">
  <sheets>
    <sheet name="模板" sheetId="1" r:id="rId1"/>
  </sheets>
</workbook>"""
    workbook_rels = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet1.xml"/>
</Relationships>"""
    sheet_xml = _build_sheet_xml(rows)

    output = io.BytesIO()
    with zipfile.ZipFile(output, mode="w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("[Content_Types].xml", content_types)
        archive.writestr("_rels/.rels", rels)
        archive.writestr("xl/workbook.xml", workbook)
        archive.writestr("xl/_rels/workbook.xml.rels", workbook_rels)
        archive.writestr("xl/worksheets/sheet1.xml", sheet_xml)
    return output.getvalue()


def _build_sheet_xml(rows: list[list[str]]) -> str:
    row_nodes: list[str] = []
    for row_index, row in enumerate(rows, start=1):
        cell_nodes: list[str] = []
        for col_index, value in enumerate(row, start=1):
            cell_ref = f"{_column_index_to_name(col_index)}{row_index}"
            text = escape(str(value or ""))
            cell_nodes.append(
                f'<c r="{cell_ref}" t="inlineStr"><is><t>{text}</t></is></c>'
            )
        row_nodes.append(f'<row r="{row_index}">{"".join(cell_nodes)}</row>')

    return (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
        f'<sheetData>{"".join(row_nodes)}</sheetData>'
        "</worksheet>"
    )


def _column_index_to_name(index: int) -> str:
    value = index
    result = []
    while value > 0:
        value, remainder = divmod(value - 1, 26)
        result.append(chr(ord("A") + remainder))
    return "".join(reversed(result))


def _parse_xlsx_rows(raw_bytes: bytes) -> list[list[str]]:
    try:
        with zipfile.ZipFile(io.BytesIO(raw_bytes)) as archive:
            shared_strings = _read_xlsx_shared_strings(archive)
            sheet_path = _resolve_first_sheet_path(archive)
            if not sheet_path:
                raise ValueError("Excel 文件中未找到工作表，请检查模板。")
            xml_bytes = archive.read(sheet_path)
    except zipfile.BadZipFile as exc:
        raise ValueError("无法识别 Excel 文件，请确认上传的是 .xlsx 文件。") from exc
    except KeyError as exc:
        raise ValueError("Excel 文件结构异常，请重新导出模板后上传。") from exc

    root = ET.fromstring(xml_bytes)
    namespace = {"x": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}
    rows: list[list[str]] = []
    for row_node in root.findall(".//x:sheetData/x:row", namespace):
        cells: dict[int, str] = {}
        for cell_node in row_node.findall("x:c", namespace):
            cell_ref = (cell_node.attrib.get("r") or "").upper()
            column_index = _cell_ref_to_column_index(cell_ref)
            if column_index < 0:
                continue
            cell_type = cell_node.attrib.get("t")
            value = _read_xlsx_cell_value(cell_node, cell_type, shared_strings, namespace)
            cells[column_index] = value.strip()
        if not cells:
            continue
        max_index = max(cells.keys())
        row = [cells.get(idx, "") for idx in range(max_index + 1)]
        if any(item.strip() for item in row):
            rows.append(row)
    return rows


def _read_xlsx_shared_strings(archive: zipfile.ZipFile) -> list[str]:
    shared_path = "xl/sharedStrings.xml"
    if shared_path not in archive.namelist():
        return []
    root = ET.fromstring(archive.read(shared_path))
    namespace = {"x": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}
    values: list[str] = []
    for si in root.findall(".//x:si", namespace):
        text_nodes = si.findall(".//x:t", namespace)
        values.append("".join(node.text or "" for node in text_nodes))
    return values


def _resolve_first_sheet_path(archive: zipfile.ZipFile) -> str:
    workbook_xml = ET.fromstring(archive.read("xl/workbook.xml"))
    rels_xml = ET.fromstring(archive.read("xl/_rels/workbook.xml.rels"))
    ns_main = {"x": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}
    ns_rel = {"r": "http://schemas.openxmlformats.org/officeDocument/2006/relationships"}
    ns_pkg = {"p": "http://schemas.openxmlformats.org/package/2006/relationships"}

    sheet = workbook_xml.find(".//x:sheets/x:sheet", ns_main)
    if sheet is None:
        return ""

    rel_id = sheet.attrib.get("{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id")
    if not rel_id:
        return ""

    for rel in rels_xml.findall(".//p:Relationship", ns_pkg):
        if rel.attrib.get("Id") != rel_id:
            continue
        target = rel.attrib.get("Target", "")
        if target.startswith("/"):
            return target.lstrip("/")
        normalized_target = target.replace("..\\", "").replace("../", "")
        return "xl/" + normalized_target
    return ""


def _read_xlsx_cell_value(cell_node, cell_type: str | None, shared_strings: list[str], namespace: dict) -> str:
    if cell_type == "inlineStr":
        text_nodes = cell_node.findall(".//x:t", namespace)
        return "".join(node.text or "" for node in text_nodes)

    value_node = cell_node.find("x:v", namespace)
    raw_value = (value_node.text or "").strip() if value_node is not None else ""
    if cell_type == "s":
        try:
            return shared_strings[int(raw_value)]
        except (ValueError, IndexError):
            return ""
    return raw_value


def _cell_ref_to_column_index(cell_ref: str) -> int:
    match = re.match(r"([A-Z]+)", cell_ref or "")
    if not match:
        return -1
    letters = match.group(1)
    value = 0
    for char in letters:
        value = value * 26 + (ord(char) - ord("A") + 1)
    return value - 1


def _normalize_import_rows(rows: list[list[str]]) -> list[dict]:
    if not rows:
        return []

    header_index_map = _build_header_index_map(rows[0])
    has_header = bool(header_index_map)
    data_rows = rows[1:] if has_header else rows

    normalized: list[dict] = []
    start_line = 2 if has_header else 1
    for index, row in enumerate(data_rows, start=start_line):
        employee_id = _read_row_value(row, header_index_map, "employee_id", fallback_index=0)
        real_name = _read_row_value(row, header_index_map, "real_name", fallback_index=1)
        department = _read_row_value(row, header_index_map, "department", fallback_index=2)
        if not (employee_id or real_name or department):
            continue
        normalized.append(
            {
                "row_number": index,
                "employee_id": employee_id,
                "real_name": real_name,
                "department": department,
            }
        )
    return normalized


def _build_header_index_map(header_row: list[str]) -> dict[str, int]:
    mapping: dict[str, int] = {}
    aliases = {
        "employee_id": {"工号", "教工号", "账号", "登录账号", "employee_id", "username", "id"},
        "real_name": {"姓名", "教师姓名", "真实姓名", "name", "real_name"},
        "department": {"学院", "所属学院", "院系", "department", "college"},
    }
    normalized_header = [str(item or "").strip().lower() for item in header_row]
    for idx, value in enumerate(normalized_header):
        for field, field_aliases in aliases.items():
            if field in mapping:
                continue
            normalized_aliases = {alias.strip().lower() for alias in field_aliases}
            if value in normalized_aliases:
                mapping[field] = idx
                break
    if "employee_id" in mapping and "real_name" in mapping:
        return mapping
    return {}


def _read_row_value(row: list[str], header_index_map: dict[str, int], field: str, *, fallback_index: int) -> str:
    index = header_index_map.get(field, fallback_index)
    if index >= len(row):
        return ""
    return str(row[index] or "").strip()
