from __future__ import annotations

import math
import re
from decimal import Decimal, InvalidOperation

from django.db.models import Sum

from evaluation_rules.models import EvaluationRuleItem

from .models import RuleBasedAchievement


def _to_decimal(value) -> Decimal | None:
    if value in {None, ''}:
        return None
    try:
        return Decimal(str(value))
    except (InvalidOperation, ValueError, TypeError, ArithmeticError):
        return None


def parse_score_text(score_text: str) -> dict:
    raw = (score_text or '').strip()
    if not raw:
        return {}

    fixed = _to_decimal(raw)
    if fixed is not None:
        return {
            'score_mode': EvaluationRuleItem.SCORE_MODE_FIXED,
            'base_score': fixed,
        }

    for pattern, unit_label in (
        (r'^([0-9]+(?:\.[0-9]+)?)\s*/\s*万元$', '万元'),
        (r'^([0-9]+(?:\.[0-9]+)?)\s*/\s*万字$', '万字'),
        (r'^([0-9]+(?:\.[0-9]+)?)\s*/\s*辑$', '辑'),
        (r'^([0-9]+(?:\.[0-9]+)?)\s*/\s*首$', '首'),
    ):
        matched = re.match(pattern, raw)
        if matched:
            return {
                'score_mode': EvaluationRuleItem.SCORE_MODE_PER_AMOUNT,
                'score_per_unit': _to_decimal(matched.group(1)),
                'score_unit_label': unit_label,
                'requires_amount_input': True,
            }

    if '人工' in raw or '评议' in raw:
        return {
            'score_mode': EvaluationRuleItem.SCORE_MODE_MANUAL,
        }

    return {}


def resolve_rule_item_scoring(rule_item: EvaluationRuleItem) -> dict:
    parsed = parse_score_text(rule_item.score_text)
    score_mode = rule_item.score_mode or parsed.get('score_mode') or EvaluationRuleItem.SCORE_MODE_FIXED
    if (
        score_mode == EvaluationRuleItem.SCORE_MODE_FIXED
        and parsed.get('score_mode') in {EvaluationRuleItem.SCORE_MODE_PER_AMOUNT, EvaluationRuleItem.SCORE_MODE_MANUAL}
        and not rule_item.score_per_unit
        and not rule_item.requires_amount_input
    ):
        score_mode = parsed['score_mode']

    return {
        'score_mode': score_mode,
        'base_score': _to_decimal(rule_item.base_score) or parsed.get('base_score'),
        'score_per_unit': _to_decimal(rule_item.score_per_unit) or parsed.get('score_per_unit'),
        'score_unit_label': rule_item.score_unit_label or parsed.get('score_unit_label') or '',
        'requires_amount_input': bool(rule_item.requires_amount_input or parsed.get('requires_amount_input')),
    }


NS_SECOND_UNIT_HALF_RULE_CODES = {
    'PAPER_NS_01',
    'PAPER_NS_02',
    'PAPER_NS_03',
    'PAPER_NS_04',
    'PAPER_NS_05',
    'PAPER_NS_06',
}
HS_SECOND_UNIT_HALF_RULE_CODES = {
    'PAPER_HS_01',
    'PAPER_HS_02',
    'PAPER_HS_03',
    'PAPER_HS_04',
}
SPECIAL_AUTHOR_SHARE = {
    1: Decimal('0.50'),
    2: Decimal('0.25'),
    3: Decimal('0.15'),
}
STANDARD_PARTICIPATION_SCORES = {
    'TRANS_05': Decimal('200'),
    'TRANS_06': Decimal('100'),
}
AWARD_UNIT_SHARE_TABLE = {
    2: {2: Decimal('0.30')},
    3: {2: Decimal('0.25'), 3: Decimal('0.10')},
    4: {2: Decimal('0.25'), 3: Decimal('0.10'), 4: Decimal('0.05')},
    5: {2: Decimal('0.25'), 3: Decimal('0.10'), 4: Decimal('0.05'), 5: Decimal('0.05')},
}


def _rule_code(rule_item: EvaluationRuleItem | None) -> str:
    return (getattr(rule_item, 'rule_code', '') or '').strip().upper()


def _payload_dict(instance: RuleBasedAchievement | None) -> dict:
    payload = getattr(instance, 'factual_payload', {}) or {}
    return payload if isinstance(payload, dict) else {}


def _normalize_role_text(value) -> str:
    return _normalize_reference_text(value)


