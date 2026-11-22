from io import BytesIO

from pypdf import PdfReader
from docx import Document


# ============================================================
# PDF
# ============================================================

def extract_pdf_text(
    file_bytes: bytes
):
    """
    Extract PDF text page-by-page.
    """

    reader = PdfReader(
        BytesIO(file_bytes)
    )

    pages = []

    for page_number, page in enumerate(
        reader.pages,
        start=1
    ):

        text = page.extract_text() or ""

        pages.append({
            "page_number": page_number,
            "text": text
        })

    return pages


# ============================================================
# DOCX
# ============================================================

def extract_docx_text(
    file_bytes: bytes
):
    """
    Extract text from DOCX.
    """

    document = Document(
        BytesIO(file_bytes)
    )

    text_parts = []

    for paragraph in document.paragraphs:

        text = paragraph.text.strip()

        if text:
            text_parts.append(text)

    return [
        {
            "page_number": None,
            "text": "\n".join(
                text_parts
            )
        }
    ]


# ============================================================
# TXT
# ============================================================

def extract_txt_text(
    file_bytes: bytes
):
    """
    Extract text from TXT.
    """

    text = file_bytes.decode(
        "utf-8",
        errors="ignore"
    )

    return [
        {
            "page_number": None,
            "text": text
        }
    ]


# ============================================================
# GENERIC PARSER
# ============================================================

def extract_document_text(
    file_bytes: bytes,
    filename: str
):
    """
    Automatically select parser based
    on file extension.
    """

    filename_lower = filename.lower()

    if filename_lower.endswith(
        ".pdf"
    ):

        return extract_pdf_text(
            file_bytes
        )

    if filename_lower.endswith(
        ".docx"
    ):

        return extract_docx_text(
            file_bytes
        )

    if filename_lower.endswith(
        ".txt"
    ):

        return extract_txt_text(
            file_bytes
        )

    raise ValueError(
        "Unsupported document type. "
        "Only PDF, DOCX and TXT are supported."
    )