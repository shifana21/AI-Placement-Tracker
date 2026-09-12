from .models import Company


def check_company_eligibility(student_profile, company):
    """
    Check whether a student is eligible for a company.
    """

    criteria = {}
    reasons = []

    # 1. CGPA check
    cgpa_eligible = (
        student_profile.cgpa is not None
        and student_profile.cgpa >= company.minimum_cgpa
    )

    criteria["cgpa"] = cgpa_eligible

    if not cgpa_eligible:
        if student_profile.cgpa is None:
            reasons.append("CGPA is not provided.")
        else:
            reasons.append(
                f"Minimum CGPA required is {company.minimum_cgpa}."
            )

    # 2. Branch check
    eligible_branches = [
        branch.strip().lower()
        for branch in company.eligible_branches.split(",")
        if branch.strip()
    ]

    student_branch = student_profile.branch.strip().lower()

    branch_eligible = (
        not eligible_branches
        or student_branch in eligible_branches
    )

    criteria["branch"] = branch_eligible

    if not branch_eligible:
        reasons.append(
            f"Branch {student_profile.branch} is not eligible."
        )

    # 3. Backlog check
    backlog_eligible = (
        student_profile.backlogs <= company.maximum_backlogs
    )

    criteria["backlogs"] = backlog_eligible

    if not backlog_eligible:
        reasons.append(
            f"Maximum allowed backlogs is "
            f"{company.maximum_backlogs}."
        )

    # 4. Skills check
    required_skills = [
        skill.strip().lower()
        for skill in company.required_skills.split(",")
        if skill.strip()
    ]

    student_skills = [
        skill.strip().lower()
        for skill in student_profile.skills.split(",")
        if skill.strip()
    ]

    missing_skills = [
        skill
        for skill in required_skills
        if skill not in student_skills
    ]

    skills_eligible = len(missing_skills) == 0

    criteria["skills"] = skills_eligible

    for skill in missing_skills:
        reasons.append(f"Missing required skill: {skill}")

    # Overall eligibility
    eligible = all(criteria.values())

    if eligible:
        reasons.append("Student meets all eligibility criteria.")

    return {
        "company": company.name,
        "eligible": eligible,
        "criteria": criteria,
        "reasons": reasons,
    }