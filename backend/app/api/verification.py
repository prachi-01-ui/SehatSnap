import uuid
import datetime
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from backend.app.database import get_db
from backend.app.models import (
    LabVerificationLog,
    MedicineVerificationLog,
    AuditEvent,
    MedicalRecord,
    ReportDocument,
)
from backend.app.schemas import (
    LabVerificationRequest,
    LabVerificationResponse,
    VerifiedLabDetails,
    MedicineVerificationRequest,
    MedicineVerificationResponse,
    VerifiedMedicineProduct,
)
from backend.app.services.lab_verification import (
    verify_laboratory_identity_and_scope,
    SYNTHETIC_NABL_REGISTRY,
)
from backend.app.services.medicine_verification import (
    verify_medicine_identity_and_composition,
    SYNTHETIC_SUGAM_REGISTRY,
)

router = APIRouter(prefix="/verify", tags=["Verification"])


@router.post("/laboratory", response_model=LabVerificationResponse, status_code=200)
def verify_laboratory(
    payload: LabVerificationRequest,
    db: Session = Depends(get_db),
):
    """
    Laboratory Accreditation and Test-Scope Verification Endpoint.

    - Verifies facility identity and accreditation against a synthetic NABL directory demo dataset.
    - Distinctly evaluates general accreditation validity vs specific test-scope authorization.
    - Yields deterministic verdicts: verified, not_verified, mismatch, or inconclusive.
    - Records verification check in local tamper-evident audit logs.
    - Never invents official verification results or treats missing demo data as fraud.
    """
    now_utc = datetime.datetime.now(datetime.timezone.utc)
    result = verify_laboratory_identity_and_scope(payload, current_time=now_utc)

    # Persist verification check in database
    log_id = f"VER-{uuid.uuid4().hex[:6].upper()}"
    audit_event_id: Optional[str] = None

    # Check if a linked report or record was provided
    target_doc_id: Optional[str] = None
    target_record_id: Optional[str] = None

    if payload.reportId:
        doc = db.query(ReportDocument).filter(ReportDocument.id == payload.reportId).first()
        if doc:
            target_doc_id = doc.id

    if payload.recordId:
        rec = db.query(MedicalRecord).filter(MedicalRecord.id == payload.recordId).first()
        if rec:
            target_record_id = rec.id
            if not target_doc_id and rec.report_document_id:
                target_doc_id = rec.report_document_id
            # If lab and test scope are verified, update record status to Verified
            if result.status == "verified" and result.testScopeStatus == "verified":
                rec.status = "Verified"

    # Create audit event if associated with an active record or document
    if target_doc_id or target_record_id:
        audit_event_id = f"EVT-{uuid.uuid4().hex[:4].upper()}"
        audit_event = AuditEvent(
            id=audit_event_id,
            patient_id="AN-PATIENT-01",
            report_document_id=target_doc_id,
            event_type="Lab verification check",
            artifact_hash=f"verify-{log_id.lower()}",
            timestamp_display=f"Today · {now_utc.strftime('%H:%M')}",
            actor_name="Lab verification service",
            rule_or_model="nabl-demo-v1.0",
            verification_status="Hash-linked" if result.status == "verified" else "Review-needed",
        )
        db.add(audit_event)

    # Persist verification log
    matched_lab = result.laboratory.name if result.laboratory else None
    matched_cert = result.laboratory.certificateNumber if result.laboratory else None

    verification_log = LabVerificationLog(
        id=log_id,
        patient_id="AN-PATIENT-01",
        report_document_id=target_doc_id,
        medical_record_id=target_record_id,
        queried_lab_name=payload.laboratoryName,
        queried_city=payload.city,
        queried_certificate=payload.certificateNumber,
        queried_discipline=payload.discipline,
        queried_test_name=payload.testName,
        matched_lab_name=matched_lab,
        matched_certificate=matched_cert,
        match_confidence=result.matchConfidence,
        overall_status=result.status,
        accreditation_status=result.accreditationStatus,
        test_scope_status=result.testScopeStatus,
        verdict=result.verdict,
        source_authority=result.sourceReference.authority,
        is_demo_source="true",
        created_at=now_utc,
    )
    db.add(verification_log)
    db.commit()

    if audit_event_id:
        result.auditEventId = audit_event_id

    return result