def _contains_any_token(value: str, tokens: tuple[str, ...]) -> bool:
    normalized = _normalize_reference_text(value)
    return any(_normalize_reference_text(token) in normalized for token in tokens)


def _infer_author_rank(instance: RuleBasedAchievement | None) -> int | None:
    if instance is None:
        return None
    rank = getattr(instance, 'author_rank', None)
    if rank:
        try:
            return int(rank)
        except (TypeError, ValueError):
            return None
    normalized_role = _normalize_role_text(getattr(instance, 'role_text', ''))
    if '第一' in normalized_role:
        return 1
    if '第二' in normalized_role:
        return 2
    if '第三' in normalized_role:
        return 3
    return None


def _unit_order_position(unit_order: str) -> int | None:
    normalized = _normalize_reference_text(unit_order)
    if not normalized:
        return None
    if '独立' in normalized or '唯一' in normalized:
        return 1
    mapping = {
        '第一': 1,
        '第二': 2,
        '第三': 3,
        '第四': 4,
        '第五': 5,
    }
    for token, position in mapping.items():
        if _normalize_reference_text(token) in normalized:
            return position
    return None


def _extract_positive_int(payload: dict, *keys: str) -> int | None:
    for key in keys:
        value = payload.get(key)
        if value in {None, ''}:
            continue
        try:
            parsed = int(value)
        except (TypeError, ValueError):
            continue
        if parsed > 0:
            return parsed
    return None


def _is_project_host(instance: RuleBasedAchievement) -> bool:
    normalized_role = _normalize_role_text(instance.role_text)
    return any(token in normalized_role for token in ('负责人', '主持'))


def _is_article_like_output(instance: RuleBasedAchievement) -> bool:
    output_kind = _normalize_reference_text(_get_payload_value(_payload_dict(instance), 'output_kind'))
    return output_kind in {_normalize_reference_text('JOURNAL_PAPER'), _normalize_reference_text('CONFERENCE_PAPER')}


def _is_special_ns_distribution(instance: RuleBasedAchievement, rule_code: str) -> bool:
    if rule_code == 'PAPER_NS_01':
        return True
    if rule_code != 'PAPER_NS_02':
        return False
    publication_name = _normalize_reference_text(instance.publication_name)
    return any(token in publication_name for token in ('nature', 'science', 'cell'))


def _is_special_hs_distribution(instance: RuleBasedAchievement, rule_code: str) -> bool:
    if rule_code == 'PAPER_HS_01':
        return True
    publication_name = _normalize_free_text(instance.publication_name)
    return '中国社会科学' in publication_name


def _is_lead_paper_contributor(instance: RuleBasedAchievement) -> bool:
    rank = _infer_author_rank(instance)
    if rank == 1:
        return True
    if bool(getattr(instance, 'is_corresponding_author', False)):
        return True
    normalized_role = _normalize_role_text(instance.role_text)
    return any(token in normalized_role for token in ('第一作者', '通讯作者', '独著'))


def _is_corresponding_paper_contributor(instance: RuleBasedAchievement) -> bool:
    if bool(getattr(instance, 'is_corresponding_author', False)):
        return True
    normalized_role = _normalize_role_text(instance.role_text)
    return '通讯作者' in normalized_role


def _adjust_project_preview(instance: RuleBasedAchievement, preview_score: Decimal, notes: list[str]) -> Decimal:
    if not _is_project_host(instance):
        notes.append('科研项目按 PDF 仅认定主持项目，当前录入角色若非负责人/主持人，则预估分按 0 处理。')
        return Decimal('0')
    return preview_score


