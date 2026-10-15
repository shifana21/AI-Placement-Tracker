from django.conf import settings
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models


class CareerRecommendation(models.Model):
    student = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="career_recommendations",
    )
    target_role = models.CharField(
        max_length=150,
    )
    match_score = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        validators=[
            MinValueValidator(0.0),
            MaxValueValidator(100.0),
        ],
    )
    explanation = models.TextField(
        blank=True,
    )
    matching_skills = models.JSONField(
        default=list,
        blank=True,
    )
    missing_skills = models.JSONField(
        default=list,
        blank=True,
    )
    recommended_skills = models.JSONField(
        default=list,
        blank=True,
    )
    suggested_projects = models.JSONField(
        default=list,
        blank=True,
    )
    learning_roadmap = models.JSONField(
        default=list,
        blank=True,
    )
    source_summary = models.JSONField(
        default=dict,
        blank=True,
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
    )
    updated_at = models.DateTimeField(
        auto_now=True,
    )

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["student", "created_at"]),
            models.Index(fields=["student", "target_role"]),
            models.Index(fields=["student", "match_score"]),
        ]

    def __str__(self):
        return f"{self.student.email} - {self.target_role} ({self.match_score}%)"
