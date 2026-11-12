import re
from unittest.mock import patch
from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from rest_framework.test import APIClient

from ai_services.rag_service import RAGService
from apps.accounts.models import LearningProfile
from apps.quiz.models import QuizAttempt

Student = get_user_model()


class QAFixesRegressionTestCase(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.student = Student.objects.create_user(
            email='student@example.com',
            username='student1',
            password='Password123!',
            full_name='Regular Student',
        )
        LearningProfile.objects.create(student=self.student)
        self.admin = Student.objects.create_user(
            email='admin@example.com',
            username='admin1',
            password='Password123!',
            full_name='Admin User',
            is_staff=True,
            is_superuser=True,
        )
        self.other_student = Student.objects.create_user(
            email='other@example.com',
            username='other1',
            password='Password123!',
            full_name='Other Student',
        )

    @override_settings(
        STORAGES={
            'default': {'BACKEND': 'django.core.files.storage.FileSystemStorage'},
            'staticfiles': {'BACKEND': 'django.contrib.staticfiles.storage.StaticFilesStorage'},
        }
    )
    def test_bug1_admin_role_flags_and_hidden_nav_default(self):
        self.client.force_authenticate(user=self.student)
        profile_res = self.client.get('/api/auth/profile/')
        self.assertEqual(profile_res.status_code, 200)
        self.assertFalse(profile_res.data['student']['is_staff'])
        self.assertFalse(profile_res.data['student']['is_superuser'])

        stats_res = self.client.get('/api/auth/dashboard-stats/')
        self.assertEqual(stats_res.status_code, 200)
        self.assertFalse(stats_res.data['is_staff'])
        self.assertFalse(stats_res.data['is_superuser'])

        self.client.force_authenticate(user=self.admin)
        admin_res = self.client.get('/api/auth/profile/')
        self.assertEqual(admin_res.status_code, 200)
        self.assertTrue(admin_res.data['student']['is_staff'])
        self.assertTrue(admin_res.data['student']['is_superuser'])

        for route in ['/dashboard/', '/content/', '/quiz/', '/profile/']:
            page_res = self.client.get(route)
            self.assertEqual(page_res.status_code, 200)
            html = page_res.content.decode('utf-8')
            self.assertIn('id="adminNavSection" style="display:none"', html)

    @patch('ai_services.llm_service.LLMService.generate_raw', return_value='')
    def test_bug2_and_bug3_tamil_sangam_examples_relevance_and_consistent_language(self, _mock_raw):
        rag = RAGService()
        chunks = rag.retrieve('Tamil Sangam Age', k=4, subject='Tamil')
        self.assertEqual(chunks, [])

        self.client.force_authenticate(user=self.student)
        payload = {
            'subject': 'Tamil',
            'topic': 'Sangam Age',
            'skill_level': 'advanced',
            'content_type': 'examples',
        }
        res1 = self.client.post('/api/content/generate/', payload, format='json')
        res2 = self.client.post('/api/content/generate/', payload, format='json')
        self.assertEqual(res1.status_code, 201)
        self.assertEqual(res2.status_code, 201)

        body1 = res1.data['content']['content_body']
        body2 = res2.data['content']['content_body']

        for body in (body1, body2):
            self.assertNotIn('```python', body.lower())
            self.assertNotIn('def execute_task', body)
            self.assertRegex(body, r'[\u0B80-\u0BFF]')

    @patch('ai_services.llm_service.LLMService.generate_raw', return_value='')
    def test_bug4_subject_topic_validation_for_content_and_quiz(self, _mock_raw):
        self.client.force_authenticate(user=self.student)

        bad_payload = {
            'subject': 'Tamil',
            'topic': 'Python Programming Overview & Fundamentals',
            'skill_level': 'beginner',
        }
        content_res = self.client.post(
            '/api/content/generate/',
            {**bad_payload, 'content_type': 'notes'},
            format='json',
        )
        self.assertEqual(content_res.status_code, 400)
        self.assertIn('error', content_res.data)

        quiz_res = self.client.post(
            '/api/quiz/generate/',
            {**bad_payload, 'num_questions': 5},
            format='json',
        )
        self.assertEqual(quiz_res.status_code, 400)
        self.assertIn('error', quiz_res.data)

        valid_grammar = self.client.post(
            '/api/content/generate/',
            {'subject': 'Tamil', 'topic': 'Grammar', 'skill_level': 'beginner', 'content_type': 'notes'},
            format='json',
        )
        self.assertEqual(valid_grammar.status_code, 201)

    @patch('ai_services.llm_service.LLMService.generate_raw', return_value='')
    def test_bug5_and_bug6_quiz_review_and_duplicate_submission_idempotency(self, _mock_raw):
        self.client.force_authenticate(user=self.student)

        gen_res = self.client.post(
            '/api/quiz/generate/',
            {'subject': 'Tamil', 'topic': 'Sangam Age', 'skill_level': 'beginner', 'num_questions': 5},
            format='json',
        )
        self.assertEqual(gen_res.status_code, 201)
        quiz_id = gen_res.data['quiz']['id']

        submit_payload = {'quiz_id': quiz_id, 'answers': ['A', 'B', 'C', 'B', 'B'], 'time_taken_seconds': 42}
        sub1 = self.client.post('/api/quiz/submit/', submit_payload, format='json')
        sub2 = self.client.post('/api/quiz/submit/', submit_payload, format='json')
        self.assertEqual(sub1.status_code, 200)
        self.assertEqual(sub2.status_code, 200)
        self.assertTrue(sub2.data.get('duplicate_prevented'))
        self.assertEqual(sub1.data['attempt']['id'], sub2.data['attempt']['id'])

        # Only 1 attempt stored & counted
        self.assertEqual(QuizAttempt.objects.filter(student=self.student).count(), 1)
        self.student.learning_profile.refresh_from_db()
        self.assertEqual(self.student.learning_profile.total_quizzes_taken, 1)

        history_res = self.client.get('/api/quiz/history/')
        self.assertEqual(history_res.status_code, 200)
        self.assertEqual(history_res.data['count'], 1)

        attempt_id = sub1.data['attempt']['id']
        detail_res = self.client.get(f'/api/quiz/history/{attempt_id}/')
        self.assertEqual(detail_res.status_code, 200)
        self.assertEqual(detail_res.data['attempt']['quiz_topic'], 'Sangam Age')
        self.assertTrue(len(detail_res.data['attempt']['correct_answers']) > 0)

        # Other user cannot open this attempt
        self.client.force_authenticate(user=self.other_student)
        forbidden_res = self.client.get(f'/api/quiz/history/{attempt_id}/')
        self.assertEqual(forbidden_res.status_code, 404)
