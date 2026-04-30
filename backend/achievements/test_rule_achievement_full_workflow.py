from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.test import APITestCase

from evaluation_rules.models import EvaluationRuleCategory, EvaluationRuleItem, EvaluationRuleVersion


class RuleAchievementFullWorkflowClosureTests(APITestCase):
    maxDiff = None

    def setUp(self):
        user_model = get_user_model()
        self.college_admin = user_model.objects.create_user(
            username='610001',
            password='College123456',
            real_name='科研秘书李清源',
            department='生命科学学院',
            is_staff=True,
        )
        self.teacher = user_model.objects.create_user(
            username='610101',
            password='Teacher123456',
            real_name='张晓禾',
            department='生命科学学院',
            title='副教授',
        )
        self.other_teacher = user_model.objects.create_user(
            username='620201',
            password='Teacher123456',
            real_name='陈立群',
            department='化学与化工学院',
            title='讲师',
        )

        self.version = EvaluationRuleVersion.objects.filter(
            status=EvaluationRuleVersion.STATUS_ACTIVE,
        ).order_by('-id').first()
        self.assertIsNotNone(self.version)
        self.categories = {
            item.code: item
            for item in EvaluationRuleCategory.objects.filter(version=self.version, is_active=True)
        }
        self.items = {
            item.rule_code: item
            for item in EvaluationRuleItem.objects.filter(version=self.version, is_active=True).select_related('category_ref')
        }

    def _payload(self, rule_code: str, **payload):
        item = self.items[rule_code]
        return {
            'category': item.category_ref_id,
            'rule_item': item.id,
            **payload,
        }

    def _assert_response(self, response, expected_status):
        self.assertEqual(response.status_code, expected_status, response.data)

    def test_teacher_application_review_scoring_and_viewing_are_closed_for_all_open_categories(self):
        cases = [
            {
                'category_code': 'PROJECT',
                'rule_code': 'PROJECT_NS_11',
                'expected_score': '300.00',
                'payload': self._payload(
                    'PROJECT_NS_11',
                    title='陕西省黄土丘陵区苹果园土壤水分保持关键技术研究',
                    external_reference='陕自然科基〔2025〕面上-214',
                    date_acquired='2025-07-18',
                    issuing_organization='陕西省科学技术厅',
                    role_text='项目负责人',
                    school_unit_order='第一依托单位',
                    factual_payload={
                        'project_status': 'ONGOING',
                        'project_start_date': '2025-09-01',
                        'project_end_date': '2027-08-31',
                        'subject_direction': '旱区生态农业与水土保持',
                        'approved_funding_amount': '42',
                    },
                    evidence_note='立项通知书、项目任务书首页和学院科研秘书审核记录已归档。',
                ),
            },
            {
                'category_code': 'PAPER_BOOK',
                'rule_code': 'PAPER_NS_06',
                'expected_score': '520.00',
                'payload': self._payload(
                    'PAPER_NS_06',
                    title='Graph Neural Networks for Interdisciplinary Research Collaboration Discovery',
                    external_reference='',
                    date_acquired='2025-05-22',
                    publication_name='Information Processing & Management',
                    role_text='第一作者',
                    author_rank=1,
                    is_corresponding_author=False,
                    school_unit_order='第一署名单位',
                    factual_payload={
                        'output_kind': 'JOURNAL_PAPER',
                        'volume': '62',
                        'issue': '4',
                        'pages': '103812',
                        'included_database': 'SCI',
                        'keywords_text': '科研合作, 图神经网络, 学科交叉',
                    },
                    evidence_note='论文首页、检索页和学校第一署名单位截图已上传至学院科研台账。',
                ),
            },
            {
                'category_code': 'AWARD',
                'rule_code': 'AWARD_NS_06',
                'expected_score': '1200.00',
                'payload': self._payload(
                    'AWARD_NS_06',
                    title='黄土高原退化草地生态修复关键技术及应用',
                    external_reference='',
                    date_acquired='2025-11-06',
                    issuing_organization='陕西省人民政府',
                    role_text='第一完成人',
                    author_rank=1,
                    school_unit_order='第一完成单位',
                    factual_payload={
                        'award_name': '陕西省科学技术奖二等奖',
                        'award_form': 'RESEARCH_AWARD',
                    },
                    coauthor_names=['刘明川', '赵榕', '王雅宁'],
                    evidence_note='获奖公报已公示，证书编号待学院统一回填。',
                ),
                'reject_then_resubmit': True,
            },
            {
                'category_code': 'TRANSFORMATION',
                'rule_code': 'TRANS_09',
                'expected_score': '286.00',
                'payload': self._payload(
                    'TRANS_09',
                    title='一种旱区果园水肥协同调控装置许可转让',
                    external_reference='ZL202210345678.9-许可-2025-06',
                    date_acquired='2025-06-28',
                    issuing_organization='国家知识产权局',
                    role_text='第一发明人',
                    author_rank=1,
                    school_unit_order='第一专利权人',
                    amount_value='35.75',
                    factual_payload={
                        'transformation_type': 'LICENSE_TRANSFER',
                        'transformation_mode': 'LICENSE',
                        'transferee_org': '延安新绿农业科技有限公司',
                    },
                    evidence_note='许可合同、到账凭证和专利授权文本已形成一一对应材料。',
                ),
            },
            {
                'category_code': 'THINK_TANK',
                'rule_code': 'THINK_04',
                'expected_score': '400.00',
                'payload': self._payload(
                    'THINK_04',
                    title='陕北苹果产业数字化转型路径与政策建议',
                    external_reference='陕农办采纳〔2025〕34号',
                    date_acquired='2025-09-12',
                    issuing_organization='陕西省农业农村厅',
                    role_text='执笔人',
                    author_rank=1,
                    school_unit_order='第一完成单位',
                    factual_payload={
                        'result_carrier': 'CONSULTING_REPORT',
                        'adoption_type': 'ADOPTED',
                        'leader_level': 'PROVINCIAL_LEADER',
                        'report_submission_unit': '陕西省农业农村厅调研专报',
                    },
                    evidence_note='采纳函、报告首页和报送流转记录已留存。',
                ),
            },
            {
                'category_code': 'PLATFORM_TEAM',
                'rule_code': 'PLATFORM_TEAM_03',
                'expected_score': '180.50',
                'payload': self._payload(
                    'PLATFORM_TEAM_03',
                    title='陕西省旱区生态农业重点实验室',
                    external_reference='陕教科〔2025〕118号',
                    date_acquired='2025-10-20',
                    issuing_organization='陕西省教育厅',
                    role_text='骨干成员',
                    school_unit_order='第一依托单位',
                    team_identifier='陕西省旱区生态农业重点实验室-陕教科〔2025〕118号',
                    team_total_members=9,
                    team_allocated_score='180.50',
                    team_contribution_note='负责苹果园水分保持方向平台建设、开放课题组织和仪器共享管理。',
                    factual_payload={
                        'platform_type': 'RESEARCH_PLATFORM',
                    },
                    evidence_note='平台认定文件、成员贡献分配表和负责人签字页齐备。',
                ),
            },
            {
                'category_code': 'SCI_POP_AWARD',
                'rule_code': 'SCI_POP_AWARD_01',
                'expected_score': '800.00',
                'payload': self._payload(
                    'SCI_POP_AWARD_01',
                    title='黄土高原水土保持科普课程',
                    external_reference='科协普奖〔2025〕A-016',
                    date_acquired='2025-12-05',
                    issuing_organization='中国科学技术协会',
                    role_text='第一完成人',
                    author_rank=1,
                    school_unit_order='第一完成单位',
                    factual_payload={
                        'award_name': '中国科协科普类一等奖',
                        'work_type': 'SCI_POP_ACTIVITY',
                    },
                    coauthor_names=['孙若涵', '郭天宇'],
                    evidence_note='获奖通知、课程平台截图和证书扫描件已整理。',
                ),
            },
        ]

        self.assertEqual({case['category_code'] for case in cases}, set(self.categories.keys()))

        self.client.force_authenticate(self.teacher)
        created_records = {}
        for case in cases:
            preview_response = self.client.post(
                '/api/achievements/rule-achievements/preview-score/',
                case['payload'],
                format='json',
            )
            self._assert_response(preview_response, status.HTTP_200_OK)
            self.assertEqual(preview_response.data['preview_score'], case['expected_score'])

            create_response = self.client.post(
                '/api/achievements/rule-achievements/',
                case['payload'],
                format='json',
            )
            self._assert_response(create_response, status.HTTP_201_CREATED)
            self.assertEqual(create_response.data['status'], 'PENDING_REVIEW')
            self.assertEqual(create_response.data['provisional_score'], case['expected_score'])
            self.assertEqual(create_response.data['final_score'], '0.00')
            self.assertEqual(create_response.data['category_code'], case['category_code'])
            created_records[case['category_code']] = {
                'id': create_response.data['id'],
                'expected_score': case['expected_score'],
                'payload': case['payload'],
            }

            detail_response = self.client.get(f"/api/achievements/rule-achievements/{create_response.data['id']}/")
            self._assert_response(detail_response, status.HTTP_200_OK)
            self.assertEqual(detail_response.data['title'], case['payload']['title'])
            self.assertEqual(detail_response.data['same_achievement_basis'], 'composite' if not case['payload'].get('external_reference') else detail_response.data['same_achievement_basis'])

        list_response = self.client.get('/api/achievements/rule-achievements/')
        self._assert_response(list_response, status.HTTP_200_OK)
        self.assertEqual(len(list_response.data), 7)
        self.assertEqual({item['status'] for item in list_response.data}, {'PENDING_REVIEW'})

        self.client.force_authenticate(self.other_teacher)
        forbidden_detail = self.client.get(
            f"/api/achievements/rule-achievements/{created_records['PROJECT']['id']}/",
        )
        self.assertEqual(forbidden_detail.status_code, status.HTTP_404_NOT_FOUND)

        self.client.force_authenticate(self.college_admin)
        pending_response = self.client.get('/api/achievements/rule-achievements/pending-review/')
        self._assert_response(pending_response, status.HTTP_200_OK)
        self.assertEqual({item['id'] for item in pending_response.data}, {record['id'] for record in created_records.values()})

        admin_patch_response = self.client.patch(
            f"/api/achievements/rule-achievements/{created_records['PROJECT']['id']}/",
            {'evidence_note': '管理员侧仅允许审核，不代替教师修改申报材料。'},
            format='json',
        )
        self.assertEqual(admin_patch_response.status_code, status.HTTP_403_FORBIDDEN)

        award_id = created_records['AWARD']['id']
        reject_response = self.client.post(
            f'/api/achievements/rule-achievements/{award_id}/reject/',
            {'reason': '请补充陕西省人民政府科技奖励公报截图，并在佐证说明中标注证书编号来源。'},
            format='json',
        )
        self._assert_response(reject_response, status.HTTP_200_OK)
        self.assertEqual(reject_response.data['status'], 'REJECTED')
        self.assertEqual(reject_response.data['final_score'], '0.00')

        self.client.force_authenticate(self.teacher)
        rejected_list = self.client.get('/api/achievements/rule-achievements/', {'status': 'REJECTED'})
        self._assert_response(rejected_list, status.HTTP_200_OK)
        self.assertEqual([item['id'] for item in rejected_list.data], [award_id])
        self.assertIn('科技奖励公报', rejected_list.data[0]['review_comment'])

        resubmit_response = self.client.patch(
            f'/api/achievements/rule-achievements/{award_id}/',
            {
                'external_reference': '陕政奖证〔2025〕2-083',
                'evidence_note': '已补充陕西省人民政府科技奖励公报截图、证书扫描件和学院审核页。',
            },
            format='json',
        )
        self._assert_response(resubmit_response, status.HTTP_200_OK)
        self.assertEqual(resubmit_response.data['status'], 'PENDING_REVIEW')
        self.assertEqual(resubmit_response.data['provisional_score'], created_records['AWARD']['expected_score'])

        self.client.force_authenticate(self.college_admin)
        for category_code, record in created_records.items():
            latest_detail = self.client.get(f"/api/achievements/rule-achievements/{record['id']}/")
            self._assert_response(latest_detail, status.HTTP_200_OK)
            approve_response = self.client.post(
                f"/api/achievements/rule-achievements/{record['id']}/approve/",
                {'final_score': latest_detail.data['provisional_score']},
                format='json',
            )
            self._assert_response(approve_response, status.HTTP_200_OK)
            self.assertEqual(approve_response.data['status'], 'APPROVED')
            self.assertEqual(approve_response.data['final_score'], record['expected_score'])
            self.assertEqual(approve_response.data['provisional_score'], record['expected_score'])

        self.client.force_authenticate(self.teacher)
        approved_list = self.client.get('/api/achievements/rule-achievements/', {'status': 'APPROVED'})
        self._assert_response(approved_list, status.HTTP_200_OK)
        self.assertEqual(len(approved_list.data), 7)
        self.assertEqual(
            sum(float(item['final_score']) for item in approved_list.data),
            3686.5,
        )

        award_logs = self.client.get(f'/api/achievements/rule-achievements/{award_id}/workflow-logs/')
        self._assert_response(award_logs, status.HTTP_200_OK)
        logged_actions = [item['action'] for item in award_logs.data['history']]
        for expected_action in ['CREATE', 'SUBMIT_REVIEW', 'REJECT', 'UPDATE', 'APPROVE']:
            self.assertIn(expected_action, logged_actions)

        dashboard_response = self.client.get('/api/achievements/dashboard-stats/')
        self._assert_response(dashboard_response, status.HTTP_200_OK)
        self.assertEqual(dashboard_response.data['achievement_overview']['total_achievements'], 7)
        self.assertEqual(dashboard_response.data['achievement_overview']['project_count'], 1)
        self.assertEqual(dashboard_response.data['achievement_overview']['total_score'], 3686.5)
        self.assertEqual(dashboard_response.data['calculation_summary']['total_score'], 3686.5)
        self.assertEqual(dashboard_response.data['calculation_summary']['weight_mode'], 'direct_rule_score_sum')
