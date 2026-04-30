from __future__ import annotations

from copy import deepcopy

from evaluation_rules.models import EvaluationRuleItem

from .rule_scoring import resolve_rule_item_scoring


def _field(
    *,
    key: str,
    storage: str,
    component: str,
    label: str,
    required: bool = False,
    placeholder: str = '',
    help_text: str = '',
    options: list[dict] | None = None,
    column_span: int = 1,
    minimum: float | int | None = None,
    precision: int | None = None,
):
    payload = {
        'key': key,
        'storage': storage,
        'component': component,
        'label': label,
        'required': required,
        'placeholder': placeholder,
        'help_text': help_text,
        'options': deepcopy(options or []),
        'column_span': column_span,
    }
    if minimum is not None:
        payload['min'] = minimum
    if precision is not None:
        payload['precision'] = precision
    return payload


def _text(**kwargs):
    return _field(component='text', **kwargs)


def _textarea(**kwargs):
    return _field(component='textarea', **kwargs)


def _number(**kwargs):
    return _field(component='number', **kwargs)


def _date(**kwargs):
    return _field(component='date', **kwargs)


def _select(**kwargs):
    return _field(component='select', **kwargs)


def _boolean(**kwargs):
    return _field(component='boolean', **kwargs)


def _section(key: str, title: str, description: str, fields: list[dict]):
    return {
        'key': key,
        'title': title,
        'description': description,
        'fields': fields,
    }


def _option(value: str):
    return {'label': value, 'value': value}


PROJECT_STATUS_OPTIONS = [
    {'label': '在研', 'value': 'ONGOING'},
    {'label': '已结项', 'value': 'COMPLETED'},
    {'label': '已验收', 'value': 'ACCEPTED'},
    {'label': '终止/撤项', 'value': 'TERMINATED'},
]

PAPER_OUTPUT_KIND_OPTIONS = [
    {'label': '期刊论文', 'value': 'JOURNAL_PAPER'},
    {'label': '会议论文', 'value': 'CONFERENCE_PAPER'},
    {'label': '学术专著', 'value': 'ACADEMIC_BOOK'},
    {'label': '译著', 'value': 'TRANSLATION'},
    {'label': '工具书/编著', 'value': 'TOOL_BOOK'},
    {'label': '原创音乐专辑', 'value': 'ORIGINAL_ALBUM'},
    {'label': '原创歌曲', 'value': 'ORIGINAL_SONG'},
    {'label': '原创美术作品', 'value': 'ARTWORK'},
]

AWARD_FORM_OPTIONS = [
    {'label': '科研奖励', 'value': 'RESEARCH_AWARD'},
    {'label': '学术荣誉', 'value': 'ACADEMIC_HONOR'},
    {'label': '专利奖', 'value': 'PATENT_AWARD'},
    {'label': '作品奖', 'value': 'WORK_AWARD'},
]

TRANSFORMATION_TYPE_OPTIONS = [
    {'label': '发明专利授权', 'value': 'PATENT_AUTHORIZATION'},
    {'label': '标准制定', 'value': 'STANDARD'},
    {'label': '新品种/新药/新农药', 'value': 'CERTIFICATION'},
    {'label': '许可/转让到账', 'value': 'LICENSE_TRANSFER'},
]

PATENT_REGION_OPTIONS = [
    {'label': '中国大陆', 'value': 'CN'},
    {'label': '发达国家或地区', 'value': 'DEVELOPED'},
    {'label': '其他国家或地区', 'value': 'OTHER'},
]

TRANSFORMATION_MODE_OPTIONS = [
    {'label': '授权', 'value': 'AUTHORIZATION'},
    {'label': '许可', 'value': 'LICENSE'},
    {'label': '转让', 'value': 'TRANSFER'},
    {'label': '标准发布', 'value': 'STANDARD_RELEASE'},
]

THINK_TANK_CARRIER_OPTIONS = [
    {'label': '研究报告', 'value': 'RESEARCH_REPORT'},
    {'label': '咨询报告', 'value': 'CONSULTING_REPORT'},
    {'label': '内参/专刊', 'value': 'INTERNAL_REFERENCE'},
    {'label': '成果要报', 'value': 'RESULT_BULLETIN'},
]

THINK_TANK_ADOPTION_OPTIONS = [
    {'label': '领导批示', 'value': 'LEADER_INSTRUCTION'},
    {'label': '党政机构采纳', 'value': 'ADOPTED'},
    {'label': '成果入库/刊发', 'value': 'SELECTED_OR_PUBLISHED'},
]

THINK_TANK_LEVEL_OPTIONS = [
    {'label': '国家级', 'value': 'NATIONAL'},
    {'label': '正省级', 'value': 'PROVINCIAL_LEADER'},
    {'label': '副省级', 'value': 'VICE_PROVINCIAL_LEADER'},
    {'label': '市厅级', 'value': 'BUREAU_LEVEL'},
]

PLATFORM_TYPE_OPTIONS = [
    {'label': '科研平台', 'value': 'RESEARCH_PLATFORM'},
    {'label': '创新团队', 'value': 'INNOVATION_TEAM'},
    {'label': '科普基地', 'value': 'SCIENCE_POP_BASE'},
]

SCI_POP_WORK_TYPE_OPTIONS = [
    {'label': '科普作品', 'value': 'SCI_POP_WORK'},
    {'label': '科普课程/活动', 'value': 'SCI_POP_ACTIVITY'},
    {'label': '科普平台/基地', 'value': 'SCI_POP_PLATFORM'},
]

