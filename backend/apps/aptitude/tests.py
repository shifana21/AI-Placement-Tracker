import json
from decimal import Decimal
from unittest.mock import MagicMock, patch

from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from apps.accounts.models import User
from apps.aptitude.models import AptitudeAnswer, AptitudeAttempt, AptitudeQuestion
from apps.aptitude.services.ai_analysis import (
    GeminiAPIError,
    GeminiConfigurationError,
    InvalidGeminiResponseError,
    analyze_aptitude_performance,
    validate_ai_analysis_result,
)
from apps.aptitude.services.analytics import get_student_aptitude_analytics
from apps.aptitude.services.scoring import calculate_attempt_results

VALID_AI_RESULT = {
    "overall_assessment": "The candidate has demonstrated solid quantitative aptitude but needs practice on complex reasoning.",
    "strengths": ["Percentages", "Number Series"],
    "weak_areas": ["Time and Work", "Syllogisms"],
    "topic_analysis": [
        {
            "topic": "Percentages",
            "performance": "High accuracy on standard percentage calculations.",
            "recommendation": "Maintain consistency and practice multi-step word problems.",
        },
        {
            "topic": "Time and Work",
            "performance": "Struggles with inverse rate formulas.",
            "recommendation": "Review LCM method for pipes and cisterns.",
        },
    ],
    "study_recommendations": [
        "Dedicate 30 minutes daily to logical reasoning.",
        "Practice 15 time-and-work problems under timed conditions.",
    ],
    "practice_strategy": [
        "Start with easy questions to build pacing.",
        "Use elimination techniques for verbal and syllogisms.",
    ],
    "recommended_focus": ["Time and Work", "Syllogisms"],
}


class AptitudeQuestionAPITests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email="student1@example.com",
            password="TestPassword123",
            first_name="Alice",
            last_name="Student",
        )
        self.other_user = User.objects.create_user(
            email="student2@example.com",
            password="TestPassword123",
            first_name="Bob",
            last_name="Student",
        )

        self.q_quant_easy = AptitudeQuestion.objects.create(
            category=AptitudeQuestion.Category.QUANTITATIVE,
            topic="Percentages",
            difficulty=AptitudeQuestion.Difficulty.EASY,
            question_text="What is 10% of 100?",
            option_a="5",
            option_b="10",
            option_c="15",
            option_d="20",
            correct_option="B",
            explanation="10% of 100 is 10.",
            marks=1,
            is_active=True,
        )
        self.q_quant_med = AptitudeQuestion.objects.create(
            category=AptitudeQuestion.Category.QUANTITATIVE,
            topic="Profit and Loss",
            difficulty=AptitudeQuestion.Difficulty.MEDIUM,
            question_text="Cost is 50, selling price is 60. Profit %?",
            option_a="10%",
            option_b="20%",
            option_c="15%",
            option_d="25%",
            correct_option="B",
            explanation="Profit is 10/50 = 20%.",
            marks=1,
            is_active=True,
        )
        self.q_logic_hard = AptitudeQuestion.objects.create(
            category=AptitudeQuestion.Category.LOGICAL,
            topic="Number Series",
            difficulty=AptitudeQuestion.Difficulty.HARD,
            question_text="Find next: 2, 4, 8, 16, ?",
            option_a="24",
            option_b="30",
            option_c="32",
            option_d="64",
            correct_option="C",
            explanation="Powers of 2.",
            marks=2,
            is_active=True,
        )
        self.q_inactive = AptitudeQuestion.objects.create(
            category=AptitudeQuestion.Category.VERBAL,
            topic="Vocabulary",
            difficulty=AptitudeQuestion.Difficulty.EASY,
            question_text="Draft question not ready yet?",
            option_a="A",
            option_b="B",
            option_c="C",
            option_d="D",
            correct_option="A",
            explanation="None",
            marks=1,
            is_active=False,
        )

        self.list_url = reverse("aptitude-question-list")

    def test_01_authenticated_user_can_list_questions(self):
        self.client.force_authenticate(user=self.user)
        response = self.client.get(self.list_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # Should include active questions
        self.assertEqual(len(response.data), 3)

    def test_02_unauthenticated_user_receives_401(self):
        response = self.client.get(self.list_url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_03_inactive_questions_are_not_returned(self):
        self.client.force_authenticate(user=self.user)
        response = self.client.get(self.list_url)
        returned_ids = [q["id"] for q in response.data]
        self.assertNotIn(self.q_inactive.id, returned_ids)

    def test_04_category_filtering_works(self):
        self.client.force_authenticate(user=self.user)
        response = self.client.get(f"{self.list_url}?category=QUANTITATIVE")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 2)
        for q in response.data:
            self.assertEqual(q["category"], "QUANTITATIVE")

    def test_05_topic_filtering_works(self):
        self.client.force_authenticate(user=self.user)
        response = self.client.get(f"{self.list_url}?topic=Percentages")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]["id"], self.q_quant_easy.id)

    def test_06_difficulty_filtering_works(self):
        self.client.force_authenticate(user=self.user)
        response = self.client.get(f"{self.list_url}?difficulty=HARD")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]["id"], self.q_logic_hard.id)

    def test_07_correct_answer_is_not_exposed_in_list_or_detail(self):
        self.client.force_authenticate(user=self.user)
        # Check list
        response = self.client.get(self.list_url)
        for item in response.data:
            self.assertNotIn("correct_option", item)
            self.assertNotIn("explanation", item)

        # Check detail
        detail_url = reverse(
            "aptitude-question-detail",
            kwargs={"pk": self.q_quant_easy.id},
        )
        detail_res = self.client.get(detail_url)
        self.assertEqual(detail_res.status_code, status.HTTP_200_OK)
        self.assertNotIn("correct_option", detail_res.data)
        self.assertNotIn("explanation", detail_res.data)

    def test_08_explanation_is_not_exposed_before_submission(self):
        self.client.force_authenticate(user=self.user)
        detail_url = reverse(
            "aptitude-question-detail",
            kwargs={"pk": self.q_quant_med.id},
        )
        response = self.client.get(detail_url)
        self.assertNotIn("explanation", response.data)
        self.assertNotIn("correct_option", response.data)


