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
    VerificationAuditRecord,
)
from backend.app.schemas import (
    LabVerificationRequest,
    LabVerificationResponse,
    VerifiedLabDetails,
    MedicineVerificationRequest,
    MedicineVerificationResponse,
    VerifiedMedicineProduct,
    VerificationAuditRecordResponse,
    VerificationAuditListResponse,
    AuditChainIntegrityResponse,
)
from backend.app.services.lab_verification import (
    verify_laboratory_identity_and_scope,
    SYNTHETIC_NABL_REGISTRY,
)
from backend.app.services.medicine_verification import (
    verify_medicine_identity_and_composition,
    SYNTHETIC_SUGAM_REGISTRY,
)
from backend.app.services.verification_audit_service import (
    record_verification_audit,
    to_audit_record_response,
    verify_verification_audit_chain,
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

    # Record in tamper-evident VerificationAuditRecord
    findings_dict = {
        "checks": [c.model_dump() if hasattr(c, "model_dump") else c.dict() for c in result.checks],
        "accreditationStatus": result.accreditationStatus,
        "testScopeStatus": result.testScopeStatus,
        "evidenceLimitations": result.evidenceLimitations,
        "matchedEntitySummary": (
            f"{result.laboratory.name} ({result.laboratory.certificateNumber})"
            if result.laboratory
            else None
        ),
    }
    input_dict = {
        "laboratoryName": payload.laboratoryName,
        "city": payload.city,
        "certificateNumber": payload.certificateNumber,
        "discipline": payload.discipline,
        "testName": payload.testName,
        "reportId": payload.reportId,
        "recordId": payload.recordId,
        "simulateSourceFailure": payload.simulateSourceFailure,
    }

    has_source_error = bool(payload.simulateSourceFailure)
    source_error_details = (
        {
            "code": "SOURCE_UNAVAILABLE",
            "message": "Connection to demonstration accreditation registry timed out or failed",
            "simulated": True,
        }
        if has_source_error
        else None
    )

    entity_identifier = (
        payload.certificateNumber
        or payload.laboratoryName
        or (result.laboratory.name if result.laboratory else None)
    )

    audit_rec = record_verification_audit(
        db=db,
        entity_type="laboratory",
        check_type="accreditation_and_scope",
        entity_identifier=entity_identifier,
        source=result.sourceReference.authority,
        status=result.status,
        verdict=result.verdict,
        match_confidence=result.matchConfidence,
        findings_dict=findings_dict,
        input_dict=input_dict,
        has_source_error=has_source_error,
        source_error_details=source_error_details,
        report_document_id=target_doc_id,
        medical_record_id=target_record_id,
        lab_log_id=log_id,
        audit_event_id=audit_event_id,
        now_utc=now_utc,
    )
    db.commit()

    result.verificationAuditId = audit_rec.id
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

    # Record in tamper-evident VerificationAuditRecord
    findings_dict = {
        "checks": [c.model_dump() if hasattr(c, "model_dump") else c.dict() for c in result.checks],
        "reviewBanner": result.reviewBanner,
        "evidenceLimitations": result.evidenceLimitations,
        "matchedEntitySummary": (
            f"{result.product.brand} - {result.product.activeIngredient} ({result.product.strength})"
            if result.product
            else None
        ),
    }
    input_dict = {
        "brandName": payload.brandName,
        "activeIngredient": payload.activeIngredient,
        "strength": payload.strength,
        "dosageForm": payload.dosageForm,
        "manufacturer": payload.manufacturer,
        "route": payload.route,
        "reportId": payload.reportId,
        "recordId": payload.recordId,
        "simulateSourceFailure": payload.simulateSourceFailure,
    }

    has_source_error = bool(payload.simulateSourceFailure)
    source_error_details = (
        {
            "code": "SOURCE_UNAVAILABLE",
            "message": "Connection to demonstration regulatory catalogue timed out or failed",
            "simulated": True,
        }
        if has_source_error
        else None
    )

    entity_identifier = (
        payload.brandName
        or payload.activeIngredient
        or (result.product.brand if result.product else None)
    )

    audit_rec = record_verification_audit(
        db=db,
        entity_type="medicine",
        check_type="composition_and_regulatory",
        entity_identifier=entity_identifier,
        source=result.sourceReference.authority,
        status=result.status,
        verdict=result.verdict,
        match_confidence=result.matchConfidence,
        findings_dict=findings_dict,
        input_dict=input_dict,
        has_source_error=has_source_error,
        source_error_details=source_error_details,
        report_document_id=target_doc_id,
        medical_record_id=target_record_id,
        medicine_log_id=log_id,
        audit_event_id=audit_event_id,
        now_utc=now_utc,
    )
    db.commit()

    result.verificationAuditId = audit_rec.id
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


@router.get("/audit-records/chain/verify", response_model=AuditChainIntegrityResponse)
def check_audit_chain_integrity(db: Session = Depends(get_db)):
    """
    Validates cryptographic integrity of the verification audit history chain.
    Sequentially recomputes SHA-256 hashes from genesis forward, detecting any alteration or truncation.
    """
    return verify_verification_audit_chain(db)


@router.get("/audit-records", response_model=VerificationAuditListResponse)
def list_verification_audit_records(
    entity_type: Optional[str] = Query(None, description="Filter by entity type ('laboratory' or 'medicine')"),
    status: Optional[str] = Query(None, description="Filter by verification status ('verified', 'mismatch', 'inconclusive', 'not_verified', 'failed')"),
    check_type: Optional[str] = Query(None, description="Filter by check type"),
    source: Optional[str] = Query(None, description="Filter by source authority substring"),
    has_error: Optional[bool] = Query(None, description="Filter by presence of source error"),
    query: Optional[str] = Query(None, description="Free-text search across entity identifier, verdict, or ID"),
    report_id: Optional[str] = Query(None, description="Filter by linked report document ID"),
    record_id: Optional[str] = Query(None, description="Filter by linked medical record ID"),
    sort: str = Query("desc", description="Sort order by creation time: 'asc' or 'desc'"),
    limit: int = Query(20, ge=1, le=100, description="Number of records to return"),
    offset: int = Query(0, ge=0, description="Offset for pagination"),
    db: Session = Depends(get_db),
):
    """
    Retrieves verification audit records with filtering and pagination.
    """
    if sort.lower() not in ["asc", "desc"]:
        raise HTTPException(status_code=400, detail="Invalid sort parameter. Use 'asc' or 'desc'.")

    q = db.query(VerificationAuditRecord)

    if entity_type:
        q = q.filter(VerificationAuditRecord.entity_type == entity_type.lower())
    if status:
        q = q.filter(VerificationAuditRecord.status == status.lower())
    if check_type:
        q = q.filter(VerificationAuditRecord.check_type == check_type)
    if source:
        q = q.filter(VerificationAuditRecord.source.ilike(f"%{source}%"))
    if has_error is not None:
        q = q.filter(VerificationAuditRecord.has_source_error == has_error)
    if report_id:
        q = q.filter(VerificationAuditRecord.report_document_id == report_id)
    if record_id:
        q = q.filter(VerificationAuditRecord.medical_record_id == record_id)
    if query:
        search_term = f"%{query}%"
        q = q.filter(
            (VerificationAuditRecord.id.ilike(search_term))
            | (VerificationAuditRecord.entity_identifier.ilike(search_term))
            | (VerificationAuditRecord.verdict.ilike(search_term))
        )

    total = q.count()
    verified_count = q.filter(VerificationAuditRecord.status == "verified").count()
    mismatch_count = q.filter(VerificationAuditRecord.status == "mismatch").count()
    inconclusive_count = q.filter(VerificationAuditRecord.status == "inconclusive").count()
    failed_count = q.filter(VerificationAuditRecord.status.in_(["not_verified", "failed"])).count()

    if sort.lower() == "asc":
        q = q.order_by(VerificationAuditRecord.created_at.asc(), VerificationAuditRecord.id.asc())
    else:
        q = q.order_by(VerificationAuditRecord.created_at.desc(), VerificationAuditRecord.id.desc())

    records = q.offset(offset).limit(limit).all()

    return VerificationAuditListResponse(
        records=[to_audit_record_response(r) for r in records],
        total=total,
        verifiedCount=verified_count,
        mismatchCount=mismatch_count,
        inconclusiveCount=inconclusive_count,
        failedCount=failed_count,
        limit=limit,
        offset=offset,
    )


@router.get("/audit-records/{audit_id}", response_model=VerificationAuditRecordResponse)
def get_verification_audit_record(
    audit_id: str,
    db: Session = Depends(get_db),
):
    """
    Retrieves full details of a single verification audit record by ID.
    """
    record = (
        db.query(VerificationAuditRecord)
        .filter(VerificationAuditRecord.id == audit_id)
        .first()
    )
    if not record:
        raise HTTPException(
            status_code=404,
            detail=f"Verification audit record '{audit_id}' not found",
        )
    return to_audit_record_response(record)


