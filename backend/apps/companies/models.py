from django.db import models


class Company(models.Model):

    name = models.CharField(
        max_length=200,
        unique=True,
    )

    description = models.TextField(
        blank=True,
    )

    website = models.URLField(
        blank=True,
    )

    minimum_cgpa = models.DecimalField(
        max_digits=4,
        decimal_places=2,
        default=0.00,
    )

    eligible_branches = models.TextField(
        blank=True,
    )

    required_skills = models.TextField(
        blank=True,
    )

    maximum_backlogs = models.PositiveIntegerField(
        default=0,
    )

    package_lpa = models.DecimalField(
        max_digits=6,
        decimal_places=2,
        null=True,
        blank=True,
    )

    job_role = models.CharField(
        max_length=200,
    )

    location = models.CharField(
        max_length=200,
        blank=True,
    )

    application_deadline = models.DateTimeField(
        null=True,
        blank=True,
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    updated_at = models.DateTimeField(
        auto_now=True,
    )

    def __str__(self):
        return self.name