import datetime
from datetime import timedelta

from django.db import IntegrityError
from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient

from apps.accounts.models import User
from apps.coding_progress.models import CodingProblem


class CodingProblemAPITests(TestCase):
    def setUp(self):
        self.client = APIClient()

        self.user = User.objects.create_user(
            email="student@test.com",
            password="TestPassword123",
            first_name="Test",
            last_name="Student",
        )

        self.other_user = User.objects.create_user(
            email="other@test.com",
            password="TestPassword123",
            first_name="Other",
            last_name="Student",
        )

        self.client.force_authenticate(user=self.user)

    # -------------------------------------------------------------------------
    # Authentication Tests
    # -------------------------------------------------------------------------
    def test_unauthenticated_list_returns_401(self):
        self.client.force_authenticate(user=None)
        response = self.client.get("/api/coding/")
        self.assertEqual(response.status_code, 401)

    def test_unauthenticated_create_returns_401(self):
        self.client.force_authenticate(user=None)
        response = self.client.post(
            "/api/coding/",
            {
                "platform": "LEETCODE",
                "difficulty": "EASY",
                "topic": "Arrays",
                "title": "Two Sum",
                "solved_at": timezone.now().isoformat(),
            },
            format="json",
        )
        self.assertEqual(response.status_code, 401)

    def test_unauthenticated_detail_returns_401(self):
        self.client.force_authenticate(user=None)
        problem = CodingProblem.objects.create(
            student=self.user,
            platform="LEETCODE",
            difficulty="EASY",
            topic="Arrays",
            title="Two Sum",
            solved_at=timezone.now(),
        )
        response = self.client.get(f"/api/coding/{problem.id}/")
        self.assertEqual(response.status_code, 401)

    def test_unauthenticated_stats_returns_401(self):
        self.client.force_authenticate(user=None)
        response = self.client.get("/api/coding/stats/")
        self.assertEqual(response.status_code, 401)

    # -------------------------------------------------------------------------
    # Create Tests
    # -------------------------------------------------------------------------
    def test_authenticated_user_can_create_coding_problem(self):
        now = timezone.now()
        response = self.client.post(
            "/api/coding/",
            {
                "platform": "LEETCODE",
                "difficulty": "MEDIUM",
                "topic": "Arrays",
                "title": "Two Sum",
                "problem_url": "https://leetcode.com/problems/two-sum/",
                "solved_independently": True,
                "solved_at": now.isoformat(),
                "notes": "Used hash map approach",
            },
            format="json",
        )

        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data["platform"], "LEETCODE")
        self.assertEqual(response.data["difficulty"], "MEDIUM")
        self.assertEqual(response.data["topic"], "Arrays")
        self.assertEqual(response.data["title"], "Two Sum")
        self.assertEqual(response.data["student"], "student@test.com")
        self.assertEqual(response.data["notes"], "Used hash map approach")
        self.assertEqual(response.data["solved_independently"], True)

    def test_student_automatically_assigned_from_request_user(self):
        response = self.client.post(
            "/api/coding/",
            {
                "platform": "LEETCODE",
                "difficulty": "EASY",
                "topic": "Strings",
                "title": "Valid Anagram",
                "solved_at": timezone.now().isoformat(),
            },
            format="json",
        )

        self.assertEqual(response.status_code, 201)
        problem = CodingProblem.objects.get(id=response.data["id"])
        self.assertEqual(problem.student, self.user)

    def test_client_cannot_assign_another_student(self):
        response = self.client.post(
            "/api/coding/",
            {
                "student": "other@test.com",
                "platform": "LEETCODE",
                "difficulty": "EASY",
                "topic": "Strings",
                "title": "Valid Palindrome",
                "solved_at": timezone.now().isoformat(),
            },
            format="json",
        )

        self.assertEqual(response.status_code, 201)
        problem = CodingProblem.objects.get(id=response.data["id"])
        self.assertEqual(problem.student, self.user)
        self.assertNotEqual(problem.student, self.other_user)

    # -------------------------------------------------------------------------
    # Read Tests
    # -------------------------------------------------------------------------
    def test_user_can_list_own_problems(self):
        CodingProblem.objects.create(
            student=self.user,
            platform="LEETCODE",
            difficulty="EASY",
            topic="Arrays",
            title="Two Sum",
            solved_at=timezone.now(),
        )

        response = self.client.get("/api/coding/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]["student"], "student@test.com")
        self.assertEqual(response.data[0]["title"], "Two Sum")

    def test_user_cannot_access_other_users_problem(self):
        other_problem = CodingProblem.objects.create(
            student=self.other_user,
            platform="HACKERRANK",
            difficulty="MEDIUM",
            topic="Strings",
            title="Special String Again",
            solved_at=timezone.now(),
        )

        # In list: must not appear
        list_resp = self.client.get("/api/coding/")
        self.assertEqual(list_resp.status_code, 200)
        self.assertEqual(len(list_resp.data), 0)

        # In detail: must return 404 (no leak)
        detail_resp = self.client.get(f"/api/coding/{other_problem.id}/")
        self.assertEqual(detail_resp.status_code, 404)

    def test_empty_list_works_correctly(self):
        response = self.client.get("/api/coding/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data, [])

    def test_list_ordered_by_newest_solved_at_first(self):
        now = timezone.now()
        CodingProblem.objects.create(
            student=self.user,
            platform="LEETCODE",
            difficulty="EASY",
            topic="Arrays",
            title="Oldest Problem",
            solved_at=now - timedelta(days=5),
        )
        CodingProblem.objects.create(
            student=self.user,
            platform="HACKERRANK",
            difficulty="MEDIUM",
            topic="Strings",
            title="Newest Problem",
            solved_at=now,
        )
        CodingProblem.objects.create(
            student=self.user,
            platform="CODECHEF",
            difficulty="HARD",
            topic="DP",
            title="Middle Problem",
            solved_at=now - timedelta(days=2),
        )

        response = self.client.get("/api/coding/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 3)
        self.assertEqual(response.data[0]["title"], "Newest Problem")
        self.assertEqual(response.data[1]["title"], "Middle Problem")
        self.assertEqual(response.data[2]["title"], "Oldest Problem")

    # -------------------------------------------------------------------------
    # Update Tests
    # -------------------------------------------------------------------------
    def test_user_can_update_own_problem(self):
        problem = CodingProblem.objects.create(
            student=self.user,
            platform="LEETCODE",
            difficulty="EASY",
            topic="Arrays",
            title="Two Sum",
            solved_at=timezone.now(),
        )

        response = self.client.patch(
            f"/api/coding/{problem.id}/",
            {
                "difficulty": "MEDIUM",
                "solved_independently": False,
                "notes": "Reviewed editorial solution",
            },
            format="json",
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["difficulty"], "MEDIUM")
        self.assertEqual(response.data["solved_independently"], False)
        self.assertEqual(response.data["notes"], "Reviewed editorial solution")

    def test_user_cannot_update_other_users_problem(self):
        problem = CodingProblem.objects.create(
            student=self.other_user,
            platform="HACKERRANK",
            difficulty="MEDIUM",
            topic="Strings",
            title="String Construction",
            solved_at=timezone.now(),
        )

        response = self.client.patch(
            f"/api/coding/{problem.id}/",
            {"notes": "Malicious edit attempt"},
            format="json",
        )

        self.assertEqual(response.status_code, 404)
        problem.refresh_from_db()
        self.assertNotEqual(problem.notes, "Malicious edit attempt")

    def test_ownership_cannot_be_changed(self):
        problem = CodingProblem.objects.create(
            student=self.user,
            platform="LEETCODE",
            difficulty="EASY",
            topic="Arrays",
            title="Two Sum",
            solved_at=timezone.now(),
        )

        response = self.client.patch(
            f"/api/coding/{problem.id}/",
            {"student": "other@test.com"},
            format="json",
        )

        self.assertEqual(response.status_code, 200)
        problem.refresh_from_db()
        self.assertEqual(problem.student, self.user)

    # -------------------------------------------------------------------------
    # Delete Tests
    # -------------------------------------------------------------------------
    def test_user_can_delete_own_problem(self):
        problem = CodingProblem.objects.create(
            student=self.user,
            platform="LEETCODE",
            difficulty="EASY",
            topic="Arrays",
            title="Two Sum",
            solved_at=timezone.now(),
        )

        response = self.client.delete(f"/api/coding/{problem.id}/")
        self.assertEqual(response.status_code, 204)
        self.assertFalse(CodingProblem.objects.filter(id=problem.id).exists())

    def test_user_cannot_delete_other_users_problem(self):
        problem = CodingProblem.objects.create(
            student=self.other_user,
            platform="HACKERRANK",
            difficulty="MEDIUM",
            topic="Strings",
            title="String Task",
            solved_at=timezone.now(),
        )

        response = self.client.delete(f"/api/coding/{problem.id}/")
        self.assertEqual(response.status_code, 404)
        self.assertTrue(CodingProblem.objects.filter(id=problem.id).exists())

    def test_deleted_record_unavailable(self):
        problem = CodingProblem.objects.create(
            student=self.user,
            platform="LEETCODE",
            difficulty="EASY",
            topic="Arrays",
            title="Two Sum",
            solved_at=timezone.now(),
        )

        self.client.delete(f"/api/coding/{problem.id}/")

        get_resp = self.client.get(f"/api/coding/{problem.id}/")
        self.assertEqual(get_resp.status_code, 404)

        list_resp = self.client.get("/api/coding/")
        self.assertEqual(list_resp.status_code, 200)
        self.assertEqual(len(list_resp.data), 0)

    # -------------------------------------------------------------------------
    # Validation Tests
    # -------------------------------------------------------------------------
    def test_invalid_platform_rejected(self):
        response = self.client.post(
            "/api/coding/",
            {
                "platform": "INVALID_PLATFORM",
                "difficulty": "EASY",
                "topic": "Arrays",
                "title": "Problem 1",
            },
            format="json",
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("platform", response.data)

    def test_invalid_difficulty_rejected(self):
        response = self.client.post(
            "/api/coding/",
            {
                "platform": "LEETCODE",
                "difficulty": "SUPER_HARD",
                "topic": "Arrays",
                "title": "Problem 1",
            },
            format="json",
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("difficulty", response.data)

    def test_invalid_url_rejected(self):
        response = self.client.post(
            "/api/coding/",
            {
                "platform": "LEETCODE",
                "difficulty": "EASY",
                "topic": "Arrays",
                "title": "Problem 1",
                "problem_url": "not-a-valid-url",
            },
            format="json",
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("problem_url", response.data)

    def test_future_solved_at_rejected(self):
        future_datetime = timezone.now() + timedelta(days=2)
        response = self.client.post(
            "/api/coding/",
            {
                "platform": "LEETCODE",
                "difficulty": "EASY",
                "topic": "Arrays",
                "title": "Future Problem",
                "solved_at": future_datetime.isoformat(),
            },
            format="json",
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("solved_at", response.data)
        self.assertEqual(response.data["solved_at"][0], "solved_at cannot be in the future.")

    def test_future_solved_at_rejected_on_update(self):
        problem = CodingProblem.objects.create(
            student=self.user,
            platform="LEETCODE",
            difficulty="EASY",
            topic="Arrays",
            title="Two Sum",
            solved_at=timezone.now(),
        )

        future_datetime = timezone.now() + timedelta(days=1)
        response = self.client.patch(
            f"/api/coding/{problem.id}/",
            {"solved_at": future_datetime.isoformat()},
            format="json",
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("solved_at", response.data)
        self.assertEqual(response.data["solved_at"][0], "solved_at cannot be in the future.")

    def test_blank_or_whitespace_title_rejected(self):
        # Empty title
        resp1 = self.client.post(
            "/api/coding/",
            {
                "platform": "LEETCODE",
                "difficulty": "EASY",
                "topic": "Arrays",
                "title": "",
            },
            format="json",
        )
        self.assertEqual(resp1.status_code, 400)
        self.assertIn("title", resp1.data)

        # Whitespace-only title
        resp2 = self.client.post(
            "/api/coding/",
            {
                "platform": "LEETCODE",
                "difficulty": "EASY",
                "topic": "Arrays",
                "title": "   ",
            },
            format="json",
        )
        self.assertEqual(resp2.status_code, 400)
        self.assertIn("title", resp2.data)

    def test_title_whitespace_stripped_before_save(self):
        response = self.client.post(
            "/api/coding/",
            {
                "platform": "LEETCODE",
                "difficulty": "EASY",
                "topic": "Arrays",
                "title": "   Two Sum   ",
            },
            format="json",
        )
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data["title"], "Two Sum")
        problem = CodingProblem.objects.get(id=response.data["id"])
        self.assertEqual(problem.title, "Two Sum")

    def test_duplicate_record_rejected_cleanly(self):
        fixed_time = timezone.now() - timedelta(hours=1)
        CodingProblem.objects.create(
            student=self.user,
            platform="LEETCODE",
            difficulty="EASY",
            topic="Arrays",
            title="Two Sum",
            solved_at=fixed_time,
        )

        response = self.client.post(
            "/api/coding/",
            {
                "platform": "LEETCODE",
                "difficulty": "MEDIUM",
                "topic": "Arrays",
                "title": "Two Sum",
                "solved_at": fixed_time.isoformat(),
            },
            format="json",
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn("non_field_errors", response.data)
        self.assertIn("already exists", response.data["non_field_errors"][0])

    def test_different_solved_at_or_platform_or_student_allowed(self):
        fixed_time = timezone.now() - timedelta(hours=2)
        CodingProblem.objects.create(
            student=self.user,
            platform="LEETCODE",
            difficulty="EASY",
            topic="Arrays",
            title="Two Sum",
            solved_at=fixed_time,
        )

        # Different timestamp: allowed
        resp1 = self.client.post(
            "/api/coding/",
            {
                "platform": "LEETCODE",
                "difficulty": "EASY",
                "topic": "Arrays",
                "title": "Two Sum",
                "solved_at": (fixed_time - timedelta(days=1)).isoformat(),
            },
            format="json",
        )
        self.assertEqual(resp1.status_code, 201)

        # Different platform: allowed
        resp2 = self.client.post(
            "/api/coding/",
            {
                "platform": "HACKERRANK",
                "difficulty": "EASY",
                "topic": "Arrays",
                "title": "Two Sum",
                "solved_at": fixed_time.isoformat(),
            },
            format="json",
        )
        self.assertEqual(resp2.status_code, 201)

        # Other student with same details: allowed
        self.client.force_authenticate(user=self.other_user)
        resp3 = self.client.post(
            "/api/coding/",
            {
                "platform": "LEETCODE",
                "difficulty": "EASY",
                "topic": "Arrays",
                "title": "Two Sum",
                "solved_at": fixed_time.isoformat(),
            },
            format="json",
        )
        self.assertEqual(resp3.status_code, 201)

    # -------------------------------------------------------------------------
    # Filters Tests
    # -------------------------------------------------------------------------
    def test_platform_filter_works(self):
        CodingProblem.objects.create(
            student=self.user,
            platform="LEETCODE",
            difficulty="EASY",
            topic="Arrays",
            title="Problem 1",
            solved_at=timezone.now(),
        )
        CodingProblem.objects.create(
            student=self.user,
            platform="HACKERRANK",
            difficulty="MEDIUM",
            topic="Strings",
            title="Problem 2",
            solved_at=timezone.now(),
        )

        response = self.client.get("/api/coding/?platform=LEETCODE")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]["platform"], "LEETCODE")

    def test_difficulty_filter_works(self):
        CodingProblem.objects.create(
            student=self.user,
            platform="LEETCODE",
            difficulty="EASY",
            topic="Arrays",
            title="Problem 1",
            solved_at=timezone.now(),
        )
        CodingProblem.objects.create(
            student=self.user,
            platform="LEETCODE",
            difficulty="HARD",
            topic="Graphs",
            title="Problem 2",
            solved_at=timezone.now(),
        )

        response = self.client.get("/api/coding/?difficulty=HARD")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]["difficulty"], "HARD")

    def test_topic_filter_works_case_insensitive(self):
        CodingProblem.objects.create(
            student=self.user,
            platform="LEETCODE",
            difficulty="EASY",
            topic="Dynamic Programming",
            title="Problem 1",
            solved_at=timezone.now(),
        )
        CodingProblem.objects.create(
            student=self.user,
            platform="LEETCODE",
            difficulty="MEDIUM",
            topic="Arrays",
            title="Problem 2",
            solved_at=timezone.now(),
        )

        response = self.client.get("/api/coding/?topic=dynamic")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]["topic"], "Dynamic Programming")

    def test_filters_remain_user_scoped(self):
        CodingProblem.objects.create(
            student=self.user,
            platform="LEETCODE",
            difficulty="EASY",
            topic="Arrays",
            title="User Problem",
            solved_at=timezone.now(),
        )
        CodingProblem.objects.create(
            student=self.other_user,
            platform="LEETCODE",
            difficulty="EASY",
            topic="Arrays",
            title="Other User Problem",
            solved_at=timezone.now(),
        )

        response = self.client.get("/api/coding/?platform=LEETCODE&difficulty=EASY&topic=Arrays")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]["title"], "User Problem")

    # -------------------------------------------------------------------------
    # Statistics Tests
    # -------------------------------------------------------------------------
    def test_total_problem_count_is_correct(self):
        CodingProblem.objects.create(
            student=self.user,
            platform="LEETCODE",
            difficulty="EASY",
            topic="Arrays",
            title="Problem 1",
            solved_at=timezone.now(),
        )
        CodingProblem.objects.create(
            student=self.user,
            platform="HACKERRANK",
            difficulty="MEDIUM",
            topic="Strings",
            title="Problem 2",
            solved_at=timezone.now(),
        )

        response = self.client.get("/api/coding/stats/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["total_problems"], 2)

    def test_difficulty_statistics_are_correct(self):
        CodingProblem.objects.create(
            student=self.user,
            platform="LEETCODE",
            difficulty="EASY",
            topic="Arrays",
            title="P1",
            solved_at=timezone.now(),
        )
        CodingProblem.objects.create(
            student=self.user,
            platform="LEETCODE",
            difficulty="MEDIUM",
            topic="Arrays",
            title="P2",
            solved_at=timezone.now(),
        )
        CodingProblem.objects.create(
            student=self.user,
            platform="LEETCODE",
            difficulty="HARD",
            topic="Arrays",
            title="P3",
            solved_at=timezone.now(),
        )

        response = self.client.get("/api/coding/stats/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["problems_by_difficulty"]["EASY"], 1)
        self.assertEqual(response.data["problems_by_difficulty"]["MEDIUM"], 1)
        self.assertEqual(response.data["problems_by_difficulty"]["HARD"], 1)

    def test_platform_statistics_are_correct(self):
        CodingProblem.objects.create(
            student=self.user,
            platform="LEETCODE",
            difficulty="EASY",
            topic="Arrays",
            title="P1",
            solved_at=timezone.now(),
        )
        CodingProblem.objects.create(
            student=self.user,
            platform="HACKERRANK",
            difficulty="MEDIUM",
            topic="Strings",
            title="P2",
            solved_at=timezone.now(),
        )

        response = self.client.get("/api/coding/stats/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["problems_by_platform"]["LEETCODE"], 1)
        self.assertEqual(response.data["problems_by_platform"]["HACKERRANK"], 1)
        self.assertEqual(response.data["problems_by_platform"]["CODECHEF"], 0)

    def test_topic_statistics_are_correct(self):
        CodingProblem.objects.create(
            student=self.user,
            platform="LEETCODE",
            difficulty="EASY",
            topic="Arrays",
            title="P1",
            solved_at=timezone.now(),
        )
        CodingProblem.objects.create(
            student=self.user,
            platform="LEETCODE",
            difficulty="MEDIUM",
            topic="Arrays",
            title="P2",
            solved_at=timezone.now(),
        )
        CodingProblem.objects.create(
            student=self.user,
            platform="LEETCODE",
            difficulty="EASY",
            topic="Strings",
            title="P3",
            solved_at=timezone.now(),
        )

        response = self.client.get("/api/coding/stats/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["problems_by_topic"]["Arrays"], 2)
        self.assertEqual(response.data["problems_by_topic"]["Strings"], 1)

    def test_independent_vs_assisted_statistics_are_correct(self):
        CodingProblem.objects.create(
            student=self.user,
            platform="LEETCODE",
            difficulty="EASY",
            topic="Arrays",
            title="P1",
            solved_independently=True,
            solved_at=timezone.now(),
        )
        CodingProblem.objects.create(
            student=self.user,
            platform="LEETCODE",
            difficulty="MEDIUM",
            topic="Strings",
            title="P2",
            solved_independently=False,
            solved_at=timezone.now(),
        )

        response = self.client.get("/api/coding/stats/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["independent_vs_assisted"]["independent"], 1)
        self.assertEqual(response.data["independent_vs_assisted"]["assisted"], 1)

    def test_last_7_days_count_is_correct(self):
        now = timezone.now()
        CodingProblem.objects.create(
            student=self.user,
            platform="LEETCODE",
            difficulty="EASY",
            topic="Arrays",
            title="P1",
            solved_at=now - timedelta(days=2),
        )
        CodingProblem.objects.create(
            student=self.user,
            platform="LEETCODE",
            difficulty="EASY",
            topic="Arrays",
            title="P2",
            solved_at=now - timedelta(days=10),
        )

        response = self.client.get("/api/coding/stats/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["last_7_days"], 1)

    def test_last_30_days_count_is_correct(self):
        now = timezone.now()
        CodingProblem.objects.create(
            student=self.user,
            platform="LEETCODE",
            difficulty="EASY",
            topic="Arrays",
            title="P1",
            solved_at=now - timedelta(days=15),
        )
        CodingProblem.objects.create(
            student=self.user,
            platform="LEETCODE",
            difficulty="EASY",
            topic="Arrays",
            title="P2",
            solved_at=now - timedelta(days=45),
        )

        response = self.client.get("/api/coding/stats/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["last_30_days"], 1)

    def test_monthly_trend_is_correct_and_zero_filled(self):
        now = timezone.now()
        CodingProblem.objects.create(
            student=self.user,
            platform="LEETCODE",
            difficulty="EASY",
            topic="Arrays",
            title="Current Month Problem",
            solved_at=now,
        )

        response = self.client.get("/api/coding/stats/")
        self.assertEqual(response.status_code, 200)
        trend = response.data["monthly_trend"]
        self.assertIsInstance(trend, list)
        self.assertEqual(len(trend), 6)

        current_month_str = now.strftime("%Y-%m")
        self.assertEqual(trend[-1]["month"], current_month_str)
        self.assertEqual(trend[-1]["count"], 1)

        # Check earlier months have 0 count
        for item in trend[:-1]:
            self.assertEqual(item["count"], 0)

    def test_statistics_user_isolation(self):
        CodingProblem.objects.create(
            student=self.other_user,
            platform="LEETCODE",
            difficulty="EASY",
            topic="Arrays",
            title="Other Student Problem",
            solved_at=timezone.now(),
        )

        response = self.client.get("/api/coding/stats/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["total_problems"], 0)
        self.assertEqual(response.data["problems_by_difficulty"]["EASY"], 0)
        self.assertEqual(response.data["problems_by_platform"]["LEETCODE"], 0)
        self.assertEqual(response.data["problems_by_topic"], {})

    def test_statistics_empty_state(self):
        response = self.client.get("/api/coding/stats/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["total_problems"], 0)
        self.assertEqual(response.data["problems_by_difficulty"]["EASY"], 0)
        self.assertEqual(response.data["problems_by_difficulty"]["MEDIUM"], 0)
        self.assertEqual(response.data["problems_by_difficulty"]["HARD"], 0)
        self.assertEqual(response.data["independent_vs_assisted"]["independent"], 0)
        self.assertEqual(response.data["independent_vs_assisted"]["assisted"], 0)
        self.assertEqual(response.data["last_7_days"], 0)
        self.assertEqual(response.data["last_30_days"], 0)
        self.assertEqual(len(response.data["monthly_trend"]), 6)

    # -------------------------------------------------------------------------
    # Database Constraint Tests
    # -------------------------------------------------------------------------
    def test_database_unique_constraint_enforced(self):
        fixed_time = timezone.now() - timedelta(hours=3)
        CodingProblem.objects.create(
            student=self.user,
            platform="LEETCODE",
            difficulty="EASY",
            topic="Arrays",
            title="Unique Constraint Test",
            solved_at=fixed_time,
        )

        with self.assertRaises(IntegrityError):
            CodingProblem.objects.create(
                student=self.user,
                platform="LEETCODE",
                difficulty="HARD",
                topic="Graphs",
                title="Unique Constraint Test",
                solved_at=fixed_time,
            )
