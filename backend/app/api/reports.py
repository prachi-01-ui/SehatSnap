import uuid
import datetime
from fastapi import APIRouter, Depends, UploadFile, File, HTTPException
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

    # Check for existing report with identical SHA-256 hash
    existing_doc = db.query(ReportDocument).filter(ReportDocument.sha256_hash == sha256_hash).first()
    if existing_doc:
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
            integrityNotice="A report with an identical SHA-256 hash was previously uploaded. Duplicate hashes indicate file identity; they do not imply fraud.",
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
    """
    Simulated document extraction endpoint for Milestone 1.
    Explicitly labeled as prototype simulation; does not claim real OCR.
    Real OCR pipeline will be plugged in subsequent milestones.
    """
    doc = db.query(ReportDocument).filter(ReportDocument.id == report_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail=f"Report document '{report_id}' not found")

    doc.status = "EXTRACTED"
    doc.ocr_confidence = 0.94
    db.commit()

    return ExtractionResponse(
        reportId=doc.id,
        status="EXTRACTED",
        simulationNotice="OCR and PDF parsing are simulated in this milestone for client review. Actual OCR model integration is planned for subsequent milestones. All extracted values require explicit human confirmation.",
        documentSummary=DocumentSummary(
            pageCount=1,
            detectedLaboratory="Aster Diagnostics, Pune",
            detectedReportId="LAB-8821",
            detectedDate="18 Oct 2025",
            ocrQualityScore=0.94,
        ),
        extractedFields=[
            ExtractedField(
                fieldKey="test",
                label="Test name",
                value="Fasting Plasma Glucose",
                confidence=0.98,
                method="PDF Extracted",
                provenance=ExtractedFieldProvenance(page=1, region="Results table, row 3"),
            ),
            ExtractedField(
                fieldKey="value",
                label="Result value",
                value="102",
                confidence=0.96,
                method="PDF Extracted",
                provenance=ExtractedFieldProvenance(page=1, region="Results table, row 3"),
            ),
            ExtractedField(
                fieldKey="unit",
                label="Unit",
                value="mg/dL",
                confidence=0.94,
                method="PDF Extracted",
                provenance=ExtractedFieldProvenance(page=1, region="Results table, row 3"),
            ),
            ExtractedField(
                fieldKey="range",
                label="Reference range",
                value="70–99 mg/dL",
                confidence=0.91,
                method="PDF Extracted",
                provenance=ExtractedFieldProvenance(page=1, region="Results table, row 3"),
            ),
            ExtractedField(
                fieldKey="date",
                label="Collection date",
                value="18 Oct 2025",
                confidence=0.67,
                method="OCR Extracted",
                provenance=ExtractedFieldProvenance(page=1, region="Header right region"),
            ),
            ExtractedField(
                fieldKey="reportDate",
                label="Report date",
                value="19 Oct 2025",
                confidence=0.95,
                method="PDF Extracted",
                provenance=ExtractedFieldProvenance(page=1, region="Header right"),
            ),
            ExtractedField(
                fieldKey="lab",
                label="Laboratory name",
                value="Aster Diagnostics, Pune",
                confidence=0.92,
                method="PDF Extracted",
                provenance=ExtractedFieldProvenance(page=1, region="Header left"),
            ),
            ExtractedField(
                fieldKey="reportId",
                label="Report ID",
                value="LAB-8821",
                confidence=0.72,
                method="OCR Extracted",
                provenance=ExtractedFieldProvenance(page=1, region="Header top-right"),
            ),
        ],
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
