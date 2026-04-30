from unittest.mock import patch

from datetime import timedelta

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase
from users.models import UserNotification

from .models import (
    AcademicService,
    AchievementClaim,
    IntellectualProperty,
    Paper,
    PaperOperationLog,
    Project,
)


class AchievementEntryApiTests(APITestCase):
    def setUp(self):
        user_model = get_user_model()
        self.user = user_model.objects.create_user(
            id=100004,
            username='100004',
            password='teacher123456',
            real_name='姹績钃?,
        )
        self.other_user = user_model.objects.create_user(
            id=100005,
            username='100005',
            password='teacher123456',
            real_name='娴嬭瘯鏁欏笀',
        )
        self.client.force_authenticate(user=self.user)

    @patch('achievements.views.AcademicGraphSyncService')
    @patch('achievements.views.AcademicAI')
    def test_paper_flow_keeps_working_with_keywords_and_coauthors(self, academic_ai_cls, graph_sync_service):
        academic_ai_cls.return_value.extract_tags.return_value = ['鏁欏笀鐢诲儚', '鏅鸿兘杈呭姪']

        payload = {
            'title': '楂樻牎鏁欏笀绉戠爺鐢诲儚骞冲彴璁捐',
            'abstract': '鏈枃鍥寸粫楂樻牎鏁欏笀绉戠爺鐢诲儚骞冲彴鐨勫婧愭暟鎹不鐞嗐€佹垚鏋滃綍鍏ヤ笌鏅鸿兘杈呭姪鏈哄埗灞曞紑鐮旂┒銆?,
            'date_acquired': '2025-03-05',
            'paper_type': 'JOURNAL',
            'journal_name': '鐜颁唬鏁欒偛鎶€鏈?,
            'journal_level': '鏍稿績鏈熷垔',
            'published_volume': '18',
            'published_issue': '3',
            'pages': '22-30',
            'source_url': 'https://example.com/papers/teacher-100004-paper',
            'is_first_author': True,
            'is_representative': True,
            'doi': '10.1000/teacher-100004-paper',
            'coauthors': ['鏉庢櫒', '鍛ㄥ€?],
        }

        response = self.client.post('/api/achievements/papers/', payload, format='json')

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Paper.objects.count(), 1)
        self.assertEqual(response.data['teacher'], 100004)
        self.assertEqual(response.data['teacher_name'], '姹績钃?)
        self.assertEqual(response.data['published_volume'], '18')
        self.assertTrue(response.data['is_representative'])
        self.assertEqual(response.data['publication_year'], 2025)
        self.assertEqual(len(response.data['coauthor_details']), 2)
        self.assertEqual(response.data['keywords'], ['鏁欏笀鐢诲儚', '鏅鸿兘杈呭姪'])
        graph_sync_service.sync_paper.assert_not_called()

    @patch('achievements.views.AcademicGraphSyncService')
    @patch('achievements.views.AcademicAI')
    def test_paper_list_is_still_isolated_by_current_teacher(self, academic_ai_cls, graph_sync_service):
        academic_ai_cls.return_value.extract_tags.return_value = []

        Paper.objects.create(
            teacher=self.user,
            title='鎴戠殑璁烘枃',
            abstract='杩欐槸涓€涓冻澶熼暱鐨勬憳瑕侊紝鐢ㄦ潵楠岃瘉褰撳墠鏁欏笀鍙兘鐪嬪埌鑷繁褰曞叆鐨勮鏂囨暟鎹€?,
            date_acquired='2024-01-01',
            paper_type='JOURNAL',
            journal_name='娴嬭瘯鏈熷垔',
        )
        Paper.objects.create(
            teacher=self.other_user,
            title='鍏朵粬鏁欏笀鐨勮鏂?,
            abstract='杩欐槸鍙︿竴涓冻澶熼暱鐨勬憳瑕侊紝鐢ㄦ潵楠岃瘉澶氳处鍙峰満鏅笅鍒楄〃鏁版嵁涓嶄細涓插埌褰撳墠浼氳瘽銆?,
            date_acquired='2024-01-02',
            paper_type='CONFERENCE',
            journal_name='娴嬭瘯浼氳',
        )

        response = self.client.get('/api/achievements/papers/')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['title'], '鎴戠殑璁烘枃')
        self.assertEqual(response.data[0]['teacher'], 100004)

    @patch('achievements.views.AcademicGraphSyncService')
    @patch('achievements.views.AcademicAI')
    def test_duplicate_doi_for_same_teacher_is_rejected(self, academic_ai_cls, graph_sync_service):
        academic_ai_cls.return_value.extract_tags.return_value = []

        Paper.objects.create(
            teacher=self.user,
            title='宸叉湁璁烘枃',
            abstract='杩欐槸涓€涓冻澶熼暱鐨勬憳瑕侊紝鐢ㄦ潵楠岃瘉鍚屼竴鏁欏笀鍚嶄笅 DOI 閲嶅鏃舵帴鍙ｄ細姝ｇ‘鎷︽埅銆?,
            date_acquired='2024-01-01',
            paper_type='JOURNAL',
            journal_name='娴嬭瘯鏈熷垔',
            doi='10.1000/teacher-100004-duplicate',
        )

        payload = {
            'title': '閲嶅 DOI 璁烘枃',
            'abstract': '杩欓噷鏄竴娈佃冻澶熼暱鐨勬憳瑕侊紝鐢ㄦ潵娴嬭瘯閲嶅 DOI 鏍￠獙鏄惁瀵?100004 璐﹀彿鐢熸晥銆?,
            'date_acquired': '2025-03-05',
            'paper_type': 'JOURNAL',
            'journal_name': '鐜颁唬鏁欒偛鎶€鏈?,
            'doi': '10.1000/teacher-100004-duplicate',
            'coauthors': [],
        }

        response = self.client.post('/api/achievements/papers/', payload, format='json')

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('doi', response.data)

    @patch('achievements.views.AcademicGraphSyncService')
    @patch('achievements.views.AcademicAI')
    def test_teacher_cannot_update_or_delete_other_teachers_paper(self, academic_ai_cls, graph_sync_service):
        academic_ai_cls.return_value.extract_tags.return_value = []

        other_paper = Paper.objects.create(
            teacher=self.other_user,
            title='鍏朵粬鏁欏笀鐨勮鏂?,
            abstract='杩欐槸涓€涓冻澶熼暱鐨勬憳瑕侊紝鐢ㄦ潵楠岃瘉褰撳墠鏁欏笀鏃犳硶缂栬緫鎴栧垹闄ゅ叾浠栬处鍙风殑璁烘枃璁板綍銆?,
            date_acquired='2024-01-02',
            paper_type='JOURNAL',
            journal_name='娴嬭瘯鏈熷垔',
            doi='10.1000/other-user-paper',
        )

        update_response = self.client.patch(
            f'/api/achievements/papers/{other_paper.id}/',
            {
                'title': '瓒婃潈淇敼',
                'abstract': '杩欐槸涓€涓冻澶熼暱鐨勬憳瑕侊紝鐢ㄦ潵楠岃瘉瓒婃潈淇敼浼氳鎷掔粷銆?,
                'date_acquired': '2024-02-02',
                'paper_type': 'JOURNAL',
                'journal_name': '娴嬭瘯鏈熷垔',
                'doi': '10.1000/other-user-paper',
                'coauthors': [],
            },
            format='json',
        )
        delete_response = self.client.delete(f'/api/achievements/papers/{other_paper.id}/')

        self.assertEqual(update_response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(delete_response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertTrue(Paper.objects.filter(id=other_paper.id).exists())

    def test_bibtex_preview_reports_ready_duplicate_and_invalid_entries(self):
        Paper.objects.create(
            teacher=self.user,
            title='宸叉湁 DOI 璁烘枃',
            abstract='杩欐槸涓€涓冻澶熼暱鐨勬憳瑕侊紝鐢ㄤ簬楠岃瘉 BibTeX 棰勮浼氳瘑鍒綋鍓嶆暀甯堜笅宸茬粡瀛樺湪鐨?DOI銆?,
            date_acquired='2024-01-01',
            paper_type='JOURNAL',
            journal_name='娴嬭瘯鏈熷垔',
            doi='10.1000/existing-doi',
        )

        bibtex_content = """
@article{ready-entry,
  title = {BibTeX 鍙鍏ヨ鏂噠,
  author = {姹績钃?and 鏉庢櫒},
  journal = {鐜颁唬鏁欒偛鎶€鏈瘆,
  year = {2025},
  doi = {10.1000/new-doi},
  abstract = {鍥寸粫绉戠爺鐢诲儚涓庢垚鏋滀腑蹇冭仈鍔ㄥ睍寮€鐮旂┒銆倉
}

@article{duplicate-entry,
  title = {BibTeX 閲嶅 DOI 璁烘枃},
  author = {姹績钃?and 鍛ㄥ€﹠,
  journal = {涓浗鐢靛寲鏁欒偛},
  year = {2024},
  doi = {10.1000/existing-doi}
}

@inproceedings{invalid-entry,
  author = {姹績钃?and 鍚存},
  year = {2025}
}
"""

        upload = SimpleUploadedFile('papers.bib', bibtex_content.encode('utf-8'), content_type='text/plain')
        response = self.client.post('/api/achievements/papers/import/bibtex-preview/', {'file': upload})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['summary']['total_count'], 3)
        self.assertEqual(response.data['summary']['ready_count'], 1)
        self.assertEqual(response.data['summary']['duplicate_count'], 1)
        self.assertEqual(response.data['summary']['invalid_count'], 1)
        self.assertEqual(response.data['entries'][0]['preview_status'], 'ready')
        self.assertEqual(response.data['entries'][1]['preview_status'], 'duplicate')
        self.assertEqual(response.data['entries'][2]['preview_status'], 'invalid')
        self.assertEqual(response.data['entries'][0]['coauthors'], ['鏉庢櫒'])

    def test_bibtex_preview_marks_title_journal_year_duplicate_even_without_doi(self):
        Paper.objects.create(
            teacher=self.user,
            title='鍚屽悕璁烘枃',
            abstract='杩欐槸涓€涓冻澶熼暱鐨勬憳瑕侊紝鐢ㄤ簬楠岃瘉 BibTeX 棰勮浼氳瘑鍒鐩€佹湡鍒婁笌骞翠唤鐨勯珮搴﹂噸澶嶈褰曘€?,
            date_acquired='2024-01-01',
            paper_type='JOURNAL',
            journal_name='鐜颁唬鏁欒偛鎶€鏈?,
        )

        bibtex_content = """
@article{similar-entry,
  title = {鍚屽悕璁烘枃},
  author = {姹績钃?and 鏉庢櫒},
  journal = {鐜颁唬鏁欒偛鎶€鏈瘆,
  year = {2024},
  abstract = {鍥寸粫閲嶅褰曞叆鎻愮ず杩涜娴嬭瘯銆倉
}
"""

        upload = SimpleUploadedFile('papers.bib', bibtex_content.encode('utf-8'), content_type='text/plain')
        response = self.client.post('/api/achievements/papers/import/bibtex-preview/', {'file': upload})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['entries'][0]['preview_status'], 'duplicate')
        self.assertTrue(any('楂樺害閲嶅' in issue for issue in response.data['entries'][0]['issues']))

    def test_bibtex_preview_marks_batch_duplicate_doi_entries(self):
        bibtex_content = """
@article{first-entry,
  title = {鎵规閲嶅 DOI 璁烘枃涓€},
  author = {姹績钃?and 鏉庢櫒},
  journal = {鐜颁唬鏁欒偛鎶€鏈瘆,
  year = {2025},
  doi = {10.1000/batch-duplicate-doi},
  abstract = {鐢ㄤ簬楠岃瘉鎵规鍐?DOI 閲嶅鎻愮ず銆倉
}

@article{second-entry,
  title = {鎵规閲嶅 DOI 璁烘枃浜寎,
  author = {姹績钃?and 鍛ㄥ€﹠,
  journal = {涓浗鐢靛寲鏁欒偛},
  year = {2025},
  doi = {10.1000/batch-duplicate-doi},
  abstract = {鐢ㄤ簬楠岃瘉鎵规鍐?DOI 閲嶅鎻愮ず銆倉
}
"""

        upload = SimpleUploadedFile('batch-duplicate.bib', bibtex_content.encode('utf-8'), content_type='text/plain')
        response = self.client.post('/api/achievements/papers/import/bibtex-preview/', {'file': upload})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['summary']['duplicate_count'], 1)
        self.assertEqual(response.data['entries'][0]['preview_status'], 'ready')
        self.assertEqual(response.data['entries'][1]['preview_status'], 'duplicate')
        self.assertTrue(any('褰撳墠鎵规涓瓨鍦ㄩ噸澶?DOI' in issue for issue in response.data['entries'][1]['issues']))

    @patch('achievements.views.AcademicGraphSyncService')
    @patch('achievements.views.AcademicAI')
    def test_bibtex_confirm_import_reuses_existing_paper_write_flow(self, academic_ai_cls, graph_sync_service):
        academic_ai_cls.return_value.extract_tags.return_value = ['BibTeX 瀵煎叆', '鐢诲儚鑱斿姩']

        response = self.client.post(
            '/api/achievements/papers/import/bibtex-confirm/',
            {
                'entries': [
                    {
                        'source_index': 1,
                        'citation_key': 'imported-entry',
                        'entry_type': 'article',
                        'title': 'BibTeX 瀵煎叆鍚庣殑璁烘枃',
                        'abstract': '杩欐槸涓€涓冻澶熼暱鐨勬憳瑕侊紝鐢ㄤ簬楠岃瘉 BibTeX 纭瀵煎叆浠嶇劧璧扮幇鏈夎鏂囧啓鍏ラ摼璺€?,
                        'date_acquired': '2025-05-01',
                        'paper_type': 'JOURNAL',
                        'journal_name': '鐜颁唬鏁欒偛鎶€鏈?,
                        'journal_level': '鏍稿績鏈熷垔',
                        'is_first_author': True,
                        'doi': '10.1000/imported-bibtex-paper',
                        'coauthors': ['鏉庢櫒', '鍛ㄥ€?],
                        'preview_status': 'ready',
                        'issues': [],
                    },
                    {
                        'source_index': 2,
                        'citation_key': 'invalid-entry',
                        'entry_type': 'article',
                        'title': 'x',
                        'abstract': '',
                        'date_acquired': '2025-05-01',
                        'paper_type': 'JOURNAL',
                        'journal_name': '',
                        'journal_level': '',
                        'is_first_author': True,
                        'doi': '',
                        'coauthors': [],
                        'preview_status': 'invalid',
                        'issues': ['缂哄皯鏈熷垔鍚嶇О'],
                    },
                ]
            },
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['imported_count'], 1)
        self.assertEqual(response.data['failed_count'], 1)
        self.assertEqual(Paper.objects.filter(teacher=self.user, doi='10.1000/imported-bibtex-paper').count(), 1)

        imported_paper = Paper.objects.get(teacher=self.user, doi='10.1000/imported-bibtex-paper')
        self.assertEqual(imported_paper.coauthors.count(), 2)
        graph_sync_service.sync_paper.assert_not_called()

    @patch('achievements.views.AcademicGraphSyncService')
    @patch('achievements.views.AcademicAI')
    def test_bibtex_confirm_skips_duplicate_doi_entries_instead_of_importing(self, academic_ai_cls, graph_sync_service):
        academic_ai_cls.return_value.extract_tags.return_value = ['BibTeX 瀵煎叆']

        Paper.objects.create(
            teacher=self.user,
            title='宸叉湁 DOI 璁烘枃',
            abstract='杩欐槸涓€涓冻澶熼暱鐨勬憳瑕侊紝鐢ㄤ簬楠岃瘉纭瀵煎叆鏃朵細璺宠繃閲嶅 DOI銆?,
            date_acquired='2024-01-01',
            paper_type='JOURNAL',
            journal_name='娴嬭瘯鏈熷垔',
            doi='10.1000/existing-confirm-doi',
        )

        response = self.client.post(
            '/api/achievements/papers/import/bibtex-confirm/',
            {
                'entries': [
                    {
                        'source_index': 1,
                        'citation_key': 'duplicate-entry',
                        'entry_type': 'article',
                        'title': '閲嶅 DOI 瀵煎叆璁烘枃',
                        'abstract': '杩欐槸涓€涓冻澶熼暱鐨勬憳瑕侊紝鐢ㄤ簬楠岃瘉纭瀵煎叆鏃朵細璺宠繃閲嶅 DOI銆?,
                        'date_acquired': '2025-05-01',
                        'paper_type': 'JOURNAL',
                        'journal_name': '鐜颁唬鏁欒偛鎶€鏈?,
                        'journal_level': '鏍稿績鏈熷垔',
                        'is_first_author': True,
                        'doi': '10.1000/existing-confirm-doi',
                        'coauthors': ['鏉庢櫒'],
                        'preview_status': 'duplicate',
                        'issues': ['褰撳墠璐﹀彿涓嬪凡瀛樺湪鐩稿悓 DOI 鐨勮鏂囥€?],
                    }
                ]
            },
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['imported_count'], 0)
        self.assertEqual(response.data['skipped_count'], 1)
        self.assertEqual(response.data['failed_count'], 0)
        self.assertIn('閲嶅璁板綍宸茶烦杩?, response.data['skipped_entries'][0]['issue_summary'])
        self.assertEqual(Paper.objects.filter(teacher=self.user, doi='10.1000/existing-confirm-doi').count(), 1)
        graph_sync_service.sync_paper.assert_not_called()

    @patch('achievements.views.AcademicGraphSyncService')
    @patch('achievements.views.AcademicAI')
    def test_teacher_can_complete_full_achievement_entry_flow(self, academic_ai_cls, graph_sync_service):
        academic_ai_cls.return_value.extract_tags.return_value = ['绉戠爺鐢诲儚', '鐭ヨ瘑鍥捐氨']

        paper_response = self.client.post(
            '/api/achievements/papers/',
            {
                'title': '鏁欏笀鎴愭灉鍏ㄩ摼璺不鐞嗙爺绌?,
                'abstract': '鏈枃浠庢垚鏋滃綍鍏ャ€佺敾鍍忓缓妯″拰鍥捐氨鑱斿姩涓変釜灞傞潰楠岃瘉鏁欏笀绉戠爺鐢诲儚绯荤粺鐨勫彲鐢ㄦ€с€?,
                'date_acquired': '2025-04-01',
                'paper_type': 'JOURNAL',
                'journal_name': '杞欢瀵煎垔',
                'journal_level': '鏍稿績鏈熷垔',
                'is_first_author': True,
                'doi': '10.1000/teacher-100004-full-flow',
                'coauthors': ['鍚存'],
            },
            format='json',
        )
        project_response = self.client.post(
            '/api/achievements/projects/',
            {
                'title': '鏁欏笀绉戠爺鐢诲儚鍏抽敭鎶€鏈爺绌?,
                'date_acquired': '2025-01-10',
                'level': 'PROVINCIAL',
                'role': 'PI',
                'funding_amount': '25.00',
                'status': 'ONGOING',
            },
            format='json',
        )
        ip_response = self.client.post(
            '/api/achievements/intellectual-properties/',
            {
                'title': '鏁欏笀鐢诲儚鍒嗘瀽绯荤粺',
                'date_acquired': '2025-02-11',
                'ip_type': 'SOFTWARE_COPYRIGHT',
                'registration_number': '2025SR100004',
                'is_transformed': False,
            },
            format='json',
        )
        service_response = self.client.post(
            '/api/achievements/academic-services/',
            {
                'title': '浜哄伐鏅鸿兘璁哄潧鐗归個鎶ュ憡',
                'date_acquired': '2025-03-03',
                'service_type': 'INVITED_TALK',
                'organization': '涓浗璁＄畻鏈哄浼?,
            },
            format='json',
        )

        self.assertEqual(paper_response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(project_response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(ip_response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(service_response.status_code, status.HTTP_201_CREATED)

        self.assertEqual(Paper.objects.filter(teacher_id=100004).count(), 1)
        self.assertEqual(Project.objects.filter(teacher_id=100004).count(), 1)
        self.assertEqual(IntellectualProperty.objects.filter(teacher_id=100004).count(), 1)
        self.assertEqual(AcademicService.objects.filter(teacher_id=100004).count(), 1)

        graph_sync_service.sync_paper.assert_not_called()
        graph_sync_service.sync_project.assert_not_called()
        graph_sync_service.sync_intellectual_property.assert_not_called()
        graph_sync_service.sync_academic_service.assert_not_called()

    @patch('achievements.views.AcademicGraphSyncService')
    def test_new_achievement_types_are_listed_for_current_teacher_only(self, graph_sync_service):
        project = Project.objects.create(
            teacher=self.user,
            title='椤圭洰 A',
            date_acquired='2025-01-10',
            level='PROVINCIAL',
            role='PI',
            funding_amount='25.00',
            status='ONGOING',
        )
        Project.objects.create(
            teacher=self.other_user,
            title='椤圭洰 B',
            date_acquired='2025-01-11',
            level='NATIONAL',
            role='CO_PI',
            funding_amount='10.00',
            status='ONGOING',
        )
        IntellectualProperty.objects.create(
            teacher=self.user,
            title='鐭ヨ瘑浜ф潈 A',
            date_acquired='2025-02-11',
            ip_type='SOFTWARE_COPYRIGHT',
            registration_number='IP-100004',
            is_transformed=True,
        )
        IntellectualProperty.objects.create(
            teacher=self.other_user,
            title='鐭ヨ瘑浜ф潈 B',
            date_acquired='2025-02-12',
            ip_type='PATENT_INVENTION',
            registration_number='IP-100005',
            is_transformed=False,
        )
        AcademicService.objects.create(
            teacher=self.user,
            title='瀛︽湳鏈嶅姟 A',
            date_acquired='2025-03-03',
            service_type='EDITOR',
            organization='涓浗璁＄畻鏈哄浼?,
        )
        AcademicService.objects.create(
            teacher=self.other_user,
            title='瀛︽湳鏈嶅姟 B',
            date_acquired='2025-03-04',
            service_type='REVIEWER',
            organization='涓浗浜哄伐鏅鸿兘瀛︿細',
        )

        projects_response = self.client.get('/api/achievements/projects/')
        ips_response = self.client.get('/api/achievements/intellectual-properties/')
        services_response = self.client.get('/api/achievements/academic-services/')

        self.assertEqual(projects_response.status_code, status.HTTP_200_OK)
        self.assertEqual(ips_response.status_code, status.HTTP_200_OK)
        self.assertEqual(services_response.status_code, status.HTTP_200_OK)

        self.assertEqual([item['title'] for item in projects_response.data], [project.title])
        self.assertEqual([item['title'] for item in ips_response.data], ['鐭ヨ瘑浜ф潈 A'])
        self.assertEqual([item['title'] for item in services_response.data], ['瀛︽湳鏈嶅姟 A'])

    @patch('achievements.views.AcademicGraphSyncService')
    def test_new_achievement_types_can_be_deleted_and_sync_graph_cleanup(self, graph_sync_service):
        project = Project.objects.create(
            teacher=self.user,
            title='寰呭垹闄ら」鐩?,
            date_acquired='2025-01-10',
            level='PROVINCIAL',
            role='PI',
            funding_amount='25.00',
            status='ONGOING',
        )
        ip_record = IntellectualProperty.objects.create(
            teacher=self.user,
            title='寰呭垹闄ょ煡璇嗕骇鏉?,
            date_acquired='2025-02-11',
            ip_type='SOFTWARE_COPYRIGHT',
            registration_number='DEL-IP-100004',
            is_transformed=False,
        )
        service = AcademicService.objects.create(
            teacher=self.user,
            title='寰呭垹闄ゅ鏈湇鍔?,
            date_acquired='2025-03-03',
            service_type='INVITED_TALK',
            organization='涓浗璁＄畻鏈哄浼?,
        )

        project_response = self.client.delete(f'/api/achievements/projects/{project.id}/')
        ip_response = self.client.delete(f'/api/achievements/intellectual-properties/{ip_record.id}/')
        service_response = self.client.delete(f'/api/achievements/academic-services/{service.id}/')

        self.assertEqual(project_response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertEqual(ip_response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertEqual(service_response.status_code, status.HTTP_204_NO_CONTENT)

        self.assertFalse(Project.objects.filter(id=project.id).exists())
        self.assertFalse(IntellectualProperty.objects.filter(id=ip_record.id).exists())
        self.assertFalse(AcademicService.objects.filter(id=service.id).exists())

        graph_sync_service.delete_project.assert_called_once_with(project.id)
        graph_sync_service.delete_intellectual_property.assert_called_once_with(ip_record.id)
        graph_sync_service.delete_academic_service.assert_called_once_with(service.id)

    def test_dashboard_stats_includes_multi_achievement_overview_and_recent_items(self):
        Paper.objects.create(
            teacher=self.user,
            title='鐢诲儚璁烘枃',
            abstract='杩欐槸涓€涓冻澶熼暱鐨勬憳瑕侊紝鐢ㄤ簬楠岃瘉鐢诲儚棣栭〉鑱氬悎涓嶄細鍙緷璧栧崟涓€璁烘枃鍗＄墖銆?,
            date_acquired='2025-04-01',
            paper_type='JOURNAL',
            journal_name='杞欢瀵煎垔',
            status='APPROVED',
        )
        Project.objects.create(
            teacher=self.user,
            title='鐢诲儚椤圭洰',
            date_acquired='2025-03-10',
            level='PROVINCIAL',
            role='PI',
            funding_amount='18.00',
            project_status='ONGOING',
            status='APPROVED',
        )
        IntellectualProperty.objects.create(
            teacher=self.user,
            title='鐢诲儚鐭ヨ瘑浜ф潈',
            date_acquired='2025-03-12',
            ip_type='SOFTWARE_COPYRIGHT',
            registration_number='PORTRAIT-IP-001',
            is_transformed=True,
            status='APPROVED',
        )
        AcademicService.objects.create(
            teacher=self.user,
            title='鐢诲儚瀛︽湳鏈嶅姟',
            date_acquired='2025-03-18',
            service_type='EDITOR',
            organization='涓浗璁＄畻鏈哄浼?,
            status='APPROVED',
        )

        response = self.client.get('/api/achievements/dashboard-stats/')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['achievement_overview']['paper_count'], 1)
        self.assertEqual(response.data['achievement_overview']['project_count'], 1)
        self.assertEqual(response.data['achievement_overview']['intellectual_property_count'], 1)
        self.assertEqual(response.data['achievement_overview']['academic_service_count'], 1)
        self.assertEqual(response.data['achievement_overview']['total_achievements'], 4)
        self.assertTrue(any(item['type'] == 'project' for item in response.data['recent_achievements']))
        self.assertTrue(any(item['type'] == 'intellectual_property' for item in response.data['recent_achievements']))
        self.assertTrue(response.data['dimension_trend'])
        self.assertTrue(response.data['recent_structure'])
        self.assertIn('overview', response.data['portrait_explanation'])
        self.assertIn('snapshot_boundary_note', response.data['portrait_explanation'])
        self.assertTrue(any(item['key'] == 'academic_output' for item in response.data['dimension_insights']))
        self.assertIn('source_note', response.data['data_meta'])
        self.assertEqual(response.data['data_meta']['acceptance_scope'], '鏈兘鍔涚撼鍏ュ綋鍓嶉樁娈甸獙鏀躲€?)

    def test_all_achievements_endpoint_returns_representative_first_and_then_by_date(self):
        Paper.objects.create(
            teacher=self.user,
            title='浠ｈ〃浣滆鏂?,
            abstract='鐢ㄤ簬楠岃瘉鍏ㄩ儴鎴愭灉鎺ュ彛鐨勪唬琛ㄤ綔鎺掑簭銆?,
            date_acquired='2024-03-01',
            paper_type='JOURNAL',
            journal_name='娴嬭瘯鏈熷垔',
            is_first_author=True,
            is_representative=True,
            status='APPROVED',
        )
        Paper.objects.create(
            teacher=self.user,
            title='鏅€氳鏂?,
            abstract='鐢ㄤ簬楠岃瘉闈炰唬琛ㄤ綔鎺掑簭銆?,
            date_acquired='2025-01-15',
            paper_type='JOURNAL',
            journal_name='娴嬭瘯鏈熷垔',
            is_first_author=False,
            is_representative=False,
            status='APPROVED',
        )
        Project.objects.create(
            teacher=self.user,
            title='绉戠爺椤圭洰A',
            date_acquired='2024-12-20',
            level='PROVINCIAL',
            role='PI',
            funding_amount='18.00',
            project_status='ONGOING',
            status='APPROVED',
        )

        response = self.client.get(f'/api/achievements/all-achievements/{self.user.id}/')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['teacher_id'], self.user.id)
        self.assertEqual(response.data['achievement_total'], 3)
        self.assertEqual(response.data['records'][0]['title'], '浠ｈ〃浣滆鏂?)
        self.assertEqual(response.data['records'][0]['is_representative'], True)
        self.assertEqual(response.data['records'][1]['title'], '鏅€氳鏂?)
        self.assertEqual(response.data['records'][1]['author_rank_category'], 'participating')
        self.assertEqual(response.data['records'][2]['title'], '绉戠爺椤圭洰A')
        self.assertEqual(response.data['records'][2]['type_label'], '绉戠爺椤圭洰')

    def test_radar_endpoint_returns_dimension_sources(self):
        Paper.objects.create(
            teacher=self.user,
            title='闆疯揪璁烘枃',
            abstract='杩欐槸涓€涓冻澶熼暱鐨勬憳瑕侊紝鐢ㄤ簬楠岃瘉闆疯揪鑳藉姏缁村害鏉ユ簮璇存槑鎺ュ彛杩斿洖缁撴瀯銆?,
            date_acquired='2025-04-01',
            paper_type='JOURNAL',
            journal_name='娴嬭瘯鏈熷垔',
        )
        Project.objects.create(
            teacher=self.user,
            title='闆疯揪椤圭洰',
            date_acquired='2025-03-10',
            level='PROVINCIAL',
            role='PI',
            funding_amount='12.00',
            status='ONGOING',
        )

        response = self.client.get(f'/api/achievements/radar/{self.user.id}/')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['radar_dimensions']), 5)
        self.assertEqual(len(response.data['dimension_sources']), 5)
        self.assertEqual(len(response.data['dimension_insights']), 5)
        self.assertTrue(any(item['name'] == '缁忚垂涓庨」鐩敾鍏? for item in response.data['dimension_sources']))
        self.assertTrue(any(item['level'] in ['浼樺娍缁村害', '绋冲畾缁村害', '鎴愰暱缁村害'] for item in response.data['dimension_insights']))

    def test_admin_can_view_dashboard_stats_for_specified_teacher(self):
        user_model = get_user_model()
        admin = user_model.objects.create_superuser(
            id=1,
            username='admin',
            password='Admin123456',
            real_name='绯荤粺绠＄悊鍛?,
        )
        Paper.objects.create(
            teacher=self.user,
            title='绠＄悊鍛樿瑙掕鏂?,
            abstract='杩欐槸涓€涓冻澶熼暱鐨勬憳瑕侊紝鐢ㄤ簬楠岃瘉绠＄悊鍛樻煡鐪嬫寚瀹氭暀甯堢敾鍍忔椂鐨勮仛鍚堢粨鏋溿€?,
            date_acquired='2025-04-01',
            paper_type='JOURNAL',
            journal_name='娴嬭瘯鏈熷垔',
            status='APPROVED',
        )

        self.client.force_authenticate(user=admin)
        response = self.client.get('/api/achievements/dashboard-stats/', {'user_id': self.user.id})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['achievement_overview']['paper_count'], 1)
        self.assertEqual(response.data['achievement_overview']['total_achievements'], 1)

    def test_admin_can_list_papers_for_specified_teacher(self):
        user_model = get_user_model()
        admin = user_model.objects.create_superuser(
            id=1,
            username='admin',
            password='Admin123456',
            real_name='绯荤粺绠＄悊鍛?,
        )
        Paper.objects.create(
            teacher=self.user,
            title='绠＄悊鍛樻煡鐪嬬殑璁烘枃',
            abstract='杩欐槸涓€涓冻澶熼暱鐨勬憳瑕侊紝鐢ㄤ簬楠岃瘉绠＄悊鍛樺彲浠ユ寜鏁欏笀杩囨护璁烘枃鍒楄〃銆?,
            date_acquired='2025-04-01',
            paper_type='JOURNAL',
            journal_name='娴嬭瘯鏈熷垔',
        )
        Paper.objects.create(
            teacher=self.other_user,
            title='鍏朵粬鏁欏笀鐨勮鏂?,
            abstract='杩欐槸鍙︿竴涓冻澶熼暱鐨勬憳瑕侊紝鐢ㄤ簬楠岃瘉 teacher_id 杩囨护鍙繑鍥炵洰鏍囨暀甯堟暟鎹€?,
            date_acquired='2025-04-02',
            paper_type='CONFERENCE',
            journal_name='娴嬭瘯浼氳',
        )

        self.client.force_authenticate(user=admin)
        response = self.client.get('/api/achievements/papers/', {'teacher_id': self.user.id})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['teacher'], self.user.id)
        self.assertEqual(response.data[0]['title'], '绠＄悊鍛樻煡鐪嬬殑璁烘枃')

    @patch('achievements.views.AcademicGraphSyncService')
    @patch('achievements.views.AcademicAI')
    def test_admin_cannot_create_update_or_delete_teacher_paper_via_teacher_self_service_endpoint(
        self,
        academic_ai_cls,
        graph_sync_service,
    ):
        academic_ai_cls.return_value.extract_tags.return_value = []
        user_model = get_user_model()
        admin = user_model.objects.create_superuser(
            id=1,
            username='admin',
            password='Admin123456',
            real_name='绯荤粺绠＄悊鍛?,
        )
        paper = Paper.objects.create(
            teacher=self.user,
            title='鏁欏笀鑷姪鎴愭灉',
            abstract='杩欐槸涓€涓冻澶熼暱鐨勬憳瑕侊紝鐢ㄤ簬楠岃瘉绠＄悊鍛樹笉鑳介€氳繃鏁欏笀鎴愭灉鑷姪鍏ュ彛浠ｆ浛鏁欏笀缁存姢鎴愭灉銆?,
            date_acquired='2025-01-01',
            paper_type='JOURNAL',
            journal_name='娴嬭瘯鏈熷垔',
            doi='10.1000/teacher-self-service-paper',
        )

        self.client.force_authenticate(user=admin)
        create_response = self.client.post(
            '/api/achievements/papers/',
            {
                'title': '绠＄悊鍛樿秺鏉冩柊澧炶鏂?,
                'abstract': '杩欐槸涓€涓冻澶熼暱鐨勬憳瑕侊紝鐢ㄤ簬楠岃瘉绠＄悊鍛樹笉鑳介€氳繃鏁欏笀鑷姪鍏ュ彛鏂板鎴愭灉銆?,
                'date_acquired': '2025-02-01',
                'paper_type': 'JOURNAL',
                'journal_name': '娴嬭瘯鏈熷垔',
                'doi': '10.1000/admin-create-denied',
                'coauthors': [],
            },
            format='json',
        )
        update_response = self.client.patch(
            f'/api/achievements/papers/{paper.id}/',
            {
                'title': '绠＄悊鍛樿秺鏉冧慨鏀?,
                'abstract': '杩欐槸涓€涓冻澶熼暱鐨勬憳瑕侊紝鐢ㄤ簬楠岃瘉绠＄悊鍛樹笉鑳介€氳繃鏁欏笀鑷姪鍏ュ彛淇敼鎴愭灉銆?,
                'date_acquired': '2025-01-03',
                'paper_type': 'JOURNAL',
                'journal_name': '娴嬭瘯鏈熷垔',
                'doi': '10.1000/teacher-self-service-paper',
                'coauthors': [],
            },
            format='json',
        )
        delete_response = self.client.delete(f'/api/achievements/papers/{paper.id}/')

        self.assertEqual(create_response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(update_response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(delete_response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(create_response.data['detail'], '鎴愭灉褰曞叆鍜岀淮鎶や粎闄愭暀甯堟湰浜烘搷浣滐紝绠＄悊鍛樺綋鍓嶄粎鍙煡鐪嬩笌楠岃瘉銆?)
        self.assertTrue(Paper.objects.filter(id=paper.id).exists())
        self.assertEqual(Paper.objects.filter(doi='10.1000/admin-create-denied').count(), 0)
        graph_sync_service.sync_paper.assert_not_called()
        graph_sync_service.delete_paper.assert_not_called()

    def test_non_admin_cannot_access_academy_overview_dashboard(self):
        response = self.client.get('/api/achievements/academy-overview/')

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_admin_can_access_academy_overview_dashboard(self):
        user_model = get_user_model()
        admin = user_model.objects.create_superuser(
            id=1,
            username='admin',
            password='Admin123456',
            real_name='绯荤粺绠＄悊鍛?,
        )

        Paper.objects.create(
            teacher=self.user,
            title='瀛﹂櫌鐪嬫澘璁烘枃',
            abstract='杩欐槸涓€涓冻澶熼暱鐨勬憳瑕侊紝鐢ㄤ簬楠岃瘉瀛﹂櫌绾х粺璁＄湅鏉跨殑璁烘枃鑱氬悎鍜岃秼鍔胯绠椼€?,
            date_acquired='2025-04-01',
            paper_type='JOURNAL',
            journal_name='娴嬭瘯鏈熷垔',
            status='APPROVED',
        )
        Project.objects.create(
            teacher=self.user,
            title='瀛﹂櫌鐪嬫澘椤圭洰',
            date_acquired='2025-03-10',
            level='PROVINCIAL',
            role='PI',
            funding_amount='12.00',
            project_status='ONGOING',
            status='APPROVED',
        )

        self.client.force_authenticate(user=admin)
        response = self.client.get('/api/achievements/academy-overview/')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['statistics']), 5)
        self.assertTrue(response.data['yearly_trend'])
        self.assertTrue(response.data['department_distribution'])
        self.assertTrue(response.data['top_active_teachers'])
        self.assertIn('collaboration_overview', response.data)
        self.assertIn('data_meta', response.data)
        self.assertIn('filter_options', response.data)
        self.assertIn('active_filters', response.data)
        self.assertIn('trend_summary', response.data)
        self.assertIn('comparison_summary', response.data)
        self.assertIn('realtime_metrics', response.data['data_meta'])
        self.assertIn('offline_candidate_metrics', response.data['data_meta'])

    @patch('achievements.views.AcademicGraphSyncService')
    @patch('achievements.views.AcademicAI')
    def test_teacher_can_search_and_update_paper_records(self, academic_ai_cls, graph_sync_service):
        academic_ai_cls.return_value.extract_tags.return_value = ['绉戠爺鐢诲儚']

        paper = Paper.objects.create(
            teacher=self.user,
            title='寰呮洿鏂拌鏂?,
            abstract='杩欐槸涓€涓冻澶熼暱鐨勬憳瑕侊紝鐢ㄤ簬楠岃瘉璁烘枃缂栬緫鍜屾悳绱㈤摼璺湪绗簩杞紑鍙戝悗浠嶅彲姝ｅ父浣跨敤銆?,
            date_acquired='2025-01-01',
            paper_type='JOURNAL',
            journal_name='鏁欒偛鎶€鏈爺绌?,
            doi='10.1000/paper-edit-search',
        )
        Paper.objects.create(
            teacher=self.user,
            title='鏃犲叧璁烘枃',
            abstract='杩欐槸鍙︿竴涓冻澶熼暱鐨勬憳瑕侊紝鐢ㄤ簬楠岃瘉鎼滅储缁撴灉浼氭寜鍏抽敭璇嶈繃婊ゃ€?,
            date_acquired='2025-01-02',
            paper_type='CONFERENCE',
            journal_name='娴嬭瘯浼氳',
            doi='10.1000/paper-search-other',
        )

        update_response = self.client.patch(
            f'/api/achievements/papers/{paper.id}/',
            {
                'title': '宸叉洿鏂拌鏂?,
                'abstract': '杩欐槸涓€涓冻澶熼暱鐨勬憳瑕侊紝鐢ㄤ簬楠岃瘉璁烘枃缂栬緫鍦ㄥ綋鍓嶆暀甯堝悕涓嬪彲浠ユ纭洿鏂般€?,
                'date_acquired': '2025-01-03',
                'paper_type': 'CONFERENCE',
                'journal_name': '鏁欒偛鎶€鏈鍧?,
                'journal_level': 'CCF-C',
                'is_first_author': False,
                'doi': '10.1000/paper-edit-search',
                'coauthors': ['鏉庢櫒'],
            },
            format='json',
        )
        search_response = self.client.get('/api/achievements/papers/', {'search': '宸叉洿鏂?})

        self.assertEqual(update_response.status_code, status.HTTP_200_OK)
        paper.refresh_from_db()
        self.assertEqual(paper.title, '宸叉洿鏂拌鏂?)
        self.assertEqual(paper.paper_type, 'CONFERENCE')
        self.assertEqual(paper.coauthors.count(), 1)

        self.assertEqual(search_response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(search_response.data), 1)
        self.assertEqual(search_response.data[0]['title'], '宸叉洿鏂拌鏂?)

    def test_teacher_can_filter_sort_and_summarize_papers(self):
        Paper.objects.create(
            teacher=self.user,
            title='浠ｈ〃浣滆鏂?,
            abstract='杩欐槸涓€涓冻澶熼暱鐨勬憳瑕侊紝鐢ㄤ簬楠岃瘉鎴愭灉涓績鏀寔浠ｈ〃浣滅瓫閫夈€佺粺璁″拰杩戝勾鎴愭灉灞曠ず銆?,
            date_acquired='2026-02-01',
            paper_type='JOURNAL',
            journal_name='娴嬭瘯鏈熷垔 A',
            journal_level='SCI',
            pages='1-8',
            source_url='https://example.com/a',
            is_representative=True,
            doi='10.1000/summary-a',
        )
        Paper.objects.create(
            teacher=self.user,
            title='鏅€氳鏂?,
            abstract='杩欐槸鍙︿竴涓冻澶熼暱鐨勬憳瑕侊紝鐢ㄤ簬楠岃瘉鎸夊勾浠借繃婊ゅ拰鍏冩暟鎹己澶辩粺璁°€?,
            date_acquired='2024-05-10',
            paper_type='CONFERENCE',
            journal_name='娴嬭瘯浼氳 B',
            doi='',
        )
        Paper.objects.create(
            teacher=self.user,
            title='楂樿寮曡鏂?,
            abstract='杩欐槸绗笁涓冻澶熼暱鐨勬憳瑕侊紝鐢ㄤ簬楠岃瘉浠ｈ〃浣滀紭鍏堟帓搴忋€?,
            date_acquired='2025-06-01',
            paper_type='JOURNAL',
            journal_name='娴嬭瘯鏈熷垔 C',
            journal_level='鏍稿績鏈熷垔',
            pages='33-40',
            source_url='https://example.com/c',
            doi='10.1000/summary-c',
        )

        representative_response = self.client.get(
            '/api/achievements/papers/',
            {'is_representative': 'true', 'sort_by': 'representative_desc'},
        )
        yearly_response = self.client.get('/api/achievements/papers/', {'year': 2024})
        summary_response = self.client.get('/api/achievements/papers/summary/')

        self.assertEqual(representative_response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(representative_response.data), 1)
        self.assertEqual(representative_response.data[0]['title'], '浠ｈ〃浣滆鏂?)

        self.assertEqual(yearly_response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(yearly_response.data), 1)
        self.assertEqual(yearly_response.data[0]['title'], '鏅€氳鏂?)

        self.assertEqual(summary_response.status_code, status.HTTP_200_OK)
        self.assertEqual(summary_response.data['total_count'], 3)
        self.assertEqual(summary_response.data['representative_count'], 1)
        self.assertEqual(summary_response.data['missing_doi_count'], 1)
        self.assertTrue(any(item['paper_type'] == 'JOURNAL' for item in summary_response.data['type_distribution']))
        self.assertTrue(any(item['year'] == 2026 for item in summary_response.data['yearly_distribution']))
        self.assertEqual(summary_response.data['recent_records'][0]['title'], '浠ｈ〃浣滆鏂?)

    @patch('achievements.views.AcademicGraphSyncService')
    def test_teacher_can_search_projects_by_title_or_status(self, graph_sync_service):
        Project.objects.create(
            teacher=self.user,
            title='鐢诲儚骞冲彴浜屾湡椤圭洰',
            date_acquired='2025-02-01',
            level='PROVINCIAL',
            role='PI',
            funding_amount='12.00',
            status='ONGOING',
        )
        Project.objects.create(
            teacher=self.user,
            title='宸茬粨棰橀」鐩?,
            date_acquired='2025-02-02',
            level='NATIONAL',
            role='CO_PI',
            funding_amount='18.00',
            status='COMPLETED',
        )

        response = self.client.get('/api/achievements/projects/', {'search': 'ONGOING'})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['title'], '鐢诲儚骞冲彴浜屾湡椤圭洰')

    def test_admin_can_filter_academy_dashboard_by_department_and_year(self):
        user_model = get_user_model()
        admin = user_model.objects.create_superuser(
            id=1,
            username='admin',
            password='Admin123456',
            real_name='绯荤粺绠＄悊鍛?,
        )
        teacher_in_scope = user_model.objects.create_user(
            id=100090,
            username='100090',
            password='teacher123456',
            real_name='闄㈢郴鍐呮暀甯?,
            department='浜哄伐鏅鸿兘瀛﹂櫌',
            title='璁插笀',
        )
        teacher_out_scope = user_model.objects.create_user(
            id=100091,
            username='100091',
            password='teacher123456',
            real_name='闄㈢郴澶栨暀甯?,
            department='璁＄畻鏈哄闄?,
            title='璁插笀',
        )

        Paper.objects.create(
            teacher=teacher_in_scope,
            title='2025 骞撮櫌绯诲唴璁烘枃',
            abstract='杩欐槸涓€涓冻澶熼暱鐨勬憳瑕侊紝鐢ㄤ簬楠岃瘉瀛﹂櫌鐪嬫澘鏀寔鎸夐櫌绯诲拰骞翠唤杩囨护銆?,
            date_acquired='2025-03-01',
            paper_type='JOURNAL',
            journal_name='娴嬭瘯鏈熷垔',
            status='APPROVED',
        )
        Paper.objects.create(
            teacher=teacher_out_scope,
            title='2024 骞撮櫌绯诲璁烘枃',
            abstract='杩欐槸鍙︿竴涓冻澶熼暱鐨勬憳瑕侊紝鐢ㄤ簬楠岃瘉杩囨护鏉′欢涓嶄細璇寘鍚叾浠栨暀甯堟暟鎹€?,
            date_acquired='2024-03-01',
            paper_type='JOURNAL',
            journal_name='娴嬭瘯鏈熷垔',
            status='APPROVED',
        )

        self.client.force_authenticate(user=admin)
        response = self.client.get(
            '/api/achievements/academy-overview/',
            {'department': '浜哄伐鏅鸿兘瀛﹂櫌', 'year': 2025},
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['active_filters']['department'], '浜哄伐鏅鸿兘瀛﹂櫌')
        self.assertEqual(response.data['active_filters']['year'], 2025)
        self.assertEqual(response.data['statistics'][1]['value'], 1)
        self.assertEqual(len(response.data['top_active_teachers']), 1)
        self.assertEqual(response.data['top_active_teachers'][0]['user_id'], teacher_in_scope.id)

    def test_academy_dashboard_includes_extended_filter_and_ranking_fields(self):
        user_model = get_user_model()
        admin = user_model.objects.create_superuser(
            id=2,
            username='admin2',
            password='Admin123456',
            real_name='绯荤粺绠＄悊鍛樹簩鍙?,
        )
        teacher = user_model.objects.create_user(
            id=100092,
            username='100092',
            password='teacher123456',
            real_name='鍚堜綔鏁欏笀',
            department='浜哄伐鏅鸿兘瀛﹂櫌',
            title='鍓暀鎺?,
        )
        paper = Paper.objects.create(
            teacher=teacher,
            title='鍚堜綔璁烘枃',
            abstract='杩欐槸涓€涓冻澶熼暱鐨勬憳瑕侊紝鐢ㄤ簬楠岃瘉瀛﹂櫌鐪嬫澘鎵╁睍瀛楁淇濇寔绋冲畾杩斿洖銆?,
            date_acquired='2025-06-01',
            paper_type='JOURNAL',
            journal_name='娴嬭瘯鏈熷垔',
            status='APPROVED',
        )
        paper.coauthors.create(name='鏍″鍚堜綔鑰?)

        self.client.force_authenticate(user=admin)
        response = self.client.get('/api/achievements/academy-overview/', {'teacher_title': '鍓暀鎺?, 'has_collaboration': 'true'})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['active_filters']['teacher_title'], '鍓暀鎺?)
        self.assertTrue(response.data['active_filters']['has_collaboration'])
        self.assertIn('teacher_titles', response.data['filter_options'])
        self.assertIn('department_breakdown', response.data)
        self.assertIn('latest_active_year', response.data['top_active_teachers'][0])

    def test_academy_dashboard_supports_drilldown_rank_switch_and_comparison_trend(self):
        user_model = get_user_model()
        admin = user_model.objects.create_superuser(
            id=3,
            username='admin3',
            password='Admin123456',
            real_name='绯荤粺绠＄悊鍛樹笁鍙?,
        )
        teacher_a = user_model.objects.create_user(
            id=100093,
            username='100093',
            password='teacher123456',
            real_name='楂樿寮曟暀甯?,
            department='浜哄伐鏅鸿兘瀛﹂櫌',
            title='鏁欐巿',
        )
        teacher_b = user_model.objects.create_user(
            id=100094,
            username='100094',
            password='teacher123456',
            real_name='椤圭洰鏁欏笀',
            department='浜哄伐鏅鸿兘瀛﹂櫌',
            title='鏁欐巿',
        )

        paper_a = Paper.objects.create(
            teacher=teacher_a,
            title='楂樿寮曡鏂?,
            abstract='杩欐槸涓€涓冻澶熼暱鐨勬憳瑕侊紝鐢ㄤ簬楠岃瘉瀛﹂櫌鐪嬫澘鏀寔鎸夊紩鐢ㄦ帓琛屽拰鏁欏笀閽诲彇銆?,
            date_acquired='2025-05-01',
            paper_type='JOURNAL',
            journal_name='娴嬭瘯鏈熷垔',
            status='APPROVED',
        )
        paper_a.coauthors.create(name='鍚堜綔浣滆€呯敳')
        Paper.objects.create(
            teacher=teacher_a,
            title='涓婁竴骞磋鏂?,
            abstract='杩欐槸鍙︿竴涓冻澶熼暱鐨勬憳瑕侊紝鐢ㄤ簬褰㈡垚鑼冨洿瀵规瘮瓒嬪娍銆?,
            date_acquired='2024-05-01',
            paper_type='JOURNAL',
            journal_name='娴嬭瘯鏈熷垔',
            status='APPROVED',
        )
        Project.objects.create(
            teacher=teacher_b,
            title='閲嶇偣椤圭洰',
            date_acquired='2025-06-01',
            level='PROVINCIAL',
            role='PI',
            funding_amount='20.00',
            project_status='ONGOING',
            status='APPROVED',
        )

        self.client.force_authenticate(user=admin)
        response = self.client.get(
            '/api/achievements/academy-overview/',
            {
                'department': '浜哄伐鏅鸿兘瀛﹂櫌',
                'teacher_id': teacher_a.id,
                'teacher_title': '鏁欐巿',
                'achievement_type': 'paper',
                'rank_by': 'achievement_total',
                'has_collaboration': 'true',
            },
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['active_filters']['achievement_type'], 'paper')
        self.assertEqual(response.data['active_filters']['rank_by'], 'achievement_total')
        self.assertTrue(response.data['active_filters']['has_collaboration'])
        self.assertIn('achievement_types', response.data['filter_options'])
        self.assertIn('ranking_modes', response.data['filter_options'])
        self.assertTrue(response.data['comparison_trend'])
        self.assertEqual(response.data['ranking_meta']['current_rank_by'], 'achievement_total')
        self.assertEqual(response.data['top_active_teachers'][0]['rank_label'], '鎬绘垚鏋?)
        self.assertIn('selected_department_summary', response.data['drilldown'])
        self.assertIn('selected_teacher_summary', response.data['drilldown'])
        self.assertEqual(response.data['drilldown']['selected_teacher_summary']['user_id'], teacher_a.id)
        self.assertTrue(response.data['drilldown']['teacher_recent_achievements'])

    def test_academy_dashboard_export_returns_csv_for_selected_target(self):
        user_model = get_user_model()
        admin = user_model.objects.create_superuser(
            id=4,
            username='admin4',
            password='Admin123456',
            real_name='绯荤粺绠＄悊鍛樺洓鍙?,
        )
        teacher = user_model.objects.create_user(
            id=100095,
            username='100095',
            password='teacher123456',
            real_name='瀵煎嚭鏁欏笀',
            department='浜哄伐鏅鸿兘瀛﹂櫌',
            title='璁插笀',
        )
        Paper.objects.create(
            teacher=teacher,
            title='瀵煎嚭璁烘枃',
            abstract='杩欐槸涓€涓冻澶熼暱鐨勬憳瑕侊紝鐢ㄤ簬楠岃瘉瀛﹂櫌绾х湅鏉垮鍑哄寮洪摼璺€?,
            date_acquired='2025-07-01',
            paper_type='JOURNAL',
            journal_name='娴嬭瘯鏈熷垔',
        )

        self.client.force_authenticate(user=admin)
        response = self.client.get(
            '/api/achievements/academy-overview/export/',
            {'department': '浜哄伐鏅鸿兘瀛﹂櫌', 'export_target': 'departments'},
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('text/csv', response['Content-Type'])
        content = response.content.decode('utf-8')
        self.assertIn('闄㈢郴', content)
        self.assertIn('浜哄伐鏅鸿兘瀛﹂櫌', content)


class PaperGovernanceApiTests(APITestCase):
    def setUp(self):
        user_model = get_user_model()
        self.user = user_model.objects.create_user(
            id=100120,
            username='100120',
            password='teacher123456',
            real_name='鎴愭灉娌荤悊鏁欏笀',
        )
        self.client.force_authenticate(user=self.user)

    def test_bibtex_revalidate_supports_fix_after_preview(self):
        invalid_payload = {
            'entries': [
                {
                    'source_index': 1,
                    'citation_key': 'draft-entry',
                    'entry_type': 'article',
                    'title': '',
                    'abstract': '',
                    'date_acquired': '',
                    'paper_type': 'JOURNAL',
                    'journal_name': '',
                    'journal_level': '',
                    'published_volume': '',
                    'published_issue': '',
                    'pages': '',
                    'source_url': '',
                    'is_first_author': True,
                    'is_representative': False,
                    'doi': '',
                    'coauthors': [],
                    'preview_status': 'invalid',
                    'issues': [],
                    'issue_details': [],
                }
            ]
        }
        invalid_response = self.client.post('/api/achievements/papers/import/bibtex-revalidate/', invalid_payload, format='json')
        self.assertEqual(invalid_response.status_code, status.HTTP_200_OK)
        self.assertEqual(invalid_response.data['summary']['invalid_count'], 1)

        fixed_payload = invalid_payload.copy()
        fixed_payload['entries'] = [
            {
                **invalid_payload['entries'][0],
                'title': 'BibTeX 淇鍚庣殑璁烘枃',
                'journal_name': '娴嬭瘯鏈熷垔',
                'date_acquired': '2025-04-01',
                'doi': '10.1000/bibtex-revalidate',
            }
        ]
        fixed_response = self.client.post('/api/achievements/papers/import/bibtex-revalidate/', fixed_payload, format='json')
        self.assertEqual(fixed_response.status_code, status.HTTP_200_OK)
        self.assertEqual(fixed_response.data['summary']['ready_count'], 1)
        self.assertEqual(fixed_response.data['entries'][0]['preview_status'], 'ready')

    @patch('achievements.views.AcademicGraphSyncService')
    @patch('achievements.views.AcademicAI')
    def test_paper_history_governance_and_compare_endpoints_work(self, academic_ai_cls, graph_sync_service):
        academic_ai_cls.return_value.extract_tags.return_value = ['鎴愭灉娌荤悊', '鎿嶄綔鍘嗗彶']

        create_response = self.client.post(
            '/api/achievements/papers/',
            {
                'title': '娌荤悊涓昏鏂?,
                'abstract': '鐢ㄤ簬楠岃瘉娌荤悊涓績涓嬬殑鍘嗗彶璁板綍銆佸厓鏁版嵁鍛婅涓庣粨鏋勫寲瀵规瘮鎺ュ彛銆?,
                'date_acquired': '2025-04-01',
                'paper_type': 'JOURNAL',
                'journal_name': '娌荤悊鏈熷垔',
                'doi': '10.1000/governance-main',
                'coauthors': ['鏉庢櫒'],
            },
            format='json',
        )
        second_paper = Paper.objects.create(
            teacher=self.user,
            title='娌荤悊瀵规瘮璁烘枃',
            abstract='鐢ㄤ簬瀵规瘮鐨勭浜岀瘒璁烘枃锛岃ˉ榻愪簡鏇村娌荤悊瀛楁銆?,
            date_acquired='2025-05-01',
            paper_type='CONFERENCE',
            journal_name='娌荤悊浼氳',
            journal_level='CCF-B',
            pages='10-18',
            source_url='https://example.com/governance-compare',
            doi='10.1000/governance-compare',
        )

        paper_id = create_response.data['id']
        update_response = self.client.patch(
            f'/api/achievements/papers/{paper_id}/',
            {
                'title': '娌荤悊涓昏鏂囷紙淇鐗堬級',
                'abstract': '鐢ㄤ簬楠岃瘉娌荤悊涓績涓嬬殑鍘嗗彶璁板綍銆佸厓鏁版嵁鍛婅涓庣粨鏋勫寲瀵规瘮鎺ュ彛锛屽凡琛ュ厖淇璇存槑銆?,
                'date_acquired': '2025-04-02',
                'paper_type': 'JOURNAL',
                'journal_name': '娌荤悊鏈熷垔',
                'journal_level': '',
                'doi': '10.1000/governance-main',
                'coauthors': ['鏉庢櫒', '鐜嬫晱'],
            },
            format='json',
        )
        self.assertEqual(update_response.status_code, status.HTTP_200_OK)

        history_response = self.client.get(f'/api/achievements/papers/{paper_id}/history/')
        governance_response = self.client.get('/api/achievements/papers/governance/')
        compare_response = self.client.get(
            '/api/achievements/papers/compare/',
            {'left_id': paper_id, 'right_id': second_paper.id},
        )

        self.assertEqual(history_response.status_code, status.HTTP_200_OK)
        self.assertGreaterEqual(len(history_response.data['history']), 2)
        self.assertEqual(history_response.data['history'][0]['action'], 'UPDATE')
        self.assertEqual(history_response.data['history'][1]['action'], 'CREATE')

        self.assertEqual(governance_response.status_code, status.HTTP_200_OK)
        self.assertIn('summary', governance_response.data)
        self.assertIn('recent_operations', governance_response.data)
        self.assertTrue(governance_response.data['compare_candidates'])

        self.assertEqual(compare_response.status_code, status.HTTP_200_OK)
        self.assertIn('comparison_rows', compare_response.data)
        self.assertIn('summary', compare_response.data)
        self.assertEqual(compare_response.data['summary']['shared_coauthors'], [])
        graph_sync_service.sync_paper.assert_not_called()

    @patch('achievements.views.AcademicGraphSyncService')
    def test_export_representative_batch_and_cleanup_apply_work(self, graph_sync_service):
        paper_a = Paper.objects.create(
            teacher=self.user,
            title='寰呮竻娲楄鏂?A',
            abstract='鐢ㄤ簬楠岃瘉鎵归噺鏍囧噯鍖栨竻娲椾笌瀵煎嚭娌荤悊缁撴灉鐨勮鏂囪褰曘€?,
            date_acquired='2025-01-10',
            paper_type='JOURNAL',
            journal_name='瀵煎嚭鏈熷垔',
            doi=' 10.1000/NEEDS-CLEANUP ',
            source_url=' https://example.com/a ',
            pages=' 1-9 ',
        )
        paper_b = Paper.objects.create(
            teacher=self.user,
            title='寰呰繍钀ヨ鏂?B',
            abstract='鐢ㄤ簬楠岃瘉浠ｈ〃浣滄壒閲忚繍钀ヤ笌娌荤悊鏃ュ織鐢熸垚銆?,
            date_acquired='2025-02-10',
            paper_type='JOURNAL',
            journal_name='瀵煎嚭鏈熷垔',
            doi='10.1000/b',
        )

        representative_response = self.client.post(
            '/api/achievements/papers/representative/batch-update/',
            {'paper_ids': [paper_a.id, paper_b.id], 'is_representative': True},
            format='json',
        )
        cleanup_response = self.client.post(
            '/api/achievements/papers/cleanup-apply/',
            {'paper_ids': [paper_a.id], 'action': 'normalize_text_fields'},
            format='json',
        )
        export_response = self.client.get('/api/achievements/papers/export/')

        self.assertEqual(representative_response.status_code, status.HTTP_200_OK)
        self.assertEqual(representative_response.data['updated_count'], 2)
        self.assertEqual(cleanup_response.status_code, status.HTTP_200_OK)
        self.assertEqual(cleanup_response.data['updated_count'], 1)

        paper_a.refresh_from_db()
        paper_b.refresh_from_db()
        self.assertTrue(paper_a.is_representative)
        self.assertTrue(paper_b.is_representative)
        self.assertEqual(paper_a.doi, '10.1000/needs-cleanup')
        self.assertEqual(paper_a.source_url, 'https://example.com/a')
        self.assertEqual(paper_a.pages, '1-9')

        self.assertEqual(export_response.status_code, status.HTTP_200_OK)
        self.assertIn('text/csv', export_response['Content-Type'])
        self.assertIn('鏍囬', export_response.content.decode('utf-8'))
        self.assertGreaterEqual(PaperOperationLog.objects.filter(teacher=self.user).count(), 3)


class TeacherPortraitApiTests(APITestCase):
    def setUp(self):
        user_model = get_user_model()
        self.user = user_model.objects.create_user(
            id=100140,
            username='100140',
            password='teacher123456',
            real_name='鐢诲儚娣卞寲鏁欏笀',
            department='浜哄伐鏅鸿兘瀛﹂櫌',
            title='鍓暀鎺?,
        )
        self.client.force_authenticate(user=self.user)

        paper_a = Paper.objects.create(
            teacher=self.user,
            title='2024 闃舵璁烘枃',
            abstract='杩欐槸涓€涓冻澶熼暱鐨勬憳瑕侊紝鐢ㄤ簬楠岃瘉鏁欏笀鐢诲儚闃舵瀵规瘮鑳藉姏鍜岀粨鏋勫寲瑙ｉ噴瀛楁銆?,
            date_acquired='2024-04-01',
            paper_type='JOURNAL',
            journal_name='鐢诲儚鏈熷垔',
            doi='10.1000/portrait-2024',
        )
        paper_a.coauthors.create(name='闃舵鍚堜綔鑰呯敳')
        paper_b = Paper.objects.create(
            teacher=self.user,
            title='2025 闃舵璁烘枃',
            abstract='杩欐槸鍙︿竴涓冻澶熼暱鐨勬憳瑕侊紝鐢ㄤ簬楠岃瘉鏁欏笀鐢诲儚鎶ュ憡瀵煎嚭鍜岃秼鍔挎壙鎺ヨ兘鍔涖€?,
            date_acquired='2025-05-01',
            paper_type='CONFERENCE',
            journal_name='鐢诲儚浼氳',
            doi='10.1000/portrait-2025',
        )
        paper_b.coauthors.create(name='闃舵鍚堜綔鑰呬箼')

        Project.objects.create(
            teacher=self.user,
            title='鐢诲儚闃舵椤圭洰',
            date_acquired='2025-03-01',
            level='PROVINCIAL',
            role='PI',
            funding_amount='18.00',
            status='ONGOING',
        )
        IntellectualProperty.objects.create(
            teacher=self.user,
            title='鐢诲儚鍒嗘瀽杞欢',
            date_acquired='2025-02-10',
            ip_type='SOFTWARE_COPYRIGHT',
            registration_number='2025SR140000',
            is_transformed=True,
        )
        AcademicService.objects.create(
            teacher=self.user,
            title='鐢诲儚璁哄潧鎶ュ憡',
            date_acquired='2024-06-15',
            service_type='INVITED_TALK',
            organization='涓浗璁＄畻鏈哄浼?,
        )

    def test_dashboard_stats_includes_snapshot_boundary_and_stage_comparison(self):
        response = self.client.get('/api/achievements/dashboard-stats/')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('weight_spec', response.data)
        self.assertIn('calculation_summary', response.data)
        self.assertIn('stage_comparison', response.data)
        self.assertIn('snapshot_boundary', response.data)
        self.assertTrue(response.data['stage_comparison']['available'])
        self.assertEqual(response.data['snapshot_boundary']['persistence_status'], 'not_persisted')
        self.assertEqual(response.data['snapshot_boundary']['snapshot_version'], 'portrait-runtime-v1')
        self.assertEqual(response.data['snapshot_boundary']['generation_trigger'], 'dashboard_request')
        self.assertEqual(response.data['snapshot_boundary']['freeze_status'], 'response_scoped')
        self.assertTrue(response.data['stage_comparison']['structured_summary'])
        self.assertTrue(response.data['stage_comparison']['changed_dimensions'][0]['change_summary'])
        self.assertTrue(response.data['stage_comparison']['changed_dimensions'][0]['drivers'])
        self.assertIn('weight_logic_summary', response.data['portrait_explanation'])
        self.assertIn('snapshot_version_note', response.data['portrait_explanation'])

    def test_radar_endpoint_includes_weight_spec_and_calculation_summary(self):
        response = self.client.get(f'/api/achievements/radar/{self.user.id}/')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['weight_spec']), 5)
        self.assertIn('formula_note', response.data['calculation_summary'])
        self.assertIn('strongest_dimension', response.data['calculation_summary'])

    def test_portrait_report_supports_json_and_markdown_export(self):
        json_response = self.client.get(f'/api/achievements/portrait-report/{self.user.id}/')
        markdown_response = self.client.get(
            f'/api/achievements/portrait-report/{self.user.id}/',
            {'export': 'markdown'},
        )

        self.assertEqual(json_response.status_code, status.HTTP_200_OK)
        self.assertIn('report_title', json_response.data)
        self.assertTrue(json_response.data['highlights'])
        self.assertTrue(json_response.data['sections'])
        self.assertIn('snapshot_boundary', json_response.data)
        self.assertIn('snapshot_digest', json_response.data)
        self.assertEqual(json_response.data['snapshot_boundary']['generation_trigger'], 'report_request')
        self.assertEqual(json_response.data['snapshot_digest']['version'], 'portrait-runtime-v1')

        self.assertEqual(markdown_response.status_code, status.HTTP_200_OK)
        self.assertIn('text/markdown', markdown_response['Content-Type'])
        self.assertIn('鏁欏笀鐢诲儚鍒嗘瀽鎶ュ憡', markdown_response.content.decode('utf-8'))
        self.assertIn('蹇収鎽樿', markdown_response.content.decode('utf-8'))
        self.assertIn('鍙樺寲璇存槑', markdown_response.content.decode('utf-8'))


class AchievementReviewFlowApiTests(APITestCase):
    def setUp(self):
        user_model = get_user_model()
        self.system_admin = user_model.objects.create_superuser(
            id=901001,
            username='sysadmin-review',
            password='Admin123456',
            real_name='绯荤粺绠＄悊鍛樺鎵?,
            department='绉戠爺绠＄悊涓績',
        )
        self.college_admin = user_model.objects.create_user(
            id=901002,
            username='college-admin-review',
            password='Admin123456',
            real_name='瀛﹂櫌绠＄悊鍛樺鎵?,
            department='浜哄伐鏅鸿兘瀛﹂櫌',
            title='瀛﹂櫌绠＄悊鍛?,
            is_staff=True,
        )
        self.teacher = user_model.objects.create_user(
            id=901003,
            username='901003',
            password='teacher123456',
            real_name='鏈櫌鏁欏笀',
            department='浜哄伐鏅鸿兘瀛﹂櫌',
            title='璁插笀',
        )
        self.other_teacher = user_model.objects.create_user(
            id=901004,
            username='901004',
            password='teacher123456',
            real_name='澶栭櫌鏁欏笀',
            department='璁＄畻鏈哄闄?,
            title='璁插笀',
        )

    def create_paper(self, teacher, title='寰呭鏍歌鏂?, status='DRAFT'):
        return Paper.objects.create(
            teacher=teacher,
            title=title,
            abstract='杩欐槸涓€涓冻澶熼暱鐨勬憳瑕侊紝鐢ㄤ簬楠岃瘉鎴愭灉瀹℃壒娴佷笌鐗堟湰绠＄悊鍔熻兘銆?,
            date_acquired='2025-05-01',
            paper_type='JOURNAL',
            journal_name='瀹℃壒娴嬭瘯鏈熷垔',
            status=status,
        )

    def create_project(self, teacher, title='寰呭鏍搁」鐩?, status='DRAFT'):
        return Project.objects.create(
            teacher=teacher,
            title=title,
            date_acquired='2025-05-02',
            level='PROVINCIAL',
            role='PI',
            funding_amount='10.00',
            project_status='ONGOING',
            status=status,
        )

    def create_ip(self, teacher, title='寰呭鏍哥煡璇嗕骇鏉?, status='DRAFT'):
        return IntellectualProperty.objects.create(
            teacher=teacher,
            title=title,
            date_acquired='2025-05-03',
            ip_type='SOFTWARE_COPYRIGHT',
            registration_number=f'IP-{teacher.id}-{title}',
            is_transformed=False,
            status=status,
        )

    def create_service(self, teacher, title='寰呭鏍稿鏈湇鍔?, status='DRAFT'):
        return AcademicService.objects.create(
            teacher=teacher,
            title=title,
            date_acquired='2025-05-05',
            service_type='INVITED_TALK',
            organization='娴嬭瘯鏈烘瀯',
            status=status,
        )

    def test_teacher_can_submit_paper_for_review(self):
        paper = self.create_paper(self.teacher)
        self.client.force_authenticate(user=self.teacher)

        response = self.client.post(f'/api/achievements/papers/{paper.id}/submit-review/', format='json')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        paper.refresh_from_db()
        self.assertEqual(paper.status, 'PENDING_REVIEW')

    def test_teacher_create_all_achievement_types_defaults_to_pending_review(self):
        self.client.force_authenticate(user=self.teacher)

        responses = [
            self.client.post(
                '/api/achievements/papers/',
                {
                    'title': '寰呭璁烘枃',
                    'abstract': '杩欐槸涓€涓冻澶熼暱鐨勬憳瑕侊紝鐢ㄤ簬楠岃瘉棣栬疆鎻愪氦鑷姩杩涘叆寰呭鏍搞€?,
                    'date_acquired': '2025-06-01',
                    'paper_type': 'JOURNAL',
                    'journal_name': '娴嬭瘯鏈熷垔',
                    'coauthors': [],
                },
                format='json',
            ),
            self.client.post(
                '/api/achievements/projects/',
                {
                    'title': '寰呭椤圭洰',
                    'date_acquired': '2025-06-02',
                    'level': 'PROVINCIAL',
                    'role': 'PI',
                    'funding_amount': '10.00',
                    'project_status': 'ONGOING',
                },
                format='json',
            ),
            self.client.post(
                '/api/achievements/intellectual-properties/',
                {
                    'title': '寰呭鐭ヨ瘑浜ф潈',
                    'date_acquired': '2025-06-03',
                    'ip_type': 'SOFTWARE_COPYRIGHT',
                    'registration_number': 'IP-PENDING-001',
                    'is_transformed': False,
                },
                format='json',
            ),
            self.client.post(
                '/api/achievements/academic-services/',
                {
                    'title': '寰呭瀛︽湳鏈嶅姟',
                    'date_acquired': '2025-06-05',
                    'service_type': 'INVITED_TALK',
                    'organization': '娴嬭瘯鏈烘瀯',
                },
                format='json',
            ),
        ]

        for response in responses:
            self.assertEqual(response.status_code, status.HTTP_201_CREATED)
            self.assertEqual(response.data['status'], 'PENDING_REVIEW')

    def test_admin_without_teacher_id_can_list_scoped_teacher_achievements(self):
        own_college_project = self.create_project(self.teacher, title='鏈櫌椤圭洰', status='PENDING_REVIEW')
        self.create_project(self.other_teacher, title='澶栭櫌椤圭洰', status='PENDING_REVIEW')

        self.client.force_authenticate(user=self.college_admin)
        college_response = self.client.get('/api/achievements/projects/')
        self.assertEqual(college_response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(college_response.data), 1)
        self.assertEqual(college_response.data[0]['id'], own_college_project.id)

        self.client.force_authenticate(user=self.system_admin)
        system_response = self.client.get('/api/achievements/projects/')
        self.assertEqual(system_response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(system_response.data), 2)

    def test_college_admin_only_sees_pending_papers_in_own_college(self):
        self.create_paper(self.teacher, title='鏈櫌寰呭鏍?, status='PENDING_REVIEW')
        self.create_paper(self.other_teacher, title='澶栭櫌寰呭鏍?, status='PENDING_REVIEW')
        self.client.force_authenticate(user=self.college_admin)

        response = self.client.get('/api/achievements/papers/pending-review/')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['title'], '鏈櫌寰呭鏍?)

    def test_reject_requires_reason_and_logs_comment(self):
        paper = self.create_paper(self.teacher, status='PENDING_REVIEW')
        self.client.force_authenticate(user=self.college_admin)

        invalid_response = self.client.post(f'/api/achievements/papers/{paper.id}/reject/', {}, format='json')
        valid_response = self.client.post(
            f'/api/achievements/papers/{paper.id}/reject/',
            {'reason': '鏈熷垔绾у埆涓庨檮浠惰瘉鏄庝笉涓€鑷达紝璇疯ˉ鍏呰鏄庛€?},
            format='json',
        )

        self.assertEqual(invalid_response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(valid_response.status_code, status.HTTP_200_OK)
        paper.refresh_from_db()
        self.assertEqual(paper.status, 'REJECTED')

    def test_teacher_editing_approved_paper_resets_status_to_pending_review(self):
        paper = self.create_paper(self.teacher, status='APPROVED')
        self.client.force_authenticate(user=self.teacher)

        response = self.client.patch(
            f'/api/achievements/papers/{paper.id}/',
            {
                'title': '宸查€氳繃璁烘枃锛堜慨璁㈢増锛?,
                'abstract': paper.abstract,
                'date_acquired': '2025-05-01',
                'paper_type': 'JOURNAL',
                'journal_name': '瀹℃壒娴嬭瘯鏈熷垔',
                'coauthors': [],
            },
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        paper.refresh_from_db()
        self.assertEqual(paper.status, 'PENDING_REVIEW')

    def test_college_admin_can_view_pending_review_for_all_achievement_types(self):
        self.create_paper(self.teacher, title='鏈櫌寰呭鏍歌鏂?, status='PENDING_REVIEW')
        self.create_project(self.teacher, title='鏈櫌寰呭鏍搁」鐩?, status='PENDING_REVIEW')
        self.create_ip(self.teacher, title='鏈櫌寰呭鏍哥煡璇嗕骇鏉?, status='PENDING_REVIEW')
        self.create_service(self.teacher, title='鏈櫌寰呭鏍稿鏈湇鍔?, status='PENDING_REVIEW')

        self.create_project(self.other_teacher, title='澶栭櫌寰呭鏍搁」鐩?, status='PENDING_REVIEW')
        self.create_ip(self.other_teacher, title='澶栭櫌寰呭鏍哥煡璇嗕骇鏉?, status='PENDING_REVIEW')

        endpoint_map = {
            'papers': '/api/achievements/papers/pending-review/',
            'projects': '/api/achievements/projects/pending-review/',
            'intellectual_properties': '/api/achievements/intellectual-properties/pending-review/',
            'academic_services': '/api/achievements/academic-services/pending-review/',
        }

        self.client.force_authenticate(user=self.college_admin)
        results = {key: self.client.get(url) for key, url in endpoint_map.items()}

        for key, response in results.items():
            self.assertEqual(response.status_code, status.HTTP_200_OK, msg=f'{key} pending-review 鎺ュ彛鏈繑鍥?200')
            self.assertEqual(len(response.data), 1, msg=f'{key} 鏈寜瀛﹂櫌鑼冨洿杩囨护寰呭鏍稿垪琛?)

        self.assertEqual(results['papers'].data[0]['title'], '鏈櫌寰呭鏍歌鏂?)
        self.assertEqual(results['projects'].data[0]['title'], '鏈櫌寰呭鏍搁」鐩?)
        self.assertEqual(results['intellectual_properties'].data[0]['title'], '鏈櫌寰呭鏍哥煡璇嗕骇鏉?)
        self.assertEqual(results['academic_services'].data[0]['title'], '鏈櫌寰呭鏍稿鏈湇鍔?)

    def test_college_admin_can_approve_non_paper_achievements(self):
        project = self.create_project(self.teacher, status='PENDING_REVIEW')
        ip_record = self.create_ip(self.teacher, status='PENDING_REVIEW')
        service = self.create_service(self.teacher, status='PENDING_REVIEW')

        endpoint_pairs = [
            (project, f'/api/achievements/projects/{project.id}/approve/'),
            (ip_record, f'/api/achievements/intellectual-properties/{ip_record.id}/approve/'),
            (service, f'/api/achievements/academic-services/{service.id}/approve/'),
        ]

        self.client.force_authenticate(user=self.college_admin)
        for instance, endpoint in endpoint_pairs:
            response = self.client.post(endpoint, {}, format='json')
            self.assertEqual(response.status_code, status.HTTP_200_OK, msg=f'瀹℃壒閫氳繃澶辫触: {endpoint}')
            instance.refresh_from_db()
            self.assertEqual(instance.status, 'APPROVED')

    def test_college_admin_reject_requires_reason_for_non_paper_achievements(self):
        project = self.create_project(self.teacher, status='PENDING_REVIEW')
        ip_record = self.create_ip(self.teacher, status='PENDING_REVIEW')
        service = self.create_service(self.teacher, status='PENDING_REVIEW')

        endpoint_pairs = [
            (project, f'/api/achievements/projects/{project.id}/reject/'),
            (ip_record, f'/api/achievements/intellectual-properties/{ip_record.id}/reject/'),
            (service, f'/api/achievements/academic-services/{service.id}/reject/'),
        ]

        self.client.force_authenticate(user=self.college_admin)
        for instance, endpoint in endpoint_pairs:
            invalid_response = self.client.post(endpoint, {}, format='json')
            self.assertEqual(invalid_response.status_code, status.HTTP_400_BAD_REQUEST)

            valid_response = self.client.post(endpoint, {'reason': '鏉愭枡缂哄け锛岃琛ュ厖鍚庨噸鎻愩€?}, format='json')
            self.assertEqual(valid_response.status_code, status.HTTP_200_OK)
            instance.refresh_from_db()
            self.assertEqual(instance.status, 'REJECTED')


class PaperClaimOrderConfirmationApiTests(APITestCase):
    def setUp(self):
        user_model = get_user_model()
        self.teacher_a = user_model.objects.create_user(
            id=904001,
            username='904001',
            password='teacher123456',
            real_name='TeacherA',
            department='浜哄伐鏅鸿兘瀛﹂櫌',
            title='鍓暀鎺?,
        )
        self.teacher_b = user_model.objects.create_user(
            id=904002,
            username='904002',
            password='teacher123456',
            real_name='TeacherB',
            department='浜哄伐鏅鸿兘瀛﹂櫌',
            title='璁插笀',
        )
        self.teacher_c = user_model.objects.create_user(
            id=904003,
            username='904003',
            password='teacher123456',
            real_name='TeacherC',
            department='浜哄伐鏅鸿兘瀛﹂櫌',
            title='璁插笀',
        )

    def _create_paper(self, actor, payload):
        self.client.force_authenticate(user=actor)
        response = self.client.post('/api/achievements/papers/', payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        return Paper.objects.get(id=response.data['id'])

    def test_case_1_standard_claim_flow(self):
        paper = self._create_paper(
            self.teacher_a,
            {
                'title': 'Standard claim paper',
                'abstract': 'Long enough abstract for standard internal claim workflow testing.',
                'date_acquired': '2025-08-01',
                'paper_type': 'JOURNAL',
                'journal_name': 'Claim Journal',
                'is_first_author': True,
                'is_corresponding_author': False,
                'coauthor_records': [
                    {'name': self.teacher_b.real_name, 'user_id': self.teacher_b.id, 'order': 2, 'is_corresponding': False}
                ],
            },
        )
        claim = AchievementClaim.objects.get(achievement=paper, target_user=self.teacher_b)
        self.assertEqual(claim.status, 'PENDING')
        self.assertEqual(claim.proposed_order, 2)

        self.client.force_authenticate(user=self.teacher_b)
        accept_response = self.client.post(
            f'/api/claims/{claim.id}/accept/',
            {'actual_order': 2, 'actual_is_corresponding': False},
            format='json',
        )
        self.assertEqual(accept_response.status_code, status.HTTP_200_OK)
        claim.refresh_from_db()
        self.assertEqual(claim.status, 'ACCEPTED')
        self.assertEqual(claim.actual_order, 2)
        self.assertFalse(claim.confirmed_is_corresponding)
        self.assertEqual(paper.coauthors.get(internal_teacher=self.teacher_b).author_rank, 2)

    def test_case_2_student_first_teacher_corresponding(self):
        paper = self._create_paper(
            self.teacher_a,
            {
                'title': 'Student first author case',
                'abstract': 'Long enough abstract for student first and teacher corresponding author scenario.',
                'date_acquired': '2025-08-02',
                'paper_type': 'JOURNAL',
                'journal_name': 'Corresponding Journal',
                'is_first_author': False,
                'is_corresponding_author': True,
                'coauthor_records': [
                    {'name': 'StudentOne', 'order': 1, 'is_corresponding': False},
                    {'name': self.teacher_b.real_name, 'user_id': self.teacher_b.id, 'order': 3, 'is_corresponding': False},
                ],
            },
        )
        claim = AchievementClaim.objects.get(achievement=paper, target_user=self.teacher_b)
        self.assertEqual(claim.status, 'PENDING')
        self.assertEqual(claim.proposed_order, 3)
        self.assertFalse(claim.proposed_is_corresponding)

        paper.status = 'APPROVED'
        paper.save(update_fields=['status'])
        self.client.force_authenticate(user=self.teacher_a)
        all_response = self.client.get(f'/api/achievements/all-achievements/{self.teacher_a.id}/')
        self.assertEqual(all_response.status_code, status.HTTP_200_OK)
        target = next(item for item in all_response.data['records'] if item['id'] == paper.id)
        self.assertIn('閫氳浣滆€?, target['author_rank_label'])

    def test_case_3_claim_accept_with_order_correction_to_conflict(self):
        paper = self._create_paper(
            self.teacher_a,
            {
                'title': 'Conflict claim paper',
                'abstract': 'Long enough abstract for conflict scenario where claim target corrects order and corresponding.',
                'date_acquired': '2025-08-03',
                'paper_type': 'JOURNAL',
                'journal_name': 'Conflict Journal',
                'coauthor_records': [
                    {'name': self.teacher_c.real_name, 'user_id': self.teacher_c.id, 'order': 3, 'is_corresponding': False}
                ],
            },
        )
        claim = AchievementClaim.objects.get(achievement=paper, target_user=self.teacher_c)

        self.client.force_authenticate(user=self.teacher_c)
        response = self.client.post(
            f'/api/achievements/claims/{claim.id}/accept/',
            {'actual_order': 2, 'actual_is_corresponding': True},
            format='json',
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        claim.refresh_from_db()
        self.assertEqual(claim.status, 'CONFLICT')
        self.assertEqual(claim.actual_order, 2)
        self.assertTrue(claim.confirmed_is_corresponding)
        coauthor = paper.coauthors.get(internal_teacher=self.teacher_c)
        self.assertEqual(coauthor.author_rank, 2)
        self.assertTrue(coauthor.is_corresponding)

    def test_case_4_second_author_teacher_records_and_first_author_claims(self):
        paper = self._create_paper(
            self.teacher_b,
            {
                'title': 'Second author uploads for first author',
                'abstract': 'Long enough abstract for second-author teacher submission and first-author teacher claim confirmation.',
                'date_acquired': '2025-08-04',
                'paper_type': 'JOURNAL',
                'journal_name': 'Shared Journal',
                'is_first_author': False,
                'is_corresponding_author': False,
                'coauthor_records': [
                    {'name': self.teacher_a.real_name, 'user_id': self.teacher_a.id, 'order': 1, 'is_corresponding': False},
                    {'name': self.teacher_b.real_name, 'user_id': self.teacher_b.id, 'order': 2, 'is_corresponding': False},
                ],
            },
        )
        claim = AchievementClaim.objects.get(achievement=paper, target_user=self.teacher_a)
        self.assertEqual(claim.status, 'PENDING')
        self.assertEqual(claim.proposed_order, 1)

        paper.status = 'APPROVED'
        paper.save(update_fields=['status'])

        self.client.force_authenticate(user=self.teacher_b)
        owner_all_response = self.client.get(f'/api/achievements/all-achievements/{self.teacher_b.id}/')
        self.assertEqual(owner_all_response.status_code, status.HTTP_200_OK)
        owner_target = next(item for item in owner_all_response.data['records'] if item['id'] == paper.id)
        self.assertEqual(owner_target['author_rank_label'], '绗?浣滆€?)

        self.client.force_authenticate(user=self.teacher_a)
        accept_response = self.client.post(
            f'/api/achievements/claims/{claim.id}/accept/',
            {'actual_order': 1, 'actual_is_corresponding': False},
            format='json',
        )
        self.assertEqual(accept_response.status_code, status.HTTP_200_OK)
        claim.refresh_from_db()
        self.assertEqual(claim.status, 'ACCEPTED')

        a_all_response = self.client.get(f'/api/achievements/all-achievements/{self.teacher_a.id}/')
        self.assertEqual(a_all_response.status_code, status.HTTP_200_OK)
        a_target = next(item for item in a_all_response.data['records'] if item['id'] == paper.id)
        self.assertEqual(a_target['author_rank_label'], '绗?浣滆€?)


class AchievementClaimFlowApiTests(APITestCase):
    def setUp(self):
        user_model = get_user_model()
        self.teacher_a = user_model.objects.create_user(
            id=902001,
            username='902001',
            password='teacher123456',
            real_name='寮犺€佸笀',
            department='浜哄伐鏅鸿兘瀛﹂櫌',
            title='鍓暀鎺?,
        )
        self.teacher_b = user_model.objects.create_user(
            id=902002,
            username='902002',
            password='teacher123456',
            real_name='鏉庢櫒',
            department='浜哄伐鏅鸿兘瀛﹂櫌',
            title='璁插笀',
        )
        self.teacher_c = user_model.objects.create_user(
            id=902003,
            username='902003',
            password='teacher123456',
            real_name='鐜嬪垰',
            department='璁＄畻鏈哄闄?,
            title='璁插笀',
        )
        self.college_admin = user_model.objects.create_user(
            id=902004,
            username='college-admin-claim',
            password='Admin123456',
            real_name='瀛﹂櫌绠＄悊鍛樿棰?,
            department='浜哄伐鏅鸿兘瀛﹂櫌',
            title='瀛﹂櫌绠＄悊鍛?,
            is_staff=True,
        )

    def _create_approved_paper(self):
        return Paper.objects.create(
            teacher=self.teacher_a,
            title='璺ㄥ闄㈠崗鍚岃鏂?,
            abstract='杩欐槸涓€涓冻澶熼暱鐨勬憳瑕侊紝鐢ㄤ簬楠岃瘉鏍″唴鍚堣憲鑰呮垚鏋滆棰嗘満鍒跺湪瀹℃壒閫氳繃鍚庣殑鐢诲儚鑱氬悎鏁堟灉銆?,
            date_acquired='2025-04-18',
            paper_type='JOURNAL',
            journal_name='娴嬭瘯鏈熷垔',
            is_first_author=True,
            status='APPROVED',
        )

    def test_create_paper_auto_generates_pending_claim_for_internal_coauthor(self):
        self.client.force_authenticate(user=self.teacher_a)
        response = self.client.post(
            '/api/achievements/papers/',
            {
                'title': '鑷姩璇嗗埆璁ら璁烘枃',
                'abstract': '杩欐槸涓€涓冻澶熼暱鐨勬憳瑕侊紝鐢ㄤ簬楠岃瘉璁烘枃褰曞叆鍚庝細鎸夊悎钁楄€呭鍚嶈嚜鍔ㄧ敓鎴愯棰嗛個璇枫€?,
                'date_acquired': '2025-04-01',
                'paper_type': 'JOURNAL',
                'journal_name': '娴嬭瘯鏈熷垔',
                'coauthors': ['鏉庢櫒', '澶栭儴鍚堜綔鑰?],
            },
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        claim = AchievementClaim.objects.filter(target_user=self.teacher_b).first()
        self.assertIsNotNone(claim)
        self.assertEqual(claim.status, 'PENDING')
        self.assertEqual(claim.initiator_id, self.teacher_a.id)
        self.assertGreaterEqual(
            UserNotification.objects.filter(
                recipient=self.teacher_b,
                category=UserNotification.CATEGORY_ACHIEVEMENT_CLAIM,
            ).count(),
            1,
        )

    def test_accept_claim_updates_status_and_all_achievements_contains_claimed_paper(self):
        paper = self._create_approved_paper()
        AchievementClaim.objects.create(
            achievement=paper,
            initiator=self.teacher_a,
            target_user=self.teacher_b,
            status='PENDING',
        )

        self.client.force_authenticate(user=self.teacher_b)
        pending_response = self.client.get('/api/achievements/claims/pending/')
        self.assertEqual(pending_response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(pending_response.data['records']), 1)

        claim_id = pending_response.data['records'][0]['id']
        accept_response = self.client.post(f'/api/achievements/claims/{claim_id}/accept/', format='json')
        self.assertEqual(accept_response.status_code, status.HTTP_200_OK)

        all_response = self.client.get(f'/api/achievements/all-achievements/{self.teacher_b.id}/')
        self.assertEqual(all_response.status_code, status.HTTP_200_OK)
        self.assertTrue(any(item['title'] == paper.title for item in all_response.data['records']))

        dashboard_response = self.client.get('/api/achievements/dashboard-stats/')
        self.assertEqual(dashboard_response.status_code, status.HTTP_200_OK)
        self.assertEqual(dashboard_response.data['achievement_overview']['paper_count'], 1)

    def test_reject_claim_marks_status_rejected(self):
        paper = self._create_approved_paper()
        claim = AchievementClaim.objects.create(
            achievement=paper,
            initiator=self.teacher_a,
            target_user=self.teacher_b,
            status='PENDING',
        )

        self.client.force_authenticate(user=self.teacher_b)
        response = self.client.post(f'/api/achievements/claims/{claim.id}/reject/', format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        claim.refresh_from_db()
        self.assertEqual(claim.status, 'REJECTED')

    def test_college_admin_unclaimed_tracking_is_scoped_to_own_college(self):
        paper = self._create_approved_paper()
        claim_in_college = AchievementClaim.objects.create(
            achievement=paper,
            initiator=self.teacher_a,
            target_user=self.teacher_b,
            status='PENDING',
        )
        claim_other_college = AchievementClaim.objects.create(
            achievement=paper,
            initiator=self.teacher_a,
            target_user=self.teacher_c,
            status='PENDING',
        )
        old_time = timezone.now() - timedelta(days=8)
        AchievementClaim.objects.filter(id__in=[claim_in_college.id, claim_other_college.id]).update(created_at=old_time)

        self.client.force_authenticate(user=self.college_admin)
        response = self.client.get('/api/achievements/claims/college-unclaimed/', {'days_threshold': 7})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['records']), 1)
        self.assertEqual(response.data['records'][0]['target_user_name'], '鏉庢櫒')

    def test_college_admin_remind_writes_claim_notifications(self):
        paper = self._create_approved_paper()
        claim = AchievementClaim.objects.create(
            achievement=paper,
            initiator=self.teacher_a,
            target_user=self.teacher_b,
            status='PENDING',
        )
        AchievementClaim.objects.filter(id=claim.id).update(created_at=timezone.now() - timedelta(days=10))

        self.client.force_authenticate(user=self.college_admin)
        response = self.client.post(
            '/api/achievements/claims/college-unclaimed/remind/',
            {'days_threshold': 7},
            format='json',
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertGreaterEqual(response.data['reminded_count'], 1)
        self.assertGreaterEqual(
            UserNotification.objects.filter(
                recipient=self.teacher_b,
                category=UserNotification.CATEGORY_CLAIM_REMINDER,
            ).count(),
            1,
        )

