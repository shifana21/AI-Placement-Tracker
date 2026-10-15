import json
from decimal import Decimal
from unittest.mock import MagicMock, patch

from django.db.utils import IntegrityError
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from apps.accounts.models import User
from apps.ai_interview.models import (
    InterviewAnswer,
    InterviewQuestion,
    MockInterview,
)
from apps.ai_interview.services.evaluation import (
    evaluate_interview_answer,
    generate_final_interview_analysis,
)
from apps.ai_interview.services.interview_service import (
    complete_mock_interview,
    start_mock_interview,
    submit_interview_answer,
)
from apps.ai_interview.services.question_generator import (
    GeminiAPIError,
    GeminiConfigurationError,
    InvalidGeminiResponseError,
    generate_interview_questions,
)

MOCK_QUESTIONS_PAYLOAD = {
    "questions": [
        {
            "question_number": 1,
            "question_text": "Explain mutable vs immutable types in Python.",
            "question_type": "TECHNICAL",
            "topic": "Python Fundamentals",
        },
        {
            "question_number": 2,
            "question_text": "Describe a difficult bug you solved and how you approached it.",
            "question_type": "BEHAVIORAL",
            "topic": "Problem Solving",
        },
        {
            "question_number": 3,
            "question_text": "Where do you see yourself in 3 years?",
            "question_type": "HR",
            "topic": "Career Goals",
        },
    ]
}

MOCK_EVALUATION_PAYLOAD = {
    "score": 85.0,
    "evaluation": "Clear explanation with accurate technical depth.",
    "strengths": ["Clear communication", "Good code examples"],
    "weaknesses": ["Could mention memory addresses"],
    "improvement_suggestions": ["Practice explaining reference counting"],
}

MOCK_FINAL_ANALYSIS_PAYLOAD = {
    "overall_score": 85.0,
    "overall_feedback": "Strong performance across technical and behavioral aspects.",
    "strengths": ["Clear communication", "Solid fundamentals"],
    "weaknesses": ["Memory management details"],
    "recommendations": ["Review deep copy vs shallow copy concepts"],
}


@override_settings(GEMINI_API_KEY="test-mock-api-key")
class AIInterviewAuthenticationTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email="auth_student@example.com",
            password="TestPassword123",
        )
        self.interview = MockInterview.objects.create(
            student=self.user,
            interview_type="TECHNICAL",
            target_role="Software Engineer",
            experience_level="BEGINNER",
            number_of_questions=3,
            current_question=1,
            status=MockInterview.Status.IN_PROGRESS,
        )

    def test_01_unauthenticated_start_rejected(self):
        url = reverse("interview-start")
        response = self.client.post(url, {})
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_02_unauthenticated_list_rejected(self):
        url = reverse("interview-list")
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_03_unauthenticated_detail_rejected(self):
        url = reverse("interview-detail", kwargs={"pk": self.interview.id})
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_04_unauthenticated_answer_rejected(self):
        url = reverse("interview-answer", kwargs={"pk": self.interview.id})
        response = self.client.post(url, {"answer_text": "My answer"})
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_05_unauthenticated_result_rejected(self):
        url = reverse("interview-result", kwargs={"pk": self.interview.id})
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


