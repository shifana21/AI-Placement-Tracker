from django.urls import path

from apps.resume_analysis.views import ResumeAnalyzeView
from .views import (
    ResumeListCreateView,
    ResumeDetailView,
)


urlpatterns = [
    path(
        "",
        ResumeListCreateView.as_view(),
        name="resume-list-create",
    ),
    path(
        "<int:pk>/",
        ResumeDetailView.as_view(),
        name="resume-detail",
    ),
    path(
        "<int:resume_id>/analyze/",
        ResumeAnalyzeView.as_view(),
        name="resume-analyze",
    ),
]