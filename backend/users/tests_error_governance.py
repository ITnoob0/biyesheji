from django.contrib.auth import get_user_model
from django.test import override_settings
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase


User = get_user_model()


class ApiErrorGovernanceTests(APITestCase):
    def setUp(self):
        self.admin = User.objects.create_superuser(
            username="admin",
            password="Admin123456",
            real_name="系统管理员",
        )
        self.teacher = User.objects.create_user(
            id=100221,
            username="100221",
            password="Teacher123456!",
            real_name="异常治理教师",
        )

    def test_invalid_login_returns_standardized_error_payload(self):
        response = self.client.post(
            reverse("token_obtain_pair"),
            {"username": self.teacher.username, "password": "wrong-password"},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertIn("detail", response.data)
        self.assertIn("error", response.data)
        self.assertIn("request_id", response.data)
        self.assertEqual(response.data["error"]["status"], status.HTTP_401_UNAUTHORIZED)
        self.assertEqual(response["X-Request-ID"], response.data["request_id"])

    def test_permission_denied_returns_standardized_error_payload(self):
        self.client.force_authenticate(self.teacher)

        response = self.client.get("/api/achievements/academy-overview/")

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertIn("error", response.data)
        self.assertEqual(response.data["error"]["status"], status.HTTP_403_FORBIDDEN)
        self.assertTrue(response.data["error"]["next_step"])
        self.assertTrue(response.data["request_id"])

    def test_manual_not_found_branch_uses_standardized_payload(self):
        self.client.force_authenticate(self.admin)

        response = self.client.get(reverse("teacher_detail", kwargs={"user_id": 999999}))

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(response.data["error"]["code"], "teacher_not_found")
        self.assertEqual(response.data["detail"], "教师账户不存在。")
        self.assertIn("request_id", response.data)

    @override_settings(ROOT_URLCONF="core.test_urls")
    def test_unhandled_api_exception_returns_json_payload(self):
        self.client.raise_request_exception = False

        response = self.client.get("/api/test-error/")
        payload = response.json()

        self.assertEqual(response.status_code, status.HTTP_500_INTERNAL_SERVER_ERROR)
        self.assertEqual(response["Content-Type"].split(";")[0], "application/json")
        self.assertEqual(payload["error"]["code"], "internal_server_error")
        self.assertEqual(payload["detail"], "系统处理请求时出现异常，请稍后重试。")
        self.assertTrue(payload["request_id"])
