from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import or_
from typing import Optional, List
import datetime
from backend.app.database import get_db
from backend.app.models import MedicalRecord, AuditEvent
from backend.app.schemas import (
    RecordItemResponse,
    RecordListResponse,
    ManualRecordCreate,
)

router = APIRouter(prefix="/records", tags=["Medical Records"])

def _to_record_response(r: MedicalRecord) -> RecordItemResponse:
    return RecordItemResponse(
        id=r.id,
        name=r.name,
        date=r.date_display,
        lab=r.laboratory_name,
        value=r.value_display,
        unit=r.unit,
        range=r.reference_range,
        status=r.status,
        source=r.source,
        reportId=r.report_identifier,
        extractionConfidence=r.extraction_confidence,
        provenanceLocation=r.provenance_location,
    )

@router.get("", response_model=RecordListResponse)
def list_records(
    query: Optional[str] = Query(None, description="Search term for test name, lab, or ID"),
    status: Optional[str] = Query(None, description="Filter by status (Reviewed, Needs review, Verified)"),
    sort: Optional[str] = Query("newest", description="Sorting (newest, oldest)"),
    db: Session = Depends(get_db),
):
    """Lists medical records with search, status filtering, and sorting."""
    q = db.query(MedicalRecord)

    if query:
        term = f"%{query.strip()}%"
        q = q.filter(
            or_(
                MedicalRecord.name.ilike(term),
                MedicalRecord.laboratory_name.ilike(term),
                MedicalRecord.id.ilike(term),
                MedicalRecord.report_identifier.ilike(term),
            )
        )

    if status and status != "All statuses":
        q = q.filter(MedicalRecord.status == status)

    if sort == "oldest":
        q = q.order_by(MedicalRecord.created_at.asc())
    else:
        q = q.order_by(MedicalRecord.created_at.desc())

    records = q.all()
    return RecordListResponse(
        records=[_to_record_response(r) for r in records],
        total=len(records),
    )

@router.get("/{record_id}", response_model=RecordItemResponse)
def get_record(record_id: str, db: Session = Depends(get_db)):
    """Retrieves a single medical record by its identifier."""
    record = db.query(MedicalRecord).filter(MedicalRecord.id == record_id).first()
    if not record:
        raise HTTPException(status_code=404, detail=f"Medical record '{record_id}' not found")
    return _to_record_response(record)

@router.post("/manual", response_model=RecordItemResponse, status_code=201)
def create_manual_record(
    payload: ManualRecordCreate,
    db: Session = Depends(get_db),
):
    """Creates a confirmed medical record from direct manual user input."""
    # Generate sequential identifier
    count = db.query(MedicalRecord).count()
    new_id = f"SR-{1050 + count}"

    # Try parsing numeric value for trend plotting
    numeric_val = None
    try:
        numeric_val = float(payload.value.strip().split()[0])
    except (ValueError, IndexError):
        pass

    now_utc = datetime.datetime.now(datetime.timezone.utc)
    now_str = now_utc.strftime("%d %b %Y")

    new_record = MedicalRecord(
        id=new_id,
        patient_id="AN-PATIENT-01",
        name=payload.test.strip(),
        date_display="Today",
        laboratory_name=payload.lab.strip(),
        value_display=payload.value.strip(),
        value_numeric=numeric_val,
        unit=payload.unit.strip(),
        reference_range="Not provided",
        status="Reviewed",
        source="Manual",
        extraction_confidence=1.0,
        provenance_location="Direct user manual entry",
    )
    db.add(new_record)

    # Record hash-linked audit entry
    audit_id = f"EVT-{abs(hash(new_id + now_str)) % 10000:04d}"
    db.add(
        AuditEvent(
            id=audit_id,
            patient_id="AN-PATIENT-01",
            event_type="Manual entry added",
            artifact_hash=f"manual-{new_id}",
            timestamp_display=f"Today · {now_utc.strftime('%H:%M')}",
            actor_name="User AN",
            rule_or_model="user-entry-v1",
            verification_status="User-confirmed",
        )
    )

    db.commit()
    db.refresh(new_record)
    return _to_record_response(new_record)
