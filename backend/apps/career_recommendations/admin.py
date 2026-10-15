from django.contrib import admin

from apps.career_recommendations.models import CareerRecommendation


@admin.register(CareerRecommendation)
class CareerRecommendationAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "student",
        "target_role",
        "match_score",
        "created_at",
    )
    list_filter = (
        "target_role",
        "created_at",
    )
    search_fields = (
        "student__email",
        "target_role",
    )
    ordering = ("-created_at",)
    readonly_fields = (
        "student",
        "target_role",
        "match_score",
        "explanation",
        "matching_skills",
        "missing_skills",
        "recommended_skills",
        "suggested_projects",
        "learning_roadmap",
        "source_summary",
        "created_at",
        "updated_at",
    )
