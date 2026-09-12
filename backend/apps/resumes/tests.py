from io import BytesIO

from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from apps.accounts.models import User
from .models import Resume


class ResumeAPITests(APITestCase):

    def setUp(self):
        self.user = User.objects.create_user(
            email="student@example.com",
            password="TestPassword123",
            first_name="Test",
            last_name="Student",
        )

        self.other_user = User.objects.create_user(
            email="other@example.com",
            password="TestPassword123",
            first_name="Other",
            last_name="Student",
        )

        self.list_url = reverse("resume-list-create")

    def authenticate(self, user):
        self.client.force_authenticate(user=user)

    def create_pdf(self, size=1024):
        content = b"%PDF-1.4\n" + (b"a" * size)
        return SimpleUploadedFile(
            "resume.pdf",
            content,
            content_type="application/pdf",
        )

    def create_docx(self):
        return SimpleUploadedFile(
            "resume.docx",
            b"fake docx content",
            content_type=(
                "application/vnd.openxmlformats-officedocument"
                ".wordprocessingml.document"
            ),
        )

    def test_unauthenticated_user_cannot_list_resumes(self):
        response = self.client.get(self.list_url)

        self.assertEqual(
            response.status_code,
            status.HTTP_401_UNAUTHORIZED,
        )

    def test_authenticated_user_can_upload_pdf(self):
        self.authenticate(self.user)

        response = self.client.post(
            self.list_url,
            {"file": self.create_pdf()},
            format="multipart",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_201_CREATED,
        )

        self.assertEqual(
            response.data["original_filename"],
            "resume.pdf",
        )

        self.assertTrue(response.data["is_active"])

        self.assertTrue(
            Resume.objects.filter(
                student=self.user
            ).exists()
        )

    def test_authenticated_user_can_upload_docx(self):
        self.authenticate(self.user)

        response = self.client.post(
            self.list_url,
            {"file": self.create_docx()},
            format="multipart",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_201_CREATED,
        )

    def test_invalid_file_type_is_rejected(self):
        self.authenticate(self.user)

        txt_file = SimpleUploadedFile(
            "resume.txt",
            b"This is not a resume PDF or DOCX.",
            content_type="text/plain",
        )

        response = self.client.post(
            self.list_url,
            {"file": txt_file},
            format="multipart",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )

        self.assertIn("file", response.data)

    def test_file_larger_than_5mb_is_rejected(self):
        self.authenticate(self.user)

        large_pdf = self.create_pdf(
            size=(5 * 1024 * 1024) + 100
        )

        response = self.client.post(
            self.list_url,
            {"file": large_pdf},
            format="multipart",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )

        self.assertIn("file", response.data)

    def test_user_can_only_see_own_resumes(self):
        self.authenticate(self.user)

        Resume.objects.create(
            student=self.other_user,
            file=self.create_pdf(),
            original_filename="other_resume.pdf",
            is_active=True,
        )

        response = self.client.get(self.list_url)

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

        self.assertEqual(
            len(response.data),
            0,
        )

    def test_user_can_delete_own_resume(self):
        self.authenticate(self.user)

        resume = Resume.objects.create(
            student=self.user,
            file=self.create_pdf(),
            original_filename="delete_me.pdf",
            is_active=True,
        )

        response = self.client.delete(
            reverse(
                "resume-detail",
                kwargs={"pk": resume.id},
            )
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_204_NO_CONTENT,
        )

        self.assertFalse(
            Resume.objects.filter(
                id=resume.id
            ).exists()
        )

    def test_user_cannot_delete_other_users_resume(self):
        self.authenticate(self.user)

        resume = Resume.objects.create(
            student=self.other_user,
            file=self.create_pdf(),
            original_filename="other_resume.pdf",
            is_active=True,
        )

        response = self.client.delete(
            reverse(
                "resume-detail",
                kwargs={"pk": resume.id},
            )
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_404_NOT_FOUND,
        )
        def test_new_resume_deactivates_previous_active_resume(self):
            self.authenticate(self.user)

            first_response = self.client.post(
                self.list_url,
                {"file": self.create_pdf()},
                format="multipart",
            )

            self.assertEqual(
                first_response.status_code,
                status.HTTP_201_CREATED,
            )

            first_resume_id = first_response.data["id"]

            second_response = self.client.post(
                self.list_url,
                {"file": self.create_pdf()},
                format="multipart",
            )

            self.assertEqual(
                second_response.status_code,
                status.HTTP_201_CREATED,
            )

            first_resume = Resume.objects.get(
                id=first_resume_id
            )

            second_resume = Resume.objects.get(
                id=second_response.data["id"]
            )

            self.assertFalse(first_resume.is_active)
            self.assertTrue(second_resume.is_active)

            self.assertEqual(
                Resume.objects.filter(
                    student=self.user,
                    is_active=True,
                ).count(),
                1,
            )