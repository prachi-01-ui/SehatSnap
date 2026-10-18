import shutil
from io import BytesIO

import fitz
import pytesseract
from PIL import Image
from pypdf import PdfReader


tesseract_path = shutil.which("tesseract")
if tesseract_path:
    pytesseract.pytesseract.tesseract_cmd = tesseract_path


def extract_text_from_pdf(content: bytes) -> str:
    """Extract text from text-based, scanned, or mixed PDFs."""
    reader = PdfReader(BytesIO(content))
    extracted_pages = []

    for page_number, page in enumerate(reader.pages):
        text = page.extract_text() or ""

        if text.strip():
            extracted_pages.append(text.strip())
            continue

        # Fall back to OCR for scanned pages.
        with fitz.open(stream=content, filetype="pdf") as pdf:
            pdf_page = pdf.load_page(page_number)
            pixmap = pdf_page.get_pixmap(dpi=200)
            image = Image.open(BytesIO(pixmap.tobytes("png")))
            text = pytesseract.image_to_string(image)

        if text.strip():
            extracted_pages.append(text.strip())

    extracted_text = "\n\n".join(extracted_pages)

    if not extracted_text.strip():
        raise ValueError(
            "No extractable text found in the PDF, even after OCR."
        )

    return extracted_text
