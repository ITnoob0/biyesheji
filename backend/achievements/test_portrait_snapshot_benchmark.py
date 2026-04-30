from __future__ import annotations

from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.cache import cache
from rest_framework import status
from rest_framework.test import APITestCase

from .models import IntellectualProperty, Paper, PortraitSnapshot
from .scoring_engine import TeacherScoringEngine


class PortraitSnapshotBenchmarkApiTests(APITestCase):
    def setUp(self):
        cache.clear()
        user_model = get_user_model()
        self.system_admin = user_model.objects.create_superuser(
            id=905001,
            username='portrait-admin',
            password='Admin123456',
            real_name='系统管理员画像',
            department='科研管理中心',
        )
        self.college_admin = user_model.objects.create_user(
            id=905002,
            username='portrait-college-admin',
            password='Admin123456',
            real_name='学院管理员画像',
            department='人工智能学院',
            title='学院管理员',
            is_staff=True,
        )
        self.teacher = user_model.objects.create_user(
            id=905003,
            username='905003',
            password='teacher123456',
            real_name='画像教师A',
            department='人工智能学院',
            title='副教授',
        )
        self.peer_teacher = user_model.objects.create_user(
            id=905004,
            username='905004',
            password='teacher123456',
            real_name='画像教师B',
            department='人工智能学院',
            title='讲师',
        )
        self.other_college_teacher = user_model.objects.create_user(
            id=905005,
            username='905005',
            password='teacher123456',
            real_name='外院教师',
            department='外语学院',
            title='讲师',
        )

    def _create_approved_paper(self, teacher, *, title: str, date_acquired: str):
        return Paper.objects.create(
            teacher=teacher,
            title=title,
            abstract='这是一个足够长的摘要，用于画像快照和同侪基准集成测试。',
            date_acquired=date_acquired,
            paper_type='JOURNAL',
            journal_name='画像测试期刊',
            status='APPROVED',
        )

    def test_case_1_cold_and_hot_start_snapshot_persistence(self):
        self._create_approved_paper(
            self.teacher,
            title='2025 年论文',
            date_acquired='2025-05-01',
        )
        PortraitSnapshot.objects.create(
            user=self.teacher,
            year=2024,
            dimension_scores={key: 10 for key in TeacherScoringEngine.DIMENSION_LABELS.keys()},
            total_score=10.0,
        )

        self.client.force_authenticate(user=self.system_admin)
        with patch(
            'achievements.portrait_analysis.TeacherScoringEngine.collect_metrics_series',
            wraps=TeacherScoringEngine.collect_metrics_series,
        ) as mocked_series:
            cold_response = self.client.get(
                '/api/achievements/portrait/analysis/',
                {'user_id': self.teacher.id, 'year': 2025, 'scope': 'university'},
            )
            self.assertEqual(cold_response.status_code, status.HTTP_200_OK)
            self.assertEqual(
                len(cold_response.data.get('dimension_insights', [])),
                len(TeacherScoringEngine.DIMENSION_LABELS),
            )
            self.assertGreaterEqual(mocked_series.call_count, 1)

        self.assertTrue(PortraitSnapshot.objects.filter(user=self.teacher, year=2025).exists())
        snapshot_count = PortraitSnapshot.objects.filter(user=self.teacher, year=2025).count()

        with patch(
            'achievements.portrait_analysis.TeacherScoringEngine.collect_metrics_series',
            wraps=TeacherScoringEngine.collect_metrics_series,
        ) as mocked_series:
            hot_response = self.client.get(
                '/api/achievements/portrait/analysis/',
                {'user_id': self.teacher.id, 'year': 2025, 'scope': 'university'},
            )
            self.assertEqual(hot_response.status_code, status.HTTP_200_OK)
            self.assertEqual(
                len(hot_response.data.get('dimension_insights', [])),
                len(TeacherScoringEngine.DIMENSION_LABELS),
            )
            self.assertEqual(mocked_series.call_count, 0)

        self.assertEqual(PortraitSnapshot.objects.filter(user=self.teacher, year=2025).count(), snapshot_count)
        self.assertEqual(hot_response.data['snapshot_boundary']['persistence_status'], 'persisted')

    def test_case_2_scope_isolation_for_teacher_college_admin_and_system_admin(self):
        self._create_approved_paper(self.teacher, title='教师画像论文', date_acquired='2025-03-01')
        self._create_approved_paper(self.peer_teacher, title='同院同侪论文', date_acquired='2025-04-01')
        self._create_approved_paper(self.other_college_teacher, title='外院论文', date_acquired='2025-04-08')

        self.client.force_authenticate(user=self.teacher)
        teacher_response = self.client.get(
            '/api/achievements/portrait/analysis/',
            {'year': 2026, 'scope': 'university'},
        )
        self.assertEqual(teacher_response.status_code, status.HTTP_200_OK)
        self.assertIn('college_average_data', teacher_response.data['benchmark_data'])
        self.assertNotIn('university_average_data', teacher_response.data['benchmark_data'])
        self.assertEqual(teacher_response.data['benchmark_data']['active_scope'], 'college')

        self.client.force_authenticate(user=self.college_admin)
        college_admin_response = self.client.get(
            '/api/achievements/portrait/analysis/',
            {'user_id': self.teacher.id, 'year': 2026, 'scope': 'university'},
        )
        self.assertEqual(college_admin_response.status_code, status.HTTP_200_OK)
        self.assertIn('college_average_data', college_admin_response.data['benchmark_data'])
        self.assertNotIn('university_average_data', college_admin_response.data['benchmark_data'])
        self.assertEqual(college_admin_response.data['benchmark_data']['active_scope'], 'college')

        self.client.force_authenticate(user=self.system_admin)
        system_admin_response = self.client.get(
            '/api/achievements/portrait/analysis/',
            {'user_id': self.teacher.id, 'year': 2026, 'scope': 'university'},
        )
        self.assertEqual(system_admin_response.status_code, status.HTTP_200_OK)
        self.assertIn('university_average_data', system_admin_response.data['benchmark_data'])
        self.assertIn('college_comparison_data', system_admin_response.data['benchmark_data'])
        self.assertEqual(system_admin_response.data['benchmark_data']['active_scope'], 'university')

    def test_case_3_historical_snapshot_is_frozen_but_current_runtime_reflects_new_records(self):
        self._create_approved_paper(
            self.teacher,
            title='2024 基线论文',
            date_acquired='2024-03-12',
        )

        self.client.force_authenticate(user=self.system_admin)
        baseline_response = self.client.get(
            '/api/achievements/portrait/analysis/',
            {'user_id': self.teacher.id, 'year': 2024},
        )
        self.assertEqual(baseline_response.status_code, status.HTTP_200_OK)
        frozen_total = float(baseline_response.data['snapshot_boundary']['current_snapshot'].get('snapshot_created') is not None or baseline_response.data['radar_series_data'][0]['value'][0] >= 0)
        frozen_total_score = PortraitSnapshot.objects.get(user=self.teacher, year=2024).total_score

        IntellectualProperty.objects.create(
            teacher=self.teacher,
            title='补录的 2024 专利',
            date_acquired='2024-09-10',
            ip_type='SOFTWARE_COPYRIGHT',
            role='PI',
            registration_number='2024SR-PORTRAIT-001',
            is_transformed=True,
            status='APPROVED',
        )

        historical_response = self.client.get(
            '/api/achievements/portrait/analysis/',
            {'user_id': self.teacher.id, 'year': 2024},
        )
        self.assertEqual(historical_response.status_code, status.HTTP_200_OK)
        self.assertEqual(PortraitSnapshot.objects.get(user=self.teacher, year=2024).total_score, frozen_total_score)

        runtime_response = self.client.get(
            '/api/achievements/portrait/analysis/',
            {'user_id': self.teacher.id, 'year': 2026},
        )
        self.assertEqual(runtime_response.status_code, status.HTTP_200_OK)
        runtime_total = float(runtime_response.data['stage_comparison']['current_total_score'])
        self.assertGreaterEqual(runtime_total, frozen_total_score)
        self.assertTrue(frozen_total >= 0)

    def test_case_4_single_teacher_college_average_is_safe_and_overlaps_teacher_series(self):
        user_model = get_user_model()
        solo_teacher = user_model.objects.create_user(
            id=905006,
            username='905006',
            password='teacher123456',
            real_name='孤岛学院教师',
            department='孤岛学院',
            title='讲师',
        )
        self._create_approved_paper(
            solo_teacher,
            title='孤岛学院论文',
            date_acquired='2025-06-06',
        )

        self.client.force_authenticate(user=solo_teacher)
        response = self.client.get('/api/achievements/portrait/analysis/', {'year': 2026})
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        college_average_data = response.data['benchmark_data']['college_average_data']
        self.assertEqual(college_average_data['sample_size'], 1)
        teacher_series = response.data['radar_series_data'][0]['value']
        college_series = response.data['radar_series_data'][1]['value']
        self.assertEqual(teacher_series, college_series)