def _adjust_paper_preview(instance: RuleBasedAchievement, preview_score: Decimal, notes: list[str]) -> Decimal:
    if not _is_article_like_output(instance):
        return preview_score

    rule_code = _rule_code(instance.rule_item)
    author_rank = _infer_author_rank(instance)
    unit_position = _unit_order_position(instance.school_unit_order)

    if _is_special_ns_distribution(instance, rule_code) or _is_special_hs_distribution(instance, rule_code):
        share = SPECIAL_AUTHOR_SHARE.get(author_rank or 0)
        is_corresponding = _is_corresponding_paper_contributor(instance)
        if share is None and not is_corresponding:
            notes.append('该顶级论文仅通讯作者、第一作者及排名前三作者参与分配，当前排序不满足条件，预估分按 0 处理。')
            return Decimal('0')
        if is_corresponding and share is None:
            share = SPECIAL_AUTHOR_SHARE[1]
        notes.append('当前论文按 PDF 的特殊作者分配规则试算。')
        return preview_score * share

    if unit_position == 2:
        if rule_code in NS_SECOND_UNIT_HALF_RULE_CODES or rule_code in HS_SECOND_UNIT_HALF_RULE_CODES:
            if _is_lead_paper_contributor(instance):
                notes.append('当前按延安大学第二署名单位的 50% 口径试算。')
                return preview_score * Decimal('0.50')
            notes.append('第二署名单位论文仅通讯作者或第一作者可计分，当前作者位次不满足条件，预估分按 0 处理。')
            return Decimal('0')
        notes.append('当前论文在第二署名单位口径下不属于可按 50% 计分的等级，预估分按 0 处理。')
        return Decimal('0')

    if _rule_code(instance.rule_item).startswith('PAPER_') and not _is_lead_paper_contributor(instance):
        notes.append('当前论文按 PDF 默认仅第一作者或通讯作者可计分，当前作者位次不满足条件，预估分按 0 处理。')
        return Decimal('0')

    return preview_score


def _adjust_award_preview(instance: RuleBasedAchievement, preview_score: Decimal, notes: list[str]) -> Decimal:
    author_rank = _infer_author_rank(instance)
    if author_rank and author_rank > 1:
        notes.append('科研成果获奖积分全部计于我校获奖第一人，当前完成人排序不满足条件，预估分按 0 处理。')
        return Decimal('0')

    unit_position = _unit_order_position(instance.school_unit_order)
    if unit_position and unit_position > 1:
        payload = _payload_dict(instance)
        cooperation_unit_count = _extract_positive_int(
            payload,
            'cooperation_unit_count',
            'cooperation_units_total',
            'collaboration_unit_count',
        )
        share = AWARD_UNIT_SHARE_TABLE.get(cooperation_unit_count or 0, {}).get(unit_position)
        if share is None:
            notes.append('当前成果存在合作完成单位顺位，请补充合作完成单位总数后再精确试算单位折算比例。')
            return preview_score
        notes.append('当前按合作完成单位顺位折算后试算。')
        return preview_score * share

    return preview_score


def _adjust_transformation_preview(instance: RuleBasedAchievement, preview_score: Decimal, notes: list[str]) -> Decimal:
    rule_code = _rule_code(instance.rule_item)
    normalized_role = _normalize_role_text(instance.role_text)
    unit_position = _unit_order_position(instance.school_unit_order)
    author_rank = _infer_author_rank(instance)

    if rule_code in STANDARD_PARTICIPATION_SCORES and '参与' in normalized_role:
        notes.append('当前标准类成果按“参与制定”口径试算。')
        return STANDARD_PARTICIPATION_SCORES[rule_code]

    if unit_position and unit_position > 1:
        notes.append('成果转化类成果原则上要求延安大学为唯一权利人或第一完成单位，当前顺位不满足条件，预估分按 0 处理。')
        return Decimal('0')

    if author_rank and author_rank > 1 and rule_code not in {'TRANS_05', 'TRANS_06'}:
        notes.append('成果转化类成果原则上仅第一完成人计分，当前排序不满足条件，预估分按 0 处理。')
        return Decimal('0')

    return preview_score


def _adjust_think_tank_preview(instance: RuleBasedAchievement, preview_score: Decimal, notes: list[str]) -> Decimal:
    unit_position = _unit_order_position(instance.school_unit_order)
    if unit_position == 2:
        notes.append('当前智库成果按第二完成单位 50% 口径试算。')
        return preview_score * Decimal('0.50')
    return preview_score


def _adjust_platform_team_preview(instance: RuleBasedAchievement, preview_score: Decimal, notes: list[str]) -> Decimal:
    unit_position = _unit_order_position(instance.school_unit_order)
    if unit_position and unit_position > 1:
        notes.append('平台与团队仅认定延安大学第一依托单位，当前依托顺位不满足条件，预估分按 0 处理。')
        return Decimal('0')
    return preview_score


