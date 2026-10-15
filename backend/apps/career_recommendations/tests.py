from decimal import Decimal
import json
from unittest.mock import MagicMock, patch

from django.test import TestCase, override_settings
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from apps.accounts.models import User
from apps.career_recommendations.models import CareerRecommendation
from apps.career_recommendations.services.ai_advisor import (
    GeminiAPIError,
    GeminiConfigurationError,
    InvalidGeminiResponseError,
    enrich_recommendation_with_gemini,
)
from apps.career_recommendations.services.data_collector import (
    collect_student_evidence,
)
from apps.career_recommendations.services.matching_engine import (
    compute_role_match,
    generate_baseline_recommendations,
    match_skills,
)
from apps.career_recommendations.services.recommendation_service import (
    generate_student_career_recommendations,
)
from apps.coding_progress.models import CodingProblem
from apps.profiles.models import StudentProfile

MOCK_AI_PAYLOAD = {
    "target_role": "Backend Developer",
    "explanation": "Strong alignment with backend development based on Python and SQL skills.",
    "matching_skills": ["python", "django", "sql"],
    "missing_skills": ["docker", "redis"],
    "recommended_skills": ["docker", "redis"],
    "suggested_projects": [
        "Distributed task queue with Redis and Django",
        "Containerized REST API using Docker and PostgreSQL",
    ],
    "learning_roadmap": [
        {
            "phase": "Phase 1: Containerization",
            "focus_areas": ["docker"],
            "goal": "Build and run multi-container applications.",
        },
        {
            "phase": "Phase 2: In-Memory Caching",
            "focus_areas": ["redis"],
            "goal": "Optimize backend queries and caching.",
        },
    ],
}


@override_settings(GEMINI_API_KEY="test-mock-api-key")
class CareerRecommendationsAuthTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email="auth_career@example.com",
            password="TestPassword123",
        )
        self.rec = CareerRecommendation.objects.create(
            student=self.user,
            target_role="Backend Developer",
            match_score=Decimal("80.00"),
            explanation="Initial test rec",
        )

    def test_unauthenticated_generate_rejected(self):
        url = reverse("career-generate")
        response = self.client.post(url, {})
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_unauthenticated_list_rejected(self):
        url = reverse("career-list")
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_unauthenticated_detail_rejected(self):
        url = reverse("career-detail", kwargs={"pk": self.rec.id})
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_unauthenticated_refresh_rejected(self):
        url = reverse("career-refresh")
        response = self.client.post(url, {})
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_unauthenticated_skill_gaps_rejected(self):
        url = reverse("career-skill-gaps")
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_unauthenticated_roadmap_rejected(self):
        url = reverse("career-roadmap")
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


@override_settings(GEMINI_API_KEY="test-mock-api-key")
class CareerRecommendationsEngineTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email="engine_student@example.com",
            password="TestPassword123",
        )

    def test_skill_matching_exact_and_substring(self):
        candidate_skills = ["python", "django rest framework", "sql"]
        required = ["python", "django", "sql", "git"]
        preferred = ["docker", "redis"]

        result = match_skills(candidate_skills, required, preferred)
        self.assertIn("python", result["matching_skills"])
        self.assertIn("django", result["matching_skills"])
        self.assertIn("sql", result["matching_skills"])
        self.assertIn("git", result["missing_skills"])
        self.assertIn("docker", result["missing_skills"])

    def test_missing_profile_and_source_data_handles_gracefully(self):
        # User has no profile, no resume, no coding, no aptitude, no interview
        evidence = collect_student_evidence(self.user)
        self.assertFalse(evidence["profile"]["exists"])
        self.assertFalse(evidence["resume"]["exists"])
        self.assertEqual(evidence["coding"]["total_solved"], 0)
        self.assertEqual(evidence["all_candidate_skills"], [])

        recs, _ = generate_baseline_recommendations(self.user)
        self.assertEqual(len(recs), 3)
        for r in recs:
            self.assertGreaterEqual(r["match_score"], Decimal("0.00"))
            self.assertLessEqual(r["match_score"], Decimal("100.00"))

    def test_candidate_skills_increase_match_score(self):
        # Baseline score with no skills
        recs_empty, _ = generate_baseline_recommendations(self.user)
        score_empty = recs_empty[0]["match_score"]

        # Add profile skills matching Backend Developer
        StudentProfile.objects.create(
            user=self.user,
            skills="Python, Django, SQL, REST API, Git, Database",
        )
        recs_with_skills, _ = generate_baseline_recommendations(self.user)
        backend_rec = next(
            r for r in recs_with_skills if r["target_role"] == "Backend Developer"
        )
        self.assertGreater(backend_rec["match_score"], score_empty)
        self.assertIn("python", backend_rec["matching_skills"])

    def test_coding_history_increases_composite_score(self):
        StudentProfile.objects.create(
            user=self.user,
            skills="Python, SQL",
        )
        recs_before, _ = generate_baseline_recommendations(self.user)
        score_before = next(
            r for r in recs_before if r["target_role"] == "Backend Developer"
        )["match_score"]

        # Add coding problems
        for i in range(10):
            CodingProblem.objects.create(
                student=self.user,
                platform="LEETCODE",
                difficulty="MEDIUM",
                topic="Arrays",
                title=f"Problem {i}",
            )

        recs_after, _ = generate_baseline_recommendations(self.user)
        score_after = next(
            r for r in recs_after if r["target_role"] == "Backend Developer"
        )["match_score"]
        self.assertGreater(score_after, score_before)