PROJECT_ROLE_OPTIONS = [
    _option('项目负责人'),
    _option('课题负责人'),
    _option('子课题负责人'),
    _option('项目骨干'),
    _option('参与人'),
]

PAPER_ROLE_OPTIONS = [
    _option('第一作者'),
    _option('通讯作者'),
    _option('第一作者/通讯作者'),
    _option('独著'),
    _option('主编'),
    _option('编著'),
    _option('译者'),
    _option('参编'),
    _option('其他作者'),
]

AWARD_ROLE_OPTIONS = [
    _option('第一完成人'),
    _option('主要完成人'),
    _option('完成人'),
    _option('主持人'),
    _option('参与人'),
]

TRANSFORMATION_ROLE_OPTIONS = [
    _option('第一发明人'),
    _option('发明人'),
    _option('完成人'),
    _option('负责人'),
    _option('参与人'),
]

THINK_TANK_ROLE_OPTIONS = [
    _option('第一作者'),
    _option('执笔人'),
    _option('主要执笔人'),
    _option('参与人'),
]

PLATFORM_ROLE_OPTIONS = [
    _option('负责人'),
    _option('带头人'),
    _option('骨干成员'),
    _option('参与成员'),
]

SCI_POP_ROLE_OPTIONS = [
    _option('第一完成人'),
    _option('主创人'),
    _option('负责人'),
    _option('参与人'),
]

PROJECT_UNIT_ORDER_OPTIONS = [
    _option('第一依托单位'),
    _option('第二依托单位'),
    _option('参与单位'),
]

OUTPUT_UNIT_ORDER_OPTIONS = [
    _option('第一署名单位'),
    _option('第二署名单位'),
    _option('参与单位'),
]

AWARD_UNIT_ORDER_OPTIONS = [
    _option('第一完成单位'),
    _option('第二完成单位'),
    _option('参与单位'),
]

TRANSFORMATION_UNIT_ORDER_OPTIONS = [
    _option('第一专利权人'),
    _option('第二专利权人'),
    _option('第一牵头单位'),
    _option('参与单位'),
]

PLATFORM_UNIT_ORDER_OPTIONS = [
    _option('第一依托单位'),
    _option('第二依托单位'),
    _option('参与单位'),
]

SCI_POP_UNIT_ORDER_OPTIONS = [
    _option('第一完成单位'),
    _option('第二完成单位'),
    _option('参与单位'),
]


UNIQUE_IDENTIFIER_HELP_TEXT = '用于识别同一成果并执行数量去重，请填写正式编号或正式标识，不得使用简称、自拟简称或模糊写法。'
TEAM_IDENTIFIER_HELP_TEXT = '同一平台或团队由不同教师分别录入时，团队归并标识必须保持完全一致，建议使用“平台/团队名称 + 认定文号”。'


def build_rule_entry_form_schema(rule_item: EvaluationRuleItem) -> list[dict]:
    if isinstance(rule_item.entry_form_schema, list) and rule_item.entry_form_schema:
        return deepcopy(rule_item.entry_form_schema)

    builder = CATEGORY_SCHEMA_BUILDERS.get(rule_item.category_ref.code if rule_item.category_ref_id else '')
    if builder is None:
        return []
    return builder(rule_item)


def flatten_rule_entry_form_schema(form_schema: list[dict]) -> list[dict]:
    fields: list[dict] = []
    for section in form_schema or []:
        fields.extend(section.get('fields', []))
    return fields


def _resolve_amount_field(rule_item: EvaluationRuleItem) -> dict | None:
    score_config = resolve_rule_item_scoring(rule_item)
    if not score_config['requires_amount_input']:
        return None

    category_code = rule_item.category_ref.code if rule_item.category_ref_id else ''
    unit_label = score_config['score_unit_label'] or '计分基数'
    label = f'计分基数（{unit_label}）'
    help_text = '请填写与规则积分直接对应的数量基数。'

    if category_code == 'PROJECT':
        label = '到账经费（万元）'
        help_text = '横向项目按实际到账经费填报，不是合同总额。'
    elif category_code == 'TRANSFORMATION' and rule_item.rule_code == 'TRANS_09':
        label = '许可/转让到账金额（万元）'
        help_text = '按实际到账金额填报，并与到账凭证保持一致。'
    elif category_code == 'PAPER_BOOK':
        if unit_label == '万字':
            label = '字数（万字）'
            help_text = '著作、译著、工具书按公开出版字数填报。'
        elif unit_label == '辑':
            label = '专辑数量（辑）'
            help_text = '按公开出版并可核验的专辑数量填报。'
        elif unit_label == '首':
            label = '歌曲数量（首）'
            help_text = '按正式公开发表并可核验的原创歌曲数量填报。'

    return _number(
        key='amount_value',
        storage='root',
        label=label,
        required=True,
        placeholder='请输入计分基数',
        help_text=help_text,
        minimum=0,
        precision=2,
    )


