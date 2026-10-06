from django.db.models import Avg, Count, Q, Sum
from apps.aptitude.models import AptitudeAnswer, AptitudeAttempt, AptitudeQuestion

WEAK_TOPIC_ACCURACY_THRESHOLD = 60.0
STRONG_TOPIC_ACCURACY_THRESHOLD = 80.0


def get_student_aptitude_analytics(student):
    """
    Compute structured aptitude practice analytics for a specific student.
    Calculations are strictly scoped to the student's submitted attempts.
    """
    submitted_attempts = AptitudeAttempt.objects.filter(
        student=student,
        submitted_at__isnull=False,
    )

    total_attempts = submitted_attempts.count()

    if total_attempts == 0:
        return {
            "total_attempts": 0,
            "total_questions": 0,
            "total_correct": 0,
            "overall_accuracy": 0.0,
            "average_score": 0.0,
            "by_category": {},
            "by_difficulty": {},
            "by_topic": {},
            "recent_attempts": [],
            "weak_topics": [],
            "strong_topics": [],
        }

    attempt_agg = submitted_attempts.aggregate(
        total_q=Sum("total_questions"),
        total_c=Sum("correct_answers"),
        avg_score=Avg("score"),
    )

    total_questions = attempt_agg["total_q"] or 0
    total_correct = attempt_agg["total_c"] or 0
    average_score = round(float(attempt_agg["avg_score"] or 0.0), 2)
    overall_accuracy = (
        round((total_correct / total_questions) * 100.0, 2)
        if total_questions > 0
        else 0.0
    )

    user_answers = AptitudeAnswer.objects.filter(
        attempt__student=student,
        attempt__submitted_at__isnull=False,
    )

    # 1. By Category
    category_rows = (
        user_answers.values("question__category")
        .annotate(
            questions=Count("id"),
            correct=Count("id", filter=Q(is_correct=True)),
            attempt_count=Count("attempt_id", distinct=True),
        )
        .order_by("question__category")
    )
    by_category = {}
    for row in category_rows:
        cat_key = row["question__category"]
        q_count = row["questions"]
        c_count = row["correct"]
        att_count = row["attempt_count"]
        cat_acc = round((c_count / q_count) * 100.0, 2) if q_count > 0 else 0.0
        cat_avg = round(c_count / att_count, 2) if att_count > 0 else 0.0
        by_category[cat_key] = {
            "attempt_count": att_count,
            "questions": q_count,
            "correct": c_count,
            "accuracy": cat_acc,
            "average_score": cat_avg,
        }

    # 2. By Difficulty
    difficulty_rows = (
        user_answers.values("question__difficulty")
        .annotate(
            questions=Count("id"),
            correct=Count("id", filter=Q(is_correct=True)),
            attempt_count=Count("attempt_id", distinct=True),
        )
        .order_by("question__difficulty")
    )
    by_difficulty = {}
    for row in difficulty_rows:
        diff_key = row["question__difficulty"]
        q_count = row["questions"]
        c_count = row["correct"]
        att_count = row["attempt_count"]
        diff_acc = round((c_count / q_count) * 100.0, 2) if q_count > 0 else 0.0
        diff_avg = round(c_count / att_count, 2) if att_count > 0 else 0.0
        by_difficulty[diff_key] = {
            "attempt_count": att_count,
            "questions": q_count,
            "correct": c_count,
            "accuracy": diff_acc,
            "average_score": diff_avg,
        }

    # 3. By Topic
    topic_rows = (
        user_answers.exclude(question__topic="")
        .values("question__topic")
        .annotate(
            questions=Count("id"),
            correct=Count("id", filter=Q(is_correct=True)),
            attempt_count=Count("attempt_id", distinct=True),
        )
        .order_by("question__topic")
    )
    by_topic = {}
    weak_topics_list = []
    strong_topics_list = []

    for row in topic_rows:
        topic_name = row["question__topic"]
        q_count = row["questions"]
        c_count = row["correct"]
        att_count = row["attempt_count"]
        topic_acc = round((c_count / q_count) * 100.0, 2) if q_count > 0 else 0.0
        by_topic[topic_name] = {
            "attempt_count": att_count,
            "questions": q_count,
            "correct": c_count,
            "accuracy": topic_acc,
        }

        if topic_acc < WEAK_TOPIC_ACCURACY_THRESHOLD:
            weak_topics_list.append((topic_name, topic_acc))
        elif topic_acc >= STRONG_TOPIC_ACCURACY_THRESHOLD:
            strong_topics_list.append((topic_name, topic_acc))

    weak_topics_list.sort(key=lambda x: x[1])
    strong_topics_list.sort(key=lambda x: x[1], reverse=True)

    weak_topics = [t[0] for t in weak_topics_list]
    strong_topics = [t[0] for t in strong_topics_list]

    # 4. Recent Attempts
    recent_qs = submitted_attempts.order_by("-submitted_at", "-created_at")[:5]
    recent_attempts = [
        {
            "id": att.id,
            "category": att.category,
            "topic": att.topic,
            "difficulty": att.difficulty,
            "total_questions": att.total_questions,
            "correct_answers": att.correct_answers,
            "wrong_answers": att.wrong_answers,
            "unanswered": att.unanswered,
            "score": float(att.score),
            "accuracy": float(att.accuracy),
            "time_taken_seconds": att.time_taken_seconds,
            "submitted_at": att.submitted_at.isoformat() if att.submitted_at else None,
        }
        for att in recent_qs
    ]

    return {
        "total_attempts": total_attempts,
        "total_questions": total_questions,
        "total_correct": total_correct,
        "overall_accuracy": overall_accuracy,
        "average_score": average_score,
        "by_category": by_category,
        "by_difficulty": by_difficulty,
        "by_topic": by_topic,
        "recent_attempts": recent_attempts,
        "weak_topics": weak_topics,
        "strong_topics": strong_topics,
    }
