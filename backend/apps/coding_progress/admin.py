from django.contrib import admin

from .models import CodingProblem


@admin.register(CodingProblem)
class CodingProblemAdmin(admin.ModelAdmin):
    list_display = [
        "student",
        "platform",
        "difficulty",
        "topic",
        "title",
        "solved_at",
        "solved_independently",
    ]
    list_filter = ["platform", "difficulty", "solved_independently", "solved_at"]
    search_fields = ["student__email", "title", "topic", "notes"]
    date_hierarchy = "solved_at"
    ordering = ["-solved_at", "-created_at"]
