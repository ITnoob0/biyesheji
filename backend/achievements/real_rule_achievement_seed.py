from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime, time, timedelta
from decimal import Decimal
from typing import Any

from django.contrib.auth import get_user_model
from django.utils import timezone

from evaluation_rules.models import EvaluationRuleItem, EvaluationRuleVersion

from .models import AchievementOperationLog, RuleBasedAchievement
from .portrait_analysis import invalidate_benchmark_score_cache
from .rule_scoring import apply_rule_snapshots


DEMO_PASSWORD = 'liujianlei'
DEMO_SOURCE_TAG = 'REAL_RULE_DEMO'


@dataclass(frozen=True)
class DemoUserSpec:
    username: str
    real_name: str
    department: str
    title: str = ''
    research_direction: tuple[str, ...] = ()
    bio: str = ''
    is_staff: bool = False


@dataclass(frozen=True)
class DemoAchievementSpec:
    seed_key: str
    teacher_username: str
    reviewer_username: str
    rule_code: str
    status: str
    title: str
    external_reference: str
    date_acquired: date
    issuing_organization: str = ''
    publication_name: str = ''
    role_text: str = ''
    author_rank: int | None = None
    is_corresponding_author: bool = False
    is_representative: bool = False
    school_unit_order: str = ''
    amount_value: Decimal | None = None
    amount_unit: str = ''
    keywords_text: str = ''
    coauthor_names: tuple[str, ...] = ()
    team_identifier: str = ''
    team_total_members: int | None = None
    team_allocated_score: Decimal | None = None
    team_contribution_note: str = ''
    evidence_note: str = ''
    factual_payload: dict[str, Any] = field(default_factory=dict)
    review_comment: str = ''
    source_title: str = ''
    source_urls: tuple[str, ...] = ()
    source_note: str = ''
    source_date_note: str = ''


COLLEGE_ADMIN_SPECS: tuple[DemoUserSpec, ...] = (
    DemoUserSpec(
        username='demo_admin_physics',
        real_name='物理与电子信息学院管理员',
        department='物理与电子信息学院',
        title='学院管理员',
        is_staff=True,
    ),
    DemoUserSpec(
        username='demo_admin_literature',
        real_name='文学院管理员',
        department='文学院',
        title='学院管理员',
        is_staff=True,
    ),
    DemoUserSpec(
        username='demo_admin_law',
        real_name='政法与公共管理学院管理员',
        department='政法与公共管理学院',
        title='学院管理员',
        is_staff=True,
    ),
    DemoUserSpec(
        username='demo_admin_education',
        real_name='教育科学学院管理员',
        department='教育科学学院',
        title='学院管理员',
        is_staff=True,
    ),
)


TEACHER_SPECS: tuple[DemoUserSpec, ...] = (
    DemoUserSpec(
        username='demo_cao_xinliang',
        real_name='曹新亮',
        department='物理与电子信息学院',
        title='教授',
        research_direction=('卫星导航', '信号处理', '北斗应用'),
        bio='延安大学公开师资页面显示其长期从事卫星导航与信号处理相关研究。',
    ),
    DemoUserSpec(
        username='demo_li_hui',
        real_name='李惠',
        department='文学院',
        title='教授',
        research_direction=('中国现当代文学', '延安文艺研究'),
        bio='延安大学公开师资页面显示其研究方向涉及中国现当代文学与延安文艺研究。',
    ),
    DemoUserSpec(
        username='demo_hu_junsheng',
        real_name='胡俊生',
        department='政法与公共管理学院',
        title='教授',
        research_direction=('教育社会学', '扶贫研究'),
        bio='延安大学公开页面显示其长期从事教育社会学与扶贫研究。',
    ),
    DemoUserSpec(
        username='demo_zhou_xuejun',
        real_name='周学军',
        department='物理与电子信息学院',
        title='副教授',
        research_direction=('通信工程', '工程结构设计'),
        bio='延安大学公开教师页面显示其在物理与电子信息学院任教。',
    ),
    DemoUserSpec(
        username='demo_yang_caixia',
        real_name='杨彩霞',
        department='教育科学学院',
        title='副教授',
        research_direction=('心理健康教育', '学校心理学'),
        bio='延安大学公开教师页面显示其研究方向与学生心理健康教育相关。',
    ),
    DemoUserSpec(
        username='demo_xing_xin',
        real_name='邢鑫',
        department='教育科学学院',
        title='副教授',
        research_direction=('干部教育', '红色资源开发'),
        bio='延安大学公开教师页面显示其研究涉及干部教育与红色资源开发。',
    ),
)


