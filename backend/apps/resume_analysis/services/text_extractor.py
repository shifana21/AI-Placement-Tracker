from io import BytesIO

from docx import Document
from pypdf import PdfReader


def extract_text_from_pdf(file):
    """
    Extract text from a PDF resume.
    """

    file.seek(0)

    reader = PdfReader(file)
    pages_text = []

    for page in reader.pages:
        text = page.extract_text()

        if text:
            pages_text.append(text)

    return "\n".join(pages_text)


def extract_text_from_docx(file):
    """
    Extract text from a DOCX resume.
    """

    file.seek(0)

    document = Document(BytesIO(file.read()))

    paragraphs = []

    for paragraph in document.paragraphs:
        text = paragraph.text.strip()

        if text:
            paragraphs.append(text)

    return "\n".join(paragraphs)


def clean_text(text):
    """
    Clean extracted resume text.
    """

    lines = []

    for line in text.splitlines():
        line = " ".join(line.split())

        if line:
            lines.append(line)

    return "\n".join(lines)


def extract_resume_text(file):
    """
    Extract and clean text from a PDF or DOCX resume.
    """

    filename = file.name.lower()

    if filename.endswith(".pdf"):
        text = extract_text_from_pdf(file)

    elif filename.endswith(".docx"):
        text = extract_text_from_docx(file)

    else:
        raise ValueError(
            "Unsupported resume format. Only PDF and DOCX are supported."
        )

    return clean_text(text)