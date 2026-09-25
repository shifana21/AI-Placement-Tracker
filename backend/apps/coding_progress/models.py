from django.conf import settings
from django.db import models
from django.utils import timezone


class CodingProblem(models.Model):
    class Platform(models.TextChoices):
        LEETCODE = "LEETCODE", "LeetCode"
        HACKERRANK = "HACKERRANK", "HackerRank"
        CODECHEF = "CODECHEF", "CodeChef"
        CODEFORCES = "CODEFORCES", "Codeforces"
        GEEKSFORGEEKS = "GEEKSFORGEEKS", "GeeksforGeeks"
        OTHER = "OTHER", "Other"

    class Difficulty(models.TextChoices):
        EASY = "EASY", "Easy"
        MEDIUM = "MEDIUM", "Medium"
        HARD = "HARD", "Hard"

    student = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="coding_problems",
    )

    platform = models.CharField(
        max_length=20,
        choices=Platform.choices,
    )

    difficulty = models.CharField(
        max_length=10,
        choices=Difficulty.choices,
    )

    topic = models.CharField(
        max_length=100,
        blank=True,
    )

    title = models.CharField(
        max_length=255,
    )

    problem_url = models.URLField(
        blank=True,
    )

    solved_independently = models.BooleanField(
        default=True,
    )

    solved_at = models.DateTimeField(
        default=timezone.now,
    )

    notes = models.TextField(
        blank=True,
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    updated_at = models.DateTimeField(
        auto_now=True,
    )

    class Meta:
        ordering = ["-solved_at", "-created_at"]
        indexes = [
            models.Index(fields=["student", "solved_at"]),
            models.Index(fields=["student", "platform"]),
            models.Index(fields=["student", "difficulty"]),
            models.Index(fields=["student", "topic"]),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["student", "platform", "title", "solved_at"],
                condition=~models.Q(title=""),
                name="unique_coding_problem_record",
            )
        ]

    def __str__(self):
        return f"{self.student.email} - {self.platform} - {self.title}"
