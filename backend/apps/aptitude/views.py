import logging
import random
from decimal import Decimal

from django.db import transaction
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import generics, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.aptitude.models import AptitudeAnswer, AptitudeAttempt, AptitudeQuestion
from apps.aptitude.serializers import (
    AptitudeAnswerSubmitSerializer,
    AptitudeAttemptDetailSerializer,
    AptitudeAttemptSerializer,
    AptitudeAttemptStartSerializer,
    AptitudeQuestionSerializer,
)
from apps.aptitude.services.ai_analysis import (
    GeminiAPIError,
    GeminiConfigurationError,
    InvalidGeminiResponseError,
    analyze_aptitude_performance,
)
from apps.aptitude.services.analytics import get_student_aptitude_analytics
from apps.aptitude.services.scoring import calculate_attempt_results

logger = logging.getLogger(__name__)


class AptitudeQuestionListView(generics.ListAPIView):
    """
    List active aptitude questions with optional category, topic, and difficulty filters.
    Correct answers and explanations are never exposed to students.
    """

    permission_classes = [IsAuthenticated]
    serializer_class = AptitudeQuestionSerializer

    def get_queryset(self):
        queryset = AptitudeQuestion.objects.filter(is_active=True).order_by("-created_at")

        category = self.request.query_params.get("category")
        topic = self.request.query_params.get("topic")
        difficulty = self.request.query_params.get("difficulty")

        if category:
            queryset = queryset.filter(category=category.strip().upper())
        if topic:
            queryset = queryset.filter(topic__icontains=topic.strip())
        if difficulty:
            queryset = queryset.filter(difficulty=difficulty.strip().upper())

        return queryset


class AptitudeQuestionDetailView(generics.RetrieveAPIView):
    """
    Retrieve single active aptitude question without exposing the correct option.
    """

    permission_classes = [IsAuthenticated]
    serializer_class = AptitudeQuestionSerializer
    queryset = AptitudeQuestion.objects.filter(is_active=True)


