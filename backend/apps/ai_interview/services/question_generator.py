import json
import logging
import re

from django.conf import settings
from google import genai
from google.genai import types
from pydantic import BaseModel, Field, ValidationError, field_validator

logger = logging.getLogger(__name__)


class GeminiServiceError(Exception):
    """Base exception for AI Interview Gemini service."""


class GeminiConfigurationError(GeminiServiceError):
    """Raised when Gemini API key is missing or not configured."""


class GeminiAPIError(GeminiServiceError):
    """Raised when the Gemini API call fails."""


class InvalidGeminiResponseError(GeminiServiceError):
    """Raised when Gemini returns malformed or invalid response data."""


class GeneratedQuestionItemSchema(BaseModel):
    question_number: int = Field(ge=1)
    question_text: str
    question_type: str = "TECHNICAL"
    topic: str = ""

    @field_validator("question_text")
    @classmethod
    def validate_text(cls, v):
        if not v or not v.strip():
            raise ValueError("question_text cannot be blank.")
        return v.strip()

    @field_validator("question_type")
    @classmethod
    def normalize_type(cls, v):
        allowed = {"TECHNICAL", "BEHAVIORAL", "HR"}
        upper = (v or "").strip().upper()
        if upper in allowed:
            return upper
        return "TECHNICAL"


class QuestionGenerationResultSchema(BaseModel):
    questions: list[GeneratedQuestionItemSchema]


SYSTEM_INSTRUCTION = """You are an expert AI technical recruiter and interviewer for a college placement preparation platform.

Generate realistic placement interview questions tailored to:
- Interview type (TECHNICAL, HR, BEHAVIORAL, or MIXED)
- Target role
- Experience level (BEGINNER, INTERMEDIATE, ADVANCED)
- Number of questions requested

Guidelines:
1. Questions must be realistic, challenging, and suitable for college placement candidates.
2. For TECHNICAL interviews, focus on core computer science, coding fundamentals, system architecture, database concepts, algorithms, or tech stack relevant to the role.
3. For HR / BEHAVIORAL interviews, focus on leadership, problem-solving, situational judgment, team dynamics, ethics, and career goals.
4. For MIXED interviews, distribute questions evenly across Technical, Behavioral, and HR.
5. Avoid duplicate questions.
6. Keep question text clear, focused, and concise.
7. Avoid asking for sensitive personal, private, or protected characteristics.
8. Return valid JSON only with exactly this structure:
{
    "questions": [
        {
            "question_number": 1,
            "question_text": "...",
            "question_type": "TECHNICAL",
            "topic": "Data Structures"
        }
    ]
}"""

USER_PROMPT_TEMPLATE = """Generate exactly {number_of_questions} placement interview questions for the following specifications:
- Interview Type: {interview_type}
- Target Role: {target_role}
- Experience Level: {experience_level}
- Number of Questions: {number_of_questions}

Ensure question_number values are sequentially 1 to {number_of_questions}.
Return structured JSON only."""


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


def generate_interview_questions(
    interview_type,
    target_role,
    experience_level,
    number_of_questions,
):
    """
    Generate structured interview questions using Gemini and validate with Pydantic.
    """
    if number_of_questions < 1 or number_of_questions > 20:
        raise ValueError("number_of_questions must be between 1 and 20.")

    api_key = _get_api_key()
    model_name = getattr(settings, "GEMINI_MODEL", "gemini-2.0-flash")

    client = genai.Client(api_key=api_key)

    prompt = USER_PROMPT_TEMPLATE.format(
        interview_type=interview_type,
        target_role=target_role,
        experience_level=experience_level,
        number_of_questions=number_of_questions,
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
        logger.exception("Gemini API call failed during question generation.")
        raise GeminiAPIError("Failed to generate interview questions with Gemini.") from exc

    raw_text = _extract_response_text(response)
    payload = _parse_json_from_text(raw_text)

    if not isinstance(payload, dict) or "questions" not in payload:
        raise InvalidGeminiResponseError("Response missing 'questions' key.")

    try:
        validated = QuestionGenerationResultSchema.model_validate(payload)
    except (ValidationError, TypeError) as exc:
        raise InvalidGeminiResponseError(
            "Generated questions failed validation."
        ) from exc

    questions_list = [q.model_dump() for q in validated.questions]

    # Ensure sequential numbering up to requested count
    normalized_questions = []
    for idx, q_data in enumerate(questions_list[:number_of_questions], start=1):
        q_data["question_number"] = idx
        normalized_questions.append(q_data)

    if len(normalized_questions) < number_of_questions:
        raise InvalidGeminiResponseError(
            f"Expected {number_of_questions} questions, but model returned {len(normalized_questions)}."
        )

    return normalized_questions