def _build_project_schema(rule_item: EvaluationRuleItem) -> list[dict]:
    execution_fields = [
        _select(
            key='project_status',
            storage='factual_payload',
            label='项目状态',
            help_text='用于区分在研、结项、验收等阶段。',
            options=PROJECT_STATUS_OPTIONS,
        ),
        _date(
            key='project_start_date',
            storage='factual_payload',
            label='项目开始日期',
            help_text='与任务书或合同记载时间保持一致。',
        ),
        _date(
            key='project_end_date',
            storage='factual_payload',
            label='项目结束日期',
            help_text='填写计划结束或实际结项日期。',
        ),
        _text(
            key='subject_direction',
            storage='factual_payload',
            label='学科代码/研究方向',
            placeholder='如有请填写学科代码或项目所属研究方向',
            help_text='便于后续画像维度归档与审核。',
        ),
        _number(
            key='approved_funding_amount',
            storage='factual_payload',
            label='批准/合同经费（万元）',
            placeholder='如有请填写',
            help_text='非计分字段，仅用于还原项目事实。',
            minimum=0,
            precision=2,
        ),
        _text(
            key='cooperation_unit',
            storage='factual_payload',
            label='合作/委托单位',
            placeholder='横向项目可填写委托方或合作单位',
            help_text='如无可不填。',
        ),
    ]
    amount_field = _resolve_amount_field(rule_item)
    if amount_field:
        execution_fields.insert(4, amount_field)

    return [
        _section(
            'project_core',
            '项目核心信息',
            '先确认项目名称、编号、时间和承担角色，再补充执行与经费信息，避免把编号、奖项名混写进项目名称。',
            [
                _text(
                    key='title',
                    storage='root',
                    label='项目名称',
                    required=True,
                    placeholder='与立项通知、合同首页保持一致',
                ),
                _text(
                    key='external_reference',
                    storage='root',
                    label='立项编号/合同编号/任务书编号',
                    required=True,
                    placeholder='请输入正式编号',
                ),
                _date(
                    key='date_acquired',
                    storage='root',
                    label='立项/签约日期',
                    required=True,
                ),
                _text(
                    key='issuing_organization',
                    storage='root',
                    label='立项/委托单位',
                    required=True,
                    placeholder='如国家自然科学基金委员会、陕西省科技厅、委托企业',
                ),
                _select(
                    key='role_text',
                    storage='root',
                    label='本人角色',
                    required=True,
                    options=PROJECT_ROLE_OPTIONS,
                    placeholder='请选择本人角色',
                ),
                _select(
                    key='school_unit_order',
                    storage='root',
                    label='学校依托顺位',
                    required=True,
                    options=PROJECT_UNIT_ORDER_OPTIONS,
                    placeholder='请选择学校依托顺位',
                    help_text='评价文件要求积分项目以延安大学为第一主持单位，请按正式材料确认依托顺位。',
                ),
            ],
        ),
        _section(
            'project_execution',
            '执行与归属信息',
            '此部分用于支撑学院审核与后续画像分析。',
            execution_fields,
        ),
    ]


def _build_paper_book_schema(rule_item: EvaluationRuleItem) -> list[dict]:
    publication_fields = [
        _select(
            key='output_kind',
            storage='factual_payload',
            label='成果载体类型',
            required=True,
            help_text='论文、著作、译著、工具书、专辑、歌曲等请明确区分。',
            options=PAPER_OUTPUT_KIND_OPTIONS,
        ),
        _text(
            key='publication_name',
            storage='root',
            label='期刊/出版社/会议名称',
            required=True,
            placeholder='如期刊名、出版社名、会议名',
        ),
        _text(
            key='external_reference',
            storage='root',
            label='DOI / ISBN / 检索号 / 刊号',
            placeholder='如有请填写',
            help_text='用于减少重录和歧义。',
        ),
        _date(
            key='date_acquired',
            storage='root',
            label='发表/出版时间',
            required=True,
        ),
        _select(
            key='role_text',
            storage='root',
            label='本人角色',
            required=True,
            options=PAPER_ROLE_OPTIONS,
            placeholder='请选择本人角色',
        ),
        _number(
            key='author_rank',
            storage='root',
            label='作者/完成人排序',
            required=True,
            help_text='如为唯一作者也请填 1。',
            minimum=1,
            precision=0,
        ),
        _select(
            key='school_unit_order',
            storage='root',
            label='学校署名顺位',
            options=OUTPUT_UNIT_ORDER_OPTIONS,
            placeholder='请选择学校署名顺位',
        ),
    ]
    amount_field = _resolve_amount_field(rule_item)
    if amount_field:
        publication_fields.append(amount_field)

    return [
        _section(
            'paper_book_core',
            '成果发表与出版信息',
            '先确认载体，再填写正式标题、发表来源和作者信息，减少标题与载体信息混填。',
            [
                _text(
                    key='title',
                    storage='root',
                    label='论文/著作/作品标题',
                    required=True,
                    placeholder='与正式发表或出版题名保持一致',
                ),
                *publication_fields,
            ],
        ),
        _section(
            'paper_book_detail',
            '发表细节与作者信息',
            '用于还原发表事实，支撑后续主题、合作与成果结构分析。',
            [
                _text(
                    key='volume',
                    storage='factual_payload',
                    label='卷号',
                    placeholder='如有请填写',
                ),
                _text(
                    key='issue',
                    storage='factual_payload',
                    label='期号',
                    placeholder='如有请填写',
                ),
                _text(
                    key='pages',
                    storage='factual_payload',
                    label='页码范围',
                    placeholder='如 12-26',
                ),
                _text(
                    key='included_database',
                    storage='factual_payload',
                    label='收录/检索信息',
                    placeholder='如 SCI、EI、CPCI-S、CSSCI',
                ),
                _text(
                    key='keywords_text',
                    storage='root',
                    label='关键词',
                    placeholder='多个关键词用逗号或换行分隔',
                    help_text='用于后续画像主题抽取。',
                ),
                _select(
                    key='school_unit_order',
                    storage='root',
                    label='瀛︽牎瀹屾垚鍗曚綅椤轰綅',
                    options=AWARD_UNIT_ORDER_OPTIONS,
                    placeholder='璇烽€夋嫨瀛︽牎瀹屾垚鍗曚綅椤轰綅',
                ),
                _number(
                    key='cooperation_unit_count',
                    storage='factual_payload',
                    label='鍚堜綔瀹屾垚鍗曚綅鎬绘暟',
                    help_text='褰撳欢瀹夊ぇ瀛︿笉鏄涓€瀹屾垚鍗曚綅鏃讹紝璇峰～鍐欏悎浣滃畬鎴愬崟浣嶆€绘暟锛岀郴缁熸墠鑳芥寜 PDF 鎶樼畻鍗曚綅姣斾緥銆?',
                    minimum=2,
                    precision=0,
                ),
                _number(
                    key='cooperation_unit_count',
                    storage='factual_payload',
                    label='鍚堜綔瀹屾垚鍗曚綅鎬绘暟',
                    help_text='褰撳欢瀹夊ぇ瀛︿笉鏄涓€瀹屾垚鍗曚綅鏃讹紝璇峰～鍐欏悎浣滃畬鎴愬崟浣嶆€绘暟锛岀郴缁熸墠鑳芥寜 PDF 鎶樼畻鍗曚綅姣斾緥銆?',
                    minimum=2,
                    precision=0,
                ),
                _textarea(
                    key='coauthor_names',
                    storage='root',
                    label='合作作者名单',
                    placeholder='每行一个，或使用逗号分隔',
                    help_text='建议按作者顺序填写。',
                    column_span=2,
                ),
                _textarea(
                    key='summary',
                    storage='factual_payload',
                    label='摘要/内容说明',
                    placeholder='如有请填写摘要或作品简介',
                    column_span=2,
                ),
                _boolean(
                    key='is_representative',
                    storage='root',
                    label='是否代表性成果',
                ),
            ],
        ),
    ]


