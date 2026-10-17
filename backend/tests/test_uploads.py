import hashlib
import io
import pytest
from pathlib import Path
import backend.app.storage as storage_module

def test_valid_pdf_upload_and_sha256(client):
    # Valid PDF content starting with %PDF- header
    pdf_bytes = b"%PDF-1.4\n1 0 obj\n<<>>\nendobj\ntrailer\n<<>>\n%%EOF\n"
    expected_hash = hashlib.sha256(pdf_bytes).hexdigest()

    response = client.post(
        "/api/v1/reports/upload",
        files={"file": ("lab_report_oct2025.pdf", io.BytesIO(pdf_bytes), "application/pdf")},
    )
    assert response.status_code == 201
    data = response.json()
    assert data["reportId"].startswith("REP-")
    assert data["originalFilename"] == "lab_report_oct2025.pdf"
    assert data["fileSizeBytes"] == len(pdf_bytes)
    assert data["sha256Hash"] == expected_hash
    assert data["status"] == "UPLOADED"
    assert data["isDuplicate"] is False

    # Check file exists in uploads dir
    stored_files = list(storage_module.UPLOADS_DIR.glob("*.pdf"))
    assert len(stored_files) >= 1

def test_valid_png_upload(client):
    # Valid PNG header \x89PNG\r\n\x1a\n
    png_bytes = b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00"
    expected_hash = hashlib.sha256(png_bytes).hexdigest()

    response = client.post(
        "/api/v1/reports/upload",
        files={"file": ("prescription_scan.png", io.BytesIO(png_bytes), "image/png")},
    )
    assert response.status_code == 201
    data = response.json()
    assert data["sha256Hash"] == expected_hash
    assert data["mimeType"] == "image/png"

def test_duplicate_upload_is_handled_gracefully(client):
    pdf_bytes = b"%PDF-1.4\nDuplicate sample content\n%%EOF\n"

    # First upload
    res1 = client.post(
        "/api/v1/reports/upload",
        files={"file": ("sample.pdf", io.BytesIO(pdf_bytes), "application/pdf")},
    )
    assert res1.status_code == 201
    first_id = res1.json()["reportId"]

    # Second upload with same bytes
    res2 = client.post(
        "/api/v1/reports/upload",
        files={"file": ("sample_copy.pdf", io.BytesIO(pdf_bytes), "application/pdf")},
    )
    assert res2.status_code == 201
    data2 = res2.json()
    assert data2["isDuplicate"] is True
    assert data2["existingReportId"] == first_id
    assert "identical sha-256" in data2["integrityNotice"].lower()

def test_disallowed_extension_rejected(client):
    exe_bytes = b"MZ\x90\x00\x03\x00\x00\x00"
    response = client.post(
        "/api/v1/reports/upload",
        files={"file": ("malicious_payload.exe", io.BytesIO(exe_bytes), "application/octet-stream")},
    )
    assert response.status_code == 415
    assert "unsupported file extension" in response.json()["detail"].lower()

def test_invalid_signature_rejected_and_cleaned_up(client):
    # File named .pdf but containing plain text without %PDF- magic bytes
    fake_pdf = b"Plain text file pretending to be a PDF"

    initial_files = set(storage_module.UPLOADS_DIR.iterdir())
    response = client.post(
        "/api/v1/reports/upload",
        files={"file": ("fake.pdf", io.BytesIO(fake_pdf), "application/pdf")},
    )
    assert response.status_code == 400
    assert "invalid file signature" in response.json()["detail"].lower()

    # Verify no dangling partial files were left in uploads directory
    final_files = set(storage_module.UPLOADS_DIR.iterdir())
    assert final_files == initial_files

def test_oversized_upload_rejected_and_cleaned_up(client, monkeypatch):
    # Set MAX_UPLOAD_SIZE_BYTES to a small threshold (100 KiB) for fast testing
    monkeypatch.setattr(storage_module, "MAX_UPLOAD_SIZE_BYTES", 100 * 1024)

    # Create 150 KiB file starting with valid %PDF- header
    oversized_bytes = b"%PDF-1.4\n" + (b"A" * (150 * 1024))

    initial_files = set(storage_module.UPLOADS_DIR.iterdir())
    response = client.post(
        "/api/v1/reports/upload",
        files={"file": ("large_scan.pdf", io.BytesIO(oversized_bytes), "application/pdf")},
    )
    assert response.status_code == 413
    assert "exceeds maximum upload size" in response.json()["detail"].lower()

    # Ensure partial file was removed
    final_files = set(storage_module.UPLOADS_DIR.iterdir())
    assert final_files == initial_files
