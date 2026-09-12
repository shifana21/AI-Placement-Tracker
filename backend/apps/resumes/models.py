from django.conf import settings
from django.db import models


class Resume(models.Model):

    student = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="resumes",
    )

    file = models.FileField(
        upload_to="resumes/",
    )

    original_filename = models.CharField(
        max_length=255,
    )

    uploaded_at = models.DateTimeField(
        auto_now_add=True,
    )

    updated_at = models.DateTimeField(
        auto_now=True,
    )

    is_active = models.BooleanField(
        default=True,
    )

    def __str__(self):
        return f"{self.student.email} - {self.original_filename}"