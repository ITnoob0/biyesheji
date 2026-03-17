from __future__ import annotations

import re
from datetime import date
from typing import Any

from .models import Paper


MONTH_MAP = {
    'jan': 1,
    'january': 1,
    'feb': 2,
    'february': 2,
    'mar': 3,
    'march': 3,
    'apr': 4,
    'april': 4,
    'may': 5,
    'jun': 6,
    'june': 6,
    'jul': 7,
    'july': 7,
    'aug': 8,
    'august': 8,
    'sep': 9,
    'sept': 9,
    'september': 9,
    'oct': 10,
    'october': 10,
    'nov': 11,
    'november': 11,
    'dec': 12,
    'december': 12,
}


def decode_bibtex_bytes(raw_bytes: bytes) -> str:
    for encoding in ('utf-8-sig', 'utf-8', 'gbk'):
        try:
            return raw_bytes.decode(encoding)
        except UnicodeDecodeError:
            continue
    raise ValueError('无法识别 BibTeX 文件编码，请使用 UTF-8 或 GBK 编码后重试。')


def split_bibtex_entries(raw_text: str) -> list[str]:
    entries: list[str] = []
    cursor = 0
    total = len(raw_text)

    while cursor < total:
        start = raw_text.find('@', cursor)
        if start == -1:
            break

        brace_start = raw_text.find('{', start)
        if brace_start == -1:
            break

        depth = 0
        for index in range(brace_start, total):
            char = raw_text[index]
            if char == '{':
                depth += 1
            elif char == '}':
                depth -= 1
                if depth == 0:
                    entries.append(raw_text[start:index + 1])
                    cursor = index + 1
                    break
        else:
            break

    return entries


def _split_citation_key_and_body(entry_content: str) -> tuple[str, str]:
    depth = 0
    in_quote = False

    for index, char in enumerate(entry_content):
        if char == '"' and (index == 0 or entry_content[index - 1] != '\\'):
            in_quote = not in_quote
            continue

        if in_quote:
            continue

        if char == '{':
            depth += 1
        elif char == '}':
            depth -= 1
        elif char == ',' and depth == 0:
            return entry_content[:index].strip(), entry_content[index + 1 :]

    return entry_content.strip(), ''


def _parse_bibtex_fields(fields_blob: str) -> dict[str, str]:
    parsed: dict[str, str] = {}
    index = 0
    length = len(fields_blob)

    while index < length:
        while index < length and fields_blob[index] in ' \t\r\n,':
            index += 1

        if index >= length:
            break

        field_start = index
        while index < length and fields_blob[index] not in '=\r\n':
            index += 1
        field_name = fields_blob[field_start:index].strip().lower()

        while index < length and fields_blob[index] != '=':
            index += 1
        if index >= length:
            break

        index += 1
        while index < length and fields_blob[index].isspace():
            index += 1

        if index >= length or not field_name:
            break

        if fields_blob[index] == '{':
            depth = 0
            value_start = index + 1
            index += 1
            while index < length:
                char = fields_blob[index]
                if char == '{':
                    depth += 1
                elif char == '}':
                    if depth == 0:
                        value = fields_blob[value_start:index]
                        index += 1
                        break
                    depth -= 1
                index += 1
            else:
                value = fields_blob[value_start:]
        elif fields_blob[index] == '"':
            value_start = index + 1
            index += 1
            while index < length:
                if fields_blob[index] == '"' and fields_blob[index - 1] != '\\':
                    value = fields_blob[value_start:index]
                    index += 1
                    break
                index += 1
            else:
                value = fields_blob[value_start:]
        else:
            value_start = index
            while index < length and fields_blob[index] != ',':
                index += 1
            value = fields_blob[value_start:index]

        parsed[field_name] = clean_bibtex_value(value)

    return parsed


def parse_bibtex_text(raw_text: str) -> list[dict[str, Any]]:
    parsed_entries: list[dict[str, Any]] = []

    for raw_entry in split_bibtex_entries(raw_text):
        type_match = re.match(r'@\s*([^\s{]+)\s*{', raw_entry)
        if not type_match:
            continue

        entry_type = type_match.group(1).strip().lower()
        content_start = raw_entry.find('{') + 1
        content = raw_entry[content_start:-1].strip()
        citation_key, body = _split_citation_key_and_body(content)
        fields = _parse_bibtex_fields(body)

        parsed_entries.append(
            {
                'entry_type': entry_type,
                'citation_key': citation_key,
                'fields': fields,
            }
        )

    return parsed_entries


def clean_bibtex_value(value: str) -> str:
    normalized = value.replace('\r', ' ').replace('\n', ' ').replace('\t', ' ')
    normalized = normalized.replace('~', ' ')
    normalized = normalized.replace('\\&', '&')
    normalized = normalized.replace('{', '').replace('}', '')
    normalized = re.sub(r'\s+', ' ', normalized)
    return normalized.strip().strip(',')


def normalize_author_name(raw_name: str) -> str:
    name = clean_bibtex_value(raw_name)
    if ',' not in name:
        return name

    last_name, first_name = [part.strip() for part in name.split(',', 1)]
    return f'{first_name} {last_name}'.strip()


