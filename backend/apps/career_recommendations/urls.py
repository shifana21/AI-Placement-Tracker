from django.urls import path

from apps.career_recommendations.views import (
    CareerRecommendationDetailView,
    CareerRecommendationGenerateView,
    CareerRecommendationListView,
    CareerRecommendationRefreshView,
    CareerRoadmapView,
    CareerSkillGapsView,
)

urlpatterns = [
    path(
        "generate/",
        CareerRecommendationGenerateView.as_view(),
        name="career-generate",
    ),
    path(
        "",
        CareerRecommendationListView.as_view(),
        name="career-list",
    ),
    path(
        "refresh/",
        CareerRecommendationRefreshView.as_view(),
        name="career-refresh",
    ),
    path(
        "skill-gaps/",
        CareerSkillGapsView.as_view(),
        name="career-skill-gaps",
    ),
    path(
        "roadmap/",
        CareerRoadmapView.as_view(),
        name="career-roadmap",
    ),
    path(
        "<int:pk>/",
        CareerRecommendationDetailView.as_view(),
        name="career-detail",
    ),
]
