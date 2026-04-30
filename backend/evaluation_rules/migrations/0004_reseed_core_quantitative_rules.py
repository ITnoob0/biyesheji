from decimal import Decimal, InvalidOperation
import re

from django.db import migrations


CORE_VERSION_CODE = 'YAU_RESEARCH_CORE_2022_CORE_V1'


CATEGORY_CONFIGS = [
    {
        'code': 'PROJECT',
        'name': '科研项目',
        'description': '按项目类别、层级和到款金额认定的科研项目成果。',
        'dimension_key': 'funding_support',
        'dimension_label': '项目竞争与资源获取',
        'entry_enabled': True,
        'include_in_total': True,
        'include_in_radar': True,
        'sort_order': 10,
        'is_active': True,
    },
    {
        'code': 'PAPER_BOOK',
        'name': '学术论文与著作',
        'description': '按论文级别、期刊层级和著作出版情况认定的学术产出。',
        'dimension_key': 'academic_output',
        'dimension_label': '学术产出与著作',
        'entry_enabled': True,
        'include_in_total': True,
        'include_in_radar': True,
        'sort_order': 20,
        'is_active': True,
    },
    {
        'code': 'AWARD',
        'name': '科研成果获奖',
        'description': '按科研成果奖励级别、学术荣誉等级认定的获奖成果。',
        'dimension_key': 'ip_strength',
        'dimension_label': '成果获奖与学术荣誉',
        'entry_enabled': True,
        'include_in_total': True,
        'include_in_radar': True,
        'sort_order': 30,
        'is_active': True,
    },
    {
        'code': 'TRANSFORMATION',
        'name': '成果转化',
        'description': '按专利授权、标准制定、许可转让到账金额等认定的成果转化成果。',
        'dimension_key': 'academic_reputation',
        'dimension_label': '转化服务与智库贡献',
        'entry_enabled': True,
        'include_in_total': True,
        'include_in_radar': True,
        'sort_order': 40,
        'is_active': True,
    },
    {
        'code': 'THINK_TANK',
        'name': '智库成果',
        'description': '按智库入库、批示、采纳和咨询报告认定的决策咨询成果。',
        'dimension_key': 'academic_reputation',
        'dimension_label': '转化服务与智库贡献',
        'entry_enabled': True,
        'include_in_total': True,
        'include_in_radar': True,
        'sort_order': 50,
        'is_active': True,
    },
    {
        'code': 'PLATFORM_TEAM',
        'name': '平台与团队',
        'description': '按平台与团队认定级别计分，积分由负责人按成员贡献分配。',
        'dimension_key': 'interdisciplinary',
        'dimension_label': '平台团队与科普影响',
        'entry_enabled': True,
        'include_in_total': True,
        'include_in_radar': True,
        'sort_order': 60,
        'is_active': True,
    },
    {
        'code': 'SCI_POP_AWARD',
        'name': '科普类获奖',
        'description': '按科普类奖励级别计分，分配口径参照科技成果获奖分配方案执行。',
        'dimension_key': 'interdisciplinary',
        'dimension_label': '平台团队与科普影响',
        'entry_enabled': True,
        'include_in_total': True,
        'include_in_radar': True,
        'sort_order': 70,
        'is_active': True,
    },
]


TEAM_DISTRIBUTION_NOTE = '平台与团队必须是以延安大学作为第一依托单位。积分由平台、团队负责人按照成员贡献大小自行确定，积分人数不得超过总成员数的1/3。'
SCI_POP_AWARD_NOTE = '参照科技成果获奖分配方案执行。'


PLATFORM_TEAM_RULES = [
    {
        'rule_code': 'PLATFORM_TEAM_01',
        'title': '国家级科研平台（研究基地、重点实验室、工程中心等）和创新团队',
        'score_text': '5000',
        'sort_order': 610,
    },
    {
        'rule_code': 'PLATFORM_TEAM_02',
        'title': '教育部科研平台和创新团队',
        'score_text': '2000',
        'sort_order': 620,
    },
    {
        'rule_code': 'PLATFORM_TEAM_03',
        'title': '省级科研平台和创新团队',
        'score_text': '600',
        'sort_order': 630,
    },
    {
        'rule_code': 'PLATFORM_TEAM_04',
        'title': '中国科协科普基地',
        'score_text': '240',
        'sort_order': 640,
    },
    {
        'rule_code': 'PLATFORM_TEAM_05',
        'title': '全国一级学会科普基地；省级科协科普基地',
        'score_text': '120',
        'sort_order': 650,
    },
]


