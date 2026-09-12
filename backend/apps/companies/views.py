from rest_framework import generics
from rest_framework.permissions import IsAuthenticated, IsAdminUser
from rest_framework.response import Response

from .models import Company
from .serializers import CompanySerializer
from .services import check_company_eligibility


class CompanyListCreateView(generics.ListCreateAPIView):
    queryset = Company.objects.all()
    serializer_class = CompanySerializer

    def get_permissions(self):
        if self.request.method == 'POST':
            return [IsAdminUser()]

        return [IsAuthenticated()]


class CompanyEligibilityView(generics.GenericAPIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        student_profile = request.user.profile
        companies = Company.objects.all()

        results = [
            check_company_eligibility(student_profile, company)
            for company in companies
        ]

        return Response(results)