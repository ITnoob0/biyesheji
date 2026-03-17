from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand

from project_guides.models import ProjectGuide


class Command(BaseCommand):
    help = 'Initialize demo project guide data for recommendation and management pages.'

    def handle(self, *args, **options):
        user_model = get_user_model()
        admin_user = user_model.objects.filter(id=1).first()

        demo_guides = [
            {
                'title': '教育数字化转型重点项目申报指南',
                'issuing_agency': '省教育厅',
                'guide_level': 'PROVINCIAL',
                'status': 'OPEN',
                'application_deadline': '2026-06-30',
                'summary': '围绕教育数字化、教师画像、学习分析与智能评价等方向组织重点项目申报。',
                'target_keywords': ['教师画像', '学习分析', '教育数据智能', '智能评价'],
                'target_disciplines': ['教育数据智能', '教育技术学院'],
                'support_amount': '20-30 万元',
                'eligibility_notes': '申报人需具备近三年相关论文或项目基础，鼓励跨学科团队联合申报。',
                'source_url': 'https://example.com/guides/education-digital',
            },
            {
                'title': '高校科研治理与智能辅助专项指南',
                'issuing_agency': '教育部科研司',
                'guide_level': 'NATIONAL',
                'status': 'OPEN',
                'application_deadline': '2026-07-15',
                'summary': '支持面向高校科研管理、成果画像建模、智能辅助决策和知识组织的关键技术研究。',
                'target_keywords': ['科研画像', '智能推荐', '科研管理', '知识图谱'],
                'target_disciplines': ['人工智能', '教育数据智能', '计算机学院'],
                'support_amount': '50-80 万元',
                'eligibility_notes': '需有稳定研究团队和前期成果积累，优先支持已有平台基础的高校。',
                'source_url': 'https://example.com/guides/research-governance',
            },
            {
                'title': '教育知识图谱与学习平台创新应用指南',
                'issuing_agency': '国家教育数字化推进办公室',
                'guide_level': 'NATIONAL',
                'status': 'OPEN',
                'application_deadline': '2026-08-05',
                'summary': '聚焦教育知识图谱、学习平台智能服务、课程知识组织与个性化推荐应用。',
                'target_keywords': ['教育知识图谱', '学习分析', '个性化推荐', '课程建设'],
                'target_disciplines': ['教育数据智能', '教育技术学院'],
                'support_amount': '40-60 万元',
                'eligibility_notes': '鼓励依托课程群、学习平台或资源库开展示范应用研究。',
                'source_url': 'https://example.com/guides/knowledge-graph-learning',
            },
            {
                'title': '大模型驱动的高校科研服务技术指南',
                'issuing_agency': '科技部高技术研究中心',
                'guide_level': 'NATIONAL',
                'status': 'OPEN',
                'application_deadline': '2026-07-28',
                'summary': '支持面向科研服务、知识图谱构建、大模型辅助决策和学术资源治理的技术攻关。',
                'target_keywords': ['大语言模型', '知识图谱', '智能决策', '科研服务'],
                'target_disciplines': ['人工智能', '计算机学院', '智能计算'],
                'support_amount': '80-120 万元',
                'eligibility_notes': '建议具备算法、系统和典型场景验证能力，支持高校与企业联合申报。',
                'source_url': 'https://example.com/guides/llm-research-service',
            },
            {
                'title': '学术社交网络分析与科研可视化指南',
                'issuing_agency': '省科技厅',
                'guide_level': 'PROVINCIAL',
                'status': 'OPEN',
                'application_deadline': '2026-06-18',
                'summary': '面向学术合作网络、科研关系图谱、成果传播和可视化分析开展技术研究与平台建设。',
                'target_keywords': ['学术社交网络', '可视化分析', '合作网络', '成果传播'],
                'target_disciplines': ['数据科学', '信息工程学院'],
                'support_amount': '15-25 万元',
                'eligibility_notes': '鼓励与科研管理部门、图情单位或数据平台协同开展应用研究。',
                'source_url': 'https://example.com/guides/academic-network-visualization',
            },
            {
                'title': '跨模态智能与数字人应用指南',
                'issuing_agency': '国家自然科学基金合作专项',
                'guide_level': 'NATIONAL',
                'status': 'OPEN',
                'application_deadline': '2026-08-20',
                'summary': '支持跨模态智能、数字人、情感计算与智能媒体交互相关基础与应用研究。',
                'target_keywords': ['跨模态智能', '数字人', '情感计算', '智能媒体'],
                'target_disciplines': ['智能计算', '人工智能学院'],
                'support_amount': '60-100 万元',
                'eligibility_notes': '需具备扎实研究基础，优先支持已发表高水平成果的团队。',
                'source_url': 'https://example.com/guides/multimodal-digital-human',
            },
            {
                'title': '企业联合科研场景智能化升级合作指南',
                'issuing_agency': '某头部教育科技企业',
                'guide_level': 'ENTERPRISE',
                'status': 'OPEN',
                'application_deadline': '2026-05-30',
                'summary': '聚焦教育平台、教师发展服务、课程推荐与科研成果运营场景的校企联合创新。',
                'target_keywords': ['教师发展', '智能推荐', '教育平台', '成果运营'],
                'target_disciplines': ['教育技术学院', '计算机学院', '信息工程学院'],
                'support_amount': '企业联合经费 30 万元起',
                'eligibility_notes': '建议具备可落地的产品场景与演示平台，支持校企共建联合实验室。',
                'source_url': 'https://example.com/guides/enterprise-collaboration',
            },
            {
                'title': '已截止示范指南（用于状态演示）',
                'issuing_agency': '市科技局',
                'guide_level': 'MUNICIPAL',
                'status': 'CLOSED',
                'application_deadline': '2026-03-01',
                'summary': '该条数据主要用于演示指南状态管理和教师侧开放指南过滤能力。',
                'target_keywords': ['示范数据'],
                'target_disciplines': ['教育数据智能'],
                'support_amount': '10 万元',
                'eligibility_notes': '仅作演示，不参与当前推荐展示。',
                'source_url': 'https://example.com/guides/demo-closed',
            },
        ]

        created_count = 0
        updated_count = 0

        for guide_data in demo_guides:
            _, created = ProjectGuide.objects.update_or_create(
                title=guide_data['title'],
                issuing_agency=guide_data['issuing_agency'],
                defaults={
                    **guide_data,
                    'created_by': admin_user,
                },
            )
            if created:
                created_count += 1
            else:
                updated_count += 1

        total_count = ProjectGuide.objects.count()
        self.stdout.write(
            self.style.SUCCESS(
                f'Demo project guides initialized successfully. created={created_count}, updated={updated_count}, total={total_count}'
            )
        )
