from django.conf import settings
from django.core.validators import MinValueValidator
from django.db import models
from django.utils import timezone


class AptitudeQuestion(models.Model):
    class Category(models.TextChoices):
        QUANTITATIVE = "QUANTITATIVE", "Quantitative"
        LOGICAL = "LOGICAL", "Logical"
        VERBAL = "VERBAL", "Verbal"

    class Difficulty(models.TextChoices):
        EASY = "EASY", "Easy"
        MEDIUM = "MEDIUM", "Medium"
        HARD = "HARD", "Hard"

    class Option(models.TextChoices):
        A = "A", "A"
        B = "B", "B"
        C = "C", "C"
        D = "D", "D"

    category = models.CharField(
        max_length=20,
        choices=Category.choices,
    )
    topic = models.CharField(
        max_length=100,
    )
    difficulty = models.CharField(
        max_length=10,
        choices=Difficulty.choices,
    )
    question_text = models.TextField()
    option_a = models.CharField(
        max_length=500,
    )
    option_b = models.CharField(
        max_length=500,
    )
    option_c = models.CharField(
        max_length=500,
    )
    option_d = models.CharField(
        max_length=500,
    )
    correct_option = models.CharField(
        max_length=1,
        choices=Option.choices,
    )
    explanation = models.TextField(
        blank=True,
    )
    marks = models.PositiveIntegerField(
        default=1,
        validators=[MinValueValidator(1)],
    )
    is_active = models.BooleanField(
        default=True,
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
            models.Index(fields=["category"]),
            models.Index(fields=["topic"]),
            models.Index(fields=["difficulty"]),
            models.Index(fields=["is_active"]),
            models.Index(fields=["category", "difficulty"]),
            models.Index(fields=["is_active", "category"]),
        ]

    def __str__(self):
        return f"[{self.category} - {self.topic}] {self.question_text[:50]}"


class AptitudeAttempt(models.Model):
    student = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="aptitude_attempts",
    )
    category = models.CharField(
        max_length=20,
        choices=AptitudeQuestion.Category.choices,
        blank=True,
        null=True,
    )
    topic = models.CharField(
        max_length=100,
        blank=True,
    )
    difficulty = models.CharField(
        max_length=10,
        choices=AptitudeQuestion.Difficulty.choices,
        blank=True,
        null=True,
    )
    total_questions = models.PositiveIntegerField(
        default=0,
    )
    correct_answers = models.PositiveIntegerField(
        default=0,
    )
    wrong_answers = models.PositiveIntegerField(
        default=0,
    )
    unanswered = models.PositiveIntegerField(
        default=0,
    )
    score = models.DecimalField(
        max_digits=6,
        decimal_places=2,
        default=0.00,
    )
    accuracy = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=0.00,
    )
    time_taken_seconds = models.PositiveIntegerField(
        default=0,
    )
    started_at = models.DateTimeField(
        default=timezone.now,
    )
    submitted_at = models.DateTimeField(
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
            models.Index(fields=["student", "category"]),
            models.Index(fields=["student", "difficulty"]),
        ]

    @property
    def is_submitted(self):
        return self.submitted_at is not None

    def __str__(self):
        status_str = "Submitted" if self.is_submitted else "In Progress"
        return f"Attempt {self.id} by {self.student.email} ({status_str})"


class AptitudeAnswer(models.Model):
    attempt = models.ForeignKey(
        AptitudeAttempt,
        on_delete=models.CASCADE,
        related_name="answers",
    )
    question = models.ForeignKey(
        AptitudeQuestion,
        on_delete=models.CASCADE,
        related_name="aptitude_answers",
    )
    selected_option = models.CharField(
        max_length=1,
        choices=AptitudeQuestion.Option.choices,
        blank=True,
        default="",
    )
    is_correct = models.BooleanField(
        default=False,
    )
    marks_awarded = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=0.00,
    )
    answered_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    class Meta:
        indexes = [
            models.Index(fields=["attempt"]),
            models.Index(fields=["question"]),
            models.Index(fields=["attempt", "question"]),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["attempt", "question"],
                name="unique_question_per_attempt",
            )
        ]

    def __str__(self):
        return f"Attempt {self.attempt_id} - Q{self.question_id}: {self.selected_option or 'Unanswered'}"