class AptitudeAttemptAPITests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email="attempt_student@example.com",
            password="TestPassword123",
            first_name="Candidate",
            last_name="One",
        )
        self.other_user = User.objects.create_user(
            email="other_student@example.com",
            password="TestPassword123",
            first_name="Candidate",
            last_name="Two",
        )

        # Create 5 questions
        self.questions = []
        for i in range(1, 6):
            q = AptitudeQuestion.objects.create(
                category=AptitudeQuestion.Category.QUANTITATIVE,
                topic="Percentages",
                difficulty=AptitudeQuestion.Difficulty.EASY,
                question_text=f"Sample Question {i}?",
                option_a="A",
                option_b="B",
                option_c="C",
                option_d="D",
                correct_option="A",
                explanation=f"Explanation for question {i}.",
                marks=1,
                is_active=True,
            )
            self.questions.append(q)

        self.start_url = reverse("aptitude-attempt-start")
        self.history_url = reverse("aptitude-attempt-list")

    def test_09_user_can_start_a_test(self):
        self.client.force_authenticate(user=self.user)
        payload = {
            "category": "QUANTITATIVE",
            "topic": "Percentages",
            "difficulty": "EASY",
            "number_of_questions": 3,
        }
        response = self.client.post(self.start_url, data=payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIn("attempt_id", response.data)
        self.assertEqual(response.data["total_questions"], 3)
        self.assertEqual(len(response.data["questions"]), 3)

    def test_10_test_creates_answer_records(self):
        self.client.force_authenticate(user=self.user)
        payload = {"number_of_questions": 3}
        response = self.client.post(self.start_url, data=payload, format="json")
        attempt_id = response.data["attempt_id"]

        attempt = AptitudeAttempt.objects.get(id=attempt_id)
        self.assertEqual(attempt.answers.count(), 3)
        for ans in attempt.answers.all():
            self.assertEqual(ans.selected_option, "")
            self.assertFalse(ans.is_correct)
            self.assertIsNone(ans.answered_at)

    def test_11_random_question_selection_works(self):
        self.client.force_authenticate(user=self.user)
        payload = {"number_of_questions": 2}
        response = self.client.post(self.start_url, data=payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        ids = [q["id"] for q in response.data["questions"]]
        self.assertEqual(len(set(ids)), 2)

    def test_12_insufficient_questions_returns_400(self):
        self.client.force_authenticate(user=self.user)
        payload = {
            "category": "QUANTITATIVE",
            "number_of_questions": 50,  # Only 5 exist
        }
        response = self.client.post(self.start_url, data=payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("error", response.data)

    def test_13_number_of_questions_validation_works(self):
        self.client.force_authenticate(user=self.user)
        # Negative or 0
        response = self.client.post(
            self.start_url,
            data={"number_of_questions": 0},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        # Exceeds maximum (51 > 50)
        response2 = self.client.post(
            self.start_url,
            data={"number_of_questions": 51},
            format="json",
        )
        self.assertEqual(response2.status_code, status.HTTP_400_BAD_REQUEST)

    def test_14_user_cannot_access_another_users_attempt(self):
        attempt = AptitudeAttempt.objects.create(
            student=self.other_user,
            total_questions=3,
        )

        self.client.force_authenticate(user=self.user)
        detail_url = reverse("aptitude-attempt-detail", kwargs={"pk": attempt.id})
        response = self.client.get(detail_url)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_15_user_cannot_answer_a_question_outside_the_attempt(self):
        self.client.force_authenticate(user=self.user)
        start_res = self.client.post(
            self.start_url,
            data={"number_of_questions": 2},
            format="json",
        )
        attempt_id = start_res.data["attempt_id"]
        in_attempt_ids = [q["id"] for q in start_res.data["questions"]]

        outside_question = AptitudeQuestion.objects.exclude(
            id__in=in_attempt_ids
        ).first()

        answer_url = reverse(
            "aptitude-attempt-answer",
            kwargs={"attempt_id": attempt_id},
        )
        ans_res = self.client.post(
            answer_url,
            data={"question_id": outside_question.id, "selected_option": "A"},
            format="json",
        )
        self.assertEqual(ans_res.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("not part of this attempt", ans_res.data["error"])

    def test_16_duplicate_answer_is_rejected(self):
        self.client.force_authenticate(user=self.user)
        start_res = self.client.post(
            self.start_url,
            data={"number_of_questions": 2},
            format="json",
        )
        attempt_id = start_res.data["attempt_id"]
        q_id = start_res.data["questions"][0]["id"]

        answer_url = reverse(
            "aptitude-attempt-answer",
            kwargs={"attempt_id": attempt_id},
        )
        first_res = self.client.post(
            answer_url,
            data={"question_id": q_id, "selected_option": "A"},
            format="json",
        )
        self.assertEqual(first_res.status_code, status.HTTP_200_OK)

        # Second attempt to answer the exact same question
        second_res = self.client.post(
            answer_url,
            data={"question_id": q_id, "selected_option": "B"},
            format="json",
        )
        self.assertEqual(second_res.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("already been answered", second_res.data["error"])

    def test_17_correctness_is_calculated_server_side(self):
        self.client.force_authenticate(user=self.user)
        start_res = self.client.post(
            self.start_url,
            data={"number_of_questions": 1},
            format="json",
        )
        attempt_id = start_res.data["attempt_id"]
        q_id = start_res.data["questions"][0]["id"]
        question = AptitudeQuestion.objects.get(id=q_id)

        answer_url = reverse(
            "aptitude-attempt-answer",
            kwargs={"attempt_id": attempt_id},
        )
        # We submit the wrong answer 'B' while correct is 'A'
        self.client.post(
            answer_url,
            data={"question_id": q_id, "selected_option": "B"},
            format="json",
        )

        ans_obj = AptitudeAnswer.objects.get(attempt_id=attempt_id, question_id=q_id)
        self.assertFalse(ans_obj.is_correct)
        self.assertEqual(ans_obj.marks_awarded, Decimal("0.00"))

    def test_18_client_cannot_manipulate_score(self):
        self.client.force_authenticate(user=self.user)
        start_res = self.client.post(
            self.start_url,
            data={"number_of_questions": 1},
            format="json",
        )
        attempt_id = start_res.data["attempt_id"]

        submit_url = reverse(
            "aptitude-attempt-submit",
            kwargs={"attempt_id": attempt_id},
        )
        # Client tries injecting score
        submit_res = self.client.post(
            submit_url,
            data={"score": 999, "accuracy": 100},
            format="json",
        )
        self.assertEqual(submit_res.status_code, status.HTTP_200_OK)
        # Unanswered, so score should be 0.0
        self.assertEqual(submit_res.data["score"], 0.0)

    def test_19_client_cannot_manipulate_accuracy(self):
        self.client.force_authenticate(user=self.user)
        start_res = self.client.post(
            self.start_url,
            data={"number_of_questions": 2},
            format="json",
        )
        attempt_id = start_res.data["attempt_id"]

        submit_url = reverse(
            "aptitude-attempt-submit",
            kwargs={"attempt_id": attempt_id},
        )
        submit_res = self.client.post(
            submit_url,
            data={"accuracy": 100.0},
            format="json",
        )
        self.assertEqual(submit_res.status_code, status.HTTP_200_OK)
        self.assertEqual(submit_res.data["accuracy"], 0.0)

    def test_20_submitted_attempt_becomes_immutable(self):
        self.client.force_authenticate(user=self.user)
        start_res = self.client.post(
            self.start_url,
            data={"number_of_questions": 2},
            format="json",
        )
        attempt_id = start_res.data["attempt_id"]
        q_id = start_res.data["questions"][0]["id"]

        submit_url = reverse(
            "aptitude-attempt-submit",
            kwargs={"attempt_id": attempt_id},
        )
        self.client.post(submit_url, format="json")

        # Try to answer after submission
        answer_url = reverse(
            "aptitude-attempt-answer",
            kwargs={"attempt_id": attempt_id},
        )
        ans_res = self.client.post(
            answer_url,
            data={"question_id": q_id, "selected_option": "A"},
            format="json",
        )
        self.assertEqual(ans_res.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("already submitted", ans_res.data["error"])

    def test_21_attempt_cannot_be_submitted_twice(self):
        self.client.force_authenticate(user=self.user)
        start_res = self.client.post(
            self.start_url,
            data={"number_of_questions": 2},
            format="json",
        )
        attempt_id = start_res.data["attempt_id"]

        submit_url = reverse(
            "aptitude-attempt-submit",
            kwargs={"attempt_id": attempt_id},
        )
        first_submit = self.client.post(submit_url, format="json")
        self.assertEqual(first_submit.status_code, status.HTTP_200_OK)

        second_submit = self.client.post(submit_url, format="json")
        self.assertEqual(second_submit.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("already been submitted", second_submit.data["error"])

    def test_22_time_taken_is_calculated_server_side(self):
        self.client.force_authenticate(user=self.user)
        start_res = self.client.post(
            self.start_url,
            data={"number_of_questions": 2},
            format="json",
        )
        attempt_id = start_res.data["attempt_id"]
        attempt = AptitudeAttempt.objects.get(id=attempt_id)
        # Artificially set started_at in the past
        attempt.started_at = timezone.now() - timezone.timedelta(seconds=120)
        attempt.save()

        submit_url = reverse(
            "aptitude-attempt-submit",
            kwargs={"attempt_id": attempt_id},
        )
        submit_res = self.client.post(submit_url, format="json")
        self.assertEqual(submit_res.status_code, status.HTTP_200_OK)
        self.assertGreaterEqual(submit_res.data["time_taken_seconds"], 120)

    def test_attempt_detail_exposes_answers_and_explanations_only_after_submission(self):
        self.client.force_authenticate(user=self.user)
        start_res = self.client.post(
            self.start_url,
            data={"number_of_questions": 2},
            format="json",
        )
        attempt_id = start_res.data["attempt_id"]
        q_id = start_res.data["questions"][0]["id"]

        detail_url = reverse("aptitude-attempt-detail", kwargs={"pk": attempt_id})

        # Answer 1 question
        answer_url = reverse(
            "aptitude-attempt-answer",
            kwargs={"attempt_id": attempt_id},
        )
        self.client.post(
            answer_url,
            data={"question_id": q_id, "selected_option": "A"},
            format="json",
        )

        # Before submission: no correct_option or explanation
        before_res = self.client.get(detail_url)
        self.assertEqual(before_res.status_code, status.HTTP_200_OK)
        for ans_item in before_res.data["answers"]:
            self.assertNotIn("correct_option", ans_item["question"])
            self.assertNotIn("explanation", ans_item["question"])
            self.assertNotIn("is_correct", ans_item)

        # Submit attempt
        submit_url = reverse(
            "aptitude-attempt-submit",
            kwargs={"attempt_id": attempt_id},
        )
        self.client.post(submit_url, format="json")

        # After submission: correct_option, explanation, and is_correct are present
        after_res = self.client.get(detail_url)
        self.assertEqual(after_res.status_code, status.HTTP_200_OK)
        for ans_item in after_res.data["answers"]:
            self.assertIn("correct_option", ans_item["question"])
            self.assertIn("explanation", ans_item["question"])
            self.assertIn("is_correct", ans_item)


class AptitudeScoringServiceTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email="scoring_student@example.com",
            password="TestPassword123",
        )
        self.q1 = AptitudeQuestion.objects.create(
            category=AptitudeQuestion.Category.QUANTITATIVE,
            topic="Percentages",
            difficulty=AptitudeQuestion.Difficulty.EASY,
            question_text="Q1?",
            option_a="A",
            option_b="B",
            option_c="C",
            option_d="D",
            correct_option="A",
            marks=1,
        )
        self.q2 = AptitudeQuestion.objects.create(
            category=AptitudeQuestion.Category.QUANTITATIVE,
            topic="Percentages",
            difficulty=AptitudeQuestion.Difficulty.EASY,
            question_text="Q2?",
            option_a="A",
            option_b="B",
            option_c="C",
            option_d="D",
            correct_option="B",
            marks=2,
        )

    def test_23_all_correct_answers_produce_100_percent_accuracy(self):
        attempt = AptitudeAttempt.objects.create(
            student=self.user,
            total_questions=2,
        )
        AptitudeAnswer.objects.create(
            attempt=attempt,
            question=self.q1,
            selected_option="A",
        )
        AptitudeAnswer.objects.create(
            attempt=attempt,
            question=self.q2,
            selected_option="B",
        )

        results = calculate_attempt_results(attempt)
        self.assertEqual(results["correct_answers"], 2)
        self.assertEqual(results["wrong_answers"], 0)
        self.assertEqual(results["unanswered"], 0)
        self.assertEqual(results["score"], Decimal("3.00"))
        self.assertEqual(results["accuracy"], Decimal("100.00"))

    def test_24_all_wrong_answers_produce_0_percent_accuracy(self):
        attempt = AptitudeAttempt.objects.create(
            student=self.user,
            total_questions=2,
        )
        AptitudeAnswer.objects.create(
            attempt=attempt,
            question=self.q1,
            selected_option="C",
        )
        AptitudeAnswer.objects.create(
            attempt=attempt,
            question=self.q2,
            selected_option="D",
        )

        results = calculate_attempt_results(attempt)
        self.assertEqual(results["correct_answers"], 0)
        self.assertEqual(results["wrong_answers"], 2)
        self.assertEqual(results["score"], Decimal("0.00"))
        self.assertEqual(results["accuracy"], Decimal("0.00"))

    def test_25_mixed_answers_calculate_correctly(self):
        attempt = AptitudeAttempt.objects.create(
            student=self.user,
            total_questions=2,
        )
        AptitudeAnswer.objects.create(
            attempt=attempt,
            question=self.q1,
            selected_option="A",  # Correct (1 mark)
        )
        AptitudeAnswer.objects.create(
            attempt=attempt,
            question=self.q2,
            selected_option="C",  # Wrong (0 marks)
        )

        results = calculate_attempt_results(attempt)
        self.assertEqual(results["correct_answers"], 1)
        self.assertEqual(results["wrong_answers"], 1)
        self.assertEqual(results["score"], Decimal("1.00"))
        self.assertEqual(results["accuracy"], Decimal("50.00"))

    def test_26_unanswered_questions_are_counted_correctly(self):
        attempt = AptitudeAttempt.objects.create(
            student=self.user,
            total_questions=2,
        )
        AptitudeAnswer.objects.create(
            attempt=attempt,
            question=self.q1,
            selected_option="A",
        )
        AptitudeAnswer.objects.create(
            attempt=attempt,
            question=self.q2,
            selected_option="",  # Unanswered
        )

        results = calculate_attempt_results(attempt)
        self.assertEqual(results["correct_answers"], 1)
        self.assertEqual(results["wrong_answers"], 0)
        self.assertEqual(results["unanswered"], 1)
        self.assertEqual(results["accuracy"], Decimal("50.00"))

    def test_27_zero_question_edge_case_is_handled(self):
        attempt = AptitudeAttempt.objects.create(
            student=self.user,
            total_questions=0,
        )
        results = calculate_attempt_results(attempt)
        self.assertEqual(results["total_questions"], 0)
        self.assertEqual(results["accuracy"], Decimal("0.00"))
        self.assertEqual(results["score"], Decimal("0.00"))


class AptitudeAnalyticsServiceTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email="analytics_user@example.com",
            password="TestPassword123",
        )
        self.other_user = User.objects.create_user(
            email="other_analytics@example.com",
            password="TestPassword123",
        )

        self.q_strong1 = AptitudeQuestion.objects.create(
            category=AptitudeQuestion.Category.QUANTITATIVE,
            topic="Percentages",
            difficulty=AptitudeQuestion.Difficulty.EASY,
            question_text="Q Strong 1?",
            option_a="A",
            option_b="B",
            option_c="C",
            option_d="D",
            correct_option="A",
            marks=1,
        )
        self.q_strong2 = AptitudeQuestion.objects.create(
            category=AptitudeQuestion.Category.QUANTITATIVE,
            topic="Percentages",
            difficulty=AptitudeQuestion.Difficulty.EASY,
            question_text="Q Strong 2?",
            option_a="A",
            option_b="B",
            option_c="C",
            option_d="D",
            correct_option="A",
            marks=1,
        )
        self.q_weak1 = AptitudeQuestion.objects.create(
            category=AptitudeQuestion.Category.LOGICAL,
            topic="Syllogisms",
            difficulty=AptitudeQuestion.Difficulty.HARD,
            question_text="Q Weak 1?",
            option_a="A",
            option_b="B",
            option_c="C",
            option_d="D",
            correct_option="A",
            marks=2,
        )
        self.q_weak2 = AptitudeQuestion.objects.create(
            category=AptitudeQuestion.Category.LOGICAL,
            topic="Syllogisms",
            difficulty=AptitudeQuestion.Difficulty.HARD,
            question_text="Q Weak 2?",
            option_a="A",
            option_b="B",
            option_c="C",
            option_d="D",
            correct_option="A",
            marks=2,
        )

        # Submitted attempt 1 for self.user: 2 questions in Percentages (both correct -> 100%)
        attempt1 = AptitudeAttempt.objects.create(
            student=self.user,
            category=AptitudeQuestion.Category.QUANTITATIVE,
            topic="Percentages",
            difficulty=AptitudeQuestion.Difficulty.EASY,
            total_questions=2,
            correct_answers=2,
            wrong_answers=0,
            unanswered=0,
            score=Decimal("2.00"),
            accuracy=Decimal("100.00"),
            time_taken_seconds=60,
            submitted_at=timezone.now(),
        )
        AptitudeAnswer.objects.create(
            attempt=attempt1,
            question=self.q_strong1,
            selected_option="A",
            is_correct=True,
            marks_awarded=Decimal("1.00"),
        )
        AptitudeAnswer.objects.create(
            attempt=attempt1,
            question=self.q_strong2,
            selected_option="A",
            is_correct=True,
            marks_awarded=Decimal("1.00"),
        )

        # Submitted attempt 2 for self.user: 2 questions in Syllogisms (both wrong -> 0%)
        attempt2 = AptitudeAttempt.objects.create(
            student=self.user,
            category=AptitudeQuestion.Category.LOGICAL,
            topic="Syllogisms",
            difficulty=AptitudeQuestion.Difficulty.HARD,
            total_questions=2,
            correct_answers=0,
            wrong_answers=2,
            unanswered=0,
            score=Decimal("0.00"),
            accuracy=Decimal("0.00"),
            time_taken_seconds=90,
            submitted_at=timezone.now(),
        )
        AptitudeAnswer.objects.create(
            attempt=attempt2,
            question=self.q_weak1,
            selected_option="B",
            is_correct=False,
            marks_awarded=Decimal("0.00"),
        )
        AptitudeAnswer.objects.create(
            attempt=attempt2,
            question=self.q_weak2,
            selected_option="C",
            is_correct=False,
            marks_awarded=Decimal("0.00"),
        )

        # Unsubmitted attempt for self.user (should be ignored)
        AptitudeAttempt.objects.create(
            student=self.user,
            total_questions=5,
            submitted_at=None,
        )

        # Attempt for other_user (should be completely excluded)
        other_attempt = AptitudeAttempt.objects.create(
            student=self.other_user,
            total_questions=10,
            correct_answers=10,
            score=Decimal("10.00"),
            accuracy=Decimal("100.00"),
            submitted_at=timezone.now(),
        )
        AptitudeAnswer.objects.create(
            attempt=other_attempt,
            question=self.q_weak1,
            selected_option="A",
            is_correct=True,
            marks_awarded=Decimal("2.00"),
        )

    def test_28_analytics_are_user_specific(self):
        analytics = get_student_aptitude_analytics(self.user)
        self.assertEqual(analytics["total_attempts"], 2)

    def test_29_other_users_attempts_are_excluded(self):
        analytics = get_student_aptitude_analytics(self.user)
        # Total questions: 2 + 2 = 4 (not including other_user's 10)
        self.assertEqual(analytics["total_questions"], 4)
        self.assertEqual(analytics["total_correct"], 2)

    def test_30_category_analytics_are_correct(self):
        analytics = get_student_aptitude_analytics(self.user)
        self.assertIn("QUANTITATIVE", analytics["by_category"])
        self.assertIn("LOGICAL", analytics["by_category"])
        self.assertEqual(analytics["by_category"]["QUANTITATIVE"]["accuracy"], 100.0)
        self.assertEqual(analytics["by_category"]["LOGICAL"]["accuracy"], 0.0)

    def test_31_difficulty_analytics_are_correct(self):
        analytics = get_student_aptitude_analytics(self.user)
        self.assertIn("EASY", analytics["by_difficulty"])
        self.assertIn("HARD", analytics["by_difficulty"])
        self.assertEqual(analytics["by_difficulty"]["EASY"]["accuracy"], 100.0)
        self.assertEqual(analytics["by_difficulty"]["HARD"]["accuracy"], 0.0)

    def test_32_topic_analytics_are_correct(self):
        analytics = get_student_aptitude_analytics(self.user)
        self.assertIn("Percentages", analytics["by_topic"])
        self.assertIn("Syllogisms", analytics["by_topic"])
        self.assertEqual(analytics["by_topic"]["Percentages"]["accuracy"], 100.0)
        self.assertEqual(analytics["by_topic"]["Syllogisms"]["accuracy"], 0.0)

    def test_33_weak_topics_are_detected(self):
        analytics = get_student_aptitude_analytics(self.user)
        self.assertIn("Syllogisms", analytics["weak_topics"])
        self.assertNotIn("Percentages", analytics["weak_topics"])

    def test_34_strong_topics_are_detected(self):
        analytics = get_student_aptitude_analytics(self.user)
        self.assertIn("Percentages", analytics["strong_topics"])
        self.assertNotIn("Syllogisms", analytics["strong_topics"])

    def test_35_overall_accuracy_is_correct(self):
        analytics = get_student_aptitude_analytics(self.user)
        # 2 correct out of 4 total = 50.0%
        self.assertEqual(analytics["overall_accuracy"], 50.0)

    def test_36_average_score_is_correct(self):
        analytics = get_student_aptitude_analytics(self.user)
        # Attempt 1: score 2.00, Attempt 2: score 0.00 => Avg = 1.00
        self.assertEqual(analytics["average_score"], 1.0)


@override_settings(GEMINI_API_KEY="test-mock-api-key")
class AptitudeGeminiServiceTests(TestCase):
    def test_validate_ai_analysis_result_accepts_valid_payload(self):
        result = validate_ai_analysis_result(VALID_AI_RESULT)
        self.assertIn("overall_assessment", result)
        self.assertEqual(result["strengths"], ["Percentages", "Number Series"])

    def test_validate_ai_analysis_result_rejects_missing_fields(self):
        invalid = {"overall_assessment": "Incomplete"}
        with self.assertRaises(InvalidGeminiResponseError):
            validate_ai_analysis_result(invalid)

    def test_validate_ai_analysis_result_rejects_non_dict(self):
        with self.assertRaises(InvalidGeminiResponseError):
            validate_ai_analysis_result("Not a dict")

    @patch("apps.aptitude.services.ai_analysis.genai.Client")
    def test_37_gemini_service_is_called_with_structured_performance_data(
        self,
        mock_client,
    ):
        mock_response = mock_client.return_value.models.generate_content.return_value
        mock_response.text = json.dumps(VALID_AI_RESULT)

        perf_data = {
            "total_attempts": 2,
            "overall_accuracy": 75.0,
            "average_score": 7.5,
            "by_category": {},
            "by_difficulty": {},
            "by_topic": {},
            "weak_topics": ["Time and Work"],
            "strong_topics": ["Percentages"],
            "recent_attempts": [],
        }

        result = analyze_aptitude_performance(perf_data)
        self.assertEqual(result["strengths"], ["Percentages", "Number Series"])
        mock_client.return_value.models.generate_content.assert_called_once()

    @patch("apps.aptitude.services.ai_analysis.genai.Client")
    def test_38_gemini_response_is_validated(self, mock_client):
        mock_response = mock_client.return_value.models.generate_content.return_value
        mock_response.text = json.dumps(VALID_AI_RESULT)

        result = analyze_aptitude_performance({"total_attempts": 1})
        self.assertEqual(
            result["overall_assessment"],
            VALID_AI_RESULT["overall_assessment"],
        )

    @patch("apps.aptitude.services.ai_analysis.genai.Client")
    def test_39_malformed_gemini_json_is_handled(self, mock_client):
        mock_response = mock_client.return_value.models.generate_content.return_value
        mock_response.text = "This is not valid json {"

        with self.assertRaises(InvalidGeminiResponseError):
            analyze_aptitude_performance({"total_attempts": 1})

    @patch("apps.aptitude.services.ai_analysis.genai.Client")
    def test_40_gemini_api_failure_is_handled(self, mock_client):
        mock_client.return_value.models.generate_content.side_effect = Exception(
            "Connection reset by peer"
        )

        with self.assertRaises(GeminiAPIError):
            analyze_aptitude_performance({"total_attempts": 1})

    @override_settings(GEMINI_API_KEY="")
    def test_41_missing_api_key_is_handled_safely(self):
        with self.assertRaises(GeminiConfigurationError):
            analyze_aptitude_performance({"total_attempts": 1})

    @patch("apps.aptitude.services.ai_analysis.genai.Client")
    def test_42_api_key_is_never_returned_in_responses(self, mock_client):
        mock_response = mock_client.return_value.models.generate_content.return_value
        mock_response.text = json.dumps(VALID_AI_RESULT)

        result = analyze_aptitude_performance({"total_attempts": 1})
        serialized = json.dumps(result)
        self.assertNotIn("test-mock-api-key", serialized)


@override_settings(GEMINI_API_KEY="test-mock-api-key")
class AptitudeAIAnalysisAPITests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email="ai_test_user@example.com",
            password="TestPassword123",
        )
        self.url = reverse("aptitude-ai-analysis")

    def test_ai_analysis_fails_if_no_submitted_attempts(self):
        self.client.force_authenticate(user=self.user)
        response = self.client.post(self.url)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("No submitted attempts found", response.data["error"])

    @patch("apps.aptitude.views.analyze_aptitude_performance")
    def test_ai_analysis_success_returns_structured_payload(self, mock_analyze):
        mock_analyze.return_value = VALID_AI_RESULT

        # Create one submitted attempt
        AptitudeAttempt.objects.create(
            student=self.user,
            total_questions=5,
            correct_answers=4,
            submitted_at=timezone.now(),
        )

        self.client.force_authenticate(user=self.user)
        response = self.client.post(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            response.data["overall_assessment"],
            VALID_AI_RESULT["overall_assessment"],
        )
        self.assertEqual(response.data["strengths"], ["Percentages", "Number Series"])

    @patch("apps.aptitude.views.analyze_aptitude_performance")
    def test_ai_analysis_handles_gemini_api_error(self, mock_analyze):
        mock_analyze.side_effect = GeminiAPIError("Gemini unavailable")

        AptitudeAttempt.objects.create(
            student=self.user,
            total_questions=5,
            submitted_at=timezone.now(),
        )

        self.client.force_authenticate(user=self.user)
        response = self.client.post(self.url)
        self.assertEqual(response.status_code, status.HTTP_502_BAD_GATEWAY)
        self.assertIn("error", response.data)
        # Ensure raw exception details / API keys are not exposed
        self.assertNotIn("Gemini unavailable", response.data["error"])

    @patch("apps.aptitude.views.analyze_aptitude_performance")
    def test_ai_analysis_handles_gemini_config_error(self, mock_analyze):
        mock_analyze.side_effect = GeminiConfigurationError("Missing key")

        AptitudeAttempt.objects.create(
            student=self.user,
            total_questions=5,
            submitted_at=timezone.now(),
        )

        self.client.force_authenticate(user=self.user)
        response = self.client.post(self.url)
        self.assertEqual(
            response.status_code,
            status.HTTP_500_INTERNAL_SERVER_ERROR,
        )
        self.assertIn("not properly configured", response.data["error"])
