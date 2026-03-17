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