SCI_POP_AWARD_RULES = [
    {
        'rule_code': 'SCI_POP_AWARD_01',
        'title': '中国科协科普类一等奖',
        'score_text': '800',
        'sort_order': 710,
    },
    {
        'rule_code': 'SCI_POP_AWARD_02',
        'title': '中国科协科普类二等奖；国家一级学会科普一等奖；省级科协科普一等奖',
        'score_text': '600',
        'sort_order': 720,
    },
    {
        'rule_code': 'SCI_POP_AWARD_03',
        'title': '中国科协科普类三等奖；国家一级学会科普二等奖；省级科协科普二等奖',
        'score_text': '240',
        'sort_order': 730,
    },
    {
        'rule_code': 'SCI_POP_AWARD_04',
        'title': '国家一级学会科普三等奖；省级科协科普三等奖',
        'score_text': '80',
        'sort_order': 740,
    },
]


WORKFLOW_STEPS = [
    {
        'step_order': 10,
        'actor': 'TEACHER',
        'title': '教师选择成果大类与加分项',
        'description': '教师按评价规则先选择成果所属大类和对应加分项，系统同步锁定对应规则口径与分值。',
        'material_requirements': '须先确认所填成果确属核心科研能力范围内的科研项目、论文著作、成果获奖、成果转化、智库成果、平台与团队或科普类获奖。',
        'operation_note': '教师端不允许手工填写分值，只能按规则项录入事实。'
    },
    {
        'step_order': 20,
        'actor': 'TEACHER',
        'title': '教师录入成果事实并上传佐证',
        'description': '教师填写成果名称、时间、单位、角色、排序、计分基数、团队分配等事实字段，并上传佐证材料。',
        'material_requirements': '须上传与成果事实对应的正式证明材料，平台与团队类须补充分配说明。',
        'operation_note': '平台与团队类必须填写团队标识、总成员数和本人分配积分。'
    },
    {
        'step_order': 30,
        'actor': 'SYSTEM',
        'title': '系统自动预估积分并校验规则',
        'description': '系统依据所选规则项自动显示规则分值，并对金额计分、团队分配人数与总分上限进行校验。',
        'material_requirements': '',
        'operation_note': '若同一成果存在冲突规则，按规则配置处理；团队类记录自动限制重复计分。'
    },
    {
        'step_order': 40,
        'actor': 'COLLEGE_ADMIN',
        'title': '学院管理员审核成果事实',
        'description': '学院管理员审核成果事实、佐证材料、团队归属和规则匹配是否准确。',
        'material_requirements': '须核验成果真实性、佐证完整性、团队分配说明及单位归属。',
        'operation_note': '审核未通过的成果不进入教师画像。'
    },
    {
        'step_order': 50,
        'actor': 'SYSTEM',
        'title': '审核通过后写入教师画像',
        'description': '成果审核通过后，系统将正式积分写入教师画像总分与能力雷达，并参与后续聚合统计。',
        'material_requirements': '',
        'operation_note': '只有审核通过的规则化成果才参与画像、总分、雷达和统计。'
    },
]


def _parse_score_text(score_text):
    raw = (score_text or '').strip()
    if not raw:
        return {
            'score_mode': 'FIXED',
            'base_score': None,
            'score_per_unit': None,
            'score_unit_label': '',
            'requires_amount_input': False,
        }

    try:
        return {
            'score_mode': 'FIXED',
            'base_score': Decimal(raw),
            'score_per_unit': None,
            'score_unit_label': '',
            'requires_amount_input': False,
        }
    except (InvalidOperation, ValueError, ArithmeticError):
        pass

    per_amount_match = re.match(r'^([0-9]+(?:\.[0-9]+)?)\s*/\s*万元$', raw)
    if per_amount_match:
        return {
            'score_mode': 'PER_AMOUNT',
            'base_score': None,
            'score_per_unit': Decimal(per_amount_match.group(1)),
            'score_unit_label': '万元',
            'requires_amount_input': True,
        }

    if '人工' in raw or '评议' in raw:
        return {
            'score_mode': 'MANUAL',
            'base_score': None,
            'score_per_unit': None,
            'score_unit_label': '',
            'requires_amount_input': False,
        }

    return {
        'score_mode': 'FIXED',
        'base_score': None,
        'score_per_unit': None,
        'score_unit_label': '',
        'requires_amount_input': False,
    }