def _apply_contextual_preview_rules(
    *,
    instance: RuleBasedAchievement | None,
    preview_score: Decimal,
    notes: list[str],
) -> Decimal:
    if instance is None or getattr(instance, 'rule_item', None) is None:
        return preview_score

    category_code = (
        getattr(getattr(instance, 'category', None), 'code', '')
        or getattr(instance, 'category_code_snapshot', '')
        or getattr(instance.rule_item.category_ref, 'code', '')
        or ''
    ).strip().upper()

    if category_code == 'PROJECT':
        return _adjust_project_preview(instance, preview_score, notes)
    if category_code == 'PAPER_BOOK':
        return _adjust_paper_preview(instance, preview_score, notes)
    if category_code in {'AWARD', 'SCI_POP_AWARD'}:
        return _adjust_award_preview(instance, preview_score, notes)
    if category_code == 'TRANSFORMATION':
        return _adjust_transformation_preview(instance, preview_score, notes)
    if category_code == 'THINK_TANK':
        return _adjust_think_tank_preview(instance, preview_score, notes)
    if category_code == 'PLATFORM_TEAM':
        return _adjust_platform_team_preview(instance, preview_score, notes)
    return preview_score


def build_score_preview(
    *,
    rule_item: EvaluationRuleItem,
    amount_value=None,
    team_allocated_score=None,
    instance: RuleBasedAchievement | None = None,
) -> dict:
    score_config = resolve_rule_item_scoring(rule_item)
    preview_score = Decimal('0')
    notes: list[str] = []

    if score_config['score_mode'] == EvaluationRuleItem.SCORE_MODE_FIXED:
        preview_score = score_config['base_score'] or Decimal('0')
    elif score_config['score_mode'] == EvaluationRuleItem.SCORE_MODE_PER_AMOUNT:
        normalized_amount = _to_decimal(amount_value) or Decimal('0')
        preview_score = (score_config['score_per_unit'] or Decimal('0')) * normalized_amount
        if normalized_amount <= 0:
            notes.append('当前规则按金额或数量自动计分，请补充计分基数后再查看有效预估分。')
    elif score_config['score_mode'] == EvaluationRuleItem.SCORE_MODE_MANUAL:
        preview_score = Decimal('0')
        notes.append('当前规则需要管理员或专家人工认定，系统仅展示规则口径。')

    if rule_item.is_team_rule:
        allocated = _to_decimal(team_allocated_score)
        if allocated is None:
            preview_score = Decimal('0')
            notes.append('当前条目属于团队积分分配项，请填写本人分配积分。')
        else:
            preview_score = allocated
        notes.append(
            rule_item.team_distribution_note
            or '平台、团队负责人按照成员贡献大小确定积分分配，计分人数不得超过总成员数的 1/3。'
        )

    preview_score = _apply_contextual_preview_rules(
        instance=instance,
        preview_score=preview_score,
        notes=notes,
    )
    preview_score = preview_score.quantize(Decimal('0.01'))
    return {
        'score_mode': score_config['score_mode'],
        'score_text': rule_item.score_text,
        'base_score': str(score_config['base_score'] or Decimal('0')),
        'score_per_unit': str(score_config['score_per_unit'] or Decimal('0')),
        'score_unit_label': score_config['score_unit_label'],
        'requires_amount_input': score_config['requires_amount_input'],
        'is_team_rule': rule_item.is_team_rule,
        'preview_score': str(preview_score),
        'notes': notes,
    }


def apply_rule_snapshots(instance: RuleBasedAchievement) -> RuleBasedAchievement:
    preview = build_score_preview(
        rule_item=instance.rule_item,
        amount_value=instance.amount_value,
        team_allocated_score=instance.team_allocated_score,
        instance=instance,
    )
    instance.version = instance.rule_item.version
    instance.category = instance.rule_item.category_ref
    instance.provisional_score = _to_decimal(preview['preview_score']) or Decimal('0')
    instance.rule_code_snapshot = instance.rule_item.rule_code
    instance.rule_title_snapshot = instance.rule_item.title
    instance.category_code_snapshot = instance.category.code if instance.category_id else ''
    instance.category_name_snapshot = instance.category.name if instance.category_id else ''
    instance.score_text_snapshot = instance.rule_item.score_text
    instance.include_in_total_snapshot = bool(instance.rule_item.include_in_total)
    instance.include_in_radar_snapshot = bool(instance.rule_item.include_in_radar)
    instance.amount_unit = instance.amount_unit or preview['score_unit_label']
    instance.score_detail = preview
    return instance


