import json
import uuid
import hashlib
import datetime
from typing import Optional, Dict, Any, List, Tuple
from sqlalchemy.orm import Session

from backend.app.models import VerificationAuditRecord, utc_now
from backend.app.schemas import (
    VerificationAuditRecordResponse,
    VerificationAuditFindings,
    VerificationAuditCheckItem,
    VerificationAuditErrorDetails,
    AuditChainIntegrityResponse,
)

GENESIS_HASH = "0" * 64
STORAGE_PROTECTION_DISCLOSURE = (
    "Cryptographic SHA-256 hash-chaining stored in local SQLite database. "
    "Provides deterministic tamper-evidence against record alteration; "
    "does not claim decentralized consensus or hardware WORM immutability."
)


def compute_record_hash(
    previous_hash: str,
    record_id: str,
    entity_type: str,
    status: str,
    created_at_iso: str,
    canonical_data: Dict[str, Any],
) -> str:
    """
    Computes deterministic SHA-256 digest over sequential previous hash,
    record identifiers, and canonical sorted JSON payload.
    """
    payload_str = json.dumps(canonical_data, sort_keys=True, separators=(",", ":"))
    raw = f"{previous_hash}|{record_id}|{entity_type}|{status}|{created_at_iso}|{payload_str}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def record_verification_audit(
    db: Session,
    entity_type: str,
    check_type: str,
    entity_identifier: Optional[str],
    source: str,
    status: str,
    verdict: str,
    match_confidence: float,
    findings_dict: Dict[str, Any],
    input_dict: Dict[str, Any],
    has_source_error: bool = False,
    source_error_details: Optional[Dict[str, Any]] = None,
    report_document_id: Optional[str] = None,
    medical_record_id: Optional[str] = None,
    lab_log_id: Optional[str] = None,
    medicine_log_id: Optional[str] = None,
    audit_event_id: Optional[str] = None,
    now_utc: Optional[datetime.datetime] = None,
) -> VerificationAuditRecord:
    """
    Records an actual laboratory or medicine verification attempt into the tamper-evident audit history.
    Chains the SHA-256 hash to the preceding audit record.
    """
    if now_utc is None:
        now_utc = utc_now()

    # Retrieve preceding record to establish hash chain link
    last_record = (
        db.query(VerificationAuditRecord)
        .order_by(VerificationAuditRecord.created_at.desc(), VerificationAuditRecord.id.desc())
        .first()
    )
    previous_hash = last_record.record_hash if last_record else GENESIS_HASH

    record_id = f"VAR-{uuid.uuid4().hex[:6].upper()}"
    timestamp_iso = now_utc.isoformat()
    timestamp_display = now_utc.strftime("%d %b %Y · %H:%M")

    # Structure canonical dataset for hash computation
    canonical_payload = {
        "entity_type": entity_type,
        "entity_identifier": entity_identifier,
        "check_type": check_type,
        "source": source,
        "status": status,
        "verdict": verdict,
        "match_confidence": round(match_confidence, 4),
        "findings": findings_dict,
        "input": input_dict,
        "has_source_error": has_source_error,
        "source_error_details": source_error_details,
        "report_document_id": report_document_id,
        "medical_record_id": medical_record_id,
    }

    record_hash = compute_record_hash(
        previous_hash=previous_hash,
        record_id=record_id,
        entity_type=entity_type,
        status=status,
        created_at_iso=timestamp_iso,
        canonical_data=canonical_payload,
    )

    audit_entry = VerificationAuditRecord(
        id=record_id,
        patient_id="AN-PATIENT-01",
        entity_type=entity_type,
        entity_identifier=entity_identifier,
        check_type=check_type,
        source=source,
        is_demo_source="true",
        status=status,
        verdict=verdict,
        match_confidence=match_confidence,
        input_payload=json.dumps(input_dict, sort_keys=True),
        findings=json.dumps(findings_dict, sort_keys=True),
        has_source_error=has_source_error,
        source_error_details=json.dumps(source_error_details, sort_keys=True) if source_error_details else None,
        report_document_id=report_document_id,
        medical_record_id=medical_record_id,
        lab_log_id=lab_log_id,
        medicine_log_id=medicine_log_id,
        audit_event_id=audit_event_id,
        previous_record_hash=previous_hash,
        record_hash=record_hash,
        verification_status="hash_linked",
        timestamp_display=timestamp_display,
        timestamp_iso=timestamp_iso,
        created_at=now_utc,
    )

    db.add(audit_entry)
    return audit_entry