def _upsert_scored_rule(Item, version, category, config, *, is_team_rule=False, note='', evidence_requirements=''):
    parsed = _parse_score_text(config['score_text'])
    Item.objects.update_or_create(
        version=version,
        rule_code=config['rule_code'],
        defaults={
            'category_ref': category,
            'category': category.code,
            'discipline': 'GENERAL',
            'entry_policy': 'REQUIRED',
            'score_mode': parsed['score_mode'],
            'base_score': parsed['base_score'],
            'score_per_unit': parsed['score_per_unit'],
            'score_unit_label': parsed['score_unit_label'],
            'requires_amount_input': parsed['requires_amount_input'],
            'is_team_rule': is_team_rule,
            'team_distribution_note': TEAM_DISTRIBUTION_NOTE if is_team_rule else '',
            'team_max_member_ratio': Decimal('0.333'),
            'multi_match_policy': 'EXCLUSIVE_HIGHER',
            'entry_form_schema': [],
            'title': config['title'],
            'description': '',
            'score_text': config['score_text'],
            'note': note,
            'evidence_requirements': evidence_requirements,
            'include_in_total': True,
            'include_in_radar': True,
            'sort_order': config['sort_order'],
            'is_active': True,
        },
    )


def reseed_core_quantitative_rules(apps, schema_editor):
    EvaluationRuleVersion = apps.get_model('evaluation_rules', 'EvaluationRuleVersion')
    EvaluationRuleCategory = apps.get_model('evaluation_rules', 'EvaluationRuleCategory')
    EvaluationRuleItem = apps.get_model('evaluation_rules', 'EvaluationRuleItem')
    FilingWorkflowStep = apps.get_model('evaluation_rules', 'FilingWorkflowStep')

    version = EvaluationRuleVersion.objects.filter(code=CORE_VERSION_CODE).first()
    if version is None:
        version = EvaluationRuleVersion.objects.order_by('-updated_at', '-id').first()
    if version is None:
        return

    version.name = '延安大学核心科研能力评价规则（2022版首版落库）'
    version.source_document = '延安大学高质量贡献评价与激励标准（科研部分2022版）'
    version.summary = '教师按成果大类和加分项录入成果事实，系统自动显示规则分值；提交后进入学院管理员审核，审核通过后正式进入教师画像，并参与总分与能力雷达。'
    version.status = 'ACTIVE'
    version.save(update_fields=['name', 'source_document', 'summary', 'status', 'updated_at'])

    category_map = {}
    for config in CATEGORY_CONFIGS:
        category, _ = EvaluationRuleCategory.objects.update_or_create(
            version=version,
            code=config['code'],
            defaults=config,
        )
        category_map[config['code']] = category

    EvaluationRuleItem.objects.filter(
        version=version,
        category__in=['QUALITATIVE', 'COMMON_RULE', 'EXCLUDED'],
    ).delete()

    base_items = EvaluationRuleItem.objects.filter(version=version)
    for item in base_items:
        category = category_map.get(item.category)
        if category is None:
            continue
        parsed = _parse_score_text(item.score_text)
        item.category_ref = category
        item.category = category.code
        item.entry_policy = 'REQUIRED'
        item.score_mode = parsed['score_mode']
        item.base_score = parsed['base_score']
        item.score_per_unit = parsed['score_per_unit']
        item.score_unit_label = parsed['score_unit_label']
        item.requires_amount_input = parsed['requires_amount_input']
        item.is_team_rule = False
        item.team_distribution_note = ''
        item.team_max_member_ratio = Decimal('0.333')
        item.include_in_total = True
        item.include_in_radar = True
        item.is_active = True
        item.save(
            update_fields=[
                'category_ref',
                'category',
                'entry_policy',
                'score_mode',
                'base_score',
                'score_per_unit',
                'score_unit_label',
                'requires_amount_input',
                'is_team_rule',
                'team_distribution_note',
                'team_max_member_ratio',
                'include_in_total',
                'include_in_radar',
                'is_active',
                'updated_at',
            ]
        )

    platform_category = category_map['PLATFORM_TEAM']
    science_pop_category = category_map['SCI_POP_AWARD']

    for config in PLATFORM_TEAM_RULES:
        _upsert_scored_rule(
            EvaluationRuleItem,
            version,
            platform_category,
            config,
            is_team_rule=True,
            note=TEAM_DISTRIBUTION_NOTE,
            evidence_requirements='认定文件、依托单位证明、团队成员名单、负责人积分分配说明。',
        )

    for config in SCI_POP_AWARD_RULES:
        _upsert_scored_rule(
            EvaluationRuleItem,
            version,
            science_pop_category,
            config,
            is_team_rule=False,
            note=SCI_POP_AWARD_NOTE,
            evidence_requirements='获奖证书、等级证明、获奖人员名单或排序说明。',
        )

    FilingWorkflowStep.objects.filter(version=version).delete()
    FilingWorkflowStep.objects.bulk_create(
        [FilingWorkflowStep(version=version, **config) for config in WORKFLOW_STEPS]
    )


def noop_reverse(apps, schema_editor):
    return


class Migration(migrations.Migration):

    dependencies = [
        ('evaluation_rules', '0003_alter_evaluationruleitem_options_and_more'),
    ]

    operations = [
        migrations.RunPython(reseed_core_quantitative_rules, noop_reverse),
    ]