def normalize_identity(value: str) -> str:
    return re.sub(r'[\s\-_.]', '', (value or '').strip().lower())


def parse_authors(author_field: str) -> list[str]:
    if not author_field:
        return []
    return [normalize_author_name(item) for item in re.split(r'\s+and\s+', author_field) if item.strip()]


def resolve_date(fields: dict[str, str]) -> tuple[str, list[str]]:
    issues: list[str] = []
    raw_date = fields.get('date', '')
    raw_year = fields.get('year', '')
    raw_month = fields.get('month', '')

    if raw_date:
        match = re.search(r'(\d{4})(?:[-/](\d{1,2}))?(?:[-/](\d{1,2}))?', raw_date)
        if match:
            year = int(match.group(1))
            month = int(match.group(2) or 1)
            day = int(match.group(3) or 1)
            try:
                return date(year, month, day).isoformat(), issues
            except ValueError:
                issues.append('日期字段无法识别，已按年份补全失败。')

    year_match = re.search(r'\d{4}', raw_year)
    if not year_match:
        return '', ['缺少可识别的发表年份/日期。']

    year = int(year_match.group())
    month = 1

    if raw_month:
        month_key = clean_bibtex_value(raw_month).lower()
        if month_key.isdigit():
            month = max(1, min(12, int(month_key)))
        else:
            month = MONTH_MAP.get(month_key, MONTH_MAP.get(month_key[:3], 1))

    return date(year, month, 1).isoformat(), issues


def normalize_bibtex_paper_entry(entry: dict[str, Any], user) -> dict[str, Any]:
    fields = entry['fields']
    title = clean_bibtex_value(fields.get('title', ''))
    abstract = clean_bibtex_value(fields.get('abstract', ''))
    journal_name = clean_bibtex_value(fields.get('journal', '') or fields.get('booktitle', ''))
    journal_level = clean_bibtex_value(fields.get('journal_level', '') or fields.get('note', ''))
    doi = clean_bibtex_value(fields.get('doi', '')).lower()
    date_acquired, date_issues = resolve_date(fields)
    authors = parse_authors(fields.get('author', ''))

    teacher_aliases = {
        normalize_identity(user.real_name or ''),
        normalize_identity(user.username or ''),
    }
    is_first_author = True
    if authors:
        normalized_authors = [normalize_identity(name) for name in authors]
        matched_index = next((idx for idx, item in enumerate(normalized_authors) if item in teacher_aliases), None)
        if matched_index is not None:
            is_first_author = matched_index == 0

    coauthors = [
        name for name in authors if normalize_identity(name) not in teacher_aliases
    ][:20]

    paper_type = 'CONFERENCE' if fields.get('booktitle') and not fields.get('journal') else 'JOURNAL'

    return {
        'citation_key': entry['citation_key'],
        'entry_type': entry['entry_type'],
        'title': title,
        'abstract': abstract,
        'date_acquired': date_acquired,
        'paper_type': paper_type,
        'journal_name': journal_name,
        'journal_level': journal_level,
        'citation_count': 0,
        'is_first_author': is_first_author,
        'doi': doi,
        'coauthors': coauthors,
        'issues': date_issues,
    }


def build_bibtex_preview_entries(raw_text: str, user) -> dict[str, Any]:
    parsed_entries = parse_bibtex_text(raw_text)
    if not parsed_entries:
        raise ValueError('未识别到有效的 BibTeX 条目，请检查文件内容。')

    existing_dois = {
        doi.strip().lower()
        for doi in Paper.objects.filter(teacher=user).exclude(doi='').values_list('doi', flat=True)
        if doi
    }
    batch_dois: set[str] = set()
    preview_entries: list[dict[str, Any]] = []

    for index, entry in enumerate(parsed_entries, start=1):
        normalized = normalize_bibtex_paper_entry(entry, user)
        issues = list(normalized.pop('issues', []))
        doi = normalized.get('doi', '')

        if not normalized['title']:
            issues.append('缺少论文题目。')
        if not normalized['journal_name']:
            issues.append('缺少期刊或会议名称。')
        if not normalized['date_acquired']:
            issues.append('缺少发表时间。')

        preview_status = 'ready'
        if doi and doi in existing_dois:
            preview_status = 'duplicate'
            issues.append('当前账号下已存在相同 DOI 的论文。')
        elif doi and doi in batch_dois:
            preview_status = 'duplicate'
            issues.append('当前批次中存在重复 DOI。')
        elif issues:
            preview_status = 'invalid'

        if doi:
            batch_dois.add(doi)

        preview_entries.append(
            {
                'source_index': index,
                'citation_key': normalized['citation_key'],
                'entry_type': normalized['entry_type'],
                **normalized,
                'preview_status': preview_status,
                'issues': issues,
            }
        )

    return {
        'entries': preview_entries,
        'summary': {
            'total_count': len(preview_entries),
            'ready_count': sum(1 for item in preview_entries if item['preview_status'] == 'ready'),
            'duplicate_count': sum(1 for item in preview_entries if item['preview_status'] == 'duplicate'),
            'invalid_count': sum(1 for item in preview_entries if item['preview_status'] == 'invalid'),
        },
    }