def calculate_team_member_limit(total_members: int, ratio=None) -> int:
    if total_members <= 0:
        return 0
    normalized_ratio = _to_decimal(ratio) or Decimal('0.333')
    calculated = math.floor(total_members * float(normalized_ratio))
    return max(calculated, 1)


def validate_team_rule_constraints(instance: RuleBasedAchievement, *, approval_phase: bool = False) -> list[str]:
    if not instance.rule_item.is_team_rule:
        return []

    errors: list[str] = []
    allocated_score = _to_decimal(instance.team_allocated_score)
    total_members = instance.team_total_members or 0

    if not instance.team_identifier.strip():
        errors.append('团队积分条目必须填写团队归并标识。')
    if total_members <= 0:
        errors.append('团队积分条目必须填写团队总成员数。')
    if allocated_score is None or allocated_score <= 0:
        errors.append('团队积分条目必须填写本人分配积分。')

    if errors or not approval_phase:
        return errors

    existing_queryset = RuleBasedAchievement.objects.filter(
        status='APPROVED',
        rule_item=instance.rule_item,
        team_identifier=instance.team_identifier,
    ).exclude(pk=instance.pk)

    existing_count = existing_queryset.count()
    existing_allocated_sum = _to_decimal(existing_queryset.aggregate(total=Sum('team_allocated_score'))['total']) or Decimal('0')
    current_allocated_sum = existing_allocated_sum + (allocated_score or Decimal('0'))
    current_scored_count = existing_count + 1

    member_limit = calculate_team_member_limit(total_members, instance.rule_item.team_max_member_ratio)
    if current_scored_count > member_limit:
        errors.append(f'按当前团队分配，计分人数已超过允许上限（最多 {member_limit} 人）。')

    rule_score_config = resolve_rule_item_scoring(instance.rule_item)
    total_team_score = rule_score_config['base_score']
    if total_team_score is not None and current_allocated_sum > total_team_score:
        errors.append('当前团队累计分配积分已超过该规则条目的总积分。')

    return errors


def _normalize_free_text(value) -> str:
    return re.sub(r'[^\w\u4e00-\u9fff]+', '', str(value or '').casefold(), flags=re.UNICODE)


def _normalize_reference_text(value) -> str:
    return re.sub(r'\s+', '', str(value or '').casefold())


def _normalize_page_text(value) -> str:
    return re.sub(r'[^0-9a-zA-Z\-]+', '', str(value or '').casefold())


def _normalize_date_text(value) -> str:
    if not value:
        return ''
    if hasattr(value, 'isoformat'):
        return value.isoformat()
    return str(value).strip()


def _extract_year_text(value) -> str:
    if not value:
        return ''
    if hasattr(value, 'year'):
        return str(value.year)
    matched = re.match(r'^\s*(\d{4})', str(value))
    return matched.group(1) if matched else ''


def _get_payload_value(payload: dict, *keys: str):
    for key in keys:
        value = payload.get(key)
        if value is not None and value != '':
            return value
    return ''


def _compose_identity_key(prefix: str, basis: str, *parts: str) -> str:
    normalized_parts = [part for part in parts if part]
    return ':'.join([prefix, basis, *normalized_parts])


