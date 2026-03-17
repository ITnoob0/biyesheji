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
from users.serializers import DEFAULT_TEACHER_PASSWORD, sync_teacher_profile


class Command(BaseCommand):
    help = 'Initialize demo teacher accounts, profiles, and achievement data.'

    def handle(self, *args, **options):
        user_model = get_user_model()

        self._bootstrap_admin(user_model)

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

        for teacher_data in teachers:
            user = self._create_or_update_teacher(user_model, teacher_data)
            self._sync_papers(user, teacher_data['papers'])
            if 'project' in teacher_data:
                self._sync_project(user, teacher_data['project'])
            if 'ip' in teacher_data:
                self._sync_ip(user, teacher_data['ip'])
            if 'teaching' in teacher_data:
                self._sync_teaching(user, teacher_data['teaching'])
            if 'service' in teacher_data:
                self._sync_service(user, teacher_data['service'])

        self.stdout.write(self.style.SUCCESS('Demo teacher accounts and base data initialized successfully.'))

    def _bootstrap_admin(self, user_model):
        admin_user, _ = user_model.objects.get_or_create(
            id=1,
            defaults={
                'username': 'admin',
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
        admin_user.set_password('Admin123456')
        admin_user.save()

    def _create_or_update_teacher(self, user_model, data):
        login_account = str(data['id'])
        user, _ = user_model.objects.get_or_create(
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
        user.set_password(DEFAULT_TEACHER_PASSWORD)
        user.save()

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
