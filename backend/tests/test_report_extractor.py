
import pytest
from unittest.mock import MagicMock, patch

from backend.app.services.report_extractor import extract_text_from_pdf


def test_extract_text_from_pdf():
    mock_page = MagicMock()
    mock_page.extract_text.return_value = "Patient Name: Demo\nReport: Normal"

    mock_reader = MagicMock()
    mock_reader.pages = [mock_page]

    with patch(
        "backend.app.services.report_extractor.PdfReader",
        return_value=mock_reader,
    ):
        result = extract_text_from_pdf(b"%PDF-test")

    assert "Patient Name: Demo" in result
    assert "Report: Normal" in result


def test_pdf_without_extractable_text_raises_error():
    mock_page = MagicMock()
    mock_page.extract_text.return_value = ""

    mock_reader = MagicMock()
    mock_reader.pages = [mock_page]

    with patch(
        "backend.app.services.report_extractor.PdfReader",
        return_value=mock_reader,
    ):
        with pytest.raises(ValueError, match="OCR"):
            extract_text_from_pdf(b"%PDF-test")


def test_invalid_pdf_raises_error():
    with pytest.raises(Exception):
        extract_text_from_pdf(b"this is not a PDF")


def test_empty_pdf_bytes_raises_error():
    with pytest.raises(Exception):
        extract_text_from_pdf(b"")

