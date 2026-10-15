from decimal import Decimal
import logging

from django.db import transaction
from django.utils import timezone

from apps.ai_interview.models import (
    InterviewAnswer,
    InterviewQuestion,
    MockInterview,
)
from .evaluation import evaluate_interview_answer, generate_final_interview_analysis
from .question_generator import generate_interview_questions

logger = logging.getLogger(__name__)


def start_mock_interview(
    student,
    interview_type,
    target_role,
    experience_level,
    number_of_questions,
):
    """
    Start a new mock interview session and generate AI interview questions.
    """
    generated_questions = generate_interview_questions(
        interview_type=interview_type,
        target_role=target_role,
        experience_level=experience_level,
        number_of_questions=number_of_questions,
    )

    with transaction.atomic():
        interview = MockInterview.objects.create(
            student=student,
            interview_type=interview_type,
            target_role=target_role.strip(),
            experience_level=experience_level,
            number_of_questions=number_of_questions,
            current_question=1,
            status=MockInterview.Status.IN_PROGRESS,
        )

        question_objs = [
            InterviewQuestion(
                interview=interview,
                question_number=item["question_number"],
                question_text=item["question_text"],
                question_type=item["question_type"],
                topic=item.get("topic", ""),
            )
            for item in generated_questions
        ]
        InterviewQuestion.objects.bulk_create(question_objs)

    first_question = interview.questions.filter(question_number=1).first()
    return interview, first_question


def submit_interview_answer(interview, answer_text):
    """
    Evaluate candidate's answer for the current question, record results,
    advance to the next question or complete interview if all are answered.
    """
    if interview.status != MockInterview.Status.IN_PROGRESS:
        raise ValueError("Cannot submit answers to an interview that is not in progress.")

    current_q = interview.questions.filter(
        question_number=interview.current_question
    ).first()

    if not current_q:
        raise ValueError("Current question not found for this interview.")

    if hasattr(current_q, "answer"):
        raise ValueError("Current question has already been answered.")

    # Call AI evaluation
    eval_result = evaluate_interview_answer(
        question_text=current_q.question_text,
        question_type=current_q.question_type,
        topic=current_q.topic,
        target_role=interview.target_role,
        experience_level=interview.experience_level,
        answer_text=answer_text,
    )

    score_val = Decimal(str(round(eval_result["score"], 2)))

    with transaction.atomic():
        answer_obj = InterviewAnswer.objects.create(
            question=current_q,
            answer_text=answer_text.strip(),
            score=score_val,
            evaluation=eval_result["evaluation"],
            strengths=eval_result["strengths"],
            weaknesses=eval_result["weaknesses"],
            improvement_suggestions=eval_result["improvement_suggestions"],
            answered_at=timezone.now(),
        )

        if interview.current_question < interview.number_of_questions:
            interview.current_question += 1
            interview.save()
            next_q = interview.questions.filter(
                question_number=interview.current_question
            ).first()
            is_completed = False
        else:
            # Last question answered: complete interview
            complete_mock_interview(interview)
            next_q = None
            is_completed = True

    return answer_obj, next_q, is_completed


def complete_mock_interview(interview):
    """
    Finalize mock interview, compute overall score, generate AI analysis debrief.
    """
    if interview.status == MockInterview.Status.COMPLETED:
        return interview

    if interview.status != MockInterview.Status.IN_PROGRESS:
        raise ValueError("Only an in-progress interview can be completed.")

    # Calculate overall score as mathematical average of answer scores
    answers = InterviewAnswer.objects.filter(
        question__interview=interview
    ).select_related("question").order_by("question__question_number")

    scores = [ans.score for ans in answers if ans.score is not None]
    if scores:
        overall_score = Decimal(str(round(sum(scores) / len(scores), 2)))
    else:
        overall_score = Decimal("0.00")

    questions_summary = [
        {
            "question_number": ans.question.question_number,
            "question_text": ans.question.question_text,
            "topic": ans.question.topic,
            "score": float(ans.score or 0),
            "evaluation": ans.evaluation,
            "strengths": ans.strengths,
            "weaknesses": ans.weaknesses,
        }
        for ans in answers
    ]

    final_analysis = generate_final_interview_analysis(
        interview_type=interview.interview_type,
        target_role=interview.target_role,
        experience_level=interview.experience_level,
        computed_overall_score=overall_score,
        questions_evaluations=questions_summary,
    )

    with transaction.atomic():
        interview.overall_score = overall_score
        interview.overall_feedback = final_analysis["overall_feedback"]
        interview.strengths = final_analysis["strengths"]
        interview.weaknesses = final_analysis["weaknesses"]
        interview.recommendations = final_analysis["recommendations"]
        interview.status = MockInterview.Status.COMPLETED
        interview.completed_at = timezone.now()
        interview.save()

    return interview
