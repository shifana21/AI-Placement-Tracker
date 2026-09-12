from rest_framework import generics
from rest_framework.permissions import IsAuthenticated

from .models import Resume
from .serializers import ResumeSerializer


class ResumeListCreateView(generics.ListCreateAPIView):
    serializer_class = ResumeSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Resume.objects.filter(
            student=self.request.user
        ).order_by("-uploaded_at")


class ResumeDetailView(generics.RetrieveDestroyAPIView):
    serializer_class = ResumeSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Resume.objects.filter(
            student=self.request.user
        )