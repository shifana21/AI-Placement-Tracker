import json
import logging
import re

from django.conf import settings
from google import genai
from google.genai import types
from pydantic import BaseModel, Field, ValidationError, field_validator

logger = logging.getLogger(__name__)

SYSTEM_INSTRUCTION = """You are an aptitude performance analysis assistant for a college placement preparation platform.

Analyze ONLY the student's actual performance data provided.
Do NOT invent test scores, topics, or performance statistics.
Do NOT make hiring or employment selection decisions.
Your focus must be strictly on:
- Learning gaps and misconceptions
- Practice recommendations
- Study planning and schedule prioritization
- Topic prioritization based on weak and strong areas
- Strategic improvement tips for campus placements

Return valid JSON only, with exactly these keys:
overall_assessment, strengths, weak_areas, topic_analysis, study_recommendations, practice_strategy, recommended_focus.

- overall_assessment: A comprehensive narrative assessing the student's aptitude readiness and key insights.
- strengths: List of specific topics or areas where the student performs strongly.
- weak_areas: List of topics or areas needing targeted improvement.
- topic_analysis: A list of objects, each containing:
    "topic": topic name,
    "performance": brief summary of student's performance,
    "recommendation": actionable advice for that specific topic.
- study_recommendations: List of actionable study recommendations.
- practice_strategy: List of practice strategies (e.g. time management, pacing, question difficulty progression).
- recommended_focus: Immediate priority focus areas for upcoming placement rounds."""

USER_PROMPT_TEMPLATE = """Analyze the following student's aptitude performance data and generate the structured JSON evaluation described in your instructions.

Performance Data:
---
{performance_summary}
---"""


class GeminiServiceError(Exception):
    """Base error for Gemini aptitude analysis."""


class GeminiConfigurationError(GeminiServiceError):
    """Raised when Gemini API key is missing or not configured."""


class GeminiAPIError(GeminiServiceError):
    """Raised when the Gemini API call fails."""


class InvalidGeminiResponseError(GeminiServiceError):
    """Raised when Gemini returns invalid or unparseable analysis data."""


class TopicAnalysisItemSchema(BaseModel):
    topic: str = ""
    performance: str = ""
    recommendation: str = ""


class AptitudeAIAnalysisSchema(BaseModel):
    overall_assessment: str
    strengths: list[str] = Field(default_factory=list)
    weak_areas: list[str] = Field(default_factory=list)
    topic_analysis: list[TopicAnalysisItemSchema] = Field(default_factory=list)
    study_recommendations: list[str] = Field(default_factory=list)
    practice_strategy: list[str] = Field(default_factory=list)
    recommended_focus: list[str] = Field(default_factory=list)

    @field_validator(
        "strengths",
        "weak_areas",
        "study_recommendations",
        "practice_strategy",
        "recommended_focus",
        mode="before",
    )
    @classmethod
    def ensure_string_list(cls, value):
        if value is None:
            return []
        if not isinstance(value, list):
            raise TypeError("Expected a list of strings.")
        normalized = []
        for item in value:
            if not isinstance(item, str):
                raise TypeError("List items must be strings.")
            normalized.append(item)
        return normalized


def validate_ai_analysis_result(data):
    """
    Validate and normalize structured AI analysis from Gemini.
    """
    if not isinstance(data, dict):
        raise InvalidGeminiResponseError(
            "AI analysis response must be a JSON object."
        )

    required_keys = [
        "overall_assessment",
        "strengths",
        "weak_areas",
        "topic_analysis",
        "study_recommendations",
        "practice_strategy",
        "recommended_focus",
    ]
    missing_keys = [key for key in required_keys if key not in data]
    if missing_keys:
        raise InvalidGeminiResponseError(
            f"AI analysis response is missing required fields: {', '.join(missing_keys)}"
        )

    try:
        validated = AptitudeAIAnalysisSchema.model_validate(data)
    except (ValidationError, TypeError) as exc:
        raise InvalidGeminiResponseError(
            "AI analysis response failed validation."
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


def analyze_aptitude_performance(performance_data):
    """
    Generate AI-powered aptitude performance analysis using Gemini.
    """
    if not performance_data or not isinstance(performance_data, dict):
        raise ValueError("performance_data must be a non-empty dictionary.")

    # Build a compact summary payload containing only necessary analytics
    compact_payload = {
        "overall_accuracy": performance_data.get("overall_accuracy", 0.0),
        "total_attempts": performance_data.get("total_attempts", 0),
        "average_score": performance_data.get("average_score", 0.0),
        "category_performance": performance_data.get("by_category", {}),
        "difficulty_performance": performance_data.get("by_difficulty", {}),
        "topic_performance": performance_data.get("by_topic", {}),
        "weak_topics": performance_data.get("weak_topics", []),
        "strong_topics": performance_data.get("strong_topics", []),
        "recent_performance": performance_data.get("recent_attempts", [])[:5],
    }

    api_key = _get_api_key()
    model_name = getattr(
        settings,
        "GEMINI_MODEL",
        "gemini-2.0-flash",
    )

    client = genai.Client(api_key=api_key)

    prompt = USER_PROMPT_TEMPLATE.format(
        performance_summary=json.dumps(compact_payload, indent=2),
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
        logger.exception("Gemini API call failed during aptitude AI analysis.")
        raise GeminiAPIError(
            "Failed to analyze aptitude performance with Gemini."
        ) from exc

    raw_text = _extract_response_text(response)
    payload = _parse_json_from_text(raw_text)

    return validate_ai_analysis_result(payload)