def _build_award_schema(rule_item: EvaluationRuleItem) -> list[dict]:
    return [
        _section(
            'award_core',
            '获奖核心信息',
            '请把“获奖成果名称”和“奖项名称”分开填写，再明确授奖单位、排序和完成单位顺位。',
            [
                _text(
                    key='title',
                    storage='root',
                    label='获奖成果名称',
                    required=True,
                    placeholder='与获奖证书或公示题名保持一致',
                ),
                _text(
                    key='award_name',
                    storage='factual_payload',
                    label='奖项名称',
                    required=True,
                    placeholder='如陕西省科学技术奖、陕西省哲学社会科学优秀成果奖',
                ),
                _date(
                    key='date_acquired',
                    storage='root',
                    label='获奖时间',
                    required=True,
                ),
                _text(
                    key='issuing_organization',
                    storage='root',
                    label='授奖单位',
                    required=True,
                    placeholder='如科技部、教育部、陕西省人民政府',
                ),
                _text(
                    key='external_reference',
                    storage='root',
                    label='证书编号/通知文号',
                    placeholder='如有请填写',
                ),
                _select(
                    key='role_text',
                    storage='root',
                    label='本人角色',
                    required=True,
                    options=AWARD_ROLE_OPTIONS,
                    placeholder='请选择本人角色',
                ),
                _number(
                    key='author_rank',
                    storage='root',
                    label='本人排序/完成人排序',
                    required=True,
                    minimum=1,
                    precision=0,
                ),
                _select(
                    key='school_unit_order',
                    storage='root',
                    label='完成单位顺位',
                    options=AWARD_UNIT_ORDER_OPTIONS,
                    placeholder='请选择完成单位顺位',
                ),
            ],
        ),
        _section(
            'award_detail',
            '补充说明',
            '用于补充奖项形态和共同完成人信息，便于学院复核。',
            [
                _select(
                    key='award_form',
                    storage='factual_payload',
                    label='奖项形态',
                    help_text='非必填，用于区分科研奖励、专利奖、作品奖等。',
                    options=AWARD_FORM_OPTIONS,
                ),
                _textarea(
                    key='coauthor_names',
                    storage='root',
                    label='共同完成人名单',
                    placeholder='每行一个，或使用逗号分隔',
                    column_span=2,
                ),
            ],
        ),
    ]


