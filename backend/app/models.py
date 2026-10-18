import datetime
from sqlalchemy import Column, String, Integer, Float, DateTime, ForeignKey, Index
from sqlalchemy.orm import relationship
from backend.app.database import Base

def utc_now():
    return datetime.datetime.now(datetime.timezone.utc)

class ReportDocument(Base):
    """Uploaded or ingested health report file."""
    __tablename__ = "report_documents"

    id = Column(String(64), primary_key=True)  # e.g., "REP-8821"
    patient_id = Column(String(64), nullable=False, default="AN-PATIENT-01")
    original_filename = Column(String(255), nullable=False)
    stored_filename = Column(String(255), nullable=False, unique=True)
    file_size_bytes = Column(Integer, nullable=False)
    mime_type = Column(String(64), nullable=False)
    sha256_hash = Column(String(64), nullable=False, index=True)
    storage_relative_path = Column(String(512), nullable=False)
    ingestion_source = Column(String(32), nullable=False, default="UPLOAD")  # UPLOAD | MANUAL | URL
    status = Column(String(32), nullable=False, default="UPLOADED")  # UPLOADED | EXTRACTED | CONFIRMED
    ocr_confidence = Column(Float, nullable=True)
    created_at = Column(DateTime, default=utc_now, nullable=False)

    records = relationship("MedicalRecord", back_populates="document", cascade="all, delete-orphan")
    audit_events = relationship("AuditEvent", back_populates="document")


class MedicalRecord(Base):
    """Clinical laboratory/test observation."""
    __tablename__ = "medical_records"

    id = Column(String(64), primary_key=True)  # e.g., "SR-1048"
    patient_id = Column(String(64), nullable=False, default="AN-PATIENT-01")
    report_document_id = Column(String(64), ForeignKey("report_documents.id", ondelete="SET NULL"), nullable=True)

    # 1:1 match with RecordItem in frontend App.tsx
    name = Column(String(255), nullable=False)  # "Fasting Plasma Glucose"
    date_display = Column(String(64), nullable=False)  # "18 Oct 2025"
    laboratory_name = Column(String(255), nullable=False)  # "Aster Diagnostics, Pune"
    value_display = Column(String(64), nullable=False)  # "102"
    value_numeric = Column(Float, nullable=True)  # 102.0
    unit = Column(String(32), nullable=False)  # "mg/dL"
    reference_range = Column(String(64), nullable=False)  # "70–99 mg/dL"
    status = Column(String(32), nullable=False, default="Needs review")  # "Reviewed" | "Needs review" | "Verified"
    source = Column(String(32), nullable=False, default="PDF Extracted")  # "PDF Extracted" | "Online Source" | "Scanned Image" | "Manual"

    # Additional provenance & integrity metadata
    report_identifier = Column(String(128), nullable=True)  # "LAB-8821"
    report_date_display = Column(String(64), nullable=True)  # "19 Oct 2025"
    extraction_confidence = Column(Float, nullable=True)  # 0.96
    provenance_location = Column(String(255), nullable=True)  # "Page 1 · Results table, row 3"

    created_at = Column(DateTime, default=utc_now, nullable=False)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now, nullable=False)

    document = relationship("ReportDocument", back_populates="records")

    __table_args__ = (
        Index("idx_records_patient_status", "patient_id", "status"),
        Index("idx_records_name", "name"),
    )


class AuditEvent(Base):
    """Tamper-evident hash-linked audit record."""
    __tablename__ = "audit_events"

    id = Column(String(64), primary_key=True)  # e.g., "EVT-8F21"
    patient_id = Column(String(64), nullable=False, default="AN-PATIENT-01")
    report_document_id = Column(String(64), ForeignKey("report_documents.id", ondelete="SET NULL"), nullable=True)

    event_type = Column(String(64), nullable=False)  # "File added", "Report confirmed", "Manual entry"
    artifact_hash = Column(String(64), nullable=False)
    previous_event_hash = Column(String(64), nullable=True)
    timestamp_display = Column(String(64), nullable=False)
    created_at = Column(DateTime, default=utc_now, nullable=False)
    actor_name = Column(String(128), nullable=False, default="User AN")
    rule_or_model = Column(String(64), nullable=False, default="ingest-v1.2")
    verification_status = Column(String(32), nullable=False, default="Hash-linked")

    document = relationship("ReportDocument", back_populates="audit_events")


class LabVerificationLog(Base):
    """Audit log for laboratory accreditation and test-scope verification checks."""
    __tablename__ = "lab_verification_logs"

    id = Column(String(64), primary_key=True)  # e.g., "VER-A102"
    patient_id = Column(String(64), nullable=False, default="AN-PATIENT-01")
    report_document_id = Column(String(64), ForeignKey("report_documents.id", ondelete="SET NULL"), nullable=True)
    medical_record_id = Column(String(64), ForeignKey("medical_records.id", ondelete="SET NULL"), nullable=True)

    queried_lab_name = Column(String(255), nullable=True)
    queried_city = Column(String(128), nullable=True)
    queried_certificate = Column(String(64), nullable=True)
    queried_discipline = Column(String(128), nullable=True)
    queried_test_name = Column(String(255), nullable=True)

    matched_lab_name = Column(String(255), nullable=True)
    matched_certificate = Column(String(64), nullable=True)
    match_confidence = Column(Float, nullable=False, default=0.0)

    overall_status = Column(String(32), nullable=False)  # verified | not_verified | mismatch | inconclusive
    accreditation_status = Column(String(32), nullable=False)
    test_scope_status = Column(String(32), nullable=False)
    verdict = Column(String(255), nullable=False)

    source_authority = Column(String(128), nullable=False, default="NABL directory demonstration snapshot")
    is_demo_source = Column(String(8), nullable=False, default="true")
    created_at = Column(DateTime, default=utc_now, nullable=False)

