from django.test import TestCase
from rest_framework.test import APIClient

from apps.accounts.models import User
from apps.profiles.models import StudentProfile
from apps.companies.models import Company
from apps.companies.services import check_company_eligibility


class CompanyEligibilityServiceTests(TestCase):

    def setUp(self):
        self.user = User.objects.create_user(
            email="student@test.com",
            password="TestPassword123",
            first_name="Test",
            last_name="Student",
        )

        self.profile = StudentProfile.objects.create(
            user=self.user,
            branch="CSE",
            cgpa=8.70,
            backlogs=0,
            skills="Python, Java, SQL",
        )

        self.company = Company.objects.create(
            name="TestCorp",
            description="Test company",
            minimum_cgpa=7.50,
            eligible_branches="CSE, IT, ECE",
            required_skills="Python, Java, SQL",
            maximum_backlogs=0,
            package_lpa=8.50,
            job_role="Software Engineer",
            location="Chennai",
        )

    def test_student_is_eligible(self):
        result = check_company_eligibility(
            self.profile,
            self.company,
        )

        self.assertTrue(result["eligible"])
        self.assertTrue(result["criteria"]["cgpa"])
        self.assertTrue(result["criteria"]["branch"])
        self.assertTrue(result["criteria"]["backlogs"])
        self.assertTrue(result["criteria"]["skills"])

    def test_student_is_not_eligible_due_to_cgpa(self):
        self.profile.cgpa = 6.50
        self.profile.save()

        result = check_company_eligibility(
            self.profile,
            self.company,
        )

        self.assertFalse(result["eligible"])
        self.assertFalse(result["criteria"]["cgpa"])

    def test_student_is_not_eligible_due_to_branch(self):
        self.profile.branch = "EEE"
        self.profile.save()

        result = check_company_eligibility(
            self.profile,
            self.company,
        )

        self.assertFalse(result["eligible"])
        self.assertFalse(result["criteria"]["branch"])

    def test_student_is_not_eligible_due_to_backlogs(self):
        self.profile.backlogs = 2
        self.profile.save()

        result = check_company_eligibility(
            self.profile,
            self.company,
        )

        self.assertFalse(result["eligible"])
        self.assertFalse(result["criteria"]["backlogs"])

    def test_student_is_not_eligible_due_to_missing_skill(self):
        self.profile.skills = "Python"
        self.profile.save()

        result = check_company_eligibility(
            self.profile,
            self.company,
        )

        self.assertFalse(result["eligible"])
        self.assertFalse(result["criteria"]["skills"])


class CompanyEligibilityAPITests(TestCase):

    def setUp(self):
        self.client = APIClient()

        self.user = User.objects.create_user(
            email="api@test.com",
            password="TestPassword123",
            first_name="API",
            last_name="Student",
        )

        self.profile = StudentProfile.objects.create(
            user=self.user,
            branch="CSE",
            cgpa=8.70,
            backlogs=0,
            skills="Python, Java, SQL",
        )

        Company.objects.create(
            name="APICorp",
            minimum_cgpa=7.50,
            eligible_branches="CSE, IT",
            required_skills="Python, Java",
            maximum_backlogs=0,
            job_role="Software Engineer",
        )

        self.client.force_authenticate(user=self.user)

    def test_eligibility_api(self):
        response = self.client.get(
            "/api/companies/eligibility/"
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 1)
        self.assertTrue(response.data[0]["eligible"])