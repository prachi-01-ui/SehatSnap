import re
import datetime
from typing import Optional, Tuple, Union
from backend.app.schemas import CareTaskCreate
from backend.app.models import LabVerificationLog, MedicineVerificationLog

NOTIFICATION_STATUS_UNCONFIGURED = "Not configured (local record only)"
NOTIFICATION_NOTICE = (
    "No external delivery integration (SMS/Push/Email) is configured in this deployment; "
    "care-task reminders are tracked locally."
)

ALLOWED_STATUSES = [
    "Needs Review",
    "Scheduled",
    "Completed",
    "Not Applicable",
    "Clinician Review",
]

# Regex patterns detecting prohibited autonomous actions
# (Autonomous diagnoses or autonomous prescription/dosage changes)
PROHIBITED_PRESCRIPTION_PATTERNS = [
    re.compile(r"\b(prescribe|prescribing|write\s+prescription)\b", re.IGNORECASE),
    re.compile(r"\b(increase|decrease|change|alter|adjust|double|halve)\b.*\b(dose|dosage|medication|medicine|drug|prescription)\b", re.IGNORECASE),
    re.compile(r"\b(stop\s+taking|discontinue|cease|substitute)\b.*\b(medication|medicine|drug|tablet|pill|dose|treatment)\b", re.IGNORECASE),
    re.compile(r"\b(start\s+taking|administer)\b.*\b(drug|medicine|tablet|dose|medication)\b", re.IGNORECASE),
]

PROHIBITED_DIAGNOSIS_PATTERNS = [
    re.compile(r"\b(diagnose\s+patient|diagnosed\s+with|issue\s+diagnosis)\b", re.IGNORECASE),
    re.compile(r"\b(confirm|conclude|establish|declare)\b.*\bdiagnosis\b", re.IGNORECASE),
    re.compile(r"\b(confirm|conclude)\s+that\s+patient\s+has\b", re.IGNORECASE),
    re.compile(r"\bpatient\s+(is\s+diagnosed\s+with|suffers\s+from|has\s+clinical)\b", re.IGNORECASE),
]

# Patterns that indicate a safe follow-up or consultation request
PERMITTED_CONSULTATION_EXCEPTIONS = [
    re.compile(r"\b(consult|discuss\s+with|review\s+with|request\s+clinician|ask\s+doctor|pharmacist\s+review)\b", re.IGNORECASE),
    re.compile(r"\b(for\s+clinician\s+review|evaluation\s+by\s+physician)\b", re.IGNORECASE),
]


def validate_clinical_safety(title: str, description: Optional[str] = None) -> None:
    """
    Enforces clinical safety boundary:
    Care tasks must strictly represent follow-up actions (repeating tests, scheduling consultations,
    uploading documentation, requesting records), NOT autonomous diagnoses or medication changes.
    """
    combined_text = f"{title or ''} {description or ''}".strip()
    if not combined_text:
        return

    # Check for permitted consultation exceptions
    has_consultation_context = any(pat.search(combined_text) for pat in PERMITTED_CONSULTATION_EXCEPTIONS)

    if not has_consultation_context:
        for pattern in PROHIBITED_PRESCRIPTION_PATTERNS:
            if pattern.search(combined_text):
                raise ValueError(
                    "Care tasks must represent follow-up actions (e.g., repeating tests, scheduling consultations, "
                    "requesting records, or requesting clinician review). Autonomous medication changes, dosage adjustments, "
                    "or prescribing are strictly prohibited."
                )

        for pattern in PROHIBITED_DIAGNOSIS_PATTERNS:
            if pattern.search(combined_text):
                raise ValueError(
                    "Care tasks must represent follow-up actions (e.g., repeating tests, scheduling consultations, "
                    "requesting records, or requesting clinician review). Autonomous clinical diagnoses are strictly prohibited."
                )


def parse_due_date(due_str: Optional[str]) -> Tuple[Optional[str], Optional[datetime.datetime]]:
    """
    Parses optional due date string into (display_str, utc_datetime).
    Supports formats:
      - '02 Nov 2025'
      - '2025-11-02'
      - '2025-11-02T10:00:00'
      - '02/11/2025'
    """
    if not due_str or not due_str.strip():
        return None, None

    cleaned = due_str.strip()

    formats = [
        "%d %b %Y",
        "%d %B %Y",
        "%Y-%m-%d",
        "%Y-%m-%dT%H:%M:%S",
        "%Y-%m-%dT%H:%M:%SZ",
        "%d/%m/%Y",
        "%m/%d/%Y",
        "%b %d, %Y",
        "%B %d, %Y",
    ]

    for fmt in formats:
        try:
            dt = datetime.datetime.strptime(cleaned, fmt)
            # Attach UTC timezone
            dt_utc = dt.replace(tzinfo=datetime.timezone.utc)
            display = dt_utc.strftime("%d %b %Y")
            return display, dt_utc
        except ValueError:
            continue

    raise ValueError(
        f"Invalid due date format: '{due_str}'. "
        "Expected standard formats like '02 Nov 2025' or 'YYYY-MM-DD'."
    )


