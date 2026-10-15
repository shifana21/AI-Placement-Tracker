from django.contrib import admin

from apps.ai_interview.models import (
    InterviewAnswer,
    InterviewQuestion,
    MockInterview,
)


@admin.register(MockInterview)
class MockInterviewAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "student",
        "interview_type",
        "target_role",
        "experience_level",
        "number_of_questions",
        "current_question",
        "status",
        "overall_score",
        "started_at",
        "completed_at",
    )
    list_filter = (
        "interview_type",
        "experience_level",
        "status",
        "created_at",
    )
    search_fields = (
        "student__email",
        "target_role",
    )
    ordering = ("-created_at",)
    readonly_fields = (
        "started_at",
        "completed_at",
        "created_at",
        "updated_at",
    )


@admin.register(InterviewQuestion)
class InterviewQuestionAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "interview",
        "question_number",
        "question_type",
        "topic",
        "created_at",
    )
    list_filter = (
        "question_type",
        "topic",
    )
    search_fields = (
        "question_text",
        "topic",
        "interview__student__email",
    )
    ordering = ("interview", "question_number")


@admin.register(InterviewAnswer)
class InterviewAnswerAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "question",
        "score",
        "answered_at",
    )
    list_filter = (
        "score",
    )
    search_fields = (
        "answer_text",
        "question__question_text",
        "question__interview__student__email",
    )
    readonly_fields = (
        "score",
        "evaluation",
        "strengths",
        "weaknesses",
        "improvement_suggestions",
        "answered_at",
    )
