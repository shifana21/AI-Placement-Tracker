import logging

from django.shortcuts import get_object_or_404
from rest_framework import generics, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.ai_interview.models import MockInterview
from apps.ai_interview.serializers import (
    InterviewAnswerSerializer,
    InterviewAnswerSubmitSerializer,
    InterviewQuestionSerializer,
    MockInterviewCreateSerializer,
    MockInterviewResultSerializer,
    MockInterviewSerializer,
)
from apps.ai_interview.services.interview_service import (
    complete_mock_interview,
    start_mock_interview,
    submit_interview_answer,
)
from apps.ai_interview.services.question_generator import (
    GeminiAPIError,
    GeminiConfigurationError,
    InvalidGeminiResponseError,
)

logger = logging.getLogger(__name__)


class MockInterviewStartView(APIView):
    """
    Start a new mock interview session and generate AI interview questions.
    """

    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = MockInterviewCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        interview_type = serializer.validated_data["interview_type"]
        target_role = serializer.validated_data["target_role"]
        experience_level = serializer.validated_data["experience_level"]
        number_of_questions = serializer.validated_data["number_of_questions"]

        try:
            interview, first_question = start_mock_interview(
                student=request.user,
                interview_type=interview_type,
                target_role=target_role,
                experience_level=experience_level,
                number_of_questions=number_of_questions,
            )
        except GeminiConfigurationError:
            return Response(
                {"error": "Gemini AI service is not properly configured."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
        except (GeminiAPIError, InvalidGeminiResponseError):
            return Response(
                {"error": "Failed to generate interview questions. Please try again later."},
                status=status.HTTP_502_BAD_GATEWAY,
            )
        except Exception:
            logger.exception("Unexpected error starting mock interview.")
            return Response(
                {"error": "An unexpected error occurred while starting the interview."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        data = MockInterviewSerializer(interview).data
        data["current_question_detail"] = (
            InterviewQuestionSerializer(first_question).data
            if first_question
            else None
        )
        return Response(data, status=status.HTTP_201_CREATED)


class MockInterviewListView(generics.ListAPIView):
    """
    List mock interviews for the authenticated student ordered newest first.
    """

    permission_classes = [IsAuthenticated]
    serializer_class = MockInterviewSerializer

    def get_queryset(self):
        return MockInterview.objects.filter(student=self.request.user).order_by(
            "-created_at"
        )


class MockInterviewDetailView(generics.RetrieveAPIView):
    """
    Retrieve single mock interview details for the owner.
    """

    permission_classes = [IsAuthenticated]
    serializer_class = MockInterviewSerializer

    def get_queryset(self):
        return MockInterview.objects.filter(student=self.request.user)


class MockInterviewCurrentQuestionView(APIView):
    """
    Get the current unanswered question for an in-progress interview.
    """

    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        interview = get_object_or_404(
            MockInterview,
            pk=pk,
            student=request.user,
        )

        if interview.status == MockInterview.Status.COMPLETED:
            return Response(
                {
                    "message": "Interview is already completed.",
                    "status": MockInterview.Status.COMPLETED,
                    "current_question": None,
                },
                status=status.HTTP_200_OK,
            )

        current_q = interview.questions.filter(
            question_number=interview.current_question
        ).first()

        if not current_q:
            return Response(
                {"error": "No current question found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        return Response(
            InterviewQuestionSerializer(current_q).data,
            status=status.HTTP_200_OK,
        )


class MockInterviewAnswerView(APIView):
    """
    Submit an answer to the current question in an in-progress interview.
    """

    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        interview = get_object_or_404(
            MockInterview,
            pk=pk,
            student=request.user,
        )

        if interview.status != MockInterview.Status.IN_PROGRESS:
            return Response(
                {"error": "Cannot submit answers to an interview that is not in progress."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        current_q = interview.questions.filter(
            question_number=interview.current_question
        ).first()

        if not current_q:
            return Response(
                {"error": "No active question found to answer."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if hasattr(current_q, "answer"):
            return Response(
                {"error": "Current question has already been answered."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        serializer = InterviewAnswerSubmitSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        answer_text = serializer.validated_data["answer_text"]

        try:
            answer_obj, next_q, is_completed = submit_interview_answer(
                interview=interview,
                answer_text=answer_text,
            )
        except ValueError as exc:
            return Response(
                {"error": str(exc)},
                status=status.HTTP_400_BAD_REQUEST,
            )
        except GeminiConfigurationError:
            return Response(
                {"error": "Gemini AI service is not properly configured."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
        except (GeminiAPIError, InvalidGeminiResponseError):
            return Response(
                {"error": "Failed to evaluate answer with AI. Please try again."},
                status=status.HTTP_502_BAD_GATEWAY,
            )
        except Exception:
            logger.exception("Unexpected error evaluating answer.")
            return Response(
                {"error": "An unexpected error occurred during answer evaluation."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        return Response(
            {
                "message": "Answer submitted successfully.",
                "answer": InterviewAnswerSerializer(answer_obj).data,
                "next_question": (
                    InterviewQuestionSerializer(next_q).data if next_q else None
                ),
                "is_completed": is_completed,
            },
            status=status.HTTP_200_OK,
        )


class MockInterviewCompleteView(APIView):
    """
    Manually complete an in-progress interview and generate final AI analysis debrief.
    """

    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        interview = get_object_or_404(
            MockInterview,
            pk=pk,
            student=request.user,
        )

        if interview.status == MockInterview.Status.COMPLETED:
            return Response(
                {"error": "Interview has already been completed."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if interview.status != MockInterview.Status.IN_PROGRESS:
            return Response(
                {"error": "Only in-progress interviews can be completed."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            completed_interview = complete_mock_interview(interview)
        except GeminiConfigurationError:
            return Response(
                {"error": "Gemini AI service is not properly configured."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
        except (GeminiAPIError, InvalidGeminiResponseError):
            return Response(
                {"error": "Failed to generate interview analysis. Please try again later."},
                status=status.HTTP_502_BAD_GATEWAY,
            )
        except Exception:
            logger.exception("Unexpected error completing interview.")
            return Response(
                {"error": "An unexpected error occurred while completing the interview."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        return Response(
            MockInterviewSerializer(completed_interview).data,
            status=status.HTTP_200_OK,
        )


class MockInterviewResultView(APIView):
    """
    Retrieve full question-wise results, evaluations, scores, and debrief for owner.
    """

    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        interview = get_object_or_404(
            MockInterview.objects.select_related("student").prefetch_related(
                "questions__answer"
            ),
            pk=pk,
            student=request.user,
        )

        return Response(
            MockInterviewResultSerializer(interview).data,
            status=status.HTTP_200_OK,
        )