def _build_transformation_schema(rule_item: EvaluationRuleItem) -> list[dict]:
    detail_fields = [
        _select(
            key='transformation_type',
            storage='factual_payload',
            label='转化载体类型',
            required=True,
            help_text='用于区分专利授权、标准制定、成果许可/转让等口径。',
            options=TRANSFORMATION_TYPE_OPTIONS,
        ),
        _select(
            key='patent_region',
            storage='factual_payload',
            label='专利授权区域',
            options=PATENT_REGION_OPTIONS,
            help_text='专利授权类建议填写，用于辅助复核国内/国外口径。',
        ),
        _select(
            key='transformation_mode',
            storage='factual_payload',
            label='转化方式',
            options=TRANSFORMATION_MODE_OPTIONS,
        ),
        _text(
            key='transferee_org',
            storage='factual_payload',
            label='许可/受让单位',
            placeholder='如有请填写',
        ),
    ]
    amount_field = _resolve_amount_field(rule_item)
    if amount_field:
        detail_fields.insert(3, amount_field)

    return [
        _section(
            'transformation_core',
            '成果转化核心信息',
            '专利、标准、证书与到账凭证要能一一对应，避免只填标题无法核验。',
            [
                _text(
                    key='title',
                    storage='root',
                    label='成果名称',
                    required=True,
                    placeholder='如专利名称、标准名称、成果转让名称',
                ),
                _date(
                    key='date_acquired',
                    storage='root',
                    label='授权/发布/到账时间',
                    required=True,
                ),
                _text(
                    key='external_reference',
                    storage='root',
                    label='专利号/标准号/合同编号/证书编号',
                    required=True,
                    placeholder='请输入正式编号',
                ),
                _text(
                    key='issuing_organization',
                    storage='root',
                    label='授权/发布/登记单位',
                    required=True,
                    placeholder='如国家知识产权局、标准发布主管单位',
                ),
                _select(
                    key='role_text',
                    storage='root',
                    label='本人角色',
                    required=True,
                    options=TRANSFORMATION_ROLE_OPTIONS,
                    placeholder='请选择本人角色',
                ),
                _number(
                    key='author_rank',
                    storage='root',
                    label='本人排序',
                    required=True,
                    help_text='知识产权、标准和转化成果通常按完成人排序核定；如正式材料无排序可填 1 并在说明中注明。',
                    minimum=1,
                    precision=0,
                ),
                _select(
                    key='school_unit_order',
                    storage='root',
                    label='学校/专利权人顺位',
                    required=True,
                    options=TRANSFORMATION_UNIT_ORDER_OPTIONS,
                    placeholder='请选择学校/专利权人顺位',
                    help_text='评价文件要求延安大学为唯一权利人或第一完成单位，请按权利人/完成单位顺位填写。',
                ),
            ],
        ),
        _section(
            'transformation_detail',
            '转化细节',
            '用于明确具体的授权区域、转化方式和到账信息。',
            detail_fields,
        ),
    ]


def _build_think_tank_schema(rule_item: EvaluationRuleItem) -> list[dict]:
    return [
        _section(
            'think_tank_core',
            '智库成果核心信息',
            '重点把报告题名、采纳/批示单位、采纳方式和时间对应起来。',
            [
                _text(
                    key='title',
                    storage='root',
                    label='报告/成果标题',
                    required=True,
                    placeholder='与报告首页或采纳刊物题名保持一致',
                ),
                _select(
                    key='result_carrier',
                    storage='factual_payload',
                    label='成果载体',
                    required=True,
                    options=THINK_TANK_CARRIER_OPTIONS,
                ),
                _date(
                    key='date_acquired',
                    storage='root',
                    label='采纳/批示/刊发时间',
                    required=True,
                ),
                _text(
                    key='issuing_organization',
                    storage='root',
                    label='采纳/批示/刊发单位',
                    required=True,
                    placeholder='如教育部《大学智库专刊》、省委办公厅等',
                ),
                _text(
                    key='external_reference',
                    storage='root',
                    label='批示编号/刊发编号/采纳编号',
                    placeholder='如有请填写',
                ),
                _select(
                    key='role_text',
                    storage='root',
                    label='本人角色',
                    required=True,
                    options=THINK_TANK_ROLE_OPTIONS,
                    placeholder='请选择本人角色',
                ),
                _number(
                    key='author_rank',
                    storage='root',
                    label='作者排序',
                    minimum=1,
                    precision=0,
                ),
                _textarea(
                    key='coauthor_names',
                    storage='root',
                    label='参与人名单',
                    placeholder='每行一个，或使用逗号分隔',
                    column_span=2,
                ),
            ],
        ),
        _section(
            'think_tank_detail',
            '采纳方式与层级',
            '采纳方式和领导层级是智库成果最容易混淆的部分，建议如实区分。',
            [
                _select(
                    key='adoption_type',
                    storage='factual_payload',
                    label='采纳方式',
                    required=True,
                    options=THINK_TANK_ADOPTION_OPTIONS,
                ),
                _select(
                    key='leader_level',
                    storage='factual_payload',
                    label='批示/采纳层级',
                    options=THINK_TANK_LEVEL_OPTIONS,
                ),
                _text(
                    key='report_submission_unit',
                    storage='factual_payload',
                    label='报送单位/刊物名称',
                    placeholder='如成果要报、大学智库专刊等',
                ),
            ],
        ),
    ]


