from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from achievements.models import TeacherProfile

from .serializers import DEFAULT_TEACHER_PASSWORD


class TeacherUserApiTests(APITestCase):
    def setUp(self):
        user_model = get_user_model()
        self.admin = user_model.objects.create_superuser(
            username='admin',
            password='Admin123456',
            real_name='系统管理员',
        )
        self.client.force_authenticate(user=self.admin)

    def test_teacher_registration_uses_employee_id_as_login_account(self):
        payload = {
            'employee_id': '100001',
            'real_name': '张晨阳',
            'department': '计算机学院',
            'title': '副教授',
            'discipline': '人工智能',
            'research_interests': '大语言模型, 知识图谱',
            'bio': '测试注册教师',
            'research_direction': ['大语言模型', '知识图谱'],
            'h_index': 0,
            'password': 'SecurePass789!Q',
            'confirm_password': 'SecurePass789!Q',
        }

        response = self.client.post(reverse('teacher_list_create'), payload, format='json')

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['employee_id'], 100001)
        self.assertEqual(response.data['username'], '100001')
        self.assertEqual(response.data['initial_password'], 'SecurePass789!Q')
        self.assertTrue(TeacherProfile.objects.filter(user_id=100001, discipline='人工智能').exists())

    def test_current_user_profile_can_be_updated(self):
        TeacherProfile.objects.create(
            user=self.admin,
            department='科研管理中心',
            discipline='科研管理',
            title='管理员',
            research_interests='平台建设',
            h_index=0,
        )

        response = self.client.patch(
            reverse('current_user'),
            {
                'real_name': '管理员甲',
                'department': '科研管理中心',
                'title': '平台主管',
                'discipline': '科研信息化',
                'research_interests': '科研画像, 科研治理',
                'bio': '负责系统维护与数据治理',
                'h_index': 2,
                'research_direction': ['科研画像', '科研治理'],
            },
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.admin.refresh_from_db()
        self.assertEqual(self.admin.real_name, '管理员甲')
        self.assertEqual(self.admin.profile.discipline, '科研信息化')
        self.assertEqual(self.admin.profile.h_index, 2)

    def test_teacher_password_can_be_reset_by_admin(self):
        user_model = get_user_model()
        teacher = user_model.objects.create_user(
            id=100002,
            username='100002',
            password='old-password',
            real_name='李雨桐',
            department='信息工程学院',
            title='讲师',
        )

        response = self.client.post(reverse('teacher_reset_password', kwargs={'user_id': teacher.id}))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        teacher.refresh_from_db()
        self.assertTrue(teacher.check_password(DEFAULT_TEACHER_PASSWORD))

    def test_non_admin_cannot_view_other_teacher_detail(self):
        user_model = get_user_model()
        teacher_a = user_model.objects.create_user(
            id=100010,
            username='100010',
            password='teacher123456',
            real_name='鏁欏笀鐢?',
            department='淇℃伅宸ョ▼瀛﹂櫌',
            title='璁插笀',
        )
        teacher_b = user_model.objects.create_user(
            id=100011,
            username='100011',
            password='teacher123456',
            real_name='鏁欏笀涔?',
            department='淇℃伅宸ョ▼瀛﹂櫌',
            title='鍓暀鎺?',
        )

        self.client.force_authenticate(user=teacher_a)
        response = self.client.get(reverse('teacher_detail', kwargs={'user_id': teacher_b.id}))

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_admin_updates_teacher_detail_and_profile_fields_together(self):
        user_model = get_user_model()
        teacher = user_model.objects.create_user(
            id=100012,
            username='100012',
            password='teacher123456',
            real_name='鏇存柊鍓嶆暀甯?',
            department='璁＄畻鏈哄闄?',
            title='璁插笀',
        )
        TeacherProfile.objects.create(
            user=teacher,
            department='璁＄畻鏈哄闄?',
            discipline='浜哄伐鏅鸿兘',
            title='璁插笀',
            research_interests='鏁版嵁鎸栨帢',
            h_index=1,
        )

        response = self.client.patch(
            reverse('teacher_detail', kwargs={'user_id': teacher.id}),
            {
                'real_name': '鏇存柊鍚庢暀甯?',
                'department': '鏁板瓧濯掍綋瀛﹂櫌',
                'title': '鍓暀鎺?',
                'discipline': '鏁板瓧浜烘枃',
                'research_interests': '鏁欏笀鐢诲儚, 鏅鸿兘鎺ㄨ崘',
                'bio': '绠＄悊鍛樿Е鍙戠殑鏁欏笀璧勬枡鏇存柊',
                'h_index': 5,
                'is_active': False,
                'research_direction': ['鏁欏笀鐢诲儚', '鏅鸿兘鎺ㄨ崘'],
            },
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        teacher.refresh_from_db()
        self.assertEqual(teacher.real_name, '鏇存柊鍚庢暀甯?')
        self.assertEqual(teacher.department, '鏁板瓧濯掍綋瀛﹂櫌')
        self.assertEqual(teacher.title, '鍓暀鎺?')
        self.assertFalse(teacher.is_active)
        self.assertEqual(teacher.profile.discipline, '鏁板瓧浜烘枃')
        self.assertEqual(teacher.profile.research_interests, '鏁欏笀鐢诲儚, 鏅鸿兘鎺ㄨ崘')
        self.assertEqual(teacher.profile.h_index, 5)

    def test_teacher_can_reset_password_with_employee_id_and_real_name(self):
        user_model = get_user_model()
        teacher = user_model.objects.create_user(
            id=100003,
            username='100003',
            password='old-password',
            real_name='王浩然',
            department='计算机学院',
            title='讲师',
        )

        self.client.force_authenticate(user=None)
        response = self.client.post(
            reverse('forgot_password_reset'),
            {
                'employee_id': '100003',
                'real_name': '王浩然',
                'new_password': 'SecurePass789!Q',
                'confirm_password': 'SecurePass789!Q',
            },
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        teacher.refresh_from_db()
        self.assertTrue(teacher.check_password('SecurePass789!Q'))

    def test_teacher_detail_patch_keeps_account_and_profile_fields_in_sync(self):
        user_model = get_user_model()
        teacher = user_model.objects.create_user(
            id=100021,
            username='100021',
            password='teacher123456',
            real_name='教师本人',
            department='计算机学院',
            title='讲师',
            bio='初始简介',
        )
        TeacherProfile.objects.create(
            user=teacher,
            department='计算机学院',
            discipline='计算机科学与技术',
            title='讲师',
            research_interests='知识图谱',
            h_index=2,
        )

        self.client.force_authenticate(user=teacher)
        response = self.client.patch(
            reverse('teacher_detail', kwargs={'user_id': teacher.id}),
            {
                'real_name': '教师本人-已更新',
                'department': '人工智能学院',
                'title': '副教授',
                'discipline': '人工智能',
                'research_interests': '知识图谱, 科研画像',
                'bio': '教师本人在资料页完成更新。',
                'h_index': 6,
                'research_direction': ['知识图谱', '科研画像'],
            },
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        teacher.refresh_from_db()
        self.assertEqual(teacher.real_name, '教师本人-已更新')
        self.assertEqual(teacher.department, '人工智能学院')
        self.assertEqual(teacher.title, '副教授')
        self.assertEqual(teacher.profile.department, '人工智能学院')
        self.assertEqual(teacher.profile.title, '副教授')
        self.assertEqual(teacher.profile.discipline, '人工智能')
        self.assertEqual(teacher.profile.research_interests, '知识图谱, 科研画像')
        self.assertEqual(teacher.profile.h_index, 6)