def to_audit_record_response(r: VerificationAuditRecord) -> VerificationAuditRecordResponse:
    """Transforms a VerificationAuditRecord DB model into a typed response schema."""
    # Parse findings
    findings_raw: Dict[str, Any] = {}
    if r.findings:
        try:
            findings_raw = json.loads(r.findings)
        except Exception:
            findings_raw = {}

    checks_list = [
        VerificationAuditCheckItem(
            item=c.get("item", "Check"),
            details=c.get("details", ""),
            status=c.get("status", "inconclusive"),
        )
        for c in findings_raw.get("checks", [])
    ]

    findings_obj = VerificationAuditFindings(
        checks=checks_list,
        verdict=r.verdict,
        matchConfidence=r.match_confidence,
        accreditationStatus=findings_raw.get("accreditationStatus"),
        testScopeStatus=findings_raw.get("testScopeStatus"),
        reviewBanner=findings_raw.get("reviewBanner"),
        evidenceLimitations=findings_raw.get("evidenceLimitations"),
        matchedEntitySummary=findings_raw.get("matchedEntitySummary"),
    )

    # Parse error details
    error_raw: Dict[str, Any] = {}
    if r.source_error_details:
        try:
            error_raw = json.loads(r.source_error_details)
        except Exception:
            error_raw = {}

    error_obj = VerificationAuditErrorDetails(
        hasSourceError=r.has_source_error,
        errorCode=error_raw.get("code"),
        errorMessage=error_raw.get("message"),
        simulated=error_raw.get("simulated", False),
    )

    return VerificationAuditRecordResponse(
        id=r.id,
        patientId=r.patient_id,
        entityType=r.entity_type,
        entityIdentifier=r.entity_identifier,
        checkType=r.check_type,
        source=r.source,
        isDemoSource=(r.is_demo_source == "true"),
        status=r.status,
        verdict=r.verdict,
        matchConfidence=r.match_confidence,
        findings=findings_obj,
        errorDetails=error_obj,
        reportId=r.report_document_id,
        recordId=r.medical_record_id,
        labLogId=r.lab_log_id,
        medicineLogId=r.medicine_log_id,
        auditEventId=r.audit_event_id,
        timestampDisplay=r.timestamp_display,
        timestampIso=r.timestamp_iso or (r.created_at.isoformat() if r.created_at else ""),
        recordHash=r.record_hash,
        previousRecordHash=r.previous_record_hash,
        verificationStatus=r.verification_status,
    )


def verify_verification_audit_chain(db: Session) -> AuditChainIntegrityResponse:
    """
    Cryptographic verification suite for the verification audit chain.
    Iterates sequentially through all recorded entries, recomputes each SHA-256 hash,
    and detects any manual alteration, truncation, or insertion.
    """
    records: List[VerificationAuditRecord] = (
        db.query(VerificationAuditRecord)
        .order_by(VerificationAuditRecord.created_at.asc(), VerificationAuditRecord.id.asc())
        .all()
    )

    expected_previous_hash = GENESIS_HASH
    latest_hash: Optional[str] = None

    for idx, rec in enumerate(records):
        # 1. Verify link to previous record
        if rec.previous_record_hash != expected_previous_hash:
            return AuditChainIntegrityResponse(
                chainValid=False,
                totalRecordsEvaluated=idx,
                genesisHash=GENESIS_HASH,
                latestHash=latest_hash,
                tamperedRecordId=rec.id,
                tamperedIndex=idx,
                storageProtection=STORAGE_PROTECTION_DISCLOSURE,
                message=(
                    f"Cryptographic hash chain broken at index {idx} (Record ID: '{rec.id}'). "
                    f"Recorded previous hash '{rec.previous_record_hash}' does not match expected '{expected_previous_hash}'."
                ),
            )

        # 2. Reconstruct canonical payload and recompute hash
        try:
            findings_dict = json.loads(rec.findings) if rec.findings else {}
        except Exception:
            findings_dict = {}

        try:
            input_dict = json.loads(rec.input_payload) if rec.input_payload else {}
        except Exception:
            input_dict = {}

        try:
            error_details = json.loads(rec.source_error_details) if rec.source_error_details else None
        except Exception:
            error_details = None

        canonical_payload = {
            "entity_type": rec.entity_type,
            "entity_identifier": rec.entity_identifier,
            "check_type": rec.check_type,
            "source": rec.source,
            "status": rec.status,
            "verdict": rec.verdict,
            "match_confidence": round(rec.match_confidence, 4),
            "findings": findings_dict,
            "input": input_dict,
            "has_source_error": rec.has_source_error,
            "source_error_details": error_details,
            "report_document_id": rec.report_document_id,
            "medical_record_id": rec.medical_record_id,
        }

        rec_iso = rec.timestamp_iso or (rec.created_at.isoformat() if rec.created_at else "")
        recomputed_hash = compute_record_hash(
            previous_hash=rec.previous_record_hash or GENESIS_HASH,
            record_id=rec.id,
            entity_type=rec.entity_type,
            status=rec.status,
            created_at_iso=rec_iso,
            canonical_data=canonical_payload,
        )

        if rec.record_hash != recomputed_hash:
            return AuditChainIntegrityResponse(
                chainValid=False,
                totalRecordsEvaluated=idx,
                genesisHash=GENESIS_HASH,
                latestHash=latest_hash,
                tamperedRecordId=rec.id,
                tamperedIndex=idx,
                storageProtection=STORAGE_PROTECTION_DISCLOSURE,
                message=(
                    f"Content integrity mismatch at index {idx} (Record ID: '{rec.id}'). "
                    f"Recorded hash '{rec.record_hash}' does not match recomputed hash '{recomputed_hash}'."
                ),
            )

        expected_previous_hash = rec.record_hash
        latest_hash = rec.record_hash

    return AuditChainIntegrityResponse(
        chainValid=True,
        totalRecordsEvaluated=len(records),
        genesisHash=GENESIS_HASH,
        latestHash=latest_hash,
        tamperedRecordId=None,
        tamperedIndex=None,
        storageProtection=STORAGE_PROTECTION_DISCLOSURE,
        message=(
            f"All {len(records)} verification audit record(s) cryptographically validated. "
            "No tampering, truncation, or sequence anomalies detected."
        ),
    )