DEMO_ACHIEVEMENT_SPECS: tuple[DemoAchievementSpec, ...] = (
    DemoAchievementSpec(
        seed_key='cao_xinliang_project_61661049',
        teacher_username='demo_cao_xinliang',
        reviewer_username='demo_admin_physics',
        rule_code='PROJECT_NS_06',
        status='APPROVED',
        title='北斗信号沙漠回波特性及陕北沙地参数反演算法研究',
        external_reference='61661049',
        date_acquired=date(2017, 1, 1),
        issuing_organization='国家自然科学基金委员会',
        role_text='项目负责人',
        school_unit_order='第一依托单位',
        amount_value=Decimal('35.00'),
        amount_unit='万元',
        keywords_text='北斗信号，GNSS，沙地参数反演',
        evidence_note='已按公开资料核对批准号、项目类别、批准经费与起止时间。',
        factual_payload={
            'project_status': 'COMPLETED',
            'project_start_date': '2017-01-01',
            'project_end_date': '2020-12-31',
            'subject_direction': '卫星导航与信号处理',
            'approved_funding_amount': '35.00',
        },
        source_title='延安大学教师成果与国家自然科学基金公开信息',
        source_urls=(
            'https://wdxy.yau.edu.cn/info/1257/12814.htm',
            'https://yjsc.yau.edu.cn/info/1028/13100.htm',
        ),
        source_note='公开页面可核对项目名称、批准号、批准经费、负责人和学院信息。',
    ),
    DemoAchievementSpec(
        seed_key='li_hui_paper_reprint_2022',
        teacher_username='demo_li_hui',
        reviewer_username='demo_admin_literature',
        rule_code='PAPER_HS_07',
        status='APPROVED',
        title='毛泽东《在延安文艺座谈会上的讲话》原始口述版考察',
        external_reference='人大复印资料《毛泽东思想》2022年第3期',
        date_acquired=date(2022, 10, 19),
        publication_name='河北学刊 / 人大复印资料《毛泽东思想》',
        role_text='第一作者',
        author_rank=1,
        is_representative=True,
        school_unit_order='第一署名单位',
        keywords_text='延安文艺，毛泽东，讲话版本',
        coauthor_names=('高锐',),
        evidence_note='以学校公开报道确认“人大复印资料全文转载”事实，原刊发布时间另在扩展字段中保留。',
        factual_payload={
            'output_kind': 'JOURNAL_PAPER',
            'volume': '42',
            'issue': '2',
            'pages': '53-59',
            'included_database': '人大复印资料全文转载',
            'summary': '学校公开报道载明该文刊发于《河北学刊》2022年第2期，并被人大复印资料《毛泽东思想》2022年第3期全文转载。',
            'original_publication_date': '2022-03-01',
        },
        source_title='延安大学文学院转载报道与河北学刊公开目录',
        source_urls=(
            'https://wxy.yau.edu.cn/info/1002/33623.htm',
            'https://www.hebeishkx.com/CN/10.16494/j.cnki.1003-7071.2022.02.001',
            'https://yjsy.yau.edu.cn/old/info/1028/14620.htm',
        ),
        source_note='学校公开报道可直接核对全文转载事实；河北学刊公开目录可核对原文题名、作者与刊期。',
        source_date_note='公开来源未见人大复印资料具体刊发日，测试数据按学校公开报道日期 2022-10-19 归一。',
    ),
    DemoAchievementSpec(
        seed_key='li_hui_award_2023_second_prize_pending',
        teacher_username='demo_li_hui',
        reviewer_username='demo_admin_literature',
        rule_code='AWARD_HS_05',
        status='PENDING_REVIEW',
        title='毛泽东《在延安文艺座谈会上的讲话》原始口述版考察',
        external_reference='陕西省第十六次哲学社会科学优秀成果奖（二等奖）',
        date_acquired=date(2025, 3, 3),
        issuing_organization='陕西省人民政府',
        role_text='第一完成人',
        author_rank=1,
        school_unit_order='第一完成单位',
        coauthor_names=('高锐',),
        evidence_note='该样例特意保留为待审核状态，用于展示“教师填报后进入学院审核队列”的流程。',
        factual_payload={
            'award_name': '陕西省第十六次哲学社会科学优秀成果奖二等奖',
            'award_form': 'RESEARCH_AWARD',
        },
        source_title='延安大学获奖通报',
        source_urls=(
            'https://www.yau.edu.cn/info/1120/26998.htm',
            'https://yjsy.yau.edu.cn/old/info/1028/14620.htm',
        ),
        source_note='学校公开通报列明成果题名、完成人与二等奖事实。',
        source_date_note='公开来源未披露具体授奖日，测试数据按学校发布获奖通报日期 2025-03-03 归一。',
    ),
    DemoAchievementSpec(
        seed_key='hu_junsheng_award_first_prize',
        teacher_username='demo_hu_junsheng',
        reviewer_username='demo_admin_law',
        rule_code='AWARD_HS_03',
        status='APPROVED',
        title='教育扶贫论：社会学的视角',
        external_reference='陕西省第十六次哲学社会科学优秀成果奖（一等奖）',
        date_acquired=date(2025, 3, 3),
        issuing_organization='陕西省人民政府',
        role_text='第一完成人',
        author_rank=1,
        school_unit_order='第一完成单位',
        coauthor_names=('李期',),
        evidence_note='学校公开通报列明一等奖事实、成果名称与完成人。',
        factual_payload={
            'award_name': '陕西省第十六次哲学社会科学优秀成果奖一等奖',
            'award_form': 'RESEARCH_AWARD',
        },
        source_title='延安大学获奖通报与教师主页',
        source_urls=(
            'https://www.yau.edu.cn/info/1120/26998.htm',
            'https://jjglxy.yau.edu.cn/info/1390/19766.htm',
        ),
        source_note='学校公开通报可核对一等奖事实；教师主页用于核对真实姓名与学院。',
        source_date_note='公开来源未披露具体授奖日，测试数据按学校发布获奖通报日期 2025-03-03 归一。',
    ),
    DemoAchievementSpec(
        seed_key='zhou_xuejun_patent_authorization_zl2020101593230',
        teacher_username='demo_zhou_xuejun',
        reviewer_username='demo_admin_physics',
        rule_code='TRANS_02',
        status='APPROVED',
        title='一种平台升降式独管通讯塔',
        external_reference='ZL202010159323.0',
        date_acquired=date(2021, 3, 19),
        issuing_organization='国家知识产权局',
        role_text='第一发明人',
        author_rank=1,
        school_unit_order='第一专利权人',
        evidence_note='公开来源可核对专利名称、专利号、专利类型与授权公告日。',
        factual_payload={
            'transformation_type': 'PATENT_AUTHORIZATION',
            'patent_region': 'CN',
            'transformation_mode': 'AUTHORIZATION',
        },
        source_title='延安大学发明专利授权名单与教师主页',
        source_urls=(
            'https://wdxy.yau.edu.cn/info/1056/12408.htm',
            'https://wdxy.yau.edu.cn/info/1024/11274.htm',
        ),
        source_note='学院公开专利授权名单可核对专利号和授权日期；教师主页用于核对真实姓名与职称。',
    ),
    DemoAchievementSpec(
        seed_key='zhou_xuejun_patent_transfer_20260130',
        teacher_username='demo_zhou_xuejun',
        reviewer_username='demo_admin_physics',
        rule_code='TRANS_09',
        status='APPROVED',
        title='一种平台升降式独管通讯塔',
        external_reference='ZL202010159323.0',
        date_acquired=date(2026, 1, 30),
        issuing_organization='延安大学',
        role_text='第一发明人',
        author_rank=1,
        school_unit_order='第一专利权人',
        amount_value=Decimal('1.80'),
        team_contribution_note='该成果转化由专利权人推进实施，到账金额按公开公示口径录入。',
        evidence_note='按公开公示信息录入到账金额 1.8 万元，系统自动按 8/万元折算为 14.4 分。',
        factual_payload={
            'transformation_type': 'LICENSE_TRANSFER',
            'transformation_mode': 'TRANSFER',
        },
        source_title='延安大学专利权转让公示',
        source_urls=(
            'https://kyc.yau.edu.cn/info/1032/6619.htm',
            'https://wdxy.yau.edu.cn/info/1056/12408.htm',
        ),
        source_note='学校科技处公开公示可核对专利名称、专利号、转让日期和转让金额。',
    ),
    DemoAchievementSpec(
        seed_key='yang_caixia_think_tank_yaoqingkuaibao',
        teacher_username='demo_yang_caixia',
        reviewer_username='demo_admin_education',
        rule_code='THINK_05',
        status='APPROVED',
        title='我省中小学生心理健康教育工作存在的问题及对策',
        external_reference='陕西省委办公厅《要情快报》采用',
        date_acquired=date(2024, 12, 24),
        issuing_organization='陕西省委办公厅《要情快报》',
        role_text='执笔人',
        author_rank=1,
        coauthor_names=('王红',),
        evidence_note='按学校公开报道采用“省委办公厅《要情快报》采用并获省委常委领导批示”的保守口径映射到 THINK_05。',
        factual_payload={
            'result_carrier': 'INTERNAL_REFERENCE',
            'adoption_type': 'LEADER_INSTRUCTION',
            'leader_level': 'VICE_PROVINCIAL_LEADER',
            'report_submission_unit': '陕西省委办公厅《要情快报》',
        },
        source_title='延安大学智库成果报道与教师主页',
        source_urls=(
            'https://jykxxy.yau.edu.cn/info/1053/60363.htm',
            'https://jykxxy.yau.edu.cn/info/1017/5664.htm',
        ),
        source_note='学校公开报道明确写明被《要情快报》采用并获省委常委领导批示；教师主页用于核对真实姓名与学院。',
        source_date_note='公开来源未披露具体批示日，测试数据按学校发布报道日期 2024-12-24 归一。',
    ),
    DemoAchievementSpec(
        seed_key='xing_xin_platform_intro_base',
        teacher_username='demo_xing_xin',
        reviewer_username='demo_admin_education',
        rule_code='PLATFORM_TEAM_03',
        status='APPROVED',
        title='干部教育国际交流引智基地',
        external_reference='陕教函〔2024〕36号',
        date_acquired=date(2024, 1, 9),
        issuing_organization='陕西省教育厅',
        role_text='负责人',
        school_unit_order='第一依托单位',
        team_identifier='干部教育国际交流引智基地-陕教函〔2024〕36号',
        team_total_members=3,
        team_allocated_score=Decimal('600.00'),
        team_contribution_note='作为基地负责人承担申报论证、建设方案制定与组织实施工作，按规则将本次示例积分全部分配至负责人。',
        coauthor_names=('周海军', '王苏平'),
        evidence_note='该条用于验证平台与团队类规则的团队积分分配、审核通过和教师画像联动。',
        factual_payload={
            'platform_type': 'RESEARCH_PLATFORM',
        },
        source_title='延安大学社会科学处报道与教师主页',
        source_urls=(
            'https://skc.yau.edu.cn/info/1033/23898.htm',
            'https://jykxxy.yau.edu.cn/info/1017/5665.htm',
        ),
        source_note='学校公开报道可核对基地名称与认定事实；教师主页用于核对真实姓名与学院。',
        source_date_note='测试数据按学校发布“获批”报道日期 2024-01-09 归一。',
    ),
    DemoAchievementSpec(
        seed_key='xing_xin_team_innovation_rejected',
        teacher_username='demo_xing_xin',
        reviewer_username='demo_admin_education',
        rule_code='PLATFORM_TEAM_03',
        status='REJECTED',
        title='红色资源与干部教育研究协同创新团队',
        external_reference='陕西高校青年创新团队（2023）',
        date_acquired=date(2023, 10, 8),
        issuing_organization='陕西省教育厅',
        role_text='带头人',
        school_unit_order='第一依托单位',
        team_identifier='红色资源与干部教育研究协同创新团队-2023',
        team_total_members=5,
        team_allocated_score=Decimal('300.00'),
        team_contribution_note='本条故意保留为驳回样例，用于展示学院管理员要求补充团队成员贡献说明和认定证明材料的流程。',
        coauthor_names=('周海军', '赵森', '王苏平'),
        evidence_note='当前仅录入团队基本事实，管理员驳回后需补充认定文件和团队成员贡献依据。',
        factual_payload={
            'platform_type': 'INNOVATION_TEAM',
        },
        review_comment='请补充省级认定文件扫描件、团队成员名单及个人积分分配依据后重新提交。',
        source_title='教育科学学院团队报道与教师主页',
        source_urls=(
            'https://jykxxy.yau.edu.cn/info/1043/5736.htm',
            'https://jykxxy.yau.edu.cn/info/1017/5665.htm',
        ),
        source_note='学校公开报道可核对团队名称；本条特意保留为驳回态，用于演示审核闭环。',
    ),
)