def normalize_task_status(status_str: Optional[str]) -> str:
    """Normalizes task status string to standard allowed values."""
    if not status_str or not status_str.strip():
        return "Needs Review"

    cleaned = status_str.strip().lower().replace("_", " ")

    status_map = {
        "needs review": "Needs Review",
        "pending": "Needs Review",
        "review": "Needs Review",
        "scheduled": "Scheduled",
        "booked": "Scheduled",
        "completed": "Completed",
        "done": "Completed",
        "verified": "Completed",
        "not applicable": "Not Applicable",
        "n/a": "Not Applicable",
        "na": "Not Applicable",
        "cancelled": "Not Applicable",
        "clinician review": "Clinician Review",
        "physician review": "Clinician Review",
        "doctor review": "Clinician Review",
    }

    if cleaned in status_map:
        return status_map[cleaned]

    # Check exact match in ALLOWED_STATUSES (case-insensitive)
    for allowed in ALLOWED_STATUSES:
        if allowed.lower() == cleaned:
            return allowed

    raise ValueError(
        f"Invalid status '{status_str}'. Allowed statuses: {', '.join(ALLOWED_STATUSES)}."
    )


def create_followup_from_verification_log(
    log: Union[LabVerificationLog, MedicineVerificationLog],
    verification_type: str,
    custom_notes: Optional[str] = None,
    due: Optional[str] = None,
    priority: Optional[str] = None,
) -> CareTaskCreate:
    """
    Constructs a structured follow-up care task linked to a verification log.
    Ensures tasks represent follow-up recommendations (e.g. scope clarification or pharmacist review)
    rather than autonomous changes.
    """
    vtype = (verification_type or "").lower().strip()

    if vtype == "laboratory":
        lab_log: LabVerificationLog = log
        is_verified = (lab_log.overall_status == "verified" and lab_log.test_scope_status == "verified")

        if is_verified:
            title = f"Routine follow-up: Archive accredited report for {lab_log.queried_test_name or 'test'}"
            reason = f"Laboratory '{lab_log.matched_lab_name}' verified against NABL demonstration records."
            task_priority = priority or "low"
            expected = f"Accredited scope confirmation for {lab_log.queried_test_name or 'test'}"
        else:
            test_or_discipline = lab_log.queried_test_name or lab_log.queried_discipline or "test"
            title = f"Follow-up: Clarify laboratory accreditation scope for {test_or_discipline}"
            reason = (
                f"Verification finding flagged {lab_log.overall_status} "
                f"(Accreditation: {lab_log.accreditation_status}, Test-scope: {lab_log.test_scope_status}). "
                f"Verdict: {lab_log.verdict}"
            )
            task_priority = priority or "high"
            expected = "Scope verification note or repeat test at accredited facility"

        source_label = f"NABL demonstration verification finding ({lab_log.id})"
        description = custom_notes or f"Follow-up on laboratory check {lab_log.id}. Source: {lab_log.source_authority}."

        return CareTaskCreate(
            title=title,
            description=description,
            task_type="verification_follow_up",
            expected=expected,
            due=due,
            source=source_label,
            status="Needs Review",
            priority=task_priority,
            reason=reason,
            report_id=lab_log.report_document_id,
            record_id=lab_log.medical_record_id,
            lab_verification_id=lab_log.id,
        )

    elif vtype == "medicine":
        med_log: MedicineVerificationLog = log
        is_verified = (med_log.overall_status == "verified")

        if is_verified:
            title = f"Routine follow-up: Catalog packaging record for {med_log.queried_brand or 'medicine'}"
            reason = f"Medicine metadata matched synthetic CDSCO/SUGAM cataloged product."
            task_priority = priority or "low"
            expected = f"Catalog verification entry for {med_log.queried_brand or 'medicine'}"
        else:
            brand_label = med_log.queried_brand or "medicine formulation"
            title = f"Pharmacist consultation: Formulation review for {brand_label}"
            reason = (
                f"Verification finding flagged {med_log.overall_status}: {med_log.verdict}. "
                "Consult a licensed pharmacist or physician before altering medicine intake."
            )
            task_priority = priority or "high"
            expected = "Registered pharmacist consultation note"

        source_label = f"SUGAM demonstration verification finding ({med_log.id})"
        description = custom_notes or f"Follow-up on medicine check {med_log.id}. Source: {med_log.source_authority}."

        return CareTaskCreate(
            title=title,
            description=description,
            task_type="verification_follow_up",
            expected=expected,
            due=due,
            source=source_label,
            status="Needs Review",
            priority=task_priority,
            reason=reason,
            report_id=med_log.report_document_id,
            record_id=med_log.medical_record_id,
            medicine_verification_id=med_log.id,
        )
    else:
        raise ValueError(f"Unsupported verification type '{verification_type}'. Must be 'laboratory' or 'medicine'.")
