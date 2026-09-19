from django.urls import path

from .views import ResumeAnalyzeView


urlpatterns = [
    path(
        "<int:resume_id>/analyze/",
        ResumeAnalyzeView.as_view(),
        name="resume-analyze",
    ),
]
