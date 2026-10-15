import json
import logging
import re
from decimal import Decimal

from django.conf import settings
from google import genai
from google.genai import types
from pydantic import BaseModel, Field, ValidationError, field_validator

from .question_generator import (
    GeminiAPIError,
    GeminiConfigurationError,
    InvalidGeminiResponseError,
    _extract_response_text,
    _get_api_key,
    _parse_json_from_text,
)

logger = logging.getLogger(__name__)


class AnswerEvaluationSchema(BaseModel):
    score: float = Field(ge=0, le=100)
    evaluation: str
    strengths: list[str] = Field(default_factory=list)
    weaknesses: list[str] = Field(default_factory=list)
    improvement_suggestions: list[str] = Field(default_factory=list)

    @field_validator(
        "strengths",
        "weaknesses",
        "improvement_suggestions",
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
            normalized.append(item.strip())
        return normalized


class FinalAnalysisSchema(BaseModel):
    overall_score: float = Field(ge=0, le=100)
    overall_feedback: str
    strengths: list[str] = Field(default_factory=list)
    weaknesses: list[str] = Field(default_factory=list)
    recommendations: list[str] = Field(default_factory=list)

    @field_validator(
        "strengths",
        "weaknesses",
        "recommendations",
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
            normalized.append(item.strip())
        return normalized


EVALUATION_SYSTEM_INSTRUCTION = """You are an objective AI interview evaluator for a college placement preparation platform.

Evaluate the candidate's answer to the given interview question based on:
1. Correctness and accuracy
2. Relevance to the question asked
3. Clarity and structure of thought
4. Technical understanding (or situational judgment for HR/behavioral)
5. Communication quality and completeness

Strict constraints:
- Do NOT invent facts or background about the candidate.
- Do NOT make hiring decisions or predict job offers.
- Do NOT make discriminatory judgments or evaluate based on protected personal characteristics.
- Focus strictly and exclusively on the submitted question and answer.
- Score must be an integer or decimal between 0 and 100.
- Return valid JSON only with exactly these keys:
  score, evaluation, strengths, weaknesses, improvement_suggestions."""

EVALUATION_USER_PROMPT = """Target Role: {target_role}
Experience Level: {experience_level}
Question Type: {question_type}
Topic: {topic}
Question:
{question_text}

Candidate Answer:
{answer_text}

Provide an objective evaluation as JSON."""


FINAL_ANALYSIS_SYSTEM_INSTRUCTION = """You are an AI placement interview director conducting a comprehensive debrief for a student's mock interview.

Analyze the aggregate performance data provided across all answered questions.
Generate a constructive, professional debrief highlighting overarching strengths, areas of weakness, and actionable study/interview recommendations.

Strict constraints:
- Base analysis ONLY on the provided question performance data.
- Do NOT invent credentials or test results.
- Do NOT make hiring decisions or employment guarantees.
- Return valid JSON only with exactly these keys:
  overall_score, overall_feedback, strengths, weaknesses, recommendations."""

FINAL_ANALYSIS_USER_PROMPT = """Mock Interview Aggregate Summary:
{summary_json}

Provide a final overall interview debrief as JSON."""


def evaluate_interview_answer(
    question_text,
    question_type,
    topic,
    target_role,
    experience_level,
    answer_text,
):
    """
    Evaluate an individual answer using Gemini and validate with Pydantic.
    """
    if not answer_text or not answer_text.strip():
        raise ValueError("Answer text cannot be blank.")

    api_key = _get_api_key()
    model_name = getattr(settings, "GEMINI_MODEL", "gemini-2.0-flash")

    client = genai.Client(api_key=api_key)

    prompt = EVALUATION_USER_PROMPT.format(
        target_role=target_role,
        experience_level=experience_level,
        question_type=question_type,
        topic=topic or "General",
        question_text=question_text.strip(),
        answer_text=answer_text.strip(),
    )

    try:
        response = client.models.generate_content(
            model=model_name,
            contents=prompt,
            config=types.GenerateContentConfig(
                system_instruction=EVALUATION_SYSTEM_INSTRUCTION,
                response_mime_type="application/json",
            ),
        )
    except Exception as exc:
        logger.exception("Gemini API call failed during answer evaluation.")
        raise GeminiAPIError("Failed to evaluate answer with Gemini.") from exc

    raw_text = _extract_response_text(response)
    payload = _parse_json_from_text(raw_text)

    try:
        validated = AnswerEvaluationSchema.model_validate(payload)
    except (ValidationError, TypeError) as exc:
        raise InvalidGeminiResponseError(
            "Answer evaluation failed validation."
        ) from exc

    return validated.model_dump()


def generate_final_interview_analysis(
    interview_type,
    target_role,
    experience_level,
    computed_overall_score,
    questions_evaluations,
):
    """
    Generate overall interview feedback, strengths, weaknesses, and recommendations.
    """
    api_key = _get_api_key()
    model_name = getattr(settings, "GEMINI_MODEL", "gemini-2.0-flash")

    client = genai.Client(api_key=api_key)

    summary_payload = {
        "interview_type": interview_type,
        "target_role": target_role,
        "experience_level": experience_level,
        "computed_overall_score": float(computed_overall_score),
        "questions_summary": questions_evaluations,
    }

    prompt = FINAL_ANALYSIS_USER_PROMPT.format(
        summary_json=json.dumps(summary_payload, indent=2),
    )

    try:
        response = client.models.generate_content(
            model=model_name,
            contents=prompt,
            config=types.GenerateContentConfig(
                system_instruction=FINAL_ANALYSIS_SYSTEM_INSTRUCTION,
                response_mime_type="application/json",
            ),
        )
    except Exception as exc:
        logger.exception("Gemini API call failed during final interview analysis.")
        raise GeminiAPIError("Failed to generate final interview analysis with Gemini.") from exc

    raw_text = _extract_response_text(response)
    payload = _parse_json_from_text(raw_text)

    try:
        validated = FinalAnalysisSchema.model_validate(payload)
    except (ValidationError, TypeError) as exc:
        raise InvalidGeminiResponseError(
            "Final interview analysis failed validation."
        ) from exc

    return validated.model_dump()
