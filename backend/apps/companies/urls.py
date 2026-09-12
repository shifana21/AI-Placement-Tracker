from django.urls import path

from .views import (
    CompanyListCreateView,
    CompanyEligibilityView,
)


urlpatterns = [
    path('', CompanyListCreateView.as_view(), name='company-list-create'),
    path(
        'eligibility/',
        CompanyEligibilityView.as_view(),
        name='company-eligibility',
    ),
]