def build_same_achievement_identity(instance: RuleBasedAchievement) -> dict[str, str]:
    payload = instance.factual_payload or {}
    category_code = (
        getattr(getattr(instance, 'category', None), 'code', '')
        or getattr(instance, 'category_code_snapshot', '')
        or ''
    ).strip().upper()
    group_token = _normalize_reference_text(category_code or f'item-{getattr(instance, "rule_item_id", "unknown")}')
    title = _normalize_free_text(instance.title)
    external_reference = _normalize_reference_text(instance.external_reference)
    publication_name = _normalize_free_text(instance.publication_name)
    issuing_organization = _normalize_free_text(instance.issuing_organization)
    date_text = _normalize_date_text(instance.date_acquired)
    year_text = _extract_year_text(instance.date_acquired)

    if category_code == 'PLATFORM_TEAM':
        team_identifier = _normalize_reference_text(instance.team_identifier)
        if team_identifier:
            return {
                'key': _compose_identity_key(group_token, 'team', team_identifier),
                'basis': 'team_identifier',
            }
        if external_reference:
            return {
                'key': _compose_identity_key(group_token, 'external_reference', external_reference),
                'basis': 'external_reference',
            }
        platform_type = _normalize_reference_text(_get_payload_value(payload, 'platform_type'))
        return {
            'key': _compose_identity_key(
                group_token,
                'composite',
                title,
                platform_type,
                issuing_organization,
                date_text or year_text,
            ),
            'basis': 'composite',
        }

    if external_reference:
        return {
            'key': _compose_identity_key(group_token, 'external_reference', external_reference),
            'basis': 'external_reference',
        }

    if category_code == 'PAPER_BOOK':
        output_kind = _normalize_reference_text(_get_payload_value(payload, 'output_kind'))
        volume = _normalize_reference_text(_get_payload_value(payload, 'volume', 'published_volume'))
        issue = _normalize_reference_text(_get_payload_value(payload, 'issue', 'published_issue'))
        pages = _normalize_page_text(_get_payload_value(payload, 'pages'))
        included_database = _normalize_reference_text(_get_payload_value(payload, 'included_database'))
        composite_parts = [title, publication_name, output_kind, date_text or year_text]
        if volume or issue or pages:
            composite_parts.extend([volume, issue, pages])
        elif included_database:
            composite_parts.append(included_database)
        if title and publication_name and (date_text or year_text):
            return {
                'key': _compose_identity_key(group_token, 'composite', *composite_parts),
                'basis': 'composite',
            }

    if category_code == 'PROJECT':
        start_date = _normalize_date_text(_get_payload_value(payload, 'project_start_date'))
        subject_direction = _normalize_free_text(_get_payload_value(payload, 'subject_direction'))
        if title and issuing_organization and (start_date or date_text or year_text):
            return {
                'key': _compose_identity_key(
                    group_token,
                    'composite',
                    title,
                    issuing_organization,
                    start_date or date_text or year_text,
                    subject_direction,
                ),
                'basis': 'composite',
            }

    if category_code in {'AWARD', 'SCI_POP_AWARD'}:
        award_name = _normalize_free_text(_get_payload_value(payload, 'award_name'))
        work_type = _normalize_reference_text(_get_payload_value(payload, 'work_type'))
        if title and award_name and issuing_organization and (date_text or year_text):
            return {
                'key': _compose_identity_key(
                    group_token,
                    'composite',
                    title,
                    award_name,
                    work_type,
                    issuing_organization,
                    date_text or year_text,
                ),
                'basis': 'composite',
            }

    if category_code == 'TRANSFORMATION':
        transformation_type = _normalize_reference_text(_get_payload_value(payload, 'transformation_type'))
        transferee_org = _normalize_free_text(_get_payload_value(payload, 'transferee_org'))
        if title and (transformation_type or issuing_organization) and (date_text or year_text):
            return {
                'key': _compose_identity_key(
                    group_token,
                    'composite',
                    title,
                    transformation_type,
                    issuing_organization,
                    transferee_org,
                    date_text or year_text,
                ),
                'basis': 'composite',
            }

    if category_code == 'THINK_TANK':
        result_carrier = _normalize_reference_text(_get_payload_value(payload, 'result_carrier'))
        adoption_type = _normalize_reference_text(_get_payload_value(payload, 'adoption_type'))
        report_submission_unit = _normalize_free_text(_get_payload_value(payload, 'report_submission_unit'))
        if title and issuing_organization and (date_text or year_text):
            return {
                'key': _compose_identity_key(
                    group_token,
                    'composite',
                    title,
                    result_carrier,
                    adoption_type,
                    report_submission_unit or issuing_organization,
                    date_text or year_text,
                ),
                'basis': 'composite',
            }

    if title and (publication_name or issuing_organization) and (date_text or year_text):
        return {
            'key': _compose_identity_key(
                group_token,
                'composite',
                title,
                publication_name or issuing_organization,
                date_text or year_text,
            ),
            'basis': 'composite',
        }

    fallback_id = str(getattr(instance, 'pk', None) or id(instance))
    return {
        'key': _compose_identity_key(group_token, 'record', fallback_id),
        'basis': 'record_fallback',
    }


def build_same_achievement_key(instance: RuleBasedAchievement) -> str:
    return build_same_achievement_identity(instance)['key']


def build_same_achievement_basis(instance: RuleBasedAchievement) -> str:
    return build_same_achievement_identity(instance)['basis']


def build_conflict_group_key(instance: RuleBasedAchievement) -> str:
    return build_same_achievement_key(instance)


def tokenize_keywords(raw_keywords: str) -> list[str]:
    return [item.strip() for item in re.split(r'[，、,\s]+', raw_keywords or '') if item.strip()]
