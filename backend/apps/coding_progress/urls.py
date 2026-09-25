from django.urls import path

from .views import (
    CodingProblemListCreateView,
    CodingProblemDetailView,
    CodingProblemStatsView,
)


urlpatterns = [
    path(
        "",
        CodingProblemListCreateView.as_view(),
        name="coding-problem-list-create",
    ),
    path(
        "stats/",
        CodingProblemStatsView.as_view(),
        name="coding-problem-stats",
    ),
    path(
        "<int:pk>/",
        CodingProblemDetailView.as_view(),
        name="coding-problem-detail",
    ),
]