def _build_platform_team_schema(rule_item: EvaluationRuleItem) -> list[dict]:
    return [
        _section(
            'platform_core',
            '平台与团队认定信息',
            '围绕认定名称、认定文号、依托单位和本人角色录入，避免把平台名称与团队名称混成一项。',
            [
                _text(
                    key='title',
                    storage='root',
                    label='平台/团队名称',
                    required=True,
                    placeholder='与认定文件名称保持一致',
                ),
                _select(
                    key='platform_type',
                    storage='factual_payload',
                    label='平台/团队类型',
                    required=True,
                    options=PLATFORM_TYPE_OPTIONS,
                ),
                _date(
                    key='date_acquired',
                    storage='root',
                    label='认定时间',
                    required=True,
                ),
                _text(
                    key='issuing_organization',
                    storage='root',
                    label='认定单位',
                    required=True,
                    placeholder='如教育部、陕西省科技厅、中国科协',
                ),
                _text(
                    key='external_reference',
                    storage='root',
                    label='认定文号/编号',
                    required=True,
                    placeholder='请输入正式认定文号',
                ),
                _select(
                    key='role_text',
                    storage='root',
                    label='本人角色',
                    required=True,
                    options=PLATFORM_ROLE_OPTIONS,
                    placeholder='请选择本人角色',
                ),
                _select(
                    key='school_unit_order',
                    storage='root',
                    label='学校依托顺位',
                    required=True,
                    options=PLATFORM_UNIT_ORDER_OPTIONS,
                    placeholder='请选择学校依托顺位',
                ),
                _textarea(
                    key='coauthor_names',
                    storage='root',
                    label='主要成员名单',
                    placeholder='如需补充主要成员，请按顺序填写',
                    column_span=2,
                ),
            ],
        ),
        _section(
            'platform_team_score',
            '团队计分分配',
            '平台与团队类积分需要明确归并标识、总人数和本人分配积分。',
            [
                _text(
                    key='team_identifier',
                    storage='root',
                    label='团队归并标识',
                    required=True,
                    placeholder='建议：平台/团队名称 + 认定文号',
                ),
                _number(
                    key='team_total_members',
                    storage='root',
                    label='团队总人数',
                    required=True,
                    minimum=1,
                    precision=0,
                ),
                _number(
                    key='team_allocated_score',
                    storage='root',
                    label='本人分配积分',
                    required=True,
                    minimum=0,
                    precision=2,
                ),
                _textarea(
                    key='team_contribution_note',
                    storage='root',
                    label='团队贡献说明',
                    required=True,
                    placeholder='说明本人在平台/团队中的职责、贡献和分配依据',
                    column_span=2,
                ),
            ],
        ),
    ]


def _build_science_pop_award_schema(rule_item: EvaluationRuleItem) -> list[dict]:
    return [
        _section(
            'science_pop_award_core',
            '科普获奖信息',
            '同样要区分作品/项目名称与奖项名称，并明确授奖单位和完成顺位。',
            [
                _text(
                    key='title',
                    storage='root',
                    label='获奖作品/项目名称',
                    required=True,
                    placeholder='与获奖公示或证书题名一致',
                ),
                _text(
                    key='award_name',
                    storage='factual_payload',
                    label='科普奖项名称',
                    required=True,
                    placeholder='如中国科协科普类一等奖对应的具体奖项名称',
                ),
                _select(
                    key='work_type',
                    storage='factual_payload',
                    label='成果形态',
                    required=True,
                    options=SCI_POP_WORK_TYPE_OPTIONS,
                ),
                _date(
                    key='date_acquired',
                    storage='root',
                    label='获奖时间',
                    required=True,
                ),
                _text(
                    key='issuing_organization',
                    storage='root',
                    label='授奖单位',
                    required=True,
                ),
                _text(
                    key='external_reference',
                    storage='root',
                    label='证书编号/通知文号',
                    placeholder='如有请填写',
                ),
                _select(
                    key='role_text',
                    storage='root',
                    label='本人角色',
                    required=True,
                    options=SCI_POP_ROLE_OPTIONS,
                    placeholder='请选择本人角色',
                ),
                _number(
                    key='author_rank',
                    storage='root',
                    label='本人排序',
                    required=True,
                    minimum=1,
                    precision=0,
                ),
                _select(
                    key='school_unit_order',
                    storage='root',
                    label='学校/完成单位顺位',
                    options=SCI_POP_UNIT_ORDER_OPTIONS,
                    placeholder='请选择完成单位顺位',
                ),
                _textarea(
                    key='coauthor_names',
                    storage='root',
                    label='共同完成人名单',
                    placeholder='每行一个，或使用逗号分隔',
                    column_span=2,
                ),
            ],
        ),
    ]


