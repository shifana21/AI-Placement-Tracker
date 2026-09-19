from django.db import models

from apps.resumes.models import Resume


class ResumeAnalysis(models.Model):
    class Status(models.TextChoices):
        PENDING = "PENDING", "Pending"
        COMPLETED = "COMPLETED", "Completed"
        FAILED = "FAILED", "Failed"

    resume = models.OneToOneField(
        Resume,
        on_delete=models.CASCADE,
        related_name="analysis",
    )

    extracted_text = models.TextField(
        blank=True,
    )

    analysis_result = models.JSONField(
        default=dict,
        blank=True,
    )

    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING,
    )

    error_message = models.TextField(
        blank=True,
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    updated_at = models.DateTimeField(
        auto_now=True,
    )

    def __str__(self):
        return f"Analysis - {self.resume.original_filename}"