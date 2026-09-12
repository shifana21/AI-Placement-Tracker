from django.urls import path

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
]