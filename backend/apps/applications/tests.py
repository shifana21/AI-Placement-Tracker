from django.test import TestCase
from rest_framework.test import APIClient

from apps.accounts.models import User
from apps.companies.models import Company
from apps.applications.models import Application


class ApplicationAPITests(TestCase):

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

        self.company = Company.objects.create(
            name="TestCorp",
            minimum_cgpa=7.50,
            eligible_branches="CSE, IT",
            required_skills="Python, Java",
            maximum_backlogs=0,
            package_lpa=8.50,
            job_role="Software Engineer",
            location="Chennai",
        )

        self.client.force_authenticate(
            user=self.user
        )

    def test_create_application(self):
        response = self.client.post(
            "/api/applications/",
            {
                "company": self.company.id,
                "status": "APPLIED",
                "notes": "Applied through campus placement",
            },
            format="json",
        )

        self.assertEqual(response.status_code, 201)
        self.assertEqual(
            response.data["company_name"],
            "TestCorp",
        )

        self.assertTrue(
            Application.objects.filter(
                student=self.user,
                company=self.company,
            ).exists()
        )

    def test_list_only_own_applications(self):
        Application.objects.create(
            student=self.user,
            company=self.company,
        )

        other_company = Company.objects.create(
            name="OtherCorp",
            job_role="Data Engineer",
        )

        Application.objects.create(
            student=self.other_user,
            company=other_company,
        )

        response = self.client.get(
            "/api/applications/"
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(
            response.data[0]["company_name"],
            "TestCorp",
        )

    def test_duplicate_application_is_rejected(self):
        Application.objects.create(
            student=self.user,
            company=self.company,
        )

        response = self.client.post(
            "/api/applications/",
            {
                "company": self.company.id,
                "status": "APPLIED",
            },
            format="json",
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn(
            "company",
            response.data,
        )

    def test_update_application_status(self):
        application = Application.objects.create(
            student=self.user,
            company=self.company,
        )

        response = self.client.patch(
            f"/api/applications/{application.id}/",
            {
                "status": "SHORTLISTED",
            },
            format="json",
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.data["status"],
            "SHORTLISTED",
        )

    def test_user_cannot_access_other_users_application(self):
        application = Application.objects.create(
            student=self.other_user,
            company=self.company,
        )

        response = self.client.get(
            f"/api/applications/{application.id}/"
        )

        self.assertEqual(response.status_code, 404)

    def test_unauthenticated_user_cannot_access_applications(self):
        self.client.force_authenticate(user=None)

        response = self.client.get(
            "/api/applications/"
        )

        self.assertEqual(response.status_code, 401)