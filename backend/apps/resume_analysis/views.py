from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.resumes.models import Resume
from .models import ResumeAnalysis
from .serializers import ResumeAnalysisSerializer
from .services.analysis_service import analyze_resume


class ResumeAnalyzeView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, resume_id=None, pk=None):
        target_id = resume_id if resume_id is not None else pk
        resume = get_object_or_404(
            Resume,
            id=target_id,
            student=request.user,
        )

        try:
            analysis = analyze_resume(resume)
            serializer = ResumeAnalysisSerializer(analysis)
            return Response(
                serializer.data,
                status=status.HTTP_200_OK,
            )
        except Exception:
            analysis = ResumeAnalysis.objects.get(resume=resume)
            serializer = ResumeAnalysisSerializer(analysis)
            return Response(
                serializer.data,
                status=status.HTTP_400_BAD_REQUEST,
            )

    def get(self, request, resume_id=None, pk=None):
        target_id = resume_id if resume_id is not None else pk
        resume = get_object_or_404(
            Resume,
            id=target_id,
            student=request.user,
        )
        analysis = get_object_or_404(
            ResumeAnalysis,
            resume=resume,
        )
        serializer = ResumeAnalysisSerializer(analysis)
        return Response(
            serializer.data,
            status=status.HTTP_200_OK,
        )
