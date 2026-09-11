from rest_framework import generics
from rest_framework.permissions import IsAuthenticated, IsAdminUser

from .models import Company
from .serializers import CompanySerializer


class CompanyListCreateView(generics.ListCreateAPIView):
    queryset = Company.objects.all()
    serializer_class = CompanySerializer

    def get_permissions(self):
        if self.request.method == 'POST':
            return [IsAdminUser()]

        return [IsAuthenticated()]