class RealRuleAchievementDemoSeeder:
    def __init__(self, *, stdout=None):
        self.stdout = stdout
        self.user_model = get_user_model()
        self.version = self._resolve_active_version()
        self.rule_item_map = self._build_rule_item_map()
        self.users: dict[str, Any] = {}

    def run(self) -> dict[str, int]:
        summary = {
            'users_created': 0,
            'users_updated': 0,
            'achievements_created': 0,
            'achievements_updated': 0,
            'logs_created': 0,
        }
        self._ensure_users(summary)
        for spec in DEMO_ACHIEVEMENT_SPECS:
            created = self._upsert_achievement(spec, summary)
            self._ensure_workflow_logs(spec, created=created, summary=summary)

        invalidate_benchmark_score_cache()
        return summary

    def _resolve_active_version(self) -> EvaluationRuleVersion:
        version = EvaluationRuleVersion.objects.filter(
            status=EvaluationRuleVersion.STATUS_ACTIVE
        ).order_by('-updated_at', '-id').first()
        if version is None:
            raise RuntimeError('当前未找到启用中的核心科研能力规则版本，无法注入真实演示成果。')
        return version

    def _build_rule_item_map(self) -> dict[str, EvaluationRuleItem]:
        items = EvaluationRuleItem.objects.select_related('category_ref').filter(version=self.version, is_active=True)
        mapping = {item.rule_code: item for item in items if item.rule_code}
        missing = [spec.rule_code for spec in DEMO_ACHIEVEMENT_SPECS if spec.rule_code not in mapping]
        if missing:
            raise RuntimeError(f'缺少以下规则条目，无法注入演示成果：{", ".join(sorted(set(missing)))}')
        return mapping

    def _ensure_users(self, summary: dict[str, int]) -> None:
        for spec in (*COLLEGE_ADMIN_SPECS, *TEACHER_SPECS):
            user, created = self.user_model.objects.get_or_create(
                username=spec.username,
                defaults={
                    'real_name': spec.real_name,
                    'department': spec.department,
                    'title': spec.title,
                    'research_direction': list(spec.research_direction),
                    'bio': spec.bio,
                    'is_staff': spec.is_staff,
                    'is_superuser': False,
                    'is_active': True,
                },
            )
            changed = False
            for field_name, value in (
                ('real_name', spec.real_name),
                ('department', spec.department),
                ('title', spec.title),
                ('research_direction', list(spec.research_direction)),
                ('bio', spec.bio),
                ('is_staff', spec.is_staff),
                ('is_superuser', False),
                ('is_active', True),
            ):
                if getattr(user, field_name) != value:
                    setattr(user, field_name, value)
                    changed = True
            user.set_password(DEMO_PASSWORD)
            changed = True
            user.save()

            summary['users_created' if created else 'users_updated'] += 1
            self.users[spec.username] = user

    def _seed_payload(self, spec: DemoAchievementSpec) -> dict[str, Any]:
        payload = dict(spec.factual_payload)
        payload.update(
            {
                'demo_seed_key': spec.seed_key,
                'seed_source_tag': DEMO_SOURCE_TAG,
                'seed_source_title': spec.source_title,
                'seed_source_urls': list(spec.source_urls),
                'seed_source_note': spec.source_note,
                'seed_date_note': spec.source_date_note,
            }
        )
        return payload

    def _find_existing_record(self, seed_key: str) -> RuleBasedAchievement | None:
        return (
            RuleBasedAchievement.objects.select_related('category', 'rule_item', 'teacher')
            .filter(factual_payload__demo_seed_key=seed_key)
            .first()
        )

    def _reviewed_at(self, spec: DemoAchievementSpec):
        base_dt = datetime.combine(spec.date_acquired, time(hour=10, minute=0))
        aware = timezone.make_aware(base_dt, timezone.get_current_timezone())
        if spec.status == 'PENDING_REVIEW':
            return None
        return aware

    def _submitted_at(self, spec: DemoAchievementSpec):
        base_dt = datetime.combine(spec.date_acquired, time(hour=9, minute=0))
        return timezone.make_aware(base_dt, timezone.get_current_timezone())

    def _upsert_achievement(self, spec: DemoAchievementSpec, summary: dict[str, int]) -> bool:
        rule_item = self.rule_item_map[spec.rule_code]
        teacher = self.users[spec.teacher_username]
        reviewer = self.users[spec.reviewer_username]
        record = self._find_existing_record(spec.seed_key)
        created = record is None

        if record is None:
            record = RuleBasedAchievement(teacher=teacher, version=self.version, category=rule_item.category_ref, rule_item=rule_item)

        record.teacher = teacher
        record.version = self.version
        record.category = rule_item.category_ref
        record.rule_item = rule_item
        record.title = spec.title
        record.external_reference = spec.external_reference
        record.date_acquired = spec.date_acquired
        record.issuing_organization = spec.issuing_organization
        record.publication_name = spec.publication_name
        record.role_text = spec.role_text
        record.author_rank = spec.author_rank
        record.is_corresponding_author = spec.is_corresponding_author
        record.is_representative = spec.is_representative
        record.school_unit_order = spec.school_unit_order
        record.amount_value = spec.amount_value
        record.amount_unit = spec.amount_unit
        record.keywords_text = spec.keywords_text
        record.coauthor_names = list(spec.coauthor_names)
        record.team_identifier = spec.team_identifier
        record.team_total_members = spec.team_total_members
        record.team_allocated_score = spec.team_allocated_score
        record.team_contribution_note = spec.team_contribution_note
        record.evidence_note = spec.evidence_note
        record.factual_payload = self._seed_payload(spec)
        apply_rule_snapshots(record)

        record.status = spec.status
        record.review_comment = spec.review_comment if spec.status == 'REJECTED' else ''
        record.final_score = record.provisional_score if spec.status == 'APPROVED' else Decimal('0')
        record.reviewed_by = reviewer if spec.status in {'APPROVED', 'REJECTED'} else None
        record.reviewed_at = self._reviewed_at(spec)
        record.save()

        submitted_at = self._submitted_at(spec)
        RuleBasedAchievement.objects.filter(pk=record.pk).update(
            created_at=submitted_at,
            updated_at=record.reviewed_at or (submitted_at + timedelta(minutes=1)),
        )

        summary['achievements_created' if created else 'achievements_updated'] += 1
        return created

    def _build_log_payload(self, record: RuleBasedAchievement, spec: DemoAchievementSpec) -> tuple[dict[str, Any], str]:
        payload = {
            '成果名称': record.title,
            '规则分类': record.category_name_snapshot or record.category.name,
            '规则条目': record.rule_title_snapshot or record.rule_item.title,
            '规则编码': record.rule_code_snapshot or record.rule_item.rule_code,
            '成果时间': record.date_acquired.isoformat(),
            '预估积分': str(record.provisional_score),
            '生效积分': str(record.final_score),
            '团队标识': record.team_identifier,
            '演示数据标识': spec.seed_key,
            '来源说明': spec.source_note,
        }
        detail = f"{record.category_name_snapshot or record.category.name} / {record.rule_title_snapshot or record.rule_item.title}"
        return payload, detail

    def _ensure_log(
        self,
        *,
        record: RuleBasedAchievement,
        spec: DemoAchievementSpec,
        action: str,
        operator,
        summary_text: str,
        changed_fields: list[str],
        review_comment: str = '',
        created_at,
        change_details: list[dict[str, Any]] | None = None,
    ) -> None:
        payload, detail = self._build_log_payload(record, spec)
        log = AchievementOperationLog.objects.filter(
            teacher=record.teacher,
            achievement_type='rule-achievements',
            achievement_id=record.id,
            action=action,
            source='system',
        ).order_by('id').first()
        if log is None:
            log = AchievementOperationLog.objects.create(
                teacher=record.teacher,
                operator=operator,
                achievement_type='rule-achievements',
                achievement_id=record.id,
                action=action,
                source='system',
                summary=summary_text,
                changed_fields=changed_fields,
                change_details=change_details or [],
                title_snapshot=record.title,
                detail_snapshot=detail,
                snapshot_payload=payload,
                review_comment=review_comment,
            )
            AchievementOperationLog.objects.filter(pk=log.pk).update(created_at=created_at)
        else:
            AchievementOperationLog.objects.filter(pk=log.pk).update(
                operator=operator,
                summary=summary_text,
                changed_fields=changed_fields,
                change_details=change_details or [],
                title_snapshot=record.title,
                detail_snapshot=detail,
                snapshot_payload=payload,
                review_comment=review_comment,
                created_at=created_at,
            )

    def _ensure_workflow_logs(self, spec: DemoAchievementSpec, *, created: bool, summary: dict[str, int]) -> None:
        record = self._find_existing_record(spec.seed_key)
        if record is None:
            return

        teacher = self.users[spec.teacher_username]
        reviewer = self.users[spec.reviewer_username]
        submitted_at = self._submitted_at(spec)
        review_at = self._reviewed_at(spec)

        existing_count = AchievementOperationLog.objects.filter(
            teacher=record.teacher,
            achievement_type='rule-achievements',
            achievement_id=record.id,
            source='system',
        ).count()

        self._ensure_log(
            record=record,
            spec=spec,
            action='CREATE',
            operator=teacher,
            summary_text=f'演示数据初始化：教师录入成果《{record.title}》',
            changed_fields=['规则分类', '规则条目', '预估积分'],
            created_at=submitted_at,
        )
        self._ensure_log(
            record=record,
            spec=spec,
            action='SUBMIT_REVIEW',
            operator=teacher,
            summary_text=f'演示数据初始化：教师提交成果《{record.title}》进入学院审核',
            changed_fields=['审核状态'],
            created_at=submitted_at + timedelta(minutes=1),
        )
        if spec.status == 'APPROVED' and review_at is not None:
            self._ensure_log(
                record=record,
                spec=spec,
                action='APPROVE',
                operator=reviewer,
                summary_text=f'学院管理员审核通过：{record.title}',
                changed_fields=['审核状态', '生效积分'],
                created_at=review_at,
            )
        elif spec.status == 'REJECTED' and review_at is not None:
            self._ensure_log(
                record=record,
                spec=spec,
                action='REJECT',
                operator=reviewer,
                summary_text=f'学院管理员驳回：{record.title}',
                changed_fields=['审核状态'],
                review_comment=spec.review_comment,
                created_at=review_at,
            )

        final_count = AchievementOperationLog.objects.filter(
            teacher=record.teacher,
            achievement_type='rule-achievements',
            achievement_id=record.id,
            source='system',
        ).count()
        summary['logs_created'] += max(final_count - existing_count, 0)
