from decimal import Decimal
from django.utils import timezone


def calculate_attempt_results(attempt, submitted_at=None):
    """
    Calculate and return server-side scoring metrics for an aptitude attempt.

    Formula:
      accuracy = (correct_answers / total_questions) * 100
      time_taken_seconds = submitted_at - started_at
    """
    if submitted_at is None:
        submitted_at = timezone.now()

    answers = attempt.answers.select_related("question").all()
    total_questions = attempt.total_questions or answers.count()

    correct_answers = 0
    wrong_answers = 0
    unanswered = 0
    total_score = Decimal("0.00")

    for ans in answers:
        if not ans.selected_option or not ans.selected_option.strip():
            unanswered += 1
            ans.is_correct = False
            ans.marks_awarded = Decimal("0.00")
        elif ans.selected_option.strip().upper() == ans.question.correct_option.strip().upper():
            correct_answers += 1
            ans.is_correct = True
            ans.marks_awarded = Decimal(str(ans.question.marks))
            total_score += ans.marks_awarded
        else:
            wrong_answers += 1
            ans.is_correct = False
            ans.marks_awarded = Decimal("0.00")
        ans.save()

    if total_questions > 0:
        accuracy = round(
            Decimal(correct_answers) / Decimal(total_questions) * Decimal("100.00"),
            2,
        )
    else:
        accuracy = Decimal("0.00")

    time_taken = max(0, int((submitted_at - attempt.started_at).total_seconds()))

    return {
        "total_questions": total_questions,
        "correct_answers": correct_answers,
        "wrong_answers": wrong_answers,
        "unanswered": unanswered,
        "score": total_score,
        "accuracy": accuracy,
        "time_taken_seconds": time_taken,
        "submitted_at": submitted_at,
    }
