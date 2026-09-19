import json
import logging
import re

from google import genai
from google.genai import types
from django.conf import settings
from pydantic import BaseModel, Field, ValidationError, field_validator

logger = logging.getLogger(__name__)

RESUME_ANALYSIS_JSON_SCHEMA = {
    "resume_score": 0,
    "candidate_summary": "",
    "skills": [],
    "education": [],
    "experience": [],
    "projects": [],
    "certifications": [],
    "strengths": [],
    "missing_skills": [],
    "improvement_suggestions": [],
    "recommended_roles": [],
}

SYSTEM_INSTRUCTION = """You are a resume analyst for college placement students in software, AI, and data roles.

Analyze ONLY information explicitly present in the resume text provided.
Do NOT invent work experience, education, certifications, skills, projects, or achievements.
If a category has no supported information in the resume, use an empty string or empty list.

Return valid JSON only, with exactly these keys:
resume_score, candidate_summary, skills, education, experience, projects,
certifications, strengths, missing_skills, improvement_suggestions, recommended_roles.

resume_score must be an integer from 0 to 100 reflecting resume quality for placement readiness,
based only on what is present (not assumed credentials).

skills, education, experience, projects, certifications, strengths, missing_skills,
improvement_suggestions, and recommended_roles must be JSON arrays of strings.

candidate_summary must be a concise string summarizing the candidate based only on the resume.

Focus on technical skills, education, projects, internships/experience, certifications,
strengths, gaps, improvement suggestions, and suitable software/AI/data-related roles.
Do not make unsupported claims about the candidate."""

USER_PROMPT_TEMPLATE = """Analyze the following resume text and return the JSON object described in your instructions.

Resume text:
---
{resume_text}
---"""


class GeminiServiceError(Exception):
    """Base error for Gemini resume analysis."""


class GeminiConfigurationError(GeminiServiceError):
    """Raised when Gemini is not configured."""


class GeminiAPIError(GeminiServiceError):
    """Raised when the Gemini API call fails."""


class InvalidGeminiResponseError(GeminiServiceError):
    """Raised when Gemini returns invalid or unparseable analysis data."""


class ResumeAnalysisResultSchema(BaseModel):
    resume_score: int = Field(ge=0, le=100)
    candidate_summary: str = ""
    skills: list[str] = Field(default_factory=list)
    education: list[str] = Field(default_factory=list)
    experience: list[str] = Field(default_factory=list)
    projects: list[str] = Field(default_factory=list)
    certifications: list[str] = Field(default_factory=list)
    strengths: list[str] = Field(default_factory=list)
    missing_skills: list[str] = Field(default_factory=list)
    improvement_suggestions: list[str] = Field(default_factory=list)
    recommended_roles: list[str] = Field(default_factory=list)

    @field_validator(
        "skills",
        "education",
        "experience",
        "projects",
        "certifications",
        "strengths",
        "missing_skills",
        "improvement_suggestions",
        "recommended_roles",
        mode="before",
    )
    @classmethod
    def ensure_string_list(cls, value):
        if value is None:
            return []
        if not isinstance(value, list):
            raise TypeError("Expected a list.")
        normalized = []
        for item in value:
            if not isinstance(item, str):
                raise TypeError("List items must be strings.")
            normalized.append(item)
        return normalized


def validate_resume_analysis_result(data):
    """
    Validate and normalize structured resume analysis from Gemini.
    """

    if not isinstance(data, dict):
        raise InvalidGeminiResponseError(
            "Resume analysis response must be a JSON object."
        )

    missing_keys = [
        key
        for key in RESUME_ANALYSIS_JSON_SCHEMA
        if key not in data
    ]
    if missing_keys:
        raise InvalidGeminiResponseError(
            "Resume analysis response is missing required fields."
        )

    try:
        validated = ResumeAnalysisResultSchema.model_validate(data)
    except (ValidationError, TypeError) as exc:
        raise InvalidGeminiResponseError(
            "Resume analysis response failed validation."
        ) from exc

    return validated.model_dump()


def _get_api_key():
    api_key = getattr(settings, "GEMINI_API_KEY", "") or ""
    if not api_key.strip():
        raise GeminiConfigurationError(
            "Gemini API key is not configured."
        )
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


def analyze_resume_with_gemini(extracted_text):
    """
    Send cleaned resume text to Gemini and return validated analysis JSON.
    """

    if not extracted_text or not extracted_text.strip():
        raise InvalidGeminiResponseError(
            "Resume text is empty or unreadable."
        )

    api_key = _get_api_key()
    model_name = getattr(
        settings,
        "GEMINI_MODEL",
        "gemini-2.0-flash",
    )

    client = genai.Client(api_key=api_key)

    prompt = USER_PROMPT_TEMPLATE.format(
        resume_text=extracted_text.strip(),
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
        logger.exception("Gemini API call failed during resume analysis.")
        raise GeminiAPIError(
            "Failed to analyze resume with Gemini."
        ) from exc

    raw_text = _extract_response_text(response)
    payload = _parse_json_from_text(raw_text)

    return validate_resume_analysis_result(payload)
