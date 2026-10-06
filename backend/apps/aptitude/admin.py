from django.contrib import admin

from apps.aptitude.models import AptitudeAnswer, AptitudeAttempt, AptitudeQuestion


@admin.register(AptitudeQuestion)
class AptitudeQuestionAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "category",
        "topic",
        "difficulty",
        "marks",
        "is_active",
        "created_at",
    )
    list_filter = (
        "category",
        "difficulty",
        "is_active",
    )
    search_fields = (
        "question_text",
        "topic",
    )
    ordering = ("-created_at",)


@admin.register(AptitudeAttempt)
class AptitudeAttemptAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "student",
        "category",
        "difficulty",
        "score",
        "accuracy",
        "submitted_at",
    )
    list_filter = (
        "category",
        "difficulty",
        "submitted_at",
    )
    search_fields = (
        "student__email",
        "topic",
    )
    ordering = ("-created_at",)


@admin.register(AptitudeAnswer)
class AptitudeAnswerAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "attempt",
        "question",
        "selected_option",
        "is_correct",
        "marks_awarded",
        "answered_at",
    )
    list_filter = (
        "is_correct",
    )
    search_fields = (
        "attempt__student__email",
    )
    ordering = ("-id",)