@override_settings(GEMINI_API_KEY="test-mock-api-key")
class CareerRecommendationsAPITests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email="career_api_user@example.com",
            password="TestPassword123",
        )
        self.other_user = User.objects.create_user(
            email="other_career_user@example.com",
            password="TestPassword123",
        )
        StudentProfile.objects.create(
            user=self.user,
            skills="Python, Django, React, SQL",
            branch="Computer Science",
            cgpa=Decimal("8.50"),
        )
        self.client.force_authenticate(user=self.user)

    @patch(
        "apps.career_recommendations.services.recommendation_service.enrich_recommendation_with_gemini"
    )
    def test_generate_recommendations_creates_records(self, mock_enrich):
        mock_enrich.return_value = MOCK_AI_PAYLOAD
        url = reverse("career-generate")
        response = self.client.post(url, format="json")

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(len(response.data), 3)
        self.assertEqual(
            CareerRecommendation.objects.filter(student=self.user).count(),
            3,
        )
        first = response.data[0]
        self.assertIn("target_role", first)
        self.assertIn("match_score", first)
        self.assertIn("matching_skills", first)
        self.assertIn("missing_skills", first)
        self.assertIn("suggested_projects", first)
        self.assertIn("learning_roadmap", first)

    @patch(
        "apps.career_recommendations.services.recommendation_service.enrich_recommendation_with_gemini"
    )
    def test_list_recommendations_scoped_to_current_user(self, mock_enrich):
        mock_enrich.return_value = MOCK_AI_PAYLOAD
        self.client.post(reverse("career-generate"), format="json")

        # Create record for other user
        CareerRecommendation.objects.create(
            student=self.other_user,
            target_role="Data Scientist",
            match_score=Decimal("90.00"),
        )

        response = self.client.get(reverse("career-list"))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 3)
        for item in response.data:
            self.assertEqual(item["student"], self.user.email)

    def test_detail_recommendation_accessible_only_by_owner(self):
        own_rec = CareerRecommendation.objects.create(
            student=self.user,
            target_role="Backend Developer",
            match_score=Decimal("82.00"),
        )
        other_rec = CareerRecommendation.objects.create(
            student=self.other_user,
            target_role="DevOps Engineer",
            match_score=Decimal("70.00"),
        )

        # Access own rec -> 200
        url_own = reverse("career-detail", kwargs={"pk": own_rec.id})
        res_own = self.client.get(url_own)
        self.assertEqual(res_own.status_code, status.HTTP_200_OK)
        self.assertEqual(res_own.data["id"], own_rec.id)

        # Access other rec -> 404
        url_other = reverse("career-detail", kwargs={"pk": other_rec.id})
        res_other = self.client.get(url_other)
        self.assertEqual(res_other.status_code, status.HTTP_404_NOT_FOUND)

    @patch(
        "apps.career_recommendations.services.recommendation_service.enrich_recommendation_with_gemini"
    )
    def test_refresh_recalculates_and_returns_latest(self, mock_enrich):
        mock_enrich.return_value = MOCK_AI_PAYLOAD
        url = reverse("career-refresh")
        response = self.client.post(url, format="json")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 3)

    def test_skill_gaps_endpoint_returns_matching_and_missing(self):
        CareerRecommendation.objects.create(
            student=self.user,
            target_role="Backend Developer",
            match_score=Decimal("75.00"),
            matching_skills=["python", "django", "sql"],
            missing_skills=["docker", "redis"],
            recommended_skills=["docker", "redis"],
        )
        url = reverse("career-skill-gaps")
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertGreaterEqual(len(response.data), 1)
        item = response.data[0]
        self.assertEqual(item["target_role"], "Backend Developer")
        self.assertEqual(item["matching_skills"], ["python", "django", "sql"])
        self.assertEqual(item["missing_skills"], ["docker", "redis"])
        self.assertEqual(item["priority_skills"], ["docker", "redis"])

    def test_roadmap_endpoint_returns_roadmap_and_projects(self):
        CareerRecommendation.objects.create(
            student=self.user,
            target_role="Backend Developer",
            match_score=Decimal("75.00"),
            suggested_projects=["Build Redis Cache"],
            learning_roadmap=[{"phase": "1", "goal": "Learn Docker"}],
        )
        url = reverse("career-roadmap")
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertGreaterEqual(len(response.data), 1)
        item = response.data[0]
        self.assertEqual(item["suggested_projects"], ["Build Redis Cache"])
        self.assertEqual(
            item["learning_roadmap"], [{"phase": "1", "goal": "Learn Docker"}]
        )

    def test_client_cannot_inject_match_score(self):
        # Client tries injecting custom match score into generate or refresh
        url = reverse("career-generate")
        with patch(
            "apps.career_recommendations.services.recommendation_service.enrich_recommendation_with_gemini",
            return_value=MOCK_AI_PAYLOAD,
        ):
            response = self.client.post(
                url, {"match_score": 100.0, "target_role": "CEO"}, format="json"
            )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        # Score must be calculated server-side, not client 100.0
        rec = CareerRecommendation.objects.get(id=response.data[0]["id"])
        self.assertNotEqual(rec.target_role, "CEO")


