from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from django.db import transaction
from django.utils import timezone

from evaluation_rules.models import EvaluationRuleItem, EvaluationRuleVersion

from .models import (
    AcademicService,
    AchievementOperationLog,
    IntellectualProperty,
    Paper,
    Project,
    RuleBasedAchievement,
)
from .rule_scoring import apply_rule_snapshots


SUPPORTED_REVIEW_STATUSES = {'DRAFT', 'PENDING_REVIEW', 'APPROVED', 'REJECTED'}
HUMANITIES_HINTS = (
    'CSSCI',
    '人大复印',
    '新华文摘',
    '中国社会科学',
    '中国教育报',
    '光明日报',
    '人民日报',
    '哲学',
    '社科',
    '文学',
    '艺术',
    '教育',
    '人文',
)
STATE_OWNED_HORIZONTAL_HINTS = ('国有', '招标', '政府采购', '事业单位', '央企', '国企')
EVIDENCE_NOTE = '系统依据旧成果字段自动映射生成，请学院管理员结合原始佐证材料复核。'


@dataclass
class MigrationOutcome:
    action: str
    source_key: str
    source_label: str
    reason: str = ''
    rule_code: str = ''
    achievement_id: int | None = None


class LegacyAchievementRuleMigrator:
    def __init__(
        self,
        *,
        apply_changes: bool = False,
        teacher_id: int | None = None,
        stdout=None,
    ):
        self.apply_changes = apply_changes
        self.teacher_id = teacher_id
        self.stdout = stdout
        self.version = self._resolve_active_version()
        self.rule_items = self._load_rule_items()

    def run(self) -> dict:
        if self.version is None:
            raise RuntimeError('当前未配置可用的评价规则版本，无法执行历史成果迁移。')

        summary = {
            'seen': 0,
            'created': 0,
            'existing': 0,
            'skipped': 0,
        }
        outcomes: list[MigrationOutcome] = []

        for legacy_object in self._iter_legacy_objects():
            summary['seen'] += 1
            outcome = self._migrate_one(legacy_object)
            summary[outcome.action] += 1
            outcomes.append(outcome)
            self._emit_outcome(outcome)

        self._emit_summary(summary)
        return {
            'summary': summary,
            'outcomes': outcomes,
        }

    def _resolve_active_version(self) -> EvaluationRuleVersion | None:
        version = EvaluationRuleVersion.objects.filter(status=EvaluationRuleVersion.STATUS_ACTIVE).order_by('-updated_at', '-id').first()
        if version is not None:
            return version
        return EvaluationRuleVersion.objects.order_by('-updated_at', '-id').first()

    def _load_rule_items(self) -> dict[str, EvaluationRuleItem]:
        if self.version is None:
            return {}
        queryset = (
            EvaluationRuleItem.objects.filter(
                version=self.version,
                is_active=True,
                entry_policy=EvaluationRuleItem.ENTRY_REQUIRED,
            )
            .select_related('category_ref', 'version')
            .order_by('sort_order', 'id')
        )
        return {item.rule_code: item for item in queryset if item.rule_code}

    def _iter_legacy_objects(self):
        teacher_filter = {'teacher_id': self.teacher_id} if self.teacher_id else {}

        yield from (
            Paper.objects.filter(**teacher_filter)
            .select_related('teacher')
            .prefetch_related('coauthors', 'paperkeyword_set__keyword')
            .order_by('teacher_id', 'date_acquired', 'id')
        )
        yield from (
            Project.objects.filter(**teacher_filter)
            .select_related('teacher')
            .order_by('teacher_id', 'date_acquired', 'id')
        )
        yield from (
            IntellectualProperty.objects.filter(**teacher_filter)
            .select_related('teacher')
            .order_by('teacher_id', 'date_acquired', 'id')
        )
        yield from (
            AcademicService.objects.filter(**teacher_filter)
            .select_related('teacher')
            .order_by('teacher_id', 'date_acquired', 'id')
        )

    def _migrate_one(self, legacy_object) -> MigrationOutcome:
        source_type = legacy_object.__class__.__name__.lower()
        source_key = f'legacy-{source_type}-{legacy_object.id}'
        source_label = f'{legacy_object.__class__.__name__}#{legacy_object.id}《{legacy_object.title}》'

        existing = (
            RuleBasedAchievement.objects.filter(factual_payload__legacy_source_key=source_key)
            .only('id')
            .first()
        )
        if existing is None:
            existing = (
                RuleBasedAchievement.objects.filter(external_reference=source_key)
                .only('id')
                .first()
            )
        if existing is not None:
            return MigrationOutcome(
                action='existing',
                source_key=source_key,
                source_label=source_label,
                reason='已存在对应的新体系成果记录，跳过重复迁移。',
                achievement_id=existing.id,
            )

        mapping = self._build_mapping(legacy_object, source_key)
        if mapping is None:
            return MigrationOutcome(
                action='skipped',
                source_key=source_key,
                source_label=source_label,
                reason='未找到符合当前核心科研能力规则的可自动映射项。',
            )

        rule_item = self.rule_items.get(mapping['rule_code'])
        if rule_item is None or rule_item.category_ref_id is None:
            return MigrationOutcome(
                action='skipped',
                source_key=source_key,
                source_label=source_label,
                reason=f"规则项 {mapping['rule_code']} 不存在或未绑定分类，无法迁移。",
                rule_code=mapping['rule_code'],
            )

        if not self.apply_changes:
            return MigrationOutcome(
                action='created',
                source_key=source_key,
                source_label=source_label,
                reason='干跑预览成功，未实际写入。',
                rule_code=rule_item.rule_code,
            )

        with transaction.atomic():
            instance = RuleBasedAchievement(
                teacher=legacy_object.teacher,
                version=rule_item.version,
                category=rule_item.category_ref,
                rule_item=rule_item,
                **mapping['payload'],
            )
            apply_rule_snapshots(instance)
            if instance.status == 'APPROVED':
                instance.final_score = instance.provisional_score
                instance.reviewed_at = timezone.now()
            else:
                instance.final_score = Decimal('0')
            instance.save()
            self._log_import(instance, source_key, source_label)

        return MigrationOutcome(
            action='created',
            source_key=source_key,
            source_label=source_label,
            reason='已迁移。',
            rule_code=rule_item.rule_code,
            achievement_id=instance.id,
        )

    def _build_mapping(self, legacy_object, source_key: str) -> dict | None:
        if isinstance(legacy_object, Paper):
            return self._map_paper(legacy_object, source_key)
        if isinstance(legacy_object, Project):
            return self._map_project(legacy_object, source_key)
        if isinstance(legacy_object, IntellectualProperty):
            return self._map_intellectual_property(legacy_object, source_key)
        if isinstance(legacy_object, AcademicService):
            return None
        return None

    def _map_paper(self, paper: Paper, source_key: str) -> dict | None:
        rule_code = self._resolve_paper_rule_code(paper)
        if not rule_code:
            return None

        keywords = [
            relation.keyword.name.strip()
            for relation in paper.paperkeyword_set.select_related('keyword').all()
            if relation.keyword_id and relation.keyword.name.strip()
        ]
        coauthor_names = [
            coauthor.name.strip()
            for coauthor in paper.coauthors.all()
            if coauthor.name.strip()
        ]

        return {
            'rule_code': rule_code,
            'payload': {
                'title': paper.title,
                'external_reference': source_key,
                'date_acquired': paper.date_acquired,
                'status': self._normalize_status(paper.status),
                'issuing_organization': '',
                'publication_name': (paper.journal_name or '').strip(),
                'role_text': self._build_paper_role_text(paper),
                'author_rank': 1 if paper.is_first_author else None,
                'is_corresponding_author': bool(paper.is_corresponding_author),
                'is_representative': bool(paper.is_representative),
                'school_unit_order': '',
                'amount_value': None,
                'amount_unit': '',
                'keywords_text': '，'.join(keywords),
                'coauthor_names': coauthor_names,
                'team_identifier': '',
                'team_total_members': None,
                'team_allocated_score': None,
                'team_contribution_note': '',
                'evidence_note': EVIDENCE_NOTE,
                'factual_payload': {
                    'legacy_source_key': source_key,
                    'legacy_source_type': 'paper',
                    'legacy_source_id': paper.id,
                    'legacy_status': paper.status,
                    'legacy_external_reference': (paper.doi or '').strip(),
                    'legacy_fields': {
                        'paper_type': paper.paper_type,
                        'journal_name': (paper.journal_name or '').strip(),
                        'journal_level': (paper.journal_level or '').strip(),
                        'published_volume': (paper.published_volume or '').strip(),
                        'published_issue': (paper.published_issue or '').strip(),
                        'pages': (paper.pages or '').strip(),
                        'source_url': (paper.source_url or '').strip(),
                        'doi': (paper.doi or '').strip(),
                        'abstract': (paper.abstract or '').strip(),
                    },
                    'migrated_at': timezone.now().isoformat(),
                },
                'review_comment': '',
            },
        }

    def _map_project(self, project: Project, source_key: str) -> dict | None:
        rule_code = self._resolve_project_rule_code(project)
        if not rule_code:
            return None

        rule_item = self.rule_items.get(rule_code)
        if rule_item is None:
            return None

        amount_value = project.funding_amount if rule_item.requires_amount_input else None
        amount_unit = rule_item.score_unit_label if rule_item.requires_amount_input else ''

        return {
            'rule_code': rule_code,
            'payload': {
                'title': project.title,
                'external_reference': source_key,
                'date_acquired': project.date_acquired,
                'status': self._normalize_status(project.status),
                'issuing_organization': '',
                'publication_name': '',
                'role_text': '项目负责人' if project.role == 'PI' else '项目参与人',
                'author_rank': None,
                'is_corresponding_author': False,
                'is_representative': False,
                'school_unit_order': '',
                'amount_value': amount_value,
                'amount_unit': amount_unit,
                'keywords_text': '',
                'coauthor_names': [],
                'team_identifier': '',
                'team_total_members': None,
                'team_allocated_score': None,
                'team_contribution_note': '',
                'evidence_note': EVIDENCE_NOTE,
                'factual_payload': {
                    'legacy_source_key': source_key,
                    'legacy_source_type': 'project',
                    'legacy_source_id': project.id,
                    'legacy_status': project.status,
                    'legacy_fields': {
                        'level': project.level,
                        'role': project.role,
                        'funding_amount': str(project.funding_amount),
                        'project_status': (project.project_status or '').strip(),
                    },
                    'migrated_at': timezone.now().isoformat(),
                },
                'review_comment': '',
            },
        }

    def _map_intellectual_property(self, ip: IntellectualProperty, source_key: str) -> dict | None:
        rule_code = self._resolve_ip_rule_code(ip)
        if not rule_code:
            return None

        return {
            'rule_code': rule_code,
            'payload': {
                'title': ip.title,
                'external_reference': source_key,
                'date_acquired': ip.date_acquired,
                'status': self._normalize_status(ip.status),
                'issuing_organization': '',
                'publication_name': '',
                'role_text': '负责人' if ip.role == 'PI' else '参与人',
                'author_rank': None,
                'is_corresponding_author': False,
                'is_representative': False,
                'school_unit_order': '',
                'amount_value': None,
                'amount_unit': '',
                'keywords_text': '',
                'coauthor_names': [],
                'team_identifier': '',
                'team_total_members': None,
                'team_allocated_score': None,
                'team_contribution_note': '',
                'evidence_note': EVIDENCE_NOTE,
                'factual_payload': {
                    'legacy_source_key': source_key,
                    'legacy_source_type': 'intellectualproperty',
                    'legacy_source_id': ip.id,
                    'legacy_status': ip.status,
                    'legacy_external_reference': (ip.registration_number or '').strip(),
                    'legacy_fields': {
                        'ip_type': ip.ip_type,
                        'role': ip.role,
                        'registration_number': (ip.registration_number or '').strip(),
                        'is_transformed': bool(ip.is_transformed),
                    },
                    'migrated_at': timezone.now().isoformat(),
                },
                'review_comment': '',
            },
        }

    def _resolve_paper_rule_code(self, paper: Paper) -> str | None:
        journal_level = self._normalize_text(paper.journal_level)
        journal_name = self._normalize_text(paper.journal_name)
        title = self._normalize_text(paper.title)
        is_humanities = self._looks_humanities(paper.journal_level, paper.journal_name, paper.title, paper.abstract)

        if 'CCF-A' in journal_level or 'CCFA' in journal_level:
            return 'PAPER_NS_06'
        if 'CCF-B' in journal_level or 'CCFB' in journal_level:
            return 'PAPER_NS_08'
        if 'CCF-C' in journal_level or 'CCFC' in journal_level:
            return 'PAPER_NS_09'
        if 'SCI一区TOP' in journal_level or ('SCI' in journal_level and '一区' in journal_level and 'TOP' in journal_level):
            return 'PAPER_NS_04'
        if 'SCI一区' in journal_level or ('SCI' in journal_level and '一区' in journal_level):
            return 'PAPER_NS_06'
        if 'SCI二区TOP' in journal_level or ('SCI' in journal_level and '二区' in journal_level and 'TOP' in journal_level):
            return 'PAPER_NS_07'
        if 'SCI二区' in journal_level or ('SCI' in journal_level and '二区' in journal_level):
            return 'PAPER_NS_08'
        if 'SCI' in journal_level:
            return 'PAPER_NS_09'
        if 'CSSCI核心' in journal_level or ('CSSCI' in journal_level and '核心' in journal_level):
            return 'PAPER_HS_07'
        if 'CSSCI' in journal_level:
            return 'PAPER_HS_09'
        if 'EI' in journal_level:
            return 'PAPER_HS_08' if is_humanities else 'PAPER_NS_09'
        if '核心期刊' in journal_level or ('核心' in journal_level and 'CSSCI' not in journal_level):
            return 'PAPER_HS_09' if is_humanities else 'PAPER_NS_10'
        if '会议论文' in journal_level or ('CONFERENCE' == paper.paper_type and '会议' in title):
            return 'PAPER_HS_08' if is_humanities else 'PAPER_NS_09'
        if '延安大学学报' in journal_name:
            return 'PAPER_HS_17' if is_humanities else 'PAPER_NS_15'
        if paper.paper_type == 'CONFERENCE':
            return 'PAPER_HS_08' if is_humanities else 'PAPER_NS_09'
        return None

    def _resolve_project_rule_code(self, project: Project) -> str | None:
        title = self._normalize_text(project.title)
        is_humanities = self._looks_humanities(project.title, project.project_status)
        amount = project.funding_amount or Decimal('0')

        if project.level == 'ENTERPRISE':
            if is_humanities:
                if amount < Decimal('3'):
                    return None
                if self._contains_any(title, STATE_OWNED_HORIZONTAL_HINTS):
                    return 'PROJECT_HS_H_01'
                return 'PROJECT_HS_H_02'
            if self._contains_any(title, STATE_OWNED_HORIZONTAL_HINTS):
                if amount < Decimal('7'):
                    return None
                return 'PROJECT_NS_H_01'
            if amount < Decimal('5'):
                return None
            return 'PROJECT_NS_H_02'

        if project.level == 'NATIONAL':
            if is_humanities:
                if '重大' in title:
                    return 'PROJECT_HS_01'
                if '重点' in title:
                    return 'PROJECT_HS_03'
                return 'PROJECT_HS_04'
            if '重点' in title:
                return 'PROJECT_NS_02'
            if '青年' in title:
                return 'PROJECT_NS_05'
            if '地区' in title:
                return 'PROJECT_NS_06'
            return 'PROJECT_NS_04'

        if project.level == 'PROVINCIAL':
            if is_humanities:
                if '重大' in title:
                    return 'PROJECT_HS_05'
                if '重点' in title or '一类学会' in title:
                    return 'PROJECT_HS_06'
                if '一般' in title or '青年' in title or '后期资助' in title or '艺术基金' in title:
                    return 'PROJECT_HS_07'
                return 'PROJECT_HS_08'
            if '青年托举' in title or '科技新星' in title:
                return 'PROJECT_NS_11'
            if '重点' in title:
                return 'PROJECT_NS_09'
            if '创新团队' in title or '杰出青年' in title or '秦创原' in title:
                return 'PROJECT_NS_08'
            return 'PROJECT_NS_11'

        return None

    def _resolve_ip_rule_code(self, ip: IntellectualProperty) -> str | None:
        title = self._normalize_text(ip.title)
        registration_number = self._normalize_text(ip.registration_number)
        if ip.ip_type != 'PATENT_INVENTION':
            return None
        if any(keyword in title or keyword in registration_number for keyword in ('US', 'EU', 'JP', 'WO', 'PCT', '国际')):
            return 'TRANS_01'
        return 'TRANS_02'

    def _build_paper_role_text(self, paper: Paper) -> str:
        parts: list[str] = []
        if paper.is_first_author:
            parts.append('第一作者')
        else:
            parts.append('非第一作者')
        if paper.is_corresponding_author:
            parts.append('通讯作者')
        return ' / '.join(parts)

    def _normalize_status(self, status_value: str) -> str:
        cleaned = (status_value or '').strip().upper()
        if cleaned in SUPPORTED_REVIEW_STATUSES:
            return cleaned
        return 'DRAFT'

    def _looks_humanities(self, *values) -> bool:
        merged = ' '.join(str(value or '') for value in values).upper()
        return any(hint.upper() in merged for hint in HUMANITIES_HINTS)

    def _contains_any(self, text: str, hints: tuple[str, ...]) -> bool:
        return any(hint.upper() in text for hint in hints)

    def _normalize_text(self, value) -> str:
        return ''.join(str(value or '').strip().upper().split())

    def _log_import(self, instance: RuleBasedAchievement, source_key: str, source_label: str):
        detail = f"{instance.category_name_snapshot or instance.category.name} / {instance.rule_title_snapshot or instance.rule_item.title}"
        AchievementOperationLog.objects.create(
            teacher=instance.teacher,
            operator=None,
            achievement_type='rule-achievements',
            achievement_id=instance.id,
            action='IMPORT',
            source='system',
            summary=f'历史成果自动映射迁移：{source_label}',
            changed_fields=['规则条目', '迁移来源'],
            title_snapshot=instance.title,
            detail_snapshot=detail,
            snapshot_payload={
                'legacy_source_key': source_key,
                'legacy_source_label': source_label,
                'rule_code': instance.rule_code_snapshot or instance.rule_item.rule_code,
                'rule_title': instance.rule_title_snapshot or instance.rule_item.title,
                'provisional_score': str(instance.provisional_score),
                'final_score': str(instance.final_score),
            },
            review_comment='',
        )

    def _emit_outcome(self, outcome: MigrationOutcome):
        if self.stdout is None:
            return
        prefix_map = {
            'created': '[created]',
            'existing': '[existing]',
            'skipped': '[skipped]',
        }
        prefix = prefix_map.get(outcome.action, '[info]')
        rule_part = f" -> {outcome.rule_code}" if outcome.rule_code else ''
        achievement_part = f" (id={outcome.achievement_id})" if outcome.achievement_id else ''
        self.stdout.write(f"{prefix} {outcome.source_key}{rule_part}{achievement_part} | {outcome.reason}")

    def _emit_summary(self, summary: dict):
        if self.stdout is None:
            return
        mode_text = '正式写入' if self.apply_changes else '干跑预览'
        self.stdout.write(
            'summary: '
            f"mode={mode_text}, seen={summary['seen']}, created={summary['created']}, "
            f"existing={summary['existing']}, skipped={summary['skipped']}"
        )
