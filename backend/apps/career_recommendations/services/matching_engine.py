from decimal import Decimal

from apps.career_recommendations.services.data_collector import (
    _normalize_skill,
    collect_student_evidence,
)

STANDARD_ROLE_PROFILES = [
    {
        "role": "Backend Developer",
        "required_skills": [
            "python",
            "django",
            "sql",
            "rest api",
            "data structures",
            "database",
            "git",
        ],
        "preferred_skills": [
            "docker",
            "redis",
            "postgresql",
            "fastapi",
            "system design",
            "microservices",
        ],
    },
    {
        "role": "Frontend Developer",
        "required_skills": [
            "javascript",
            "react",
            "html",
            "css",
            "git",
            "responsive design",
        ],
        "preferred_skills": [
            "typescript",
            "redux",
            "tailwind",
            "next.js",
            "ui/ux",
            "web performance",
        ],
    },
    {
        "role": "Full Stack Engineer",
        "required_skills": [
            "python",
            "javascript",
            "react",
            "django",
            "sql",
            "html",
            "css",
            "rest api",
            "git",
        ],
        "preferred_skills": [
            "docker",
            "postgresql",
            "typescript",
            "cloud",
            "ci/cd",
            "testing",
        ],
    },
    {
        "role": "Data Scientist / ML Engineer",
        "required_skills": [
            "python",
            "sql",
            "machine learning",
            "data analysis",
            "pandas",
            "numpy",
            "statistics",
        ],
        "preferred_skills": [
            "deep learning",
            "scikit-learn",
            "tensorflow",
            "data visualization",
            "nlp",
            "big data",
        ],
    },
    {
        "role": "DevOps / Cloud Engineer",
        "required_skills": [
            "linux",
            "docker",
            "git",
            "ci/cd",
            "bash",
            "networking",
            "cloud",
        ],
        "preferred_skills": [
            "kubernetes",
            "aws",
            "terraform",
            "monitoring",
            "ansible",
            "security",
        ],
    },
]


def match_skills(candidate_skills, required_skills, preferred_skills):
    """
    Computes matching, missing, and prioritized recommended skills.
    Matches skill substrings and exact matches.
    """
    candidate_set = set(candidate_skills)

    def is_present(role_skill):
        # Match exact or as word substring (e.g. 'django' in 'django rest framework')
        for c in candidate_set:
            if role_skill == c or role_skill in c or c in role_skill:
                return True
        return False

    matching_req = [s for s in required_skills if is_present(s)]
    missing_req = [s for s in required_skills if not is_present(s)]

    matching_pref = [s for s in preferred_skills if is_present(s)]
    missing_pref = [s for s in preferred_skills if not is_present(s)]

    matching_all = list(dict.fromkeys(matching_req + matching_pref))
    missing_all = list(dict.fromkeys(missing_req + missing_pref))
    recommended_all = missing_req + missing_pref

    return {
        "matching_skills": matching_all,
        "missing_skills": missing_all,
        "recommended_skills": recommended_all,
        "matching_req_count": len(matching_req),
        "total_req_count": len(required_skills),
        "matching_pref_count": len(matching_pref),
        "total_pref_count": len(preferred_skills),
    }


def compute_role_match(role_profile, evidence):
    """
    Deterministic, transparent baseline scoring algorithm based on available evidence.
    Missing data sources are never penalized.
    """
    candidate_skills = evidence.get("all_candidate_skills", [])
    skill_analysis = match_skills(
        candidate_skills=candidate_skills,
        required_skills=role_profile["required_skills"],
        preferred_skills=role_profile["preferred_skills"],
    )

    req_count = skill_analysis["total_req_count"]
    pref_count = skill_analysis["total_pref_count"]

    denominator = (req_count * 1.0) + (pref_count * 0.5)
    numerator = (skill_analysis["matching_req_count"] * 1.0) + (
        skill_analysis["matching_pref_count"] * 0.5
    )

    skill_score = (numerator / denominator * 100.0) if denominator > 0 else 0.0
    skill_score = min(100.0, max(0.0, skill_score))

    # Auxiliary evidence components
    aux_scores = []
    # 1. Coding score
    coding = evidence.get("coding", {})
    if coding.get("exists") and coding.get("total_solved", 0) > 0:
        # 20 solved problems gives 100% coding component
        c_score = min(100.0, coding["total_solved"] * 5.0)
        aux_scores.append(c_score)

    # 2. Aptitude score
    aptitude = evidence.get("aptitude", {})
    if aptitude.get("exists") and aptitude.get("total_attempts", 0) > 0:
        a_score = float(aptitude.get("overall_accuracy", 0.0))
        aux_scores.append(a_score)

    # 3. Mock Interview score
    interview = evidence.get("interview", {})
    if (
        interview.get("exists")
        and interview.get("completed_count", 0) > 0
        and interview.get("average_score") is not None
    ):
        i_score = float(interview["average_score"])
        aux_scores.append(i_score)

    # Dynamic Weight Reallocation:
    # Baseline skill weight is 60%. Remaining 40% is shared equally by existing auxiliary sources.
    # If no auxiliary data exists, skill weight is 100% (no missing data penalty).
    if not aux_scores:
        final_score = skill_score
    else:
        w_skill = 0.60
        w_aux = 0.40 / len(aux_scores)
        final_score = (w_skill * skill_score) + sum(w_aux * s for s in aux_scores)

    match_score = Decimal(str(round(min(100.0, max(0.0, final_score)), 2)))

    explanation_parts = [
        f"Calculated match score of {match_score}% for {role_profile['role']}."
    ]
    if skill_analysis["matching_skills"]:
        explanation_parts.append(
            f"Demonstrated skills: {', '.join(skill_analysis['matching_skills'][:5])}."
        )
    if skill_analysis["missing_skills"]:
        explanation_parts.append(
            f"Key skill gaps to address: {', '.join(skill_analysis['missing_skills'][:5])}."
        )

    return {
        "target_role": role_profile["role"],
        "match_score": match_score,
        "matching_skills": skill_analysis["matching_skills"],
        "missing_skills": skill_analysis["missing_skills"],
        "recommended_skills": skill_analysis["recommended_skills"],
        "explanation_baseline": " ".join(explanation_parts),
    }


def generate_baseline_recommendations(student, top_n=3):
    """
    Collects student evidence, evaluates standard role profiles,
    and returns top_n ranked recommendations.
    """
    evidence = collect_student_evidence(student)
    results = []

    for profile in STANDARD_ROLE_PROFILES:
        res = compute_role_match(profile, evidence)
        res["source_summary"] = {
            "profile_present": evidence["profile"]["exists"],
            "resume_present": evidence["resume"]["exists"],
            "coding_solved": evidence["coding"]["total_solved"],
            "aptitude_attempts": evidence["aptitude"]["total_attempts"],
            "interviews_completed": evidence["interview"]["completed_count"],
            "candidate_skills_count": len(evidence["all_candidate_skills"]),
        }
        results.append(res)

    # Sort descending by match_score
    results.sort(key=lambda x: x["match_score"], reverse=True)
    return results[:top_n], evidence