@override_settings(GEMINI_API_KEY="test-mock-api-key")
class CareerRecommendationsGeminiTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email="gemini_career@example.com",
            password="TestPassword123",
        )

    @patch("apps.career_recommendations.services.ai_advisor.genai.Client")
    def test_gemini_enrichment_validates_and_parses_json(self, mock_client):
        mock_response = mock_client.return_value.models.generate_content.return_value
        mock_response.text = json.dumps(MOCK_AI_PAYLOAD)

        role_match = {
            "target_role": "Backend Developer",
            "match_score": Decimal("80.00"),
            "matching_skills": ["python", "django"],
            "missing_skills": ["docker"],
        }
        evidence = {"all_candidate_skills": ["python", "django"]}

        result = enrich_recommendation_with_gemini(role_match, evidence)
        self.assertEqual(result["target_role"], "Backend Developer")
        self.assertEqual(result["matching_skills"], ["python", "django", "sql"])
        self.assertIn("suggested_projects", result)
        self.assertIn("learning_roadmap", result)

    @override_settings(GEMINI_API_KEY="")
    def test_missing_gemini_api_key_handled(self):
        role_match = {
            "target_role": "Backend Developer",
            "match_score": Decimal("80.00"),
        }
        with self.assertRaises(GeminiConfigurationError):
            enrich_recommendation_with_gemini(role_match, {})

    @patch("apps.career_recommendations.services.ai_advisor.genai.Client")
    def test_gemini_api_failure_handled(self, mock_client):
        mock_client.return_value.models.generate_content.side_effect = Exception(
            "Connection timeout"
        )
        role_match = {
            "target_role": "Backend Developer",
            "match_score": Decimal("80.00"),
        }
        with self.assertRaises(GeminiAPIError):
            enrich_recommendation_with_gemini(role_match, {})

    @patch("apps.career_recommendations.services.ai_advisor.genai.Client")
    def test_malformed_gemini_json_handled(self, mock_client):
        mock_response = mock_client.return_value.models.generate_content.return_value
        mock_response.text = "This is not valid json {"

        role_match = {
            "target_role": "Backend Developer",
            "match_score": Decimal("80.00"),
        }
        with self.assertRaises(InvalidGeminiResponseError):
            enrich_recommendation_with_gemini(role_match, {})

    @patch(
        "apps.career_recommendations.services.recommendation_service.enrich_recommendation_with_gemini"
    )
    def test_repeated_generation_creates_fresh_snapshots_safely(self, mock_enrich):
        mock_enrich.return_value = MOCK_AI_PAYLOAD
        recs1 = generate_student_career_recommendations(self.user, top_n=2)
        recs2 = generate_student_career_recommendations(self.user, top_n=2)
        self.assertEqual(len(recs1), 2)
        self.assertEqual(len(recs2), 2)
        self.assertEqual(
            CareerRecommendation.objects.filter(student=self.user).count(),
            4,
        )
