from .gemini_service import (
    GeminiAPIError,
    GeminiConfigurationError,
    GeminiServiceError,
    InvalidGeminiResponseError,
    analyze_resume_with_gemini,
)
from .text_extractor import extract_resume_text
from ..models import ResumeAnalysis

EMPTY_RESUME_MESSAGE = "Resume text is empty or unreadable."
EXTRACTION_FAILURE_MESSAGE = "Failed to extract text from resume."
GEMINI_FAILURE_MESSAGE = "Failed to analyze resume with Gemini."


def _persist_analysis(analysis, *, update_fields):
    analysis.save(update_fields=[*update_fields, "updated_at"])


def _mark_failed(analysis, error_message, *, clear_result=False):
    analysis.status = ResumeAnalysis.Status.FAILED
    analysis.error_message = error_message
    update_fields = ["status", "error_message"]
    if clear_result:
        analysis.analysis_result = {}
        update_fields.append("analysis_result")
    _persist_analysis(analysis, update_fields=update_fields)


def extract_and_save_resume_text(resume):
    """
    Extract text from a resume and save it to ResumeAnalysis.
    """

    analysis, _ = ResumeAnalysis.objects.get_or_create(
        resume=resume,
    )

    try:
        text = extract_resume_text(resume.file)

        analysis.extracted_text = text
        analysis.status = ResumeAnalysis.Status.PENDING
        analysis.error_message = ""
        _persist_analysis(
            analysis,
            update_fields=[
                "extracted_text",
                "status",
                "error_message",
            ],
        )

        return analysis

    except ValueError as exc:
        _mark_failed(analysis, str(exc))
        raise

    except Exception:
        _mark_failed(analysis, EXTRACTION_FAILURE_MESSAGE)
        raise


def analyze_resume(resume):
    """
    Extract resume text, analyze with Gemini, and persist structured results.
    """

    analysis, _ = ResumeAnalysis.objects.get_or_create(
        resume=resume,
    )

    try:
        text = extract_resume_text(resume.file)
        analysis.extracted_text = text
        analysis.error_message = ""
        analysis.status = ResumeAnalysis.Status.PENDING
        _persist_analysis(
            analysis,
            update_fields=[
                "extracted_text",
                "status",
                "error_message",
            ],
        )

        if not text.strip():
            _mark_failed(
                analysis,
                EMPTY_RESUME_MESSAGE,
                clear_result=True,
            )
            raise InvalidGeminiResponseError(EMPTY_RESUME_MESSAGE)

        result = analyze_resume_with_gemini(text)
        analysis.analysis_result = result
        analysis.status = ResumeAnalysis.Status.COMPLETED
        analysis.error_message = ""
        _persist_analysis(
            analysis,
            update_fields=[
                "analysis_result",
                "status",
                "error_message",
            ],
        )

        return analysis

    except ValueError as exc:
        _mark_failed(analysis, str(exc), clear_result=True)
        raise

    except InvalidGeminiResponseError as exc:
        _mark_failed(analysis, str(exc), clear_result=True)
        raise

    except (GeminiAPIError, GeminiConfigurationError) as exc:
        _mark_failed(analysis, str(exc), clear_result=True)
        raise

    except GeminiServiceError as exc:
        _mark_failed(analysis, str(exc), clear_result=True)
        raise

    except Exception:
        _mark_failed(
            analysis,
            GEMINI_FAILURE_MESSAGE,
            clear_result=True,
        )
        raise
