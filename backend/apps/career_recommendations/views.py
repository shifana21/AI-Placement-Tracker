import logging

from django.shortcuts import get_object_or_404
from rest_framework import generics, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.career_recommendations.models import CareerRecommendation
from apps.career_recommendations.serializers import (
    CareerRecommendationSerializer,
    LearningRoadmapItemSerializer,
    SkillGapItemSerializer,
)
from apps.career_recommendations.services.ai_advisor import (
    GeminiAPIError,
    GeminiConfigurationError,
    InvalidGeminiResponseError,
)
from apps.career_recommendations.services.recommendation_service import (
    generate_student_career_recommendations,
)

logger = logging.getLogger(__name__)


class CareerRecommendationGenerateView(APIView):
    """
    Generate and save personalized career recommendations based on available student evidence.
    """

    permission_classes = [IsAuthenticated]

    def post(self, request):
        try:
            recs = generate_student_career_recommendations(
                student=request.user,
                top_n=3,
                use_ai=True,
            )
        except GeminiConfigurationError:
            return Response(
                {"error": "Gemini AI service is not properly configured."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
        except (GeminiAPIError, InvalidGeminiResponseError):
            return Response(
                {"error": "Failed to generate AI career recommendations. Please try again later."},
                status=status.HTTP_502_BAD_GATEWAY,
            )
        except Exception:
            logger.exception("Unexpected error generating career recommendations.")
            return Response(
                {"error": "An unexpected error occurred while generating recommendations."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        serializer = CareerRecommendationSerializer(recs, many=True)
        return Response(serializer.data, status=status.HTTP_201_CREATED)


class CareerRecommendationListView(generics.ListAPIView):
    """
    List career recommendations for the authenticated student ordered newest first.
    """

    permission_classes = [IsAuthenticated]
    serializer_class = CareerRecommendationSerializer

    def get_queryset(self):
        return CareerRecommendation.objects.filter(student=self.request.user).order_by(
            "-created_at"
        )


class CareerRecommendationDetailView(generics.RetrieveAPIView):
    """
    Retrieve single recommendation detail belonging to authenticated student only.
    """

    permission_classes = [IsAuthenticated]
    serializer_class = CareerRecommendationSerializer

    def get_queryset(self):
        return CareerRecommendation.objects.filter(student=self.request.user)


class CareerRecommendationRefreshView(APIView):
    """
    Recalculate career recommendations using the latest available student evidence.
    """

    permission_classes = [IsAuthenticated]

    def post(self, request):
        try:
            recs = generate_student_career_recommendations(
                student=request.user,
                top_n=3,
                use_ai=True,
            )
        except GeminiConfigurationError:
            return Response(
                {"error": "Gemini AI service is not properly configured."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
        except (GeminiAPIError, InvalidGeminiResponseError):
            return Response(
                {"error": "Failed to refresh AI career recommendations. Please try again later."},
                status=status.HTTP_502_BAD_GATEWAY,
            )
        except Exception:
            logger.exception("Unexpected error refreshing career recommendations.")
            return Response(
                {"error": "An unexpected error occurred while refreshing recommendations."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        serializer = CareerRecommendationSerializer(recs, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)


class CareerSkillGapsView(APIView):
    """
    Return recommended roles and their matching, missing, and priority skills.
    """

    permission_classes = [IsAuthenticated]

    def get(self, request):
        # Fetch the latest batch of recommendations for the student
        latest_recs = (
            CareerRecommendation.objects.filter(student=request.user)
            .order_by("-created_at")[:3]
        )
        serializer = SkillGapItemSerializer(latest_recs, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)


class CareerRoadmapView(APIView):
    """
    Return personalized learning roadmap items and suggested projects from latest recommendations.
    """

    permission_classes = [IsAuthenticated]

    def get(self, request):
        latest_recs = (
            CareerRecommendation.objects.filter(student=request.user)
            .order_by("-created_at")[:3]
        )
        serializer = LearningRoadmapItemSerializer(latest_recs, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)
