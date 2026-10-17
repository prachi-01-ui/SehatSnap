
from io import BytesIO

from pypdf import PdfReader


def extract_text_from_pdf(content: bytes) -> str:
    """Extract text from a text-based PDF provided as bytes."""
    reader = PdfReader(BytesIO(content))

    extracted_pages = []

    for page in reader.pages:
        text = page.extract_text() or ""
        if text.strip():
            extracted_pages.append(text.strip())

    extracted_text = "\n\n".join(extracted_pages)

    if not extracted_text.strip():
        raise ValueError(
            "No extractable text found. This PDF may be scanned and require OCR."
        )

    return extracted_text
