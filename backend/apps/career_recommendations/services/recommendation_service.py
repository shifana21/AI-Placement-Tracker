from django.db import transaction

from apps.career_recommendations.models import CareerRecommendation
from apps.career_recommendations.services.ai_advisor import (
    enrich_recommendation_with_gemini,
)
from apps.career_recommendations.services.matching_engine import (
    generate_baseline_recommendations,
)


def _build_fallback_projects_and_roadmap(role_name, missing_skills):
    """
    Generate deterministic projects and roadmap if AI enhancement is not invoked.
    """
    projects = [
        f"Build a full-featured portfolio application demonstrating {role_name} workflows.",
        f"Design and deploy an end-to-end service addressing {', '.join(missing_skills[:3]) or 'core role fundamentals'}.",
    ]
    roadmap = [
        {
            "phase": "Phase 1: Skill Gap Remediation",
            "focus_areas": missing_skills[:4],
            "goal": "Build conceptual and hands-on familiarity with primary missing technologies.",
        },
        {
            "phase": "Phase 2: Project Implementation",
            "focus_areas": ["Hands-on projects", "System design"],
            "goal": "Apply new skills in measurable, resume-ready GitHub projects.",
        },
        {
            "phase": "Phase 3: Placement & Interview Prep",
            "focus_areas": ["Mock interviews", "Coding & Aptitude"],
            "goal": "Refine technical communication and domain problem solving.",
        },
    ]
    return projects, roadmap


def generate_student_career_recommendations(student, top_n=3, use_ai=True):
    """
    Orchestrates evidence collection, baseline role matching, optional Gemini AI
    enhancement, and database persistence.
    """
    ranked_matches, evidence = generate_baseline_recommendations(student, top_n=top_n)
    created_recommendations = []

    with transaction.atomic():
        for match in ranked_matches:
            target_role = match["target_role"]
            match_score = match["match_score"]
            matching_skills = match["matching_skills"]
            missing_skills = match["missing_skills"]
            recommended_skills = match.get("recommended_skills", missing_skills)
            source_summary = match.get("source_summary", {})

            explanation = match.get("explanation_baseline", "")
            suggested_projects, learning_roadmap = _build_fallback_projects_and_roadmap(
                target_role, missing_skills
            )

            if use_ai:
                ai_data = enrich_recommendation_with_gemini(match, evidence)
                explanation = ai_data.get("explanation", explanation)
                suggested_projects = ai_data.get("suggested_projects", suggested_projects)
                learning_roadmap = ai_data.get("learning_roadmap", learning_roadmap)
                if ai_data.get("recommended_skills"):
                    recommended_skills = ai_data["recommended_skills"]

            rec = CareerRecommendation.objects.create(
                student=student,
                target_role=target_role,
                match_score=match_score,
                explanation=explanation,
                matching_skills=matching_skills,
                missing_skills=missing_skills,
                recommended_skills=recommended_skills,
                suggested_projects=suggested_projects,
                learning_roadmap=learning_roadmap,
                source_summary=source_summary,
            )
            created_recommendations.append(rec)

    return created_recommendations