@router.get("/laboratory/demo-labs", response_model=List[VerifiedLabDetails])
def list_demo_laboratories():
    """Returns the list of synthetic demonstration laboratories available for testing."""
    return [
        VerifiedLabDetails(
            name=entry["name"],
            location=entry["location"],
            certificateNumber=entry["certificateNumber"],
            validThrough=entry["validThrough"],
            accreditationBody=entry.get("accreditationBody", "NABL"),
            disciplines=entry.get("disciplines", []),
            scopeTests=entry.get("scopeTests", []),
        )
        for entry in SYNTHETIC_NABL_REGISTRY
    ]


@router.post("/medicine", response_model=MedicineVerificationResponse, status_code=200)
def verify_medicine(
    payload: MedicineVerificationRequest,
    db: Session = Depends(get_db),
):
    """
    Medicine Packaging and Regulatory Metadata Verification Endpoint.

    - Compares brand name, active ingredient, strength, formulation, and manufacturer against synthetic CDSCO/SUGAM records.
    - Yields structured findings with verified, not_verified, mismatch, or inconclusive status.
    - Distinguishes missing evidence from confirmed mismatches.
    - Does not claim official regulatory approval without supporting source data.
    - Strictly avoids prescribing, diagnosing, or modifying medical treatment plans.
    """
    now_utc = datetime.datetime.now(datetime.timezone.utc)
    result = verify_medicine_identity_and_composition(payload, current_time=now_utc)

    log_id = f"MED-{uuid.uuid4().hex[:6].upper()}"
    audit_event_id: Optional[str] = None

    target_doc_id: Optional[str] = None
    target_record_id: Optional[str] = None

    if payload.reportId:
        doc = db.query(ReportDocument).filter(ReportDocument.id == payload.reportId).first()
        if doc:
            target_doc_id = doc.id

    if payload.recordId:
        rec = db.query(MedicalRecord).filter(MedicalRecord.id == payload.recordId).first()
        if rec:
            target_record_id = rec.id
            if not target_doc_id and rec.report_document_id:
                target_doc_id = rec.report_document_id

    if target_doc_id or target_record_id:
        audit_event_id = f"EVT-{uuid.uuid4().hex[:4].upper()}"
        audit_event = AuditEvent(
            id=audit_event_id,
            patient_id="AN-PATIENT-01",
            report_document_id=target_doc_id,
            event_type="Medicine verification check",
            artifact_hash=f"verify-{log_id.lower()}",
            timestamp_display=f"Today · {now_utc.strftime('%H:%M')}",
            actor_name="Medicine verification service",
            rule_or_model="sugam-demo-v1.0",
            verification_status="Hash-linked" if result.status == "verified" else "Review-needed",
        )
        db.add(audit_event)

    # Persist verification log
    matched_brand = result.product.brand if result.product else None
    matched_title = result.product.standardizedTitle if result.product else None

    medicine_log = MedicineVerificationLog(
        id=log_id,
        patient_id="AN-PATIENT-01",
        report_document_id=target_doc_id,
        medical_record_id=target_record_id,
        queried_brand=payload.brandName,
        queried_ingredient=payload.activeIngredient,
        queried_strength=payload.strength,
        queried_dosage_form=payload.dosageForm,
        queried_manufacturer=payload.manufacturer,
        matched_brand=matched_brand,
        matched_title=matched_title,
        match_confidence=result.matchConfidence,
        overall_status=result.status,
        verdict=result.verdict,
        source_authority=result.sourceReference.authority,
        is_demo_source="true",
        created_at=now_utc,
    )
    db.add(medicine_log)
    db.commit()

    if audit_event_id:
        result.auditEventId = audit_event_id

    return result


@router.get("/medicine/demo-medicines", response_model=List[VerifiedMedicineProduct])
def list_demo_medicines():
    """Returns the list of synthetic demonstration medicines available for regulatory comparison."""
    return [
        VerifiedMedicineProduct(
            brand=entry["brand"],
            standardizedTitle=entry["standardizedTitle"],
            activeIngredient=entry["activeIngredient"],
            strength=entry["strength"],
            dosageForm=entry["dosageForm"],
            manufacturer=entry["manufacturer"],
            route=entry.get("route", "Oral"),
            regulatoryStatus=entry.get("regulatoryStatus", "Cataloged in demo SUGAM database"),
            formulationNotes=entry.get("formulationNotes"),
        )
        for entry in SYNTHETIC_SUGAM_REGISTRY
    ]

