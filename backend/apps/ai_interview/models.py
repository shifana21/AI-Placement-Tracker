from django.conf import settings
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models


class MockInterview(models.Model):
    class InterviewType(models.TextChoices):
        TECHNICAL = "TECHNICAL", "Technical"
        HR = "HR", "HR"
        BEHAVIORAL = "BEHAVIORAL", "Behavioral"
        MIXED = "MIXED", "Mixed"

    class ExperienceLevel(models.TextChoices):
        BEGINNER = "BEGINNER", "Beginner"
        INTERMEDIATE = "INTERMEDIATE", "Intermediate"
        ADVANCED = "ADVANCED", "Advanced"

    class Status(models.TextChoices):
        IN_PROGRESS = "IN_PROGRESS", "In Progress"
        COMPLETED = "COMPLETED", "Completed"
        CANCELLED = "CANCELLED", "Cancelled"

    student = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="mock_interviews",
    )
    interview_type = models.CharField(
        max_length=20,
        choices=InterviewType.choices,
    )
    target_role = models.CharField(
        max_length=150,
    )
    experience_level = models.CharField(
        max_length=20,
        choices=ExperienceLevel.choices,
    )
    number_of_questions = models.PositiveIntegerField(
        validators=[
            MinValueValidator(1),
            MaxValueValidator(20),
        ],
    )
    current_question = models.PositiveIntegerField(
        default=0,
    )
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.IN_PROGRESS,
    )
    overall_score = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        null=True,
        blank=True,
    )
    overall_feedback = models.TextField(
        blank=True,
    )
    strengths = models.JSONField(
        default=list,
        blank=True,
    )
    weaknesses = models.JSONField(
        default=list,
        blank=True,
    )
    recommendations = models.JSONField(
        default=list,
        blank=True,
    )
    started_at = models.DateTimeField(
        auto_now_add=True,
    )
    completed_at = models.DateTimeField(
        null=True,
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
            models.Index(fields=["student", "status"]),
            models.Index(fields=["student", "interview_type"]),
        ]

    def __str__(self):
        return (
            f"MockInterview {self.id} - {self.student.email} - "
            f"{self.interview_type} ({self.status})"
        )


class InterviewQuestion(models.Model):
    class QuestionType(models.TextChoices):
        TECHNICAL = "TECHNICAL", "Technical"
        BEHAVIORAL = "BEHAVIORAL", "Behavioral"
        HR = "HR", "HR"

    interview = models.ForeignKey(
        MockInterview,
        on_delete=models.CASCADE,
        related_name="questions",
    )
    question_number = models.PositiveIntegerField(
        validators=[MinValueValidator(1)],
    )
    question_text = models.TextField()
    question_type = models.CharField(
        max_length=20,
        choices=QuestionType.choices,
    )
    topic = models.CharField(
        max_length=100,
        blank=True,
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    class Meta:
        ordering = ["question_number"]
        constraints = [
            models.UniqueConstraint(
                fields=["interview", "question_number"],
                name="unique_question_number_per_interview",
            )
        ]

    def __str__(self):
        return f"Interview {self.interview_id} - Q{self.question_number}: {self.question_text[:40]}"


class InterviewAnswer(models.Model):
    question = models.OneToOneField(
        InterviewQuestion,
        on_delete=models.CASCADE,
        related_name="answer",
    )
    answer_text = models.TextField()
    score = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        null=True,
        blank=True,
    )
    evaluation = models.TextField(
        blank=True,
    )
    strengths = models.JSONField(
        default=list,
        blank=True,
    )
    weaknesses = models.JSONField(
        default=list,
        blank=True,
    )
    improvement_suggestions = models.JSONField(
        default=list,
        blank=True,
    )
    answered_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    class Meta:
        ordering = ["id"]

    def __str__(self):
        return f"Answer for Q{self.question.question_number} (Score: {self.score})"