@override_settings(GEMINI_API_KEY="test-mock-api-key")
class AIInterviewCreationTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email="create_student@example.com",
            password="TestPassword123",
        )
        self.client.force_authenticate(user=self.user)
        self.start_url = reverse("interview-start")

    @patch("apps.ai_interview.views.start_mock_interview")
    def test_06_valid_interview_creation(self, mock_start):
        interview = MockInterview.objects.create(
            student=self.user,
            interview_type="TECHNICAL",
            target_role="Software Engineer",
            experience_level="BEGINNER",
            number_of_questions=3,
            current_question=1,
            status=MockInterview.Status.IN_PROGRESS,
        )
        q1 = InterviewQuestion.objects.create(
            interview=interview,
            question_number=1,
            question_text="Q1 text",
            question_type="TECHNICAL",
            topic="Python",
        )
        mock_start.return_value = (interview, q1)

        payload = {
            "interview_type": "TECHNICAL",
            "target_role": "Software Engineer",
            "experience_level": "BEGINNER",
            "number_of_questions": 3,
        }
        response = self.client.post(self.start_url, payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["status"], "IN_PROGRESS")
        self.assertEqual(response.data["current_question"], 1)
        self.assertIn("current_question_detail", response.data)

    def test_07_invalid_interview_type_rejected(self):
        payload = {
            "interview_type": "INVALID_TYPE",
            "target_role": "Software Engineer",
            "experience_level": "BEGINNER",
            "number_of_questions": 3,
        }
        response = self.client.post(self.start_url, payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("interview_type", response.data)

    def test_08_invalid_experience_level_rejected(self):
        payload = {
            "interview_type": "TECHNICAL",
            "target_role": "Software Engineer",
            "experience_level": "GOD_TIER",
            "number_of_questions": 3,
        }
        response = self.client.post(self.start_url, payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("experience_level", response.data)

    def test_09_number_of_questions_below_1_rejected(self):
        payload = {
            "interview_type": "TECHNICAL",
            "target_role": "Software Engineer",
            "experience_level": "BEGINNER",
            "number_of_questions": 0,
        }
        response = self.client.post(self.start_url, payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("number_of_questions", response.data)

    def test_10_number_of_questions_above_20_rejected(self):
        payload = {
            "interview_type": "TECHNICAL",
            "target_role": "Software Engineer",
            "experience_level": "BEGINNER",
            "number_of_questions": 21,
        }
        response = self.client.post(self.start_url, payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("number_of_questions", response.data)

    @patch("apps.ai_interview.services.interview_service.generate_interview_questions")
    def test_11_student_automatically_assigned_from_request_user(self, mock_gen):
        mock_gen.return_value = MOCK_QUESTIONS_PAYLOAD["questions"]
        interview, _ = start_mock_interview(
            student=self.user,
            interview_type="TECHNICAL",
            target_role="Backend Dev",
            experience_level="BEGINNER",
            number_of_questions=3,
        )
        self.assertEqual(interview.student, self.user)

    @patch("apps.ai_interview.services.interview_service.generate_interview_questions")
    def test_12_status_automatically_in_progress(self, mock_gen):
        mock_gen.return_value = MOCK_QUESTIONS_PAYLOAD["questions"]
        interview, _ = start_mock_interview(
            student=self.user,
            interview_type="TECHNICAL",
            target_role="Backend Dev",
            experience_level="BEGINNER",
            number_of_questions=3,
        )
        self.assertEqual(interview.status, MockInterview.Status.IN_PROGRESS)

    @patch("apps.ai_interview.services.interview_service.generate_interview_questions")
    def test_13_current_question_initialized_correctly(self, mock_gen):
        mock_gen.return_value = MOCK_QUESTIONS_PAYLOAD["questions"]
        interview, first_q = start_mock_interview(
            student=self.user,
            interview_type="TECHNICAL",
            target_role="Backend Dev",
            experience_level="BEGINNER",
            number_of_questions=3,
        )
        self.assertEqual(interview.current_question, 1)
        self.assertIsNotNone(first_q)
        self.assertEqual(first_q.question_number, 1)


@override_settings(GEMINI_API_KEY="test-mock-api-key")
class AIInterviewQuestionGenerationTests(TestCase):
    @patch("apps.ai_interview.services.question_generator.genai.Client")
    def test_14_gemini_question_generation_called_correctly(self, mock_client):
        mock_response = mock_client.return_value.models.generate_content.return_value
        mock_response.text = json.dumps(MOCK_QUESTIONS_PAYLOAD)

        questions = generate_interview_questions(
            interview_type="TECHNICAL",
            target_role="Software Engineer",
            experience_level="BEGINNER",
            number_of_questions=3,
        )
        mock_client.return_value.models.generate_content.assert_called_once()
        self.assertEqual(len(questions), 3)

    @patch("apps.ai_interview.services.question_generator.genai.Client")
    def test_15_correct_number_of_questions_generated(self, mock_client):
        mock_response = mock_client.return_value.models.generate_content.return_value
        mock_response.text = json.dumps(MOCK_QUESTIONS_PAYLOAD)

        questions = generate_interview_questions(
            interview_type="TECHNICAL",
            target_role="Software Engineer",
            experience_level="BEGINNER",
            number_of_questions=2,
        )
        self.assertEqual(len(questions), 2)
        self.assertEqual([q["question_number"] for q in questions], [1, 2])

    @patch("apps.ai_interview.services.interview_service.generate_interview_questions")
    def test_16_questions_saved_correctly(self, mock_gen):
        user = User.objects.create_user(
            email="q_student@example.com",
            password="TestPassword123",
        )
        mock_gen.return_value = MOCK_QUESTIONS_PAYLOAD["questions"]
        interview, _ = start_mock_interview(
            student=user,
            interview_type="TECHNICAL",
            target_role="Software Engineer",
            experience_level="BEGINNER",
            number_of_questions=3,
        )
        saved_questions = list(interview.questions.all().order_by("question_number"))
        self.assertEqual(len(saved_questions), 3)
        self.assertEqual(saved_questions[0].question_number, 1)
        self.assertEqual(saved_questions[0].topic, "Python Fundamentals")

    def test_17_duplicate_question_numbers_prevented(self):
        user = User.objects.create_user(
            email="dup_student@example.com",
            password="TestPassword123",
        )
        interview = MockInterview.objects.create(
            student=user,
            interview_type="TECHNICAL",
            target_role="Software Engineer",
            experience_level="BEGINNER",
            number_of_questions=3,
            current_question=1,
        )
        InterviewQuestion.objects.create(
            interview=interview,
            question_number=1,
            question_text="Q1 text",
            question_type="TECHNICAL",
        )
        with self.assertRaises(IntegrityError):
            InterviewQuestion.objects.create(
                interview=interview,
                question_number=1,
                question_text="Duplicate Q1 text",
                question_type="TECHNICAL",
            )

    @patch("apps.ai_interview.services.question_generator.genai.Client")
    def test_18_malformed_gemini_response_handled(self, mock_client):
        mock_response = mock_client.return_value.models.generate_content.return_value
        mock_response.text = "This is not json { [ invalid"
        with self.assertRaises(InvalidGeminiResponseError):
            generate_interview_questions(
                interview_type="TECHNICAL",
                target_role="Software Engineer",
                experience_level="BEGINNER",
                number_of_questions=3,
            )

    @patch("apps.ai_interview.services.question_generator.genai.Client")
    def test_19_gemini_api_failure_handled(self, mock_client):
        mock_client.return_value.models.generate_content.side_effect = Exception(
            "Service unavailable"
        )
        with self.assertRaises(GeminiAPIError):
            generate_interview_questions(
                interview_type="TECHNICAL",
                target_role="Software Engineer",
                experience_level="BEGINNER",
                number_of_questions=3,
            )

    @override_settings(GEMINI_API_KEY="")
    def test_20_missing_api_key_handled(self):
        with self.assertRaises(GeminiConfigurationError):
            generate_interview_questions(
                interview_type="TECHNICAL",
                target_role="Software Engineer",
                experience_level="BEGINNER",
                number_of_questions=3,
            )


@override_settings(GEMINI_API_KEY="test-mock-api-key")
class AIInterviewQuestionSecurityTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email="sec_student@example.com",
            password="TestPassword123",
        )
        self.other_user = User.objects.create_user(
            email="sec_other@example.com",
            password="TestPassword123",
        )
        self.interview = MockInterview.objects.create(
            student=self.user,
            interview_type="TECHNICAL",
            target_role="Software Engineer",
            experience_level="BEGINNER",
            number_of_questions=3,
            current_question=1,
            status=MockInterview.Status.IN_PROGRESS,
        )
        self.q1 = InterviewQuestion.objects.create(
            interview=self.interview,
            question_number=1,
            question_text="Q1 text",
            question_type="TECHNICAL",
            topic="Algorithms",
        )
        self.q2 = InterviewQuestion.objects.create(
            interview=self.interview,
            question_number=2,
            question_text="Q2 text",
            question_type="TECHNICAL",
            topic="Databases",
        )

    def test_21_correct_user_can_access_current_question(self):
        self.client.force_authenticate(user=self.user)
        url = reverse("interview-current-question", kwargs={"pk": self.interview.id})
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["question_number"], 1)
        self.assertEqual(response.data["question_text"], "Q1 text")

    def test_22_another_user_cannot_access_interview(self):
        self.client.force_authenticate(user=self.other_user)
        url = reverse("interview-current-question", kwargs={"pk": self.interview.id})
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_23_future_questions_are_not_unnecessarily_exposed(self):
        self.client.force_authenticate(user=self.user)
        url = reverse("interview-current-question", kwargs={"pk": self.interview.id})
        response = self.client.get(url)
        self.assertEqual(response.data["question_number"], 1)
        self.assertNotIn("Q2 text", json.dumps(response.data))

    def test_24_correct_answers_are_never_stored_in_question_api_response(self):
        self.client.force_authenticate(user=self.user)
        url = reverse("interview-current-question", kwargs={"pk": self.interview.id})
        response = self.client.get(url)
        self.assertNotIn("answer", response.data)
        self.assertNotIn("correct_answer", response.data)


@override_settings(GEMINI_API_KEY="test-mock-api-key")
class AIInterviewAnswerTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email="ans_student@example.com",
            password="TestPassword123",
        )
        self.client.force_authenticate(user=self.user)
        self.interview = MockInterview.objects.create(
            student=self.user,
            interview_type="TECHNICAL",
            target_role="Software Engineer",
            experience_level="BEGINNER",
            number_of_questions=2,
            current_question=1,
            status=MockInterview.Status.IN_PROGRESS,
        )
        self.q1 = InterviewQuestion.objects.create(
            interview=self.interview,
            question_number=1,
            question_text="What is a hash table?",
            question_type="TECHNICAL",
            topic="Data Structures",
        )
        self.q2 = InterviewQuestion.objects.create(
            interview=self.interview,
            question_number=2,
            question_text="Explain quicksort.",
            question_type="TECHNICAL",
            topic="Algorithms",
        )
        self.answer_url = reverse(
            "interview-answer", kwargs={"pk": self.interview.id}
        )

    @patch("apps.ai_interview.services.interview_service.evaluate_interview_answer")
    def test_25_valid_answer_recorded(self, mock_eval):
        mock_eval.return_value = MOCK_EVALUATION_PAYLOAD
        response = self.client.post(
            self.answer_url,
            {"answer_text": "A hash table is a data structure mapping keys to values."},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(InterviewAnswer.objects.filter(question=self.q1).exists())
        self.interview.refresh_from_db()
        self.assertEqual(self.interview.current_question, 2)

    def test_26_empty_answer_rejected(self):
        response = self.client.post(
            self.answer_url, {"answer_text": ""}, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_27_whitespace_only_answer_rejected(self):
        response = self.client.post(
            self.answer_url, {"answer_text": "    \n\t  "}, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_28_very_long_answer_rejected(self):
        response = self.client.post(
            self.answer_url,
            {"answer_text": "A" * 10001},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    @patch("apps.ai_interview.services.interview_service.evaluate_interview_answer")
    def test_29_ai_score_saved(self, mock_eval):
        mock_eval.return_value = MOCK_EVALUATION_PAYLOAD
        self.client.post(
            self.answer_url, {"answer_text": "Good answer."}, format="json"
        )
        answer = InterviewAnswer.objects.get(question=self.q1)
        self.assertEqual(answer.score, Decimal("85.00"))

    @patch("apps.ai_interview.services.interview_service.evaluate_interview_answer")
    def test_30_ai_evaluation_saved(self, mock_eval):
        mock_eval.return_value = MOCK_EVALUATION_PAYLOAD
        self.client.post(
            self.answer_url, {"answer_text": "Good answer."}, format="json"
        )
        answer = InterviewAnswer.objects.get(question=self.q1)
        self.assertEqual(answer.evaluation, MOCK_EVALUATION_PAYLOAD["evaluation"])

    @patch("apps.ai_interview.services.interview_service.evaluate_interview_answer")
    def test_31_strengths_saved(self, mock_eval):
        mock_eval.return_value = MOCK_EVALUATION_PAYLOAD
        self.client.post(
            self.answer_url, {"answer_text": "Good answer."}, format="json"
        )
        answer = InterviewAnswer.objects.get(question=self.q1)
        self.assertEqual(answer.strengths, MOCK_EVALUATION_PAYLOAD["strengths"])

    @patch("apps.ai_interview.services.interview_service.evaluate_interview_answer")
    def test_32_weaknesses_saved(self, mock_eval):
        mock_eval.return_value = MOCK_EVALUATION_PAYLOAD
        self.client.post(
            self.answer_url, {"answer_text": "Good answer."}, format="json"
        )
        answer = InterviewAnswer.objects.get(question=self.q1)
        self.assertEqual(answer.weaknesses, MOCK_EVALUATION_PAYLOAD["weaknesses"])

    @patch("apps.ai_interview.services.interview_service.evaluate_interview_answer")
    def test_33_improvement_suggestions_saved(self, mock_eval):
        mock_eval.return_value = MOCK_EVALUATION_PAYLOAD
        self.client.post(
            self.answer_url, {"answer_text": "Good answer."}, format="json"
        )
        answer = InterviewAnswer.objects.get(question=self.q1)
        self.assertEqual(
            answer.improvement_suggestions,
            MOCK_EVALUATION_PAYLOAD["improvement_suggestions"],
        )

    @patch("apps.ai_interview.services.interview_service.evaluate_interview_answer")
    def test_34_duplicate_answer_rejected(self, mock_eval):
        mock_eval.return_value = MOCK_EVALUATION_PAYLOAD
        # Manually create answer for Q1
        InterviewAnswer.objects.create(
            question=self.q1,
            answer_text="Already answered",
            score=Decimal("80.00"),
        )
        response = self.client.post(
            self.answer_url,
            {"answer_text": "Second attempt to answer Q1"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("already been answered", response.data["error"])

    def test_35_answer_cannot_be_submitted_after_completion(self):
        self.interview.status = MockInterview.Status.COMPLETED
        self.interview.save()

        response = self.client.post(
            self.answer_url,
            {"answer_text": "Answer after interview completed"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("not in progress", response.data["error"])

    @patch("apps.ai_interview.services.interview_service.evaluate_interview_answer")
    def test_36_client_cannot_inject_score(self, mock_eval):
        mock_eval.return_value = MOCK_EVALUATION_PAYLOAD
        self.client.post(
            self.answer_url,
            {"answer_text": "Valid answer.", "score": 100.0},
            format="json",
        )
        answer = InterviewAnswer.objects.get(question=self.q1)
        self.assertEqual(answer.score, Decimal("85.00"))

    @patch("apps.ai_interview.services.interview_service.evaluate_interview_answer")
    def test_37_client_cannot_inject_evaluation(self, mock_eval):
        mock_eval.return_value = MOCK_EVALUATION_PAYLOAD
        self.client.post(
            self.answer_url,
            {"answer_text": "Valid answer.", "evaluation": "Hacked"},
            format="json",
        )
        answer = InterviewAnswer.objects.get(question=self.q1)
        self.assertNotEqual(answer.evaluation, "Hacked")

    @patch("apps.ai_interview.services.interview_service.evaluate_interview_answer")
    def test_38_client_cannot_inject_strengths(self, mock_eval):
        mock_eval.return_value = MOCK_EVALUATION_PAYLOAD
        self.client.post(
            self.answer_url,
            {"answer_text": "Valid answer.", "strengths": ["Hacked"]},
            format="json",
        )
        answer = InterviewAnswer.objects.get(question=self.q1)
        self.assertEqual(answer.strengths, MOCK_EVALUATION_PAYLOAD["strengths"])

    @patch("apps.ai_interview.services.interview_service.evaluate_interview_answer")
    def test_39_client_cannot_inject_weaknesses(self, mock_eval):
        mock_eval.return_value = MOCK_EVALUATION_PAYLOAD
        self.client.post(
            self.answer_url,
            {"answer_text": "Valid answer.", "weaknesses": ["None"]},
            format="json",
        )
        answer = InterviewAnswer.objects.get(question=self.q1)
        self.assertEqual(answer.weaknesses, MOCK_EVALUATION_PAYLOAD["weaknesses"])


@override_settings(GEMINI_API_KEY="test-mock-api-key")
class AIInterviewScoringTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email="score_student@example.com",
            password="TestPassword123",
        )

    @patch("apps.ai_interview.services.interview_service.generate_final_interview_analysis")
    def test_40_overall_score_calculated_correctly(self, mock_final):
        mock_final.return_value = MOCK_FINAL_ANALYSIS_PAYLOAD
        interview = MockInterview.objects.create(
            student=self.user,
            interview_type="TECHNICAL",
            target_role="Software Engineer",
            experience_level="BEGINNER",
            number_of_questions=2,
            current_question=2,
            status=MockInterview.Status.IN_PROGRESS,
        )
        q1 = InterviewQuestion.objects.create(
            interview=interview, question_number=1, question_text="Q1"
        )
        q2 = InterviewQuestion.objects.create(
            interview=interview, question_number=2, question_text="Q2"
        )
        InterviewAnswer.objects.create(
            question=q1, answer_text="Ans1", score=Decimal("80.00")
        )
        InterviewAnswer.objects.create(
            question=q2, answer_text="Ans2", score=Decimal("90.00")
        )

        completed = complete_mock_interview(interview)
        self.assertEqual(completed.overall_score, Decimal("85.00"))

    @patch("apps.ai_interview.services.interview_service.generate_final_interview_analysis")
    def test_41_multiple_answer_scores_averaged_correctly(self, mock_final):
        mock_final.return_value = MOCK_FINAL_ANALYSIS_PAYLOAD
        interview = MockInterview.objects.create(
            student=self.user,
            interview_type="TECHNICAL",
            target_role="Software Engineer",
            experience_level="BEGINNER",
            number_of_questions=3,
            current_question=3,
            status=MockInterview.Status.IN_PROGRESS,
        )
        for i, score_val in enumerate([70, 80, 90], start=1):
            q = InterviewQuestion.objects.create(
                interview=interview, question_number=i, question_text=f"Q{i}"
            )
            InterviewAnswer.objects.create(
                question=q, answer_text=f"Ans{i}", score=Decimal(str(score_val))
            )

        completed = complete_mock_interview(interview)
        self.assertEqual(completed.overall_score, Decimal("80.00"))

    @patch("apps.ai_interview.services.interview_service.generate_final_interview_analysis")
    def test_42_single_question_interview_handled(self, mock_final):
        mock_final.return_value = MOCK_FINAL_ANALYSIS_PAYLOAD
        interview = MockInterview.objects.create(
            student=self.user,
            interview_type="HR",
            target_role="Software Engineer",
            experience_level="BEGINNER",
            number_of_questions=1,
            current_question=1,
            status=MockInterview.Status.IN_PROGRESS,
        )
        q1 = InterviewQuestion.objects.create(
            interview=interview, question_number=1, question_text="Q1"
        )
        InterviewAnswer.objects.create(
            question=q1, answer_text="Ans1", score=Decimal("95.00")
        )

        completed = complete_mock_interview(interview)
        self.assertEqual(completed.overall_score, Decimal("95.00"))

    @patch("apps.ai_interview.services.interview_service.generate_final_interview_analysis")
    def test_43_zero_score_interview_handled(self, mock_final):
        mock_final.return_value = {
            **MOCK_FINAL_ANALYSIS_PAYLOAD,
            "overall_score": 0.0,
        }
        interview = MockInterview.objects.create(
            student=self.user,
            interview_type="TECHNICAL",
            target_role="Software Engineer",
            experience_level="BEGINNER",
            number_of_questions=1,
            current_question=1,
            status=MockInterview.Status.IN_PROGRESS,
        )
        q1 = InterviewQuestion.objects.create(
            interview=interview, question_number=1, question_text="Q1"
        )
        InterviewAnswer.objects.create(
            question=q1, answer_text="Ans1", score=Decimal("0.00")
        )

        completed = complete_mock_interview(interview)
        self.assertEqual(completed.overall_score, Decimal("0.00"))

    @patch("apps.ai_interview.services.interview_service.generate_final_interview_analysis")
    def test_44_completion_timestamp_set(self, mock_final):
        mock_final.return_value = MOCK_FINAL_ANALYSIS_PAYLOAD
        interview = MockInterview.objects.create(
            student=self.user,
            interview_type="TECHNICAL",
            target_role="Software Engineer",
            experience_level="BEGINNER",
            number_of_questions=1,
            current_question=1,
            status=MockInterview.Status.IN_PROGRESS,
        )
        self.assertIsNone(interview.completed_at)
        completed = complete_mock_interview(interview)
        self.assertIsNotNone(completed.completed_at)

    @patch("apps.ai_interview.services.interview_service.generate_final_interview_analysis")
    def test_45_completed_interview_becomes_immutable(self, mock_final):
        mock_final.return_value = MOCK_FINAL_ANALYSIS_PAYLOAD
        interview = MockInterview.objects.create(
            student=self.user,
            interview_type="TECHNICAL",
            target_role="Software Engineer",
            experience_level="BEGINNER",
            number_of_questions=1,
            current_question=1,
            status=MockInterview.Status.IN_PROGRESS,
        )
        complete_mock_interview(interview)
        self.assertEqual(interview.status, MockInterview.Status.COMPLETED)

        with self.assertRaises(ValueError):
            submit_interview_answer(interview, "Trying to answer completed interview")


@override_settings(GEMINI_API_KEY="test-mock-api-key")
class AIInterviewOwnershipTests(APITestCase):
    def setUp(self):
        self.user_a = User.objects.create_user(
            email="user_a@example.com",
            password="TestPassword123",
        )
        self.user_b = User.objects.create_user(
            email="user_b@example.com",
            password="TestPassword123",
        )
        self.interview_b = MockInterview.objects.create(
            student=self.user_b,
            interview_type="TECHNICAL",
            target_role="Software Engineer",
            experience_level="BEGINNER",
            number_of_questions=2,
            current_question=1,
            status=MockInterview.Status.IN_PROGRESS,
        )
        self.q1_b = InterviewQuestion.objects.create(
            interview=self.interview_b,
            question_number=1,
            question_text="User B Q1",
            question_type="TECHNICAL",
        )

    def test_46_user_a_cannot_access_user_b_interview(self):
        self.client.force_authenticate(user=self.user_a)
        url = reverse("interview-detail", kwargs={"pk": self.interview_b.id})
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_47_user_a_cannot_answer_user_b_question(self):
        self.client.force_authenticate(user=self.user_a)
        url = reverse("interview-answer", kwargs={"pk": self.interview_b.id})
        response = self.client.post(
            url, {"answer_text": "Hacked answer"}, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_48_user_a_cannot_access_user_b_result(self):
        self.client.force_authenticate(user=self.user_a)
        url = reverse("interview-result", kwargs={"pk": self.interview_b.id})
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_49_user_a_cannot_modify_user_b_interview(self):
        self.client.force_authenticate(user=self.user_a)
        url = reverse("interview-complete", kwargs={"pk": self.interview_b.id})
        response = self.client.post(url, format="json")
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)


@override_settings(GEMINI_API_KEY="test-mock-api-key")
class AIInterviewResultTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email="result_student@example.com",
            password="TestPassword123",
        )
        self.client.force_authenticate(user=self.user)
        self.interview = MockInterview.objects.create(
            student=self.user,
            interview_type="TECHNICAL",
            target_role="Software Engineer",
            experience_level="BEGINNER",
            number_of_questions=1,
            current_question=1,
            status=MockInterview.Status.COMPLETED,
            overall_score=Decimal("88.00"),
            overall_feedback="Excellent interview demonstration.",
            strengths=["Coding", "Design"],
            weaknesses=["Edge cases"],
            recommendations=["Practice multithreading"],
            completed_at=timezone.now(),
        )
        self.q1 = InterviewQuestion.objects.create(
            interview=self.interview,
            question_number=1,
            question_text="Explain Python GIL.",
            question_type="TECHNICAL",
            topic="Concurrency",
        )
        self.ans1 = InterviewAnswer.objects.create(
            question=self.q1,
            answer_text="Global Interpreter Lock ensures single thread execution in CPython.",
            score=Decimal("88.00"),
            evaluation="Accurate explanation of GIL.",
            strengths=["Concise", "Accurate"],
            weaknesses=["None"],
            improvement_suggestions=["Mention multiprocessing alternative"],
            answered_at=timezone.now(),
        )
        self.result_url = reverse(
            "interview-result", kwargs={"pk": self.interview.id}
        )

    def test_50_result_contains_overall_score(self):
        response = self.client.get(self.result_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(float(response.data["overall_score"]), 88.0)

    def test_51_result_contains_feedback(self):
        response = self.client.get(self.result_url)
        self.assertEqual(
            response.data["overall_feedback"],
            "Excellent interview demonstration.",
        )

    def test_52_result_contains_strengths(self):
        response = self.client.get(self.result_url)
        self.assertEqual(response.data["strengths"], ["Coding", "Design"])

    def test_53_result_contains_weaknesses(self):
        response = self.client.get(self.result_url)
        self.assertEqual(response.data["weaknesses"], ["Edge cases"])

    def test_54_result_contains_recommendations(self):
        response = self.client.get(self.result_url)
        self.assertEqual(
            response.data["recommendations"], ["Practice multithreading"]
        )

    def test_55_result_contains_question_wise_evaluations(self):
        response = self.client.get(self.result_url)
        self.assertEqual(len(response.data["questions"]), 1)
        q_item = response.data["questions"][0]
        self.assertEqual(q_item["question_text"], "Explain Python GIL.")
        self.assertIn("answer", q_item)
        self.assertEqual(float(q_item["answer"]["score"]), 88.0)
        self.assertEqual(
            q_item["answer"]["evaluation"], "Accurate explanation of GIL."
        )


@override_settings(GEMINI_API_KEY="test-mock-api-key")
class AIInterviewGeminiSecurityTests(TestCase):
    @patch("apps.ai_interview.services.evaluation.genai.Client")
    def test_56_api_key_is_never_included_in_response(self, mock_client):
        mock_response = mock_client.return_value.models.generate_content.return_value
        mock_response.text = json.dumps(MOCK_EVALUATION_PAYLOAD)

        result = evaluate_interview_answer(
            question_text="What is recursion?",
            question_type="TECHNICAL",
            topic="Algorithms",
            target_role="Software Engineer",
            experience_level="BEGINNER",
            answer_text="A function calling itself.",
        )
        serialized = json.dumps(result)
        self.assertNotIn("test-mock-api-key", serialized)

    @patch("apps.ai_interview.services.evaluation.genai.Client")
    def test_57_raw_gemini_exception_is_not_exposed(self, mock_client):
        mock_client.return_value.models.generate_content.side_effect = Exception(
            "SecretInternalError: credentials expired"
        )
        with self.assertRaises(GeminiAPIError) as ctx:
            evaluate_interview_answer(
                question_text="What is recursion?",
                question_type="TECHNICAL",
                topic="Algorithms",
                target_role="Software Engineer",
                experience_level="BEGINNER",
                answer_text="A function calling itself.",
            )
        self.assertNotIn("credentials expired", str(ctx.exception))

    @patch("apps.ai_interview.services.evaluation.genai.Client")
    def test_58_malformed_gemini_response_handled_safely(self, mock_client):
        mock_response = mock_client.return_value.models.generate_content.return_value
        mock_response.text = "{ not valid json"
        with self.assertRaises(InvalidGeminiResponseError):
            evaluate_interview_answer(
                question_text="What is recursion?",
                question_type="TECHNICAL",
                topic="Algorithms",
                target_role="Software Engineer",
                experience_level="BEGINNER",
                answer_text="A function calling itself.",
            )
