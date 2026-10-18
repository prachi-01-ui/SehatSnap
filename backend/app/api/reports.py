import uuid
import datetime
import re
from io import BytesIO

from pypdf import PdfReader
from backend.app.services.report_extractor import extract_text_from_pdf
from fastapi import APIRouter, Depends, UploadFile, File, HTTPException
from pathlib import Path
from backend.app.config import UPLOADS_DIR
from sqlalchemy.orm import Session
from backend.app.database import get_db
from backend.app.models import ReportDocument, MedicalRecord, AuditEvent
from backend.app.storage import process_and_save_upload
from backend.app.schemas import (
    ReportUploadResponse,
    ExtractionResponse,
    DocumentSummary,
    ExtractedField,
    ExtractedFieldProvenance,
    ConfirmReportRequest,
    ConfirmReportResponse,
)

router = APIRouter(prefix="/reports", tags=["Report Ingestion"])

@router.post("/upload", response_model=ReportUploadResponse, status_code=201)
async def upload_report(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    """
    Secure report file upload handler:
    - Enforces 20 MiB streaming byte limit.
    - Validates allowed extensions and initial file signatures (magic bytes).
    - Computes SHA-256 digest on streamed bytes.
    - Stores file in local storage with random UUID filename.
    - Cleans up partial files automatically upon failure.
    """
    stored_filename, rel_path, file_size, sha256_hash = await process_and_save_upload(file)

    
    # Check for an existing report with an identical SHA-256 hash.
    existing_doc = (
        db.query(ReportDocument)
        .filter(ReportDocument.sha256_hash == sha256_hash)
        .first()
    )

    if existing_doc:
        # Delete the newly saved duplicate file to avoid unnecessary storage.
        duplicate_path = UPLOADS_DIR / stored_filename

        try:
            duplicate_path.unlink(missing_ok=True)
        except OSError:
            # Preserve the existing report response if cleanup fails.
            pass

        return ReportUploadResponse(
            reportId=existing_doc.id,
            originalFilename=existing_doc.original_filename,
            fileSizeBytes=existing_doc.file_size_bytes,
            mimeType=existing_doc.mime_type,
            sha256Hash=existing_doc.sha256_hash,
            status=existing_doc.status,
            uploadedAt=existing_doc.created_at.strftime("%d %b %Y · %H:%M"),
            isDuplicate=True,
            existingReportId=existing_doc.id,
            integrityNotice=(
                "A report with an identical SHA-256 hash was previously uploaded. "
                "Duplicate hashes indicate file identity; they do not imply fraud."
            ),
        )


    # Generate document identifier
    doc_id = f"REP-{uuid.uuid4().hex[:6].upper()}"
    uploaded_at = datetime.datetime.now(datetime.timezone.utc)

    new_doc = ReportDocument(
        id=doc_id,
        patient_id="AN-PATIENT-01",
        original_filename=file.filename or "uploaded_report",
        stored_filename=stored_filename,
        file_size_bytes=file_size,
        mime_type=file.content_type or "application/octet-stream",
        sha256_hash=sha256_hash,
        storage_relative_path=rel_path,
        ingestion_source="UPLOAD",
        status="UPLOADED",
        created_at=uploaded_at,
    )
    db.add(new_doc)

    # Log audit event
    audit_id = f"EVT-{uuid.uuid4().hex[:4].upper()}"
    db.add(
        AuditEvent(
            id=audit_id,
            patient_id="AN-PATIENT-01",
            report_document_id=doc_id,
            event_type="File added",
            artifact_hash=sha256_hash,
            timestamp_display=uploaded_at.strftime("%d %b %Y · %H:%M"),
            actor_name="Local upload",
            rule_or_model="ingest-v1.2",
            verification_status="Hash-linked",
        )
    )

    db.commit()
    db.refresh(new_doc)

    return ReportUploadResponse(
        reportId=new_doc.id,
        originalFilename=new_doc.original_filename,
        fileSizeBytes=new_doc.file_size_bytes,
        mimeType=new_doc.mime_type,
        sha256Hash=new_doc.sha256_hash,
        status=new_doc.status,
        uploadedAt=new_doc.created_at.strftime("%d %b %Y · %H:%M"),
        isDuplicate=False,
        integrityNotice="File validated and SHA-256 hash recorded in audit log.",
    )


@router.post("/{report_id}/extract", response_model=ExtractionResponse)
def extract_report_fields(
    report_id: str,
    db: Session = Depends(get_db),
):
    """Extract real text from an uploaded PDF and identify labelled metadata."""
    doc = (
        db.query(ReportDocument)
        .filter(ReportDocument.id == report_id)
        .first()
    )

    if not doc:
        raise HTTPException(
            status_code=404,
            detail=f"Report document '{report_id}' not found",
        )

    # The current extraction service supports PDF files only.
    if Path(doc.original_filename).suffix.lower() != ".pdf":
        raise HTTPException(
            status_code=415,
            detail="Text extraction currently supports PDF reports only.",
        )

    # Resolve the stored file safely within the uploads directory.
    uploads_root = UPLOADS_DIR.resolve()
    file_path = (uploads_root / doc.stored_filename).resolve()

    if file_path.parent != uploads_root or not file_path.is_file():
        raise HTTPException(
            status_code=404,
            detail="The stored report file could not be found.",
        )

    try:
        content = file_path.read_bytes()
        reader = PdfReader(BytesIO(content))

        if reader.is_encrypted:
            raise HTTPException(
                status_code=422,
                detail="Encrypted PDFs are not supported for extraction.",
            )

        page_count = len(reader.pages)
        extracted_text = extract_text_from_pdf(content)

    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(
            status_code=422,
            detail=f"Could not extract text from this PDF: {exc}",
        ) from exc

    # Extract only explicitly labelled metadata. Do not invent missing values.
    def find_value(pattern: str) -> str:
        match = re.search(
            pattern,
            extracted_text,
            flags=re.IGNORECASE | re.MULTILINE,
        )
        return match.group(1).strip() if match else ""

    lab = find_value(
        r"^(?:laboratory|lab(?:oratory)?\s+name|lab\s+name)\s*[:\-]\s*(.+)$"
    )
    report_id_value = find_value(
        r"^(?:report\s*(?:id|no\.?|number)|accession\s*(?:no\.?|number))"
        r"\s*[:#\-]\s*([A-Z0-9][A-Z0-9/_\-]*)"
    )
    report_date = find_value(
        r"^(?:report\s*date|date\s*of\s*report)\s*[:\-]\s*(.+)$"
    )
    collection_date = find_value(
        r"^(?:collection\s*date|sample\s*date|specimen\s*date|"
        r"date\s*of\s*collection)\s*[:\-]\s*(.+)$"
    )

    # These fields require explicit labelled matches. Result-table parsing
    # will be added separately to avoid guessing which number is a test result.
    field_definitions = [
        ("test", "Test name", "", "Result table"),
        ("value", "Result value", "", "Result table"),
        ("unit", "Unit", "", "Result table"),
        ("range", "Reference range", "", "Result table"),
        ("date", "Collection date", collection_date, "Labelled metadata"),
        ("reportDate", "Report date", report_date, "Labelled metadata"),
        ("lab", "Laboratory name", lab, "Labelled metadata"),
        ("reportId", "Report ID", report_id_value, "Labelled metadata"),
    ]

    extracted_fields = [
        ExtractedField(
            fieldKey=key,
            label=label,
            value=value,
            confidence=0.5 if value else 0.0,
            method="PDF text/OCR" if value else "Not detected",
            provenance=ExtractedFieldProvenance(
                page=1,
                region=region,
            ),
        )
        for key, label, value, region in field_definitions
    ]

    doc.status = "EXTRACTED"
    # This is a placeholder until a calibrated extraction-quality metric exists.
    doc.ocr_confidence = None
    db.commit()

    return ExtractionResponse(
        reportId=doc.id,
        status="EXTRACTED",
        simulationNotice=(
            "Real PDF text extraction/OCR was performed. Labelled metadata "
            "is detected using basic rules; test results are not yet parsed "
            "automatically. Blank fields were not detected. All values require "
            "human confirmation."
        ),
        documentSummary=DocumentSummary(
            pageCount=page_count,
            detectedLaboratory=lab or "Not detected",
            detectedReportId=report_id_value or "Not detected",
            detectedDate=report_date or collection_date or "Not detected",
            ocrQualityScore=0.0,
        ),
        extractedFields=extracted_fields,
    )


@router.post("/{report_id}/confirm", response_model=ConfirmReportResponse)
def confirm_report_records(
    report_id: str,
    payload: ConfirmReportRequest,
    db: Session = Depends(get_db),
):
    """
    Explicit user confirmation of extracted fields.
    Does NOT create confirmed MedicalRecord entries until this endpoint is invoked.
    """
    doc = db.query(ReportDocument).filter(ReportDocument.id == report_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail=f"Report document '{report_id}' not found")

    # Generate sequential record ID
    count = db.query(MedicalRecord).count()
    new_record_id = f"SR-{1054 + count}"

    numeric_val = None
    try:
        numeric_val = float(payload.value.strip().split()[0])
    except (ValueError, IndexError):
        pass

    confirmed_record = MedicalRecord(
        id=new_record_id,
        patient_id="AN-PATIENT-01",
        report_document_id=doc.id,
        name=payload.test.strip(),
        date_display=payload.date.strip(),
        laboratory_name=payload.lab.strip(),
        value_display=payload.value.strip(),
        value_numeric=numeric_val,
        unit=payload.unit.strip(),
        reference_range=payload.range.strip(),
        status="Reviewed",
        source="PDF Extracted",
        report_identifier=payload.reportId,
        report_date_display=payload.reportDate,
        extraction_confidence=0.96,
        provenance_location="Page 1 · Confirmed by user",
    )
    db.add(confirmed_record)

    doc.status = "CONFIRMED"

    # Audit event for confirmation
    audit_id = f"EVT-{uuid.uuid4().hex[:4].upper()}"
    db.add(
        AuditEvent(
            id=audit_id,
            patient_id="AN-PATIENT-01",
            report_document_id=doc.id,
            event_type="Report confirmed",
            artifact_hash=doc.sha256_hash,
            timestamp_display=f"Today · {datetime.datetime.now(datetime.timezone.utc).strftime('%H:%M')}",
            actor_name="User AN",
            rule_or_model="rules-v1.4",
            verification_status="Hash-linked",
        )
    )

    db.commit()
    db.refresh(confirmed_record)

    return ConfirmReportResponse(
        recordId=confirmed_record.id,
        reportId=doc.id,
        status="Reviewed",
        source="PDF Extracted",
        auditEventId=audit_id,
        message="Extracted report fields confirmed by user and committed to active medical records.",
    )
