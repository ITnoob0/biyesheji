from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand

from achievements.models import (
    AcademicService,
    CoAuthor,
    IntellectualProperty,
    Paper,
    PaperKeyword,
    Project,
    ResearchKeyword,
    TeacherProfile,
    TeachingAchievement,
)
from project_guides.models import ProjectGuide
from users.serializers import DEFAULT_TEACHER_PASSWORD, sync_teacher_profile
from users.services import set_user_password


class Command(BaseCommand):
    help = 'Initialize demo teacher accounts, profiles, and achievement data.'

    DEMO_ADMIN_ID = 1
    DEMO_ADMIN_USERNAME = 'admin'
    DEMO_ADMIN_PASSWORD = 'Admin123456'
    DEMO_GUIDE_SOURCE_PREFIX = 'https://demo.local/guides/'
    DEMO_TEACHER_IDS = (100001, 100002, 100003, 100004)

    def add_arguments(self, parser):
        parser.add_argument(
            '--reset-demo-data',
            action='store_true',
            help='删除并重建内置演示教师数据与演示项目指南，恢复到标准可演示状态。',
        )
        parser.add_argument(
            '--reset-passwords',
            action='store_true',
            help='显式将内置演示账号密码重置为标准演示密码；默认保留数据库中已有密码。',
        )
        parser.add_argument(
            '--print-accounts',
            action='store_true',
            help='初始化完成后打印演示账号清单与默认密码说明。',
        )

    def handle(self, *args, **options):
        user_model = get_user_model()
        reset_demo_data = bool(options.get('reset_demo_data'))
        reset_passwords = bool(options.get('reset_passwords'))
        print_accounts = bool(options.get('print_accounts'))

        if reset_demo_data:
            reset_summary = self._reset_demo_state(user_model)
            self.stdout.write(
                self.style.WARNING(
                    '已重置内置演示数据：'
                    f"删除教师账号 {reset_summary['teacher_count']} 个，"
                    f"删除演示指南 {reset_summary['guide_count']} 条。"
                )
            )

        account_password_states: dict[str, str] = {}
        admin_user = self._bootstrap_admin(user_model, reset_passwords, account_password_states)

        teachers = [
            {
                'id': 100001,
                'username': '100001',
                'real_name': '张晨阳',
                'department': '计算机学院',
                'title': '副教授',
                'discipline': '人工智能',
                'research_interests': '大语言模型、知识图谱、教育智能',
                'h_index': 12,
                'bio': '长期从事高校教师科研画像与智能辅助系统相关研究。',
                'research_direction': ['大语言模型', '知识图谱', '教育智能'],
                'papers': [
                    {
                        'title': '高校教师科研画像构建方法研究',
                        'date_acquired': '2025-06-18',
                        'paper_type': 'JOURNAL',
                        'journal_name': '计算机工程与应用',
                        'journal_level': 'CCF-C',
                        'citation_count': 28,
                        'doi': '10.2026/demo-teacher1-01',
                        'abstract': '本文围绕高校教师科研画像构建流程、指标体系与智能服务场景展开研究。',
                        'coauthors': ['刘佳宁', '王晨'],
                        'keywords': ['科研画像', '知识图谱', '教师评价'],
                    },
                    {
                        'title': '面向高校科研管理的大模型辅助决策机制',
                        'date_acquired': '2024-11-06',
                        'paper_type': 'CONFERENCE',
                        'journal_name': '全国教育信息化大会',
                        'journal_level': '会议论文',
                        'citation_count': 11,
                        'doi': '10.2026/demo-teacher1-02',
                        'abstract': '针对高校科研管理场景，提出一种基于大语言模型的智能辅助决策框架。',
                        'coauthors': ['马文博'],
                        'keywords': ['大语言模型', '科研管理', '智能决策'],
                    },
                ],
                'project': {
                    'title': '高校科研画像平台关键技术研究',
                    'date_acquired': '2025-01-10',
                    'level': 'PROVINCIAL',
                    'role': 'PI',
                    'funding_amount': '18.00',
                    'status': 'ONGOING',
                },
                'service': {
                    'title': '教育数据智能分析专委会委员',
                    'date_acquired': '2024-04-12',
                    'service_type': 'COMMITTEE',
                    'organization': '中国教育技术协会',
                },
            },
            {
                'id': 100002,
                'username': '100002',
                'real_name': '李雨桐',
                'department': '信息工程学院',
                'title': '讲师',
                'discipline': '数据科学',
                'research_interests': '学术社交网络、数据挖掘、可视化分析',
                'h_index': 8,
                'bio': '聚焦学术网络分析与可视化技术在高校科研中的应用。',
                'research_direction': ['数据挖掘', '可视化分析', '学术社交网络'],
                'papers': [
                    {
                        'title': '高校教师学术社交拓扑图可视化分析方法',
                        'date_acquired': '2025-03-21',
                        'paper_type': 'JOURNAL',
                        'journal_name': '现代教育技术',
                        'journal_level': '核心期刊',
                        'citation_count': 17,
                        'doi': '10.2026/demo-teacher2-01',
                        'abstract': '本文针对高校教师合作网络的可视化表达需求，提出一种多层关系拓扑构建方法。',
                        'coauthors': ['孙浩', '赵倩'],
                        'keywords': ['学术社交网络', '可视化分析', '合作网络'],
                    },
                ],
                'ip': {
                    'title': '教师科研画像数据分析平台',
                    'date_acquired': '2025-02-28',
                    'ip_type': 'SOFTWARE_COPYRIGHT',
                    'registration_number': '2025SR1234567',
                    'is_transformed': False,
                },
                'teaching': {
                    'title': '数据可视化课程教学改革实践',
                    'date_acquired': '2024-09-01',
                    'achievement_type': 'TEACHING_REFORM',
                    'level': '校级',
                },
            },
            {
                'id': 100003,
                'username': '100003',
                'real_name': '王浩然',
                'department': '人工智能学院',
                'title': '教授',
                'discipline': '智能计算',
                'research_interests': '跨模态智能、情感计算、数字人',
                'h_index': 21,
                'bio': '致力于跨模态大模型与情感数字人方向研究。',
                'research_direction': ['跨模态智能', '情感计算', '数字人'],
                'papers': [
                    {
                        'title': '跨模态数字人情感生成模型研究',
                        'date_acquired': '2024-12-15',
                        'paper_type': 'JOURNAL',
                        'journal_name': '软件学报',
                        'journal_level': 'CCF-B',
                        'citation_count': 46,
                        'doi': '10.2026/demo-teacher3-01',
                        'abstract': '本文提出一种结合语义先验与表情驱动的跨模态数字人情感生成模型。',
                        'coauthors': ['周文静', '陈思远'],
                        'keywords': ['跨模态智能', '数字人', '情感计算'],
                    },
                ],
                'project': {
                    'title': '面向数字人的跨模态情感计算研究',
                    'date_acquired': '2024-06-08',
                    'level': 'NATIONAL',
                    'role': 'PI',
                    'funding_amount': '56.00',
                    'status': 'ONGOING',
                },
                'service': {
                    'title': '国际智能媒体会议特邀报告',
                    'date_acquired': '2025-05-16',
                    'service_type': 'INVITED_TALK',
                    'organization': 'International Conference on Intelligent Media',
                },
            },
            {
                'id': 100004,
                'username': '100004',
                'real_name': '汪心蓝',
                'department': '教育技术学院',
                'title': '副教授',
                'discipline': '教育数据智能',
                'research_interests': '学习分析、教育知识图谱、科研画像评估',
                'h_index': 10,
                'bio': '长期从事教育数据智能与教师科研画像方向研究，关注成果治理、画像建模与智能辅助服务。',
                'research_direction': ['学习分析', '教育知识图谱', '科研画像'],
                'papers': [
                    {
                        'title': '面向高校教师发展的科研画像建模与应用研究',
                        'date_acquired': '2025-04-18',
                        'paper_type': 'JOURNAL',
                        'journal_name': '开放教育研究',
                        'journal_level': 'CSSCI',
                        'citation_count': 14,
                        'doi': '10.2026/demo-teacher4-01',
                        'abstract': '本文围绕高校教师科研画像的指标体系构建、数据整合方法与典型应用场景展开研究，验证画像驱动的科研服务可提升成果治理效率。',
                        'coauthors': ['赵明悦', '陈思源'],
                        'keywords': ['科研画像', '教育知识图谱', '教师发展'],
                    },
                    {
                        'title': '基于学习分析的教师成果成长轨迹可视化方法',
                        'date_acquired': '2024-10-09',
                        'paper_type': 'CONFERENCE',
                        'journal_name': '全国教育人工智能大会',
                        'journal_level': '会议论文',
                        'citation_count': 7,
                        'doi': '10.2026/demo-teacher4-02',
                        'abstract': '针对教师成果演化过程难以持续追踪的问题，提出一种结合学习分析与知识图谱的成长轨迹可视化方法，用于辅助教师科研规划。',
                        'coauthors': ['林若溪'],
                        'keywords': ['学习分析', '成果演化', '可视化'],
                    },
                ],
                'project': {
                    'title': '教师科研画像与智能辅助服务关键技术研究',
                    'date_acquired': '2025-02-20',
                    'level': 'PROVINCIAL',
                    'role': 'PI',
                    'funding_amount': '22.50',
                    'status': 'ONGOING',
                },
                'ip': {
                    'title': '教师科研成果画像分析系统',
                    'date_acquired': '2025-01-15',
                    'ip_type': 'SOFTWARE_COPYRIGHT',
                    'registration_number': '2025SR2004004',
                    'is_transformed': True,
                },
                'teaching': {
                    'title': '教育数据智能课程群建设与教学改革实践',
                    'date_acquired': '2024-12-10',
                    'achievement_type': 'COURSE',
                    'level': '省级',
                },
                'service': {
                    'title': '智慧教育论坛期刊审稿服务',
                    'date_acquired': '2025-03-12',
                    'service_type': 'REVIEWER',
                    'organization': '中国教育技术协会',
                },
            },
        ]

        created_teachers = []
        for teacher_data in teachers:
            user = self._create_or_update_teacher(user_model, teacher_data, reset_passwords, account_password_states)
            self._sync_papers(user, teacher_data['papers'])
            if 'project' in teacher_data:
                self._sync_project(user, teacher_data['project'])
            if 'ip' in teacher_data:
                self._sync_ip(user, teacher_data['ip'])
            if 'teaching' in teacher_data:
                self._sync_teaching(user, teacher_data['teaching'])
            if 'service' in teacher_data:
                self._sync_service(user, teacher_data['service'])
            created_teachers.append(user)

        self._sync_demo_guides(admin_user)

        self.stdout.write(self.style.SUCCESS('Demo teacher accounts and base data initialized successfully.'))
        if print_accounts:
            self._print_account_summary(admin_user, created_teachers, account_password_states, reset_passwords)

    def _bootstrap_admin(self, user_model, reset_passwords: bool, account_password_states: dict[str, str]):
        admin_user, created = user_model.objects.get_or_create(
            id=self.DEMO_ADMIN_ID,
            defaults={
                'username': self.DEMO_ADMIN_USERNAME,
                'real_name': '系统管理员',
                'department': '科研管理中心',
                'title': '管理员',
                'is_staff': True,
                'is_superuser': True,
                'is_active': True,
            },
        )
        admin_user.real_name = admin_user.real_name or '系统管理员'
        admin_user.department = admin_user.department or '科研管理中心'
        admin_user.title = admin_user.title or '管理员'
        admin_user.is_staff = True
        admin_user.is_superuser = True
        admin_user.is_active = True
        admin_user.save()
        if created or reset_passwords or not admin_user.has_usable_password():
            set_user_password(admin_user, self.DEMO_ADMIN_PASSWORD, require_password_change=False)
            account_password_states[admin_user.username] = self.DEMO_ADMIN_PASSWORD
        else:
            account_password_states[admin_user.username] = '__preserved__'
        sync_teacher_profile(
            admin_user,
            {
                'department': admin_user.department,
                'title': admin_user.title,
                'discipline': '科研治理',
                'research_interests': '演示治理, 系统维护',
                'h_index': 0,
            },
        )
        return admin_user

    def _create_or_update_teacher(self, user_model, data, reset_passwords: bool, account_password_states: dict[str, str]):
        login_account = str(data['id'])
        user, created = user_model.objects.get_or_create(
            id=data['id'],
            defaults={
                'username': login_account,
                'real_name': data['real_name'],
                'department': data['department'],
                'title': data['title'],
                'bio': data['bio'],
                'research_direction': data['research_direction'],
                'is_active': True,
            },
        )

        user.username = login_account
        user.real_name = data['real_name']
        user.department = data['department']
        user.title = data['title']
        user.bio = data['bio']
        user.research_direction = data['research_direction']
        user.is_active = True
        user.save()
        if created or reset_passwords or not user.has_usable_password():
            set_user_password(user, DEFAULT_TEACHER_PASSWORD, require_password_change=True)
            account_password_states[user.username] = DEFAULT_TEACHER_PASSWORD
        else:
            account_password_states[user.username] = '__preserved__'

        sync_teacher_profile(
            user,
            {
                'department': data['department'],
                'title': data['title'],
                'discipline': data['discipline'],
                'research_interests': data['research_interests'],
                'h_index': data['h_index'],
            },
        )

        TeacherProfile.objects.filter(user=user).update(
            department=data['department'],
            title=data['title'],
            discipline=data['discipline'],
            research_interests=data['research_interests'],
            h_index=data['h_index'],
        )
        return user

    def _sync_papers(self, user, papers):
        for paper_data in papers:
            paper, _ = Paper.objects.update_or_create(
                teacher=user,
                doi=paper_data['doi'],
                defaults={
                    'title': paper_data['title'],
                    'date_acquired': paper_data['date_acquired'],
                    'paper_type': paper_data['paper_type'],
                    'journal_name': paper_data['journal_name'],
                    'journal_level': paper_data['journal_level'],
                    'citation_count': paper_data['citation_count'],
                    'abstract': paper_data['abstract'],
                    'is_first_author': True,
                },
            )
            paper.coauthors.all().delete()
            PaperKeyword.objects.filter(paper=paper).delete()

            for name in paper_data['coauthors']:
                CoAuthor.objects.create(paper=paper, name=name)

            for keyword_name in paper_data['keywords']:
                keyword, _ = ResearchKeyword.objects.get_or_create(name=keyword_name)
                PaperKeyword.objects.get_or_create(paper=paper, keyword=keyword)

    def _sync_project(self, user, project_data):
        Project.objects.update_or_create(
            teacher=user,
            title=project_data['title'],
            defaults=project_data,
        )

    def _sync_ip(self, user, ip_data):
        IntellectualProperty.objects.update_or_create(
            teacher=user,
            registration_number=ip_data['registration_number'],
            defaults=ip_data,
        )

    def _sync_teaching(self, user, teaching_data):
        TeachingAchievement.objects.update_or_create(
            teacher=user,
            title=teaching_data['title'],
            defaults=teaching_data,
        )

    def _sync_service(self, user, service_data):
        AcademicService.objects.update_or_create(
            teacher=user,
            title=service_data['title'],
            defaults=service_data,
        )

    def _sync_demo_guides(self, admin_user):
        guides = [
            {
                'title': '高校教师科研画像与智能评价专项指南',
                'issuing_agency': '省教育厅',
                'guide_level': 'PROVINCIAL',
                'status': 'OPEN',
                'rule_profile': 'KEYWORD_FIRST',
                'application_deadline': '2026-06-30',
                'summary': '面向教师科研画像、教育知识图谱与智能评价方向组织申报，是推荐与问答演示的核心指南数据。',
                'target_keywords': ['科研画像', '知识图谱', '教师评价'],
                'target_disciplines': ['人工智能', '教育数据智能', '教育技术学院'],
                'recommendation_tags': ['画像重点', '省部级', '演示推荐'],
                'support_amount': '20-30 万元',
                'eligibility_notes': '申报人需具备近三年相关成果基础。',
                'source_url': f'{self.DEMO_GUIDE_SOURCE_PREFIX}portrait-evaluation',
            },
            {
                'title': '教育数据智能与学习分析项目指南',
                'issuing_agency': '省科技厅',
                'guide_level': 'PROVINCIAL',
                'status': 'OPEN',
                'rule_profile': 'DISCIPLINE_FIRST',
                'application_deadline': '2026-07-15',
                'summary': '面向教育数据智能、学习分析和科研服务平台方向，用于演示推荐筛选、排序和说明能力。',
                'target_keywords': ['教育数据智能', '学习分析', '可视化分析'],
                'target_disciplines': ['数据科学', '教育数据智能', '信息工程学院'],
                'recommendation_tags': ['学科贴合', '演示推荐'],
                'support_amount': '15-25 万元',
                'eligibility_notes': '需具备教育数据或学习分析相关研究积累。',
                'source_url': f'{self.DEMO_GUIDE_SOURCE_PREFIX}edu-data-analytics',
            },
            {
                'title': '跨模态数字人与智能交互合作指南',
                'issuing_agency': '某重点实验室',
                'guide_level': 'ENTERPRISE',
                'status': 'OPEN',
                'rule_profile': 'ACTIVITY_FIRST',
                'application_deadline': '2026-08-01',
                'summary': '面向数字人、跨模态智能和智能交互合作，用于展示不同教师画像下的推荐差异。',
                'target_keywords': ['跨模态智能', '数字人', '情感计算'],
                'target_disciplines': ['智能计算', '人工智能学院'],
                'recommendation_tags': ['企业合作', '对比演示'],
                'support_amount': '联合研发',
                'eligibility_notes': '鼓励具有跨模态成果积累的教师团队申报。',
                'source_url': f'{self.DEMO_GUIDE_SOURCE_PREFIX}multimodal-agent',
            },
            {
                'title': '科研治理平台建设预研指南',
                'issuing_agency': '校科研处',
                'guide_level': 'MUNICIPAL',
                'status': 'DRAFT',
                'rule_profile': 'BALANCED',
                'application_deadline': '2026-09-01',
                'summary': '保留一条草稿状态指南，用于管理员项目指南管理页面演示。',
                'target_keywords': ['科研治理', '平台建设'],
                'target_disciplines': ['科研治理'],
                'recommendation_tags': ['管理员演示'],
                'support_amount': '待定',
                'eligibility_notes': '当前为演示草稿数据，不面向教师开放。',
                'source_url': f'{self.DEMO_GUIDE_SOURCE_PREFIX}governance-draft',
            },
        ]

        for guide_data in guides:
            defaults = {**guide_data, 'created_by': admin_user}
            ProjectGuide.objects.update_or_create(
                source_url=guide_data['source_url'],
                defaults=defaults,
            )

    def _reset_demo_state(self, user_model):
        demo_users = user_model.objects.filter(id__in=self.DEMO_TEACHER_IDS)
        teacher_count = demo_users.count()
        demo_users.delete()

        demo_guides = ProjectGuide.objects.filter(source_url__startswith=self.DEMO_GUIDE_SOURCE_PREFIX)
        guide_count = demo_guides.count()
        demo_guides.delete()

        return {
            'teacher_count': teacher_count,
            'guide_count': guide_count,
        }

    def _print_account_summary(self, admin_user, teachers, account_password_states, reset_passwords: bool):
        self.stdout.write('')
        self.stdout.write(self.style.HTTP_INFO('演示账号清单'))
        admin_password_state = account_password_states.get(admin_user.username)
        if admin_password_state and admin_password_state != '__preserved__':
            self.stdout.write(f"- 管理员账号：{admin_user.username} / {admin_password_state}")
        else:
            self.stdout.write(
                f"- 管理员账号：{admin_user.username} / 已保留现有密码（数据库中为加密存储，无法直接回显明文）"
            )
        if reset_passwords:
            self.stdout.write(
                f"- 教师默认密码：{DEFAULT_TEACHER_PASSWORD}（本次已显式重置为标准演示密码，初始化后为临时密码）"
            )
        else:
            self.stdout.write(
                f"- 教师账号密码：默认保留数据库中已有密码；仅新建账号会使用 {DEFAULT_TEACHER_PASSWORD}"
            )
        for teacher in teachers:
            password_state = account_password_states.get(teacher.username)
            if password_state and password_state != '__preserved__':
                self.stdout.write(f"- 教师账号：{teacher.username} / {password_state} / {teacher.real_name}")
            else:
                self.stdout.write(
                    f"- 教师账号：{teacher.username} / 已保留现有密码（数据库中为加密存储，无法直接回显明文） / {teacher.real_name}"
                )
        self.stdout.write(
            '- 说明：以上仅为内置演示账号，不应与真实业务环境中的正式账号和真实业务数据混用。'
        )
