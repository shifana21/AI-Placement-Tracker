from django.urls import path

from .views import StudentProfileView


urlpatterns = [
    path(
        '',
        StudentProfileView.as_view(),
        name='student-profile',
    ),
]