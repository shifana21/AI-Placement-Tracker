import re

from apps.coding_progress.models import CodingProblem
from apps.companies.models import Company


def _normalize_skill(skill_str):
    if not skill_str:
        return ""
    cleaned = re.sub(r"[^\w\s\+\#\.\-]", "", skill_str.strip().lower())
    return cleaned


def _split_skills(raw_text):
    if not raw_text:
        return []
    # Split by comma, semicolon, newline, or pipe
    parts = re.split(r"[,;\n\|]+", raw_text)
    skills = []
    for p in parts:
        normalized = _normalize_skill(p)
        if normalized and len(normalized) >= 2:
            skills.append(normalized)
    return list(dict.fromkeys(skills))


def collect_student_evidence(student):
    """
    Safely collects student placement preparation evidence across all active modules.
    Handles missing modules/data gracefully without negative assumptions.
    """
    # 1. Profile data
    profile_data = {
        "exists": False,
        "branch": "",
        "cgpa": None,
        "skills": [],
    }
    if hasattr(student, "profile") and student.profile:
        prof = student.profile
        profile_data["exists"] = True
        profile_data["branch"] = prof.branch or ""
        profile_data["cgpa"] = float(prof.cgpa) if prof.cgpa is not None else None
        profile_data["skills"] = _split_skills(prof.skills)

    # 2. Resume & Resume Analysis data
    resume_data = {
        "exists": False,
        "skills": [],
        "projects": [],
        "resume_score": None,
    }
    try:
        from apps.resume_analysis.models import ResumeAnalysis

        latest_analysis = (
            ResumeAnalysis.objects.filter(
                resume__student=student,
                status=ResumeAnalysis.Status.COMPLETED,
            )
            .order_by("-updated_at")
            .first()
        )
        if latest_analysis and latest_analysis.analysis_result:
            resume_data["exists"] = True
            res_json = latest_analysis.analysis_result
            skills_list = res_json.get("skills", [])
            if isinstance(skills_list, list):
                resume_data["skills"] = [
                    _normalize_skill(s) for s in skills_list if _normalize_skill(s)
                ]
            projects_list = res_json.get("projects", [])
            if isinstance(projects_list, list):
                resume_data["projects"] = [
                    p.strip() for p in projects_list if isinstance(p, str) and p.strip()
                ]
            resume_data["resume_score"] = res_json.get("resume_score")
    except Exception:
        pass

    # 3. Coding Progress data
    coding_data = {
        "exists": False,
        "total_solved": 0,
        "topics": [],
        "platforms": [],
    }
    try:
        coding_qs = CodingProblem.objects.filter(student=student)
        total_solved = coding_qs.count()
        if total_solved > 0:
            coding_data["exists"] = True
            coding_data["total_solved"] = total_solved
            raw_topics = list(
                coding_qs.exclude(topic="")
                .values_list("topic", flat=True)
                .distinct()
            )
            coding_data["topics"] = [
                _normalize_skill(t) for t in raw_topics if _normalize_skill(t)
            ]
            coding_data["platforms"] = list(
                coding_qs.values_list("platform", flat=True).distinct()
            )
    except Exception:
        pass

    # 4. Aptitude Practice data
    aptitude_data = {
        "exists": False,
        "total_attempts": 0,
        "overall_accuracy": 0.0,
        "strong_topics": [],
        "weak_topics": [],
    }
    try:
        from apps.aptitude.services.analytics import get_student_aptitude_analytics

        apt_analytics = get_student_aptitude_analytics(student)
        if apt_analytics.get("total_attempts", 0) > 0:
            aptitude_data["exists"] = True
            aptitude_data["total_attempts"] = apt_analytics.get("total_attempts", 0)
            aptitude_data["overall_accuracy"] = float(
                apt_analytics.get("overall_accuracy", 0.0)
            )
            aptitude_data["strong_topics"] = apt_analytics.get("strong_topics", [])
            aptitude_data["weak_topics"] = apt_analytics.get("weak_topics", [])
    except Exception:
        pass

    # 5. Mock Interview data
    interview_data = {
        "exists": False,
        "completed_count": 0,
        "average_score": None,
        "target_roles": [],
        "strengths": [],
        "weaknesses": [],
    }
    try:
        from apps.ai_interview.models import MockInterview

        completed_interviews = MockInterview.objects.filter(
            student=student,
            status=MockInterview.Status.COMPLETED,
        )
        completed_count = completed_interviews.count()
        if completed_count > 0:
            interview_data["exists"] = True
            interview_data["completed_count"] = completed_count
            scores = [
                float(i.overall_score)
                for i in completed_interviews
                if i.overall_score is not None
            ]
            if scores:
                interview_data["average_score"] = round(sum(scores) / len(scores), 2)
            interview_data["target_roles"] = list(
                completed_interviews.values_list("target_role", flat=True).distinct()
            )
            all_str = []
            all_weak = []
            for item in completed_interviews:
                if isinstance(item.strengths, list):
                    all_str.extend(item.strengths)
                if isinstance(item.weaknesses, list):
                    all_weak.extend(item.weaknesses)
            interview_data["strengths"] = list(dict.fromkeys(all_str))[:5]
            interview_data["weaknesses"] = list(dict.fromkeys(all_weak))[:5]
    except Exception:
        pass

    # 6. Unified de-duplicated Candidate Skills list
    combined_skills = set(profile_data["skills"]) | set(resume_data["skills"])
    # Coding topics like "arrays", "graphs", "dp", "trees", "python" also count as skills/competencies
    for t in coding_data["topics"]:
        combined_skills.add(t)

    all_candidate_skills = sorted(list(combined_skills))

    return {
        "profile": profile_data,
        "resume": resume_data,
        "coding": coding_data,
        "aptitude": aptitude_data,
        "interview": interview_data,
        "all_candidate_skills": all_candidate_skills,
    }
