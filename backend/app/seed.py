from sqlalchemy.orm import Session
from backend.app.models import MedicalRecord, AuditEvent, ReportDocument
import datetime

INITIAL_RECORDS = [
    {
        "id": "SR-1048",
        "name": "Fasting Plasma Glucose",
        "date_display": "18 Oct 2025",
        "laboratory_name": "Aster Diagnostics, Pune",
        "value_display": "102",
        "value_numeric": 102.0,
        "unit": "mg/dL",
        "reference_range": "70–99 mg/dL",
        "status": "Needs review",
        "source": "PDF Extracted",
        "report_identifier": "LAB-8821",
        "report_date_display": "19 Oct 2025",
        "extraction_confidence": 0.96,
        "provenance_location": "Page 1 · Results table, row 3",
    },
    {
        "id": "SR-1043",
        "name": "Complete Blood Count",
        "date_display": "08 Sep 2025",
        "laboratory_name": "Metropolis Healthcare, Pune",
        "value_display": "13.6",
        "value_numeric": 13.6,
        "unit": "g/dL Hb",
        "reference_range": "12.0–15.5 g/dL",
        "status": "Reviewed",
        "source": "PDF Extracted",
        "report_identifier": "MET-7102",
        "report_date_display": "08 Sep 2025",
        "extraction_confidence": 0.98,
        "provenance_location": "Page 1 · Hemoglobin section",
    },
    {
        "id": "SR-1031",
        "name": "Fasting Plasma Glucose",
        "date_display": "12 Jul 2025",
        "laboratory_name": "Aster Diagnostics, Pune",
        "value_display": "96",
        "value_numeric": 96.0,
        "unit": "mg/dL",
        "reference_range": "70–99 mg/dL",
        "status": "Verified",
        "source": "Online Source",
        "report_identifier": "LAB-8614",
        "report_date_display": "12 Jul 2025",
        "extraction_confidence": 0.99,
        "provenance_location": "Patient portal direct API",
    },
    {
        "id": "SR-1022",
        "name": "Lipid Profile",
        "date_display": "14 Apr 2025",
        "laboratory_name": "CarePlus Labs, Mumbai",
        "value_display": "174",
        "value_numeric": 174.0,
        "unit": "mg/dL total",
        "reference_range": "<200 mg/dL",
        "status": "Reviewed",
        "source": "Scanned Image",
        "report_identifier": "CP-2410",
        "report_date_display": "15 Apr 2025",
        "extraction_confidence": 0.88,
        "provenance_location": "Page 1 · Lipid panel table",
    },
    {
        "id": "SR-1015",
        "name": "Complete Blood Count",
        "date_display": "04 Feb 2025",
        "laboratory_name": "Metropolis Healthcare, Pune",
        "value_display": "13.2",
        "value_numeric": 13.2,
        "unit": "g/dL Hb",
        "reference_range": "12.0–15.5 g/dL",
        "status": "Reviewed",
        "source": "Manual",
        "report_identifier": "MET-6940",
        "report_date_display": "04 Feb 2025",
        "extraction_confidence": 1.0,
        "provenance_location": "Direct clinician manual entry",
    },
]

INITIAL_AUDIT_EVENTS = [
    {
        "id": "EVT-8F21",
        "event_type": "Report confirmed",
        "artifact_hash": "a91f4e80b92c4b81d77a06421389e61129b015e100f91a27e384b6119a7cd2",
        "previous_event_hash": "c08391aa4921b721019a8421b92019a8421092109a8201948210948201948201",
        "timestamp_display": "20 Oct 2025 · 09:42",
        "actor_name": "User AN",
        "rule_or_model": "rules-v1.4",
        "verification_status": "Hash-linked",
    },
    {
        "id": "EVT-8F18",
        "event_type": "OCR extraction reviewed",
        "artifact_hash": "c08391aa4921b721019a8421b92019a8421092109a8201948210948201948201",
        "previous_event_hash": "a91f4e80b92c4b81d77a06421389e61129b015e100f91a27e384b6119a7cd2",
        "timestamp_display": "20 Oct 2025 · 09:39",
        "actor_name": "User AN",
        "rule_or_model": "ocr-demo-v2",
        "verification_status": "Hash-linked",
    },
    {
        "id": "EVT-8F11",
        "event_type": "File added",
        "artifact_hash": "a91f4e80b92c4b81d77a06421389e61129b015e100f91a27e384b6119a7cd2",
        "previous_event_hash": None,
        "timestamp_display": "20 Oct 2025 · 09:36",
        "actor_name": "Local upload",
        "rule_or_model": "ingest-v1.2",
        "verification_status": "Hash-linked",
    },
]

def seed_database(db: Session) -> None:
    """Seeds synthetic demo data if tables are empty."""
    existing_records = db.query(MedicalRecord).count()
    if existing_records == 0:
        for rec in INITIAL_RECORDS:
            db.add(MedicalRecord(**rec))

    existing_audits = db.query(AuditEvent).count()
    if existing_audits == 0:
        for audit in INITIAL_AUDIT_EVENTS:
            db.add(AuditEvent(**audit))

    db.commit()
