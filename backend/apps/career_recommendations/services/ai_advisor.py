import json
import logging
import re

from django.conf import settings
from google import genai
from google.genai import types
from pydantic import BaseModel, Field, ValidationError, field_validator

logger = logging.getLogger(__name__)


class GeminiServiceError(Exception):
    """Base exception for Career Recommendations Gemini service."""


class GeminiConfigurationError(GeminiServiceError):
    """Raised when Gemini API key is missing or not configured."""


class GeminiAPIError(GeminiServiceError):
    """Raised when the Gemini API call fails."""


class InvalidGeminiResponseError(GeminiServiceError):
    """Raised when Gemini returns malformed or invalid response data."""


class CareerRecommendationAISchema(BaseModel):
    target_role: str
    explanation: str
    matching_skills: list[str] = Field(default_factory=list)
    missing_skills: list[str] = Field(default_factory=list)
    recommended_skills: list[str] = Field(default_factory=list)
    suggested_projects: list[str] = Field(default_factory=list)
    learning_roadmap: list[dict | str] = Field(default_factory=list)

    @field_validator(
        "matching_skills",
        "missing_skills",
        "recommended_skills",
        "suggested_projects",
        mode="before",
    )
    @classmethod
    def ensure_string_list(cls, value):
        if value is None:
            return []
        if not isinstance(value, list):
            raise TypeError("Expected a list.")
        return [str(item).strip() for item in value if str(item).strip()]


SYSTEM_INSTRUCTION = """You are an objective AI career advisory engine for a college placement preparation platform.

Your task is to enrich an evidence-based career recommendation for a student based ONLY on the provided candidate evidence and target role match.

Guidelines:
1. Base your explanation strictly on the candidate's demonstrated evidence (skills, projects, coding experience, aptitude performance, and interview results).
2. Do NOT invent achievements, marks, work experience, or certifications not in the input.
3. Do NOT make hiring promises or claim guaranteed job placement.
4. Detail actionable skill gaps and suggest concrete, resume-worthy placement projects targeting those gaps.
5. Create a step-by-step learning roadmap outlining practical milestones.
6. Return valid JSON only with exactly these keys:
   target_role, explanation, matching_skills, missing_skills, recommended_skills, suggested_projects, learning_roadmap."""

USER_PROMPT_TEMPLATE = """Target Role: {target_role}
Computed Match Score: {match_score}%
Candidate Demonstrated Skills: {demonstrated_skills}
Role Matching Skills: {matching_skills}
Missing Skills to Address: {missing_skills}
Preparation Context:
- Coding Problems Solved: {coding_solved}
- Aptitude Accuracy: {aptitude_accuracy}%
- Mock Interview Completed: {interview_count}

Provide a personalized career development analysis, suggested portfolio projects, and learning roadmap as JSON."""


def _get_api_key():
    api_key = getattr(settings, "GEMINI_API_KEY", "") or ""
    if not api_key.strip():
        raise GeminiConfigurationError("Gemini API key is not configured.")
    return api_key.strip()


def _extract_response_text(response):
    try:
        text = response.text
    except (AttributeError, ValueError) as exc:
        raise InvalidGeminiResponseError(
            "Gemini returned an empty or blocked response."
        ) from exc

    if not text or not text.strip():
        raise InvalidGeminiResponseError(
            "Gemini returned an empty or blocked response."
        )

    return text.strip()


def _parse_json_from_text(text):
    cleaned = text.strip()
    fence_match = re.match(
        r"^```(?:json)?\s*(.*?)\s*```$",
        cleaned,
        flags=re.DOTALL | re.IGNORECASE,
    )
    if fence_match:
        cleaned = fence_match.group(1).strip()

    try:
        payload = json.loads(cleaned)
    except json.JSONDecodeError as exc:
        raise InvalidGeminiResponseError(
            "Gemini response was not valid JSON."
        ) from exc

    return payload


def enrich_recommendation_with_gemini(role_match, evidence):
    """
    Enrich a baseline role match with Gemini-generated explanation, projects, and roadmap.
    """
    api_key = _get_api_key()
    model_name = getattr(settings, "GEMINI_MODEL", "gemini-2.0-flash")

    client = genai.Client(api_key=api_key)

    prompt = USER_PROMPT_TEMPLATE.format(
        target_role=role_match["target_role"],
        match_score=float(role_match["match_score"]),
        demonstrated_skills=", ".join(evidence.get("all_candidate_skills", [])[:15]) or "None recorded",
        matching_skills=", ".join(role_match.get("matching_skills", [])) or "None",
        missing_skills=", ".join(role_match.get("missing_skills", [])) or "None",
        coding_solved=evidence.get("coding", {}).get("total_solved", 0),
        aptitude_accuracy=evidence.get("aptitude", {}).get("overall_accuracy", 0.0),
        interview_count=evidence.get("interview", {}).get("completed_count", 0),
    )

    try:
        response = client.models.generate_content(
            model=model_name,
            contents=prompt,
            config=types.GenerateContentConfig(
                system_instruction=SYSTEM_INSTRUCTION,
                response_mime_type="application/json",
            ),
        )
    except Exception as exc:
        logger.exception("Gemini API call failed during career recommendation enrichment.")
        raise GeminiAPIError("Failed to enrich career recommendation with Gemini.") from exc

    raw_text = _extract_response_text(response)
    payload = _parse_json_from_text(raw_text)

    try:
        validated = CareerRecommendationAISchema.model_validate(payload)
    except (ValidationError, TypeError) as exc:
        raise InvalidGeminiResponseError(
            "Career recommendation AI output failed validation."
        ) from exc

    return validated.model_dump()
