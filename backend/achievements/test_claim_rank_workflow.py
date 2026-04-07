from datetime import timedelta

from django.contrib.auth import get_user_model
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from .models import AchievementClaim, Paper


class AchievementClaimRankWorkflowApiTests(APITestCase):
    def setUp(self):
        user_model = get_user_model()
        self.initiator = user_model.objects.create_user(
            id=903001,
            username='903001',
            password='teacher123456',
            real_name='Initiator',
            department='AI College',
            title='Professor',
        )
        self.coauthor = user_model.objects.create_user(
            id=903002,
            username='903002',
            password='teacher123456',
            real_name='CoAuthor',
            department='AI College',
            title='Associate Professor',
        )
        self.other_teacher = user_model.objects.create_user(
            id=903003,
            username='903003',
            password='teacher123456',
            real_name='OtherTeacher',
            department='AI College',
            title='Lecturer',
        )
        self.college_admin = user_model.objects.create_user(
            id=903004,
            username='college-admin-rank',
            password='Admin123456',
            real_name='CollegeAdmin',
            department='AI College',
            title='College Admin',
            is_staff=True,
        )

    def test_initiator_can_publish_claim_with_rank_assignments(self):
        self.client.force_authenticate(user=self.initiator)
        response = self.client.post(
            '/api/achievements/papers/',
            {
                'title': 'Rank assignment paper',
                'abstract': 'This abstract is long enough to verify rank assignment in claim invitations.',
                'date_acquired': '2025-05-01',
                'paper_type': 'JOURNAL',
                'journal_name': 'Rank Journal',
                'coauthor_records': [
                    {'name': 'CoAuthor', 'author_rank': 2},
                    {'name': 'ExternalA', 'author_rank': 3},
                ],
            },
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        claim = AchievementClaim.objects.filter(target_user=self.coauthor).first()
        self.assertIsNotNone(claim)
        self.assertEqual(claim.status, 'PENDING')
        self.assertEqual(claim.proposed_author_rank, 2)
        self.assertEqual(claim.coauthor.author_rank, 2)

    def test_coauthor_can_correct_rank_during_acceptance(self):
        paper = Paper.objects.create(
            teacher=self.initiator,
            title='Rank correction paper',
            abstract='Long enough abstract to verify rank correction during claim acceptance.',
            date_acquired='2025-05-03',
            paper_type='JOURNAL',
            journal_name='Correction Journal',
            status='APPROVED',
            citation_count=5,
        )
        coauthor_row = paper.coauthors.create(name='CoAuthor', author_rank=2, is_internal=True, internal_teacher=self.coauthor)
        claim = AchievementClaim.objects.create(
            achievement=paper,
            initiator=self.initiator,
            target_user=self.coauthor,
            coauthor=coauthor_row,
            status='PENDING',
            proposed_author_rank=2,
        )

        self.client.force_authenticate(user=self.coauthor)
        response = self.client.post(
            f'/api/achievements/claims/{claim.id}/accept/',
            {'confirmed_author_rank': 3, 'confirmation_note': '署名确认为第三作者'},
            format='json',
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        claim.refresh_from_db()
        coauthor_row.refresh_from_db()
        self.assertEqual(claim.status, 'CONFLICT')
        self.assertEqual(claim.confirmed_author_rank, 3)
        self.assertEqual(claim.confirmation_note, '署名确认为第三作者')
        self.assertEqual(coauthor_row.author_rank, 3)
        self.assertIsNotNone(claim.rank_confirmed_at)

        all_achievements_response = self.client.get(f'/api/achievements/all-achievements/{self.coauthor.id}/')
        self.assertEqual(all_achievements_response.status_code, status.HTTP_200_OK)
        target_item = next(item for item in all_achievements_response.data['records'] if item['title'] == paper.title)
        self.assertEqual(target_item['author_rank_label'], '第3作者')

    def test_claim_reject_reason_supports_anti_misclaim_supervision(self):
        paper = Paper.objects.create(
            teacher=self.initiator,
            title='Misclaim paper',
            abstract='Long enough abstract to verify anti misclaim rejection with reason.',
            date_acquired='2025-05-05',
            paper_type='JOURNAL',
            journal_name='Audit Journal',
            status='APPROVED',
        )
        claim = AchievementClaim.objects.create(
            achievement=paper,
            initiator=self.initiator,
            target_user=self.coauthor,
            status='PENDING',
            proposed_author_rank=2,
        )

        self.client.force_authenticate(user=self.coauthor)
        response = self.client.post(
            f'/api/achievements/claims/{claim.id}/reject/',
            {'reason': '位次标注不正确，先拒绝等待发起人修正'},
            format='json',
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        claim.refresh_from_db()
        self.assertEqual(claim.status, 'REJECTED')
        self.assertEqual(claim.confirmation_note, '位次标注不正确，先拒绝等待发起人修正')

    def test_single_source_of_truth_in_academy_dashboard(self):
        paper = Paper.objects.create(
            teacher=self.initiator,
            title='Single source paper',
            abstract='Long enough abstract to verify one paper counted once in academy dashboard.',
            date_acquired='2025-05-07',
            paper_type='JOURNAL',
            journal_name='SingleSource Journal',
            status='APPROVED',
        )
        AchievementClaim.objects.create(
            achievement=paper,
            initiator=self.initiator,
            target_user=self.coauthor,
            status='ACCEPTED',
            proposed_author_rank=2,
            confirmed_author_rank=2,
            rank_confirmed_at=timezone.now(),
        )
        AchievementClaim.objects.create(
            achievement=paper,
            initiator=self.initiator,
            target_user=self.other_teacher,
            status='ACCEPTED',
            proposed_author_rank=3,
            confirmed_author_rank=3,
            rank_confirmed_at=timezone.now(),
        )

        self.client.force_authenticate(user=self.college_admin)
        response = self.client.get('/api/achievements/academy-overview/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        paper_stat = next(item for item in response.data['statistics'] if item['title'] == '论文总数')
        self.assertEqual(paper_stat['value'], 1)

    def test_college_admin_unclaimed_tracking_stays_college_scoped(self):
        paper = Paper.objects.create(
            teacher=self.initiator,
            title='Unclaimed scope paper',
            abstract='Long enough abstract to verify college-scoped unclaimed claim tracking.',
            date_acquired='2025-05-08',
            paper_type='JOURNAL',
            journal_name='Scope Journal',
            status='APPROVED',
        )
        external_user = get_user_model().objects.create_user(
            id=903005,
            username='903005',
            password='teacher123456',
            real_name='ExternalCollegeTeacher',
            department='Math College',
            title='Lecturer',
        )
        own_claim = AchievementClaim.objects.create(
            achievement=paper,
            initiator=self.initiator,
            target_user=self.coauthor,
            status='PENDING',
            proposed_author_rank=2,
        )
        external_claim = AchievementClaim.objects.create(
            achievement=paper,
            initiator=self.initiator,
            target_user=external_user,
            status='PENDING',
            proposed_author_rank=3,
        )
        old_time = timezone.now() - timedelta(days=10)
        AchievementClaim.objects.filter(id__in=[own_claim.id, external_claim.id]).update(created_at=old_time)

        self.client.force_authenticate(user=self.college_admin)
        response = self.client.get('/api/achievements/claims/college-unclaimed/', {'days_threshold': 7})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['records']), 1)
        self.assertEqual(response.data['records'][0]['target_user_name'], 'CoAuthor')
