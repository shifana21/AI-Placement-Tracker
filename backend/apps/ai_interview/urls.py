from django.urls import path

from apps.ai_interview.views import (
    MockInterviewAnswerView,
    MockInterviewCompleteView,
    MockInterviewCurrentQuestionView,
    MockInterviewDetailView,
    MockInterviewListView,
    MockInterviewResultView,
    MockInterviewStartView,
)

urlpatterns = [
    path(
        "start/",
        MockInterviewStartView.as_view(),
        name="interview-start",
    ),
    path(
        "",
        MockInterviewListView.as_view(),
        name="interview-list",
    ),
    path(
        "<int:pk>/",
        MockInterviewDetailView.as_view(),
        name="interview-detail",
    ),
    path(
        "<int:pk>/current/",
        MockInterviewCurrentQuestionView.as_view(),
        name="interview-current-question",
    ),
    path(
        "<int:pk>/answer/",
        MockInterviewAnswerView.as_view(),
        name="interview-answer",
    ),
    path(
        "<int:pk>/complete/",
        MockInterviewCompleteView.as_view(),
        name="interview-complete",
    ),
    path(
        "<int:pk>/result/",
        MockInterviewResultView.as_view(),
        name="interview-result",
    ),
]