class AptitudeAttemptStartView(APIView):
    """
    Start a new aptitude test attempt with randomized questions matching specified filters.
    """

    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = AptitudeAttemptStartSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        category = serializer.validated_data.get("category")
        topic = serializer.validated_data.get("topic")
        difficulty = serializer.validated_data.get("difficulty")
        number_of_questions = serializer.validated_data.get("number_of_questions", 10)

        # Filter active questions matching criteria
        pool = AptitudeQuestion.objects.filter(is_active=True)
        if category:
            pool = pool.filter(category=category)
        if topic:
            pool = pool.filter(topic__icontains=topic.strip())
        if difficulty:
            pool = pool.filter(difficulty=difficulty)

        question_ids = list(pool.values_list("id", flat=True))

        if len(question_ids) < number_of_questions:
            return Response(
                {
                    "error": (
                        f"Insufficient questions available. Requested {number_of_questions}, "
                        f"but only {len(question_ids)} available."
                    )
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        selected_ids = random.sample(question_ids, number_of_questions)
        selected_questions = list(
            AptitudeQuestion.objects.filter(id__in=selected_ids)
        )

        with transaction.atomic():
            attempt = AptitudeAttempt.objects.create(
                student=request.user,
                category=category or None,
                topic=topic or "",
                difficulty=difficulty or None,
                total_questions=number_of_questions,
                started_at=timezone.now(),
            )

            answers_to_create = [
                AptitudeAnswer(attempt=attempt, question=question)
                for question in selected_questions
            ]
            AptitudeAnswer.objects.bulk_create(answers_to_create)

        question_data = AptitudeQuestionSerializer(selected_questions, many=True).data

        return Response(
            {
                "attempt_id": attempt.id,
                "total_questions": number_of_questions,
                "category": attempt.category,
                "topic": attempt.topic,
                "difficulty": attempt.difficulty,
                "questions": question_data,
            },
            status=status.HTTP_201_CREATED,
        )


class AptitudeAttemptListView(generics.ListAPIView):
    """
    List test attempts for the authenticated student with optional filtering.
    """

    permission_classes = [IsAuthenticated]
    serializer_class = AptitudeAttemptSerializer

    def get_queryset(self):
        queryset = AptitudeAttempt.objects.filter(student=self.request.user).order_by(
            "-created_at"
        )

        category = self.request.query_params.get("category")
        difficulty = self.request.query_params.get("difficulty")

        if category:
            queryset = queryset.filter(category=category.strip().upper())
        if difficulty:
            queryset = queryset.filter(difficulty=difficulty.strip().upper())

        return queryset


class AptitudeAttemptDetailView(generics.RetrieveAPIView):
    """
    Retrieve full details of an aptitude attempt.
    Before submission, correct answers and explanations are hidden.
    After submission, complete review details are exposed.
    """

    permission_classes = [IsAuthenticated]
    serializer_class = AptitudeAttemptDetailSerializer

    def get_queryset(self):
        return (
            AptitudeAttempt.objects.filter(student=self.request.user)
            .select_related("student")
            .prefetch_related("answers__question")
        )


class AptitudeAttemptAnswerView(APIView):
    """
    Submit an answer to a question within an in-progress attempt.
    Cannot answer twice or submit to an already finalized attempt.
    """

    permission_classes = [IsAuthenticated]

    def post(self, request, attempt_id):
        attempt = get_object_or_404(
            AptitudeAttempt,
            pk=attempt_id,
            student=request.user,
        )

        if attempt.is_submitted:
            return Response(
                {"error": "Cannot submit answers for an already submitted attempt."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        serializer = AptitudeAnswerSubmitSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        question_id = serializer.validated_data["question_id"]
        selected_option = serializer.validated_data["selected_option"]

        answer = attempt.answers.select_related("question").filter(
            question_id=question_id
        ).first()

        if not answer:
            return Response(
                {"error": "Question is not part of this attempt."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if answer.answered_at is not None or answer.selected_option:
            return Response(
                {"error": "This question has already been answered."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Server-side validation and grading
        is_correct = (
            selected_option.strip().upper() == answer.question.correct_option.strip().upper()
        )
        marks = Decimal(str(answer.question.marks)) if is_correct else Decimal("0.00")

        answer.selected_option = selected_option
        answer.is_correct = is_correct
        answer.marks_awarded = marks
        answer.answered_at = timezone.now()
        answer.save()

        return Response(
            {"message": "Answer saved successfully."},
            status=status.HTTP_200_OK,
        )


class AptitudeAttemptSubmitView(APIView):
    """
    Finalize an aptitude test attempt, compute server-side score and accuracy,
    and make the attempt immutable.
    """

    permission_classes = [IsAuthenticated]

    def post(self, request, attempt_id):
        attempt = get_object_or_404(
            AptitudeAttempt,
            pk=attempt_id,
            student=request.user,
        )

        if attempt.is_submitted:
            return Response(
                {"error": "Attempt has already been submitted."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        with transaction.atomic():
            results = calculate_attempt_results(attempt)
            attempt.total_questions = results["total_questions"]
            attempt.correct_answers = results["correct_answers"]
            attempt.wrong_answers = results["wrong_answers"]
            attempt.unanswered = results["unanswered"]
            attempt.score = results["score"]
            attempt.accuracy = results["accuracy"]
            attempt.time_taken_seconds = results["time_taken_seconds"]
            attempt.submitted_at = results["submitted_at"]
            attempt.save()

        return Response(
            {
                "attempt_id": attempt.id,
                "total_questions": attempt.total_questions,
                "correct_answers": attempt.correct_answers,
                "wrong_answers": attempt.wrong_answers,
                "unanswered": attempt.unanswered,
                "score": float(attempt.score),
                "accuracy": float(attempt.accuracy),
                "time_taken_seconds": attempt.time_taken_seconds,
            },
            status=status.HTTP_200_OK,
        )


class AptitudeAnalyticsView(APIView):
    """
    Retrieve comprehensive user-scoped performance analytics across submitted attempts.
    """

    permission_classes = [IsAuthenticated]

    def get(self, request):
        analytics = get_student_aptitude_analytics(request.user)
        return Response(analytics, status=status.HTTP_200_OK)


class AptitudeAIAnalysisView(APIView):
    """
    Generate personalized AI analysis and study recommendations using Gemini.
    """

    permission_classes = [IsAuthenticated]

    def post(self, request):
        analytics = get_student_aptitude_analytics(request.user)

        if analytics["total_attempts"] == 0:
            return Response(
                {
                    "error": (
                        "No submitted attempts found. Please complete at least one aptitude test "
                        "before requesting AI analysis."
                    )
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            analysis_result = analyze_aptitude_performance(analytics)
            return Response(analysis_result, status=status.HTTP_200_OK)
        except GeminiConfigurationError:
            return Response(
                {"error": "Gemini AI service is not properly configured."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
        except (GeminiAPIError, InvalidGeminiResponseError):
            return Response(
                {
                    "error": "Failed to generate AI performance analysis. Please try again later."
                },
                status=status.HTTP_502_BAD_GATEWAY,
            )
        except Exception:
            logger.exception("Unexpected error during aptitude AI analysis.")
            return Response(
                {"error": "An unexpected error occurred during AI analysis."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
