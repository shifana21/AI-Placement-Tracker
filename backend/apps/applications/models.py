from django.conf import settings
from django.db import models


class Application(models.Model):

    class Status(models.TextChoices):
        APPLIED = "APPLIED", "Applied"
        SHORTLISTED = "SHORTLISTED", "Shortlisted"
        INTERVIEW = "INTERVIEW", "Interview"
        SELECTED = "SELECTED", "Selected"
        REJECTED = "REJECTED", "Rejected"

    student = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="applications",
    )

    company = models.ForeignKey(
        "companies.Company",
        on_delete=models.CASCADE,
        related_name="applications",
    )

    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.APPLIED,
    )

    applied_at = models.DateTimeField(
        auto_now_add=True
    )

    notes = models.TextField(
        blank=True
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    updated_at = models.DateTimeField(
        auto_now=True
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["student", "company"],
                name="unique_student_company_application",
            )
        ]

    def __str__(self):
        return f"{self.student.email} - {self.company.name}"