def _build_paper_book_schema_v2(rule_item: EvaluationRuleItem) -> list[dict]:
    publication_fields = [
        _select(
            key='output_kind',
            storage='factual_payload',
            label='成果载体类型',
            required=True,
            help_text='论文、著作、译著、工具书、专辑、歌曲等请明确区分。',
            options=PAPER_OUTPUT_KIND_OPTIONS,
        ),
        _text(
            key='publication_name',
            storage='root',
            label='期刊/出版社/会议名称',
            required=True,
            placeholder='如期刊名、出版社名、会议名',
        ),
        _text(
            key='external_reference',
            storage='root',
            label='DOI / ISBN / 检索号 / 刊号',
            placeholder='如有请填写',
            help_text='用于减少重录和歧义。',
        ),
        _date(
            key='date_acquired',
            storage='root',
            label='发表/出版时间',
            required=True,
        ),
        _select(
            key='role_text',
            storage='root',
            label='本人角色',
            required=True,
            options=PAPER_ROLE_OPTIONS,
            placeholder='请选择本人角色',
        ),
        _number(
            key='author_rank',
            storage='root',
            label='作者/完成人排序',
            required=True,
            help_text='如为唯一作者也请填 1。',
            minimum=1,
            precision=0,
        ),
        _select(
            key='school_unit_order',
            storage='root',
            label='学校署名顺位',
            required=True,
            options=OUTPUT_UNIT_ORDER_OPTIONS,
            placeholder='请选择学校署名顺位',
            help_text='论文、著作和作品的计分与学校署名单位顺位相关，请按正式出版或发表材料填写。',
        ),
        _boolean(
            key='is_corresponding_author',
            storage='root',
            label='是否通讯作者',
            help_text='论文类成果涉及通讯作者分配口径时请勾选；著作、作品等无通讯作者可不选。',
        ),
    ]
    amount_field = _resolve_amount_field(rule_item)
    if amount_field:
        publication_fields.append(amount_field)

    return [
        _section(
            'paper_book_core',
            '成果发表与出版信息',
            '先确认载体，再填写正式标题、发表来源和作者信息，减少标题与载体信息混填。',
            [
                _text(
                    key='title',
                    storage='root',
                    label='论文/著作/作品标题',
                    required=True,
                    placeholder='与正式发表或出版题名保持一致',
                ),
                *publication_fields,
            ],
        ),
        _section(
            'paper_book_detail',
            '发表细节与作者信息',
            '用于还原发表事实，支撑后续主题、合作与成果结构分析。',
            [
                _text(
                    key='volume',
                    storage='factual_payload',
                    label='卷号',
                    placeholder='如有请填写',
                ),
                _text(
                    key='issue',
                    storage='factual_payload',
                    label='期号',
                    placeholder='如有请填写',
                ),
                _text(
                    key='pages',
                    storage='factual_payload',
                    label='页码范围',
                    placeholder='如 12-26',
                ),
                _text(
                    key='included_database',
                    storage='factual_payload',
                    label='收录/检索信息',
                    placeholder='如 SCI、EI、CPCI-S、CSSCI',
                ),
                _text(
                    key='keywords_text',
                    storage='root',
                    label='关键词',
                    placeholder='多个关键词用逗号或换行分隔',
                    help_text='用于后续画像主题抽取。',
                ),
                _textarea(
                    key='coauthor_names',
                    storage='root',
                    label='合作作者名单',
                    placeholder='每行一个，或使用逗号分隔',
                    help_text='建议按作者顺序填写。',
                    column_span=2,
                ),
                _textarea(
                    key='summary',
                    storage='factual_payload',
                    label='摘要/内容说明',
                    placeholder='如有请填写摘要或作品简介',
                    column_span=2,
                ),
                _boolean(
                    key='is_representative',
                    storage='root',
                    label='是否代表性成果',
                ),
            ],
        ),
    ]


def _build_award_schema_v2(rule_item: EvaluationRuleItem) -> list[dict]:
    return [
        _section(
            'award_core',
            '获奖核心信息',
            '请把“获奖成果名称”和“奖项名称”分开填写，再明确授奖单位、排序和完成单位顺位。',
            [
                _text(
                    key='title',
                    storage='root',
                    label='获奖成果名称',
                    required=True,
                    placeholder='与获奖证书或公示题名保持一致',
                ),
                _text(
                    key='award_name',
                    storage='factual_payload',
                    label='奖项名称',
                    required=True,
                    placeholder='如陕西省科学技术奖、陕西省哲学社会科学优秀成果奖',
                ),
                _date(
                    key='date_acquired',
                    storage='root',
                    label='获奖时间',
                    required=True,
                ),
                _text(
                    key='issuing_organization',
                    storage='root',
                    label='授奖单位',
                    required=True,
                    placeholder='如科技部、教育部、陕西省人民政府',
                ),
                _text(
                    key='external_reference',
                    storage='root',
                    label='证书编号/通知文号',
                    placeholder='如有请填写',
                ),
                _select(
                    key='role_text',
                    storage='root',
                    label='本人角色',
                    required=True,
                    options=AWARD_ROLE_OPTIONS,
                    placeholder='请选择本人角色',
                ),
                _number(
                    key='author_rank',
                    storage='root',
                    label='本人排序/完成人排序',
                    required=True,
                    minimum=1,
                    precision=0,
                ),
                _select(
                    key='school_unit_order',
                    storage='root',
                    label='完成单位顺位',
                    required=True,
                    options=AWARD_UNIT_ORDER_OPTIONS,
                    placeholder='请选择完成单位顺位',
                    help_text='科研成果获奖按学校完成单位顺位和合作单位情况折算，请按证书或正式通知填写。',
                ),
            ],
        ),
        _section(
            'award_detail',
            '补充说明',
            '用于补充奖项形态、合作单位总数和共同完成人信息，便于学院复核。',
            [
                _select(
                    key='award_form',
                    storage='factual_payload',
                    label='奖项形态',
                    help_text='非必填，用于区分科研奖励、专利奖、作品奖等。',
                    options=AWARD_FORM_OPTIONS,
                ),
                _number(
                    key='cooperation_unit_count',
                    storage='factual_payload',
                    label='合作完成单位总数',
                    help_text='当延安大学不是第一完成单位时，请填写合作完成单位总数，系统才可按 PDF 折算单位比例。',
                    minimum=2,
                    precision=0,
                ),
                _textarea(
                    key='coauthor_names',
                    storage='root',
                    label='共同完成人名单',
                    placeholder='每行一个，或使用逗号分隔',
                    column_span=2,
                ),
            ],
        ),
    ]


def _build_think_tank_schema_v2(rule_item: EvaluationRuleItem) -> list[dict]:
    return [
        _section(
            'think_tank_core',
            '智库成果核心信息',
            '重点把报告题名、采纳/批示单位、采纳方式和时间对应起来。',
            [
                _text(
                    key='title',
                    storage='root',
                    label='报告/成果标题',
                    required=True,
                    placeholder='与报告首页或采纳刊物题名保持一致',
                ),
                _select(
                    key='result_carrier',
                    storage='factual_payload',
                    label='成果载体',
                    required=True,
                    options=THINK_TANK_CARRIER_OPTIONS,
                ),
                _date(
                    key='date_acquired',
                    storage='root',
                    label='采纳/批示/刊发时间',
                    required=True,
                ),
                _text(
                    key='issuing_organization',
                    storage='root',
                    label='采纳/批示/刊发单位',
                    required=True,
                    placeholder='如教育部《大学智库专刊》、省委办公厅等',
                ),
                _text(
                    key='external_reference',
                    storage='root',
                    label='批示编号/刊发编号/采纳编号',
                    placeholder='如有请填写',
                ),
                _select(
                    key='role_text',
                    storage='root',
                    label='本人角色',
                    required=True,
                    options=THINK_TANK_ROLE_OPTIONS,
                    placeholder='请选择本人角色',
                ),
                _number(
                    key='author_rank',
                    storage='root',
                    label='作者排序',
                    minimum=1,
                    precision=0,
                ),
                _select(
                    key='school_unit_order',
                    storage='root',
                    label='学校完成单位顺位',
                    required=True,
                    options=AWARD_UNIT_ORDER_OPTIONS,
                    placeholder='请选择学校完成单位顺位',
                    help_text='智库成果按延安大学第一/第二完成单位分别计入，请按正式采纳、批示或刊发材料填写。',
                ),
                _textarea(
                    key='coauthor_names',
                    storage='root',
                    label='参与人名单',
                    placeholder='每行一个，或使用逗号分隔',
                    column_span=2,
                ),
            ],
        ),
        _section(
            'think_tank_detail',
            '采纳方式与层级',
            '采纳方式和领导层级是智库成果最容易混淆的部分，建议如实区分。',
            [
                _select(
                    key='adoption_type',
                    storage='factual_payload',
                    label='采纳方式',
                    required=True,
                    options=THINK_TANK_ADOPTION_OPTIONS,
                ),
                _select(
                    key='leader_level',
                    storage='factual_payload',
                    label='批示/采纳层级',
                    options=THINK_TANK_LEVEL_OPTIONS,
                ),
                _text(
                    key='report_submission_unit',
                    storage='factual_payload',
                    label='报送单位/刊物名称',
                    placeholder='如成果要报、大学智库专刊等',
                ),
            ],
        ),
    ]


def _build_science_pop_award_schema_v2(rule_item: EvaluationRuleItem) -> list[dict]:
    return [
        _section(
            'science_pop_award_core',
            '科普获奖信息',
            '同样要区分作品/项目名称与奖项名称，并明确授奖单位和完成顺位。',
            [
                _text(
                    key='title',
                    storage='root',
                    label='获奖作品/项目名称',
                    required=True,
                    placeholder='与获奖公示或证书题名一致',
                ),
                _text(
                    key='award_name',
                    storage='factual_payload',
                    label='科普奖项名称',
                    required=True,
                    placeholder='如中国科协科普类一等奖对应的具体奖项名称',
                ),
                _select(
                    key='work_type',
                    storage='factual_payload',
                    label='成果形态',
                    required=True,
                    options=SCI_POP_WORK_TYPE_OPTIONS,
                ),
                _date(
                    key='date_acquired',
                    storage='root',
                    label='获奖时间',
                    required=True,
                ),
                _text(
                    key='issuing_organization',
                    storage='root',
                    label='授奖单位',
                    required=True,
                ),
                _text(
                    key='external_reference',
                    storage='root',
                    label='证书编号/通知文号',
                    placeholder='如有请填写',
                ),
                _select(
                    key='role_text',
                    storage='root',
                    label='本人角色',
                    required=True,
                    options=SCI_POP_ROLE_OPTIONS,
                    placeholder='请选择本人角色',
                ),
                _number(
                    key='author_rank',
                    storage='root',
                    label='本人排序',
                    required=True,
                    minimum=1,
                    precision=0,
                ),
                _select(
                    key='school_unit_order',
                    storage='root',
                    label='学校/完成单位顺位',
                    required=True,
                    options=SCI_POP_UNIT_ORDER_OPTIONS,
                    placeholder='请选择完成单位顺位',
                    help_text='科普类获奖参照科技奖励分配方法，请按证书或正式通知填写学校完成单位顺位。',
                ),
                _number(
                    key='cooperation_unit_count',
                    storage='factual_payload',
                    label='合作完成单位总数',
                    help_text='当延安大学不是第一完成单位时，请填写合作完成单位总数，系统才可按 PDF 折算单位比例。',
                    minimum=2,
                    precision=0,
                ),
                _textarea(
                    key='coauthor_names',
                    storage='root',
                    label='共同完成人名单',
                    placeholder='每行一个，或使用逗号分隔',
                    column_span=2,
                ),
            ],
        ),
    ]


CATEGORY_SCHEMA_BUILDERS = {
    'PROJECT': _build_project_schema,
    'PAPER_BOOK': _build_paper_book_schema_v2,
    'AWARD': _build_award_schema_v2,
    'TRANSFORMATION': _build_transformation_schema,
    'THINK_TANK': _build_think_tank_schema_v2,
    'PLATFORM_TEAM': _build_platform_team_schema,
    'SCI_POP_AWARD': _build_science_pop_award_schema_v2,
}
