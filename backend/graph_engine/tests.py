from django.contrib.auth import get_user_model
from django.test import override_settings
from rest_framework.test import APITestCase

from achievements.models import Paper


User = get_user_model()


@override_settings(ENABLE_NEO4J=False)
class GraphTopologyFallbackTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            id=100081,
            username="100081",
            password="teacher123456",
            real_name="测试教师",
        )
        self.client.force_authenticate(self.user)
        self.url = f"/api/graph/topology/{self.user.id}/"

    def test_relational_topology_includes_meta_and_detail_fields(self):
        Paper.objects.create(
            teacher=self.user,
            title="高校教师科研画像数据融合方法研究",
            abstract="围绕画像建模与知识组织展开研究。",
            date_acquired="2026-03-01",
            doi="10.1234/portrait-fallback-test",
            paper_type="journal",
            journal_name="教育信息化研究",
        )

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 200)
        self.assertIn("nodes", response.data)
        self.assertIn("links", response.data)
        self.assertIn("meta", response.data)

        meta = response.data["meta"]
        self.assertEqual(meta["source"], "mysql")
        self.assertTrue(meta["fallback_used"])
        self.assertGreaterEqual(meta["node_count"], 2)
        self.assertGreaterEqual(meta["link_count"], 1)

        self.assertTrue(
            any("nodeTypeLabel" in node for node in response.data["nodes"])
        )
        self.assertTrue(
            any("detailLines" in node for node in response.data["nodes"])
        )
        self.assertTrue(
            any(node.get("name") == "高校教师科研画像数据融合方法研究" for node in response.data["nodes"])
        )

        self.assertTrue(
            any("relationLabel" in link for link in response.data["links"])
        )
        self.assertTrue(
            any("description" in link for link in response.data["links"])
        )

    def test_empty_relational_topology_keeps_compatible_response_shape(self):
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["nodes"], [])
        self.assertEqual(response.data["links"], [])
        self.assertIn("meta", response.data)
        self.assertEqual(response.data["meta"]["source"], "mysql")
        self.assertTrue(response.data["meta"]["fallback_used"])
        self.assertIn("notice", response.data["meta"])
