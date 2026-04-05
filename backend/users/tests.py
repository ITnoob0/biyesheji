from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from achievements.models import TeacherProfile

from .serializers import DEFAULT_TEACHER_PASSWORD


class TeacherUserApiTests(APITestCase):
    def setUp(self):
        user_model = get_user_model()
        self.admin = user_model.objects.create_superuser(
            username="admin",
            password="Admin123456",
            real_name="系统管理员",
            email="admin@example.com",
        )
        TeacherProfile.objects.create(
            user=self.admin,
            department="科研管理中心",
            discipline="科研治理",
            title="管理员",
            research_interests="平台治理",
            h_index=0,
        )

    def create_teacher(self, user_id=100001, **kwargs):
        user_model = get_user_model()
        defaults = {
            "username": str(user_id),
            "password": "Teacher123456!",
            "real_name": "测试教师",
            "department": "计算机学院",
            "title": "讲师",
            "email": f"{user_id}@example.com",
            "contact_phone": "13800000000",
            "avatar_url": "https://example.com/avatar.png",
            "contact_visibility": "email_only",
        }
        defaults.update(kwargs)
        password = defaults.pop("password")
        teacher = user_model.objects.create_user(id=user_id, password=password, **defaults)
        TeacherProfile.objects.create(
            user=teacher,
            department=teacher.department,
            discipline="人工智能",
            title=teacher.title,
            research_interests="知识图谱",
            h_index=2,
        )
        return teacher

    def test_admin_can_create_college_admin_with_personal_center_fields(self):
        self.client.force_authenticate(user=self.admin)
        payload = {
            "employee_id": "100101",
            "role_code": "college_admin",
            "real_name": "张晨阳",
            "department": "计算机学院",
            "title": "副教授",
            "email": "teacher101@example.com",
            "contact_phone": "13812345678",
            "avatar_url": "https://example.com/teacher101.png",
            "discipline": "人工智能",
            "research_interests": "大模型, 知识图谱",
            "bio": "测试注册教师",
            "research_direction": ["大模型", "知识图谱"],
            "h_index": 0,
            "password": "SecurePass789!Q",
            "confirm_password": "SecurePass789!Q",
        }

        response = self.client.post(reverse("teacher_list_create"), payload, format="json")

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["employee_id"], 100101)
        self.assertEqual(response.data["username"], "100101")
        self.assertEqual(response.data["email"], "teacher101@example.com")
        self.assertEqual(response.data["contact_phone"], "13812345678")
        self.assertEqual(response.data["avatar_url"], "https://example.com/teacher101.png")
        self.assertEqual(response.data["initial_password"], "SecurePass789!Q")
        self.assertEqual(response.data["role_label"], "学院管理员")
        self.assertTrue(response.data["password_reset_required"])
        self.assertEqual(response.data["role_code"], "college_admin")
        self.assertTrue(get_user_model().objects.get(id=100101).is_staff)
        self.assertTrue(TeacherProfile.objects.filter(user_id=100101, discipline="人工智能").exists())

    def test_teacher_registration_sets_personal_center_fields(self):
        payload = {
            "employee_id": "100102",
            "real_name": "李晓雨",
            "department": "信息工程学院",
            "title": "讲师",
            "email": "teacher102@example.com",
            "contact_phone": "13912345678",
            "avatar_url": "https://example.com/teacher102.png",
            "discipline": "数据科学",
            "research_interests": "可视化分析",
            "bio": "自助注册教师",
            "research_direction": ["数据科学"],
            "h_index": 1,
            "password": "SecurePass789!Q",
            "confirm_password": "SecurePass789!Q",
        }

        response = self.client.post(reverse("teacher_register"), payload, format="json")

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertFalse(response.data["password_reset_required"])
        self.assertEqual(response.data["role_code"], "teacher")
        self.assertEqual(response.data["contact_phone"], "13912345678")

    def test_current_user_payload_includes_permission_scope(self):
        teacher = self.create_teacher(user_id=100108, real_name="边界教师")
        self.client.force_authenticate(user=teacher)

        response = self.client.get(reverse("current_user"))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("permission_scope", response.data)
        self.assertEqual(response.data["permission_scope"]["entry_role"], "teacher")
        self.assertTrue(response.data["permission_scope"]["allowed_actions"])
        self.assertTrue(response.data["permission_scope"]["restricted_actions"])

    def test_current_user_profile_can_be_updated_with_public_profile_fields(self):
        self.client.force_authenticate(user=self.admin)
        response = self.client.patch(
            reverse("current_user"),
            {
                "real_name": "管理员甲",
                "department": "科研管理中心",
                "title": "平台主管",
                "email": "manager@example.com",
                "contact_phone": "13666668888",
                "avatar_url": "https://example.com/manager.png",
                "contact_visibility": "both",
                "discipline": "科研信息化",
                "research_interests": "科研画像, 科研治理",
                "bio": "负责系统维护与数据治理",
                "h_index": 2,
                "research_direction": ["科研画像", "科研治理"],
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.admin.refresh_from_db()
        self.assertEqual(self.admin.real_name, "管理员甲")
        self.assertEqual(self.admin.email, "manager@example.com")
        self.assertEqual(self.admin.contact_phone, "13666668888")
        self.assertEqual(self.admin.avatar_url, "https://example.com/manager.png")
        self.assertEqual(self.admin.contact_visibility, "both")
        self.assertEqual(self.admin.profile.discipline, "科研信息化")
        self.assertEqual(self.admin.profile.h_index, 2)

    def test_current_user_profile_returns_contact_visibility_strategy(self):
        teacher = self.create_teacher(
            user_id=100109,
            real_name="展示策略教师",
            contact_visibility="internal_only",
            email="teacher109@example.com",
            contact_phone="13911112222",
        )
        self.client.force_authenticate(user=teacher)

        response = self.client.get(reverse("current_user"))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["contact_visibility"], "internal_only")
        self.assertEqual(response.data["contact_visibility_label"], "联系方式仅内部可见")
        self.assertEqual(response.data["public_contact_channels"], [])

    def test_teacher_can_upload_avatar_via_personal_center(self):
        teacher = self.create_teacher(user_id=100134, real_name="头像教师")
        self.client.force_authenticate(user=teacher)
        avatar = SimpleUploadedFile("avatar.png", b"fake-image-bytes", content_type="image/png")

        response = self.client.post(reverse("current_user_avatar_upload"), {"avatar": avatar}, format="multipart")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("/media/avatars/", response.data["avatar_url"])
        self.assertEqual(response.data["user"]["avatar_url"], response.data["avatar_url"])
        teacher.refresh_from_db()
        self.assertEqual(teacher.avatar_url, response.data["avatar_url"])

        avatar_path = response.data["avatar_url"].split("/media/", 1)[-1]
        file_path = settings.MEDIA_ROOT / avatar_path
        self.assertTrue(file_path.exists())
        file_path.unlink()
        avatar_dir = file_path.parent
        if avatar_dir.exists() and not any(avatar_dir.iterdir()):
            avatar_dir.rmdir()

    def test_teacher_detail_returns_personal_center_fields(self):
        teacher = self.create_teacher(user_id=100103, real_name="王老师")
        self.client.force_authenticate(user=teacher)

        response = self.client.get(reverse("teacher_detail", kwargs={"user_id": teacher.id}))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["email"], "100103@example.com")
        self.assertEqual(response.data["contact_phone"], "13800000000")
        self.assertEqual(response.data["avatar_url"], "https://example.com/avatar.png")

    def test_admin_can_reset_teacher_password_and_mark_force_change(self):
        teacher = self.create_teacher(user_id=100104, real_name="王老师")
        self.client.force_authenticate(user=self.admin)

        response = self.client.post(reverse("teacher_reset_password", kwargs={"user_id": teacher.id}))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["temporary_password"], DEFAULT_TEACHER_PASSWORD)
        self.assertTrue(response.data["password_reset_required"])
        self.assertIn("临时密码", response.data["security_notice"])
        teacher.refresh_from_db()
        self.assertTrue(teacher.check_password(DEFAULT_TEACHER_PASSWORD))
        self.assertTrue(teacher.password_reset_required)
        self.assertIsNotNone(teacher.password_updated_at)

    def test_admin_cannot_reset_admin_account_from_teacher_management(self):
        self.client.force_authenticate(user=self.admin)

        response = self.client.post(reverse("teacher_reset_password", kwargs={"user_id": self.admin.id}))

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_admin_cannot_access_admin_account_via_teacher_management_detail(self):
        self.client.force_authenticate(user=self.admin)

        response = self.client.get(reverse("teacher_detail", kwargs={"user_id": self.admin.id}))

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(response.data["detail"], "教师管理入口不支持系统管理员账户。")

    def test_teacher_can_change_own_password_and_clear_force_change_flag(self):
        teacher = self.create_teacher(user_id=100105, real_name="周老师")
        teacher.password_reset_required = True
        teacher.save(update_fields=["password_reset_required"])
        self.client.force_authenticate(user=teacher)

        response = self.client.post(
            reverse("current_user_change_password"),
            {
                "current_password": "Teacher123456!",
                "new_password": "TeacherNew456!Q",
                "confirm_password": "TeacherNew456!Q",
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["user"]["role_label"], "教师账户")
        self.assertFalse(response.data["user"]["password_reset_required"])
        teacher.refresh_from_db()
        self.assertTrue(teacher.check_password("TeacherNew456!Q"))
        self.assertFalse(teacher.password_reset_required)

    def test_teacher_change_password_requires_correct_current_password(self):
        teacher = self.create_teacher(user_id=100106)
        self.client.force_authenticate(user=teacher)

        response = self.client.post(
            reverse("current_user_change_password"),
            {
                "current_password": "wrong-password",
                "new_password": "TeacherNew456!Q",
                "confirm_password": "TeacherNew456!Q",
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("current_password", response.data)

    def test_forgot_password_reset_updates_password_and_clears_force_change_flag(self):
        teacher = self.create_teacher(user_id=100107, real_name="陈老师")
        teacher.password_reset_required = True
        teacher.save(update_fields=["password_reset_required"])

        response = self.client.post(
            reverse("forgot_password_reset"),
            {
                "employee_id": "100107",
                "real_name": "陈老师",
                "new_password": "SecurePass789!Q",
                "confirm_password": "SecurePass789!Q",
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        teacher.refresh_from_db()
        self.assertTrue(teacher.check_password("SecurePass789!Q"))
        self.assertFalse(teacher.password_reset_required)

    def test_non_admin_cannot_view_other_teacher_detail(self):
        teacher_a = self.create_teacher(user_id=100110, real_name="教师甲")
        teacher_b = self.create_teacher(user_id=100111, real_name="教师乙")

        self.client.force_authenticate(user=teacher_a)
        response = self.client.get(reverse("teacher_detail", kwargs={"user_id": teacher_b.id}))

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_non_admin_cannot_reset_teacher_password(self):
        teacher_a = self.create_teacher(user_id=100112, real_name="教师甲")
        teacher_b = self.create_teacher(user_id=100113, real_name="教师乙")

        self.client.force_authenticate(user=teacher_a)
        response = self.client.post(reverse("teacher_reset_password", kwargs={"user_id": teacher_b.id}))

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_non_admin_cannot_create_teacher_account(self):
        teacher = self.create_teacher(user_id=100121, real_name="教师甲")
        self.client.force_authenticate(user=teacher)

        response = self.client.post(
            reverse("teacher_list_create"),
            {
                "employee_id": "100122",
                "real_name": "越权创建",
                "department": "计算机学院",
                "title": "讲师",
                "password": "SecurePass789!Q",
                "confirm_password": "SecurePass789!Q",
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(response.data["detail"], "当前账号没有管理员权限。")

    def test_non_admin_cannot_update_other_teacher_detail(self):
        teacher_a = self.create_teacher(user_id=100119, real_name="教师甲")
        teacher_b = self.create_teacher(user_id=100120, real_name="教师乙")

        self.client.force_authenticate(user=teacher_a)
        response = self.client.patch(
            reverse("teacher_detail", kwargs={"user_id": teacher_b.id}),
            {"real_name": "越权修改"},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_admin_can_update_teacher_detail_and_profile_together(self):
        teacher = self.create_teacher(user_id=100114, real_name="原教师")
        self.client.force_authenticate(user=self.admin)

        response = self.client.patch(
            reverse("teacher_detail", kwargs={"user_id": teacher.id}),
            {
                "real_name": "更新后教师",
                "department": "人工智能学院",
                "title": "副教授",
                "email": "updated@example.com",
                "contact_phone": "13788886666",
                "avatar_url": "https://example.com/updated.png",
                "discipline": "人工智能",
                "research_interests": "知识图谱, 科研画像",
                "bio": "更新后的教师简介",
                "h_index": 5,
                "is_active": False,
                "research_direction": ["知识图谱", "科研画像"],
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        teacher.refresh_from_db()
        self.assertEqual(teacher.real_name, "更新后教师")
        self.assertEqual(teacher.department, "人工智能学院")
        self.assertEqual(teacher.email, "updated@example.com")
        self.assertEqual(teacher.contact_phone, "13788886666")
        self.assertEqual(teacher.avatar_url, "https://example.com/updated.png")
        self.assertFalse(teacher.is_active)
        self.assertEqual(teacher.profile.discipline, "人工智能")
        self.assertEqual(teacher.profile.h_index, 5)

    def test_admin_teacher_list_excludes_admin_accounts(self):
        self.create_teacher(user_id=100115, real_name="列表教师")
        self.client.force_authenticate(user=self.admin)

        response = self.client.get(reverse("teacher_list_create"))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        returned_usernames = [item["username"] for item in response.data]
        self.assertNotIn("admin", returned_usernames)
        self.assertIn("100115", returned_usernames)

    def test_teacher_list_for_teacher_only_returns_self(self):
        teacher_a = self.create_teacher(user_id=100116, real_name="教师甲")
        self.create_teacher(user_id=100117, real_name="教师乙")
        self.client.force_authenticate(user=teacher_a)

        response = self.client.get(reverse("teacher_list_create"))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]["id"], teacher_a.id)

    def test_teacher_account_payload_includes_lifecycle_fields(self):
        teacher = self.create_teacher(user_id=100123, real_name="生命周期教师")
        teacher.password_reset_required = True
        teacher.save(update_fields=["password_reset_required"])
        self.client.force_authenticate(user=teacher)

        response = self.client.get(reverse("current_user"))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["account_status_label"], "账户可用")
        self.assertEqual(response.data["password_status_label"], "待修改密码")
        self.assertIn("临时密码", response.data["next_action_hint"])

    def test_admin_can_view_teacher_management_summary(self):
        teacher_a = self.create_teacher(user_id=100124, real_name="汇总教师甲")
        teacher_b = self.create_teacher(user_id=100125, real_name="汇总教师乙")
        teacher_b.is_active = False
        teacher_b.password_reset_required = True
        teacher_b.save(update_fields=["is_active", "password_reset_required"])
        self.client.force_authenticate(user=self.admin)

        response = self.client.get(reverse("teacher_management_summary"))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["total_count"], 2)
        self.assertEqual(response.data["active_count"], 1)
        self.assertEqual(response.data["inactive_count"], 1)
        self.assertEqual(response.data["password_reset_required_count"], 1)
        self.assertEqual(response.data["stable_password_count"], 1)
        self.assertIn("后续如扩展多角色", response.data["future_extension_hint"])

    def test_non_admin_cannot_view_teacher_management_summary(self):
        teacher = self.create_teacher(user_id=100126, real_name="普通教师")
        self.client.force_authenticate(user=teacher)

        response = self.client.get(reverse("teacher_management_summary"))

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(response.data["detail"], "当前账号没有管理员权限。")

    def test_admin_can_bulk_deactivate_and_activate_teachers(self):
        teacher_a = self.create_teacher(user_id=100127, real_name="批量教师甲")
        teacher_b = self.create_teacher(user_id=100128, real_name="批量教师乙")
        self.client.force_authenticate(user=self.admin)

        deactivate_response = self.client.post(
            reverse("teacher_bulk_action"),
            {"action": "deactivate", "user_ids": [teacher_a.id, teacher_b.id]},
            format="json",
        )

        self.assertEqual(deactivate_response.status_code, status.HTTP_200_OK)
        self.assertEqual(deactivate_response.data["processed_count"], 2)
        self.assertEqual(deactivate_response.data["skipped_count"], 0)
        teacher_a.refresh_from_db()
        teacher_b.refresh_from_db()
        self.assertFalse(teacher_a.is_active)
        self.assertFalse(teacher_b.is_active)

        activate_response = self.client.post(
            reverse("teacher_bulk_action"),
            {"action": "activate", "user_ids": [teacher_a.id, teacher_b.id]},
            format="json",
        )

        self.assertEqual(activate_response.status_code, status.HTTP_200_OK)
        self.assertEqual(activate_response.data["processed_count"], 2)
        teacher_a.refresh_from_db()
        teacher_b.refresh_from_db()
        self.assertTrue(teacher_a.is_active)
        self.assertTrue(teacher_b.is_active)

    def test_admin_can_bulk_reset_teacher_passwords(self):
        teacher_a = self.create_teacher(user_id=100129, real_name="重置教师甲")
        teacher_b = self.create_teacher(user_id=100130, real_name="重置教师乙")
        self.client.force_authenticate(user=self.admin)

        response = self.client.post(
            reverse("teacher_bulk_action"),
            {"action": "reset_password", "user_ids": [teacher_a.id, teacher_b.id]},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["temporary_password"], DEFAULT_TEACHER_PASSWORD)
        self.assertEqual(response.data["processed_count"], 2)
        self.assertEqual(response.data["management_summary"]["password_reset_required_count"], 2)
        self.assertIn("临时密码", response.data["recovery_notice"])
        teacher_a.refresh_from_db()
        teacher_b.refresh_from_db()
        self.assertTrue(teacher_a.check_password(DEFAULT_TEACHER_PASSWORD))
        self.assertTrue(teacher_b.check_password(DEFAULT_TEACHER_PASSWORD))
        self.assertTrue(teacher_a.password_reset_required)
        self.assertTrue(teacher_b.password_reset_required)

    def test_bulk_teacher_action_skips_admin_account(self):
        teacher = self.create_teacher(user_id=100131, real_name="可管理教师")
        self.client.force_authenticate(user=self.admin)

        response = self.client.post(
            reverse("teacher_bulk_action"),
            {"action": "deactivate", "user_ids": [teacher.id, self.admin.id]},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["processed_count"], 1)
        self.assertEqual(response.data["skipped_count"], 1)
        self.assertEqual(response.data["skipped_items"][0]["user_id"], self.admin.id)
        teacher.refresh_from_db()
        self.assertFalse(teacher.is_active)

    def test_non_admin_cannot_execute_bulk_teacher_action(self):
        teacher_a = self.create_teacher(user_id=100132, real_name="教师甲")
        teacher_b = self.create_teacher(user_id=100133, real_name="教师乙")
        self.client.force_authenticate(user=teacher_a)

        response = self.client.post(
            reverse("teacher_bulk_action"),
            {"action": "deactivate", "user_ids": [teacher_b.id]},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(response.data["detail"], "当前账号没有管理员权限。")

    def test_inactive_account_login_returns_clear_message(self):
        teacher = self.create_teacher(user_id=100118, real_name="停用教师")
        teacher.is_active = False
        teacher.save(update_fields=["is_active"])

        response = self.client.post(
            reverse("token_obtain_pair"),
            {"username": "100118", "password": "Teacher123456!"},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertEqual(response.data["detail"], "账户已停用，请联系管理员处理。")
        self.assertEqual(response.data["error"]["code"], "account_inactive")
        self.assertTrue(response.data["request_id"])
