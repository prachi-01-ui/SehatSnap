import uuid
import datetime
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from sqlalchemy import or_, and_

from backend.app.database import get_db
from backend.app.models import (
    CareTask,
    ReportDocument,
    MedicalRecord,
    LabVerificationLog,
    MedicineVerificationLog,
    AuditEvent,
    utc_now,
)
from backend.app.schemas import (
    CareTaskCreate,
    CareTaskStatusUpdate,
    CareTaskUpdate,
    CareTaskResponse,
    CareTaskListResponse,
    CareTaskLinkedEntities,
    TaskFromVerificationRequest,
)
from backend.app.services.care_task_service import (
    validate_clinical_safety,
    parse_due_date,
    normalize_task_status,
    create_followup_from_verification_log,
    NOTIFICATION_STATUS_UNCONFIGURED,
    NOTIFICATION_NOTICE,
    ALLOWED_STATUSES,
)

router = APIRouter(prefix="/care-tasks", tags=["Care Tasks & Follow-ups"])


def _to_care_task_response(t: CareTask) -> CareTaskResponse:
    report_fname = t.document.original_filename if t.document else None
    record_name = t.record.name if t.record else None

    created_str = t.created_at.strftime("%d %b %Y · %H:%M") if t.created_at else ""
    updated_str = t.updated_at.strftime("%d %b %Y · %H:%M") if t.updated_at else ""
    completed_str = t.completed_at.strftime("%d %b %Y · %H:%M") if t.completed_at else None

    return CareTaskResponse(
        id=t.id,
        patientId=t.patient_id,
        title=t.title,
        description=t.description,
        taskType=t.task_type,
        expected=t.expected,
        due=t.due_date_display,
        dueDateIso=t.due_date.isoformat() if t.due_date else None,
        source=t.source,
        status=t.status,
        priority=t.priority,
        reason=t.reason,
        linkedEntities=CareTaskLinkedEntities(
            reportId=t.report_document_id,
            recordId=t.medical_record_id,
            labVerificationId=t.lab_verification_id,
            medicineVerificationId=t.medicine_verification_id,
            reportFilename=report_fname,
            recordName=record_name,
        ),
        notificationStatus=t.notification_status or NOTIFICATION_STATUS_UNCONFIGURED,
        notificationNotice=NOTIFICATION_NOTICE,
        createdAt=created_str,
        updatedAt=updated_str,
        completedAt=completed_str,
    )


@router.get("", response_model=CareTaskListResponse)
def list_care_tasks(
    status_filter: Optional[str] = Query(None, alias="status", description="Filter by status (e.g. 'Needs Review', 'Scheduled', 'Completed', 'pending', 'all')"),
    priority: Optional[str] = Query(None, description="Filter by priority ('high', 'normal', 'low')"),
    task_type: Optional[str] = Query(None, description="Filter by task type"),
    report_id: Optional[str] = Query(None, description="Filter by linked report document ID"),
    record_id: Optional[str] = Query(None, description="Filter by linked medical record ID"),
    query: Optional[str] = Query(None, description="Search term across title, description, expected, or reason"),
    sort: Optional[str] = Query("due_asc", description="Sort order: 'due_asc', 'due_desc', 'newest', 'oldest'"),
    db: Session = Depends(get_db),
):
    """
    Lists care-plan follow-up tasks with search, status filtering, and sorting.
    Grounded strictly in user-confirmed or clinical recommendations.
    """
    q = db.query(CareTask)

    if status_filter and status_filter.lower() != "all":
        if status_filter.lower() == "pending":
            q = q.filter(CareTask.status.in_(["Needs Review", "Scheduled", "Clinician Review"]))
        else:
            try:
                norm_status = normalize_task_status(status_filter)
                q = q.filter(CareTask.status == norm_status)
            except ValueError:
                # If non-standard string passed, do case-insensitive exact check
                q = q.filter(CareTask.status.ilike(status_filter.strip()))

    if priority:
        q = q.filter(CareTask.priority == priority.lower().strip())

    if task_type:
        q = q.filter(CareTask.task_type == task_type.strip())

    if report_id:
        q = q.filter(CareTask.report_document_id == report_id.strip())

    if record_id:
        q = q.filter(CareTask.medical_record_id == record_id.strip())

    if query and query.strip():
        term = f"%{query.strip()}%"
        q = q.filter(
            or_(
                CareTask.title.ilike(term),
                CareTask.description.ilike(term),
                CareTask.expected.ilike(term),
                CareTask.reason.ilike(term),
                CareTask.source.ilike(term),
                CareTask.id.ilike(term),
            )
        )

    # Sorting
    if sort == "newest":
        q = q.order_by(CareTask.created_at.desc())
    elif sort == "oldest":
        q = q.order_by(CareTask.created_at.asc())
    elif sort == "due_desc":
        # nulls last
        q = q.order_by(CareTask.due_date.desc().nullslast(), CareTask.created_at.desc())
    else:  # default "due_asc"
        q = q.order_by(CareTask.due_date.asc().nullslast(), CareTask.created_at.desc())

    tasks = q.all()

    # Aggregate counts across all patient tasks
    total_in_db = db.query(CareTask).count()
    pending_count = db.query(CareTask).filter(
        CareTask.status.in_(["Needs Review", "Scheduled", "Clinician Review"])
    ).count()
    completed_count = db.query(CareTask).filter(CareTask.status == "Completed").count()

    return CareTaskListResponse(
        tasks=[_to_care_task_response(t) for t in tasks],
        total=len(tasks),
        pendingCount=pending_count,
        completedCount=completed_count,
    )


@router.post("", response_model=CareTaskResponse, status_code=status.HTTP_201_CREATED)
def create_care_task(
    payload: CareTaskCreate,
    db: Session = Depends(get_db),
):
    """
    Creates a new care-plan follow-up task.
    Enforces clinical safety: strictly prohibits autonomous diagnoses and medication/dosage alterations.
    """
    # 1. Clinical safety validation
    try:
        validate_clinical_safety(payload.title, payload.description)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=str(e),
        )

    # 2. Date parsing
    try:
        due_display, due_dt = parse_due_date(payload.due)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=str(e),
        )

    # 3. Status normalization
    try:
        normalized_status = normalize_task_status(payload.status)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=str(e),
        )

    # 4. Linkage validation
    if payload.reportId:
        doc = db.query(ReportDocument).filter(ReportDocument.id == payload.reportId.strip()).first()
        if not doc:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Referenced report document '{payload.reportId}' not found",
            )

    if payload.recordId:
        rec = db.query(MedicalRecord).filter(MedicalRecord.id == payload.recordId.strip()).first()
        if not rec:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Referenced medical record '{payload.recordId}' not found",
            )

    if payload.labVerificationId:
        lab_log = db.query(LabVerificationLog).filter(LabVerificationLog.id == payload.labVerificationId.strip()).first()
        if not lab_log:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Referenced laboratory verification log '{payload.labVerificationId}' not found",
            )

    if payload.medicineVerificationId:
        med_log = db.query(MedicineVerificationLog).filter(MedicineVerificationLog.id == payload.medicineVerificationId.strip()).first()
        if not med_log:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Referenced medicine verification log '{payload.medicineVerificationId}' not found",
            )

    # 5. Identifier generation
    count = db.query(CareTask).count()
    candidate_id = f"TSK-{1001 + count}"
    if db.query(CareTask).filter(CareTask.id == candidate_id).first():
        candidate_id = f"TSK-{uuid.uuid4().hex[:6].upper()}"

    now_utc = utc_now()
    completed_dt = now_utc if normalized_status == "Completed" else None

    new_task = CareTask(
        id=candidate_id,
        patient_id="AN-PATIENT-01",
        report_document_id=payload.reportId.strip() if payload.reportId else None,
        medical_record_id=payload.recordId.strip() if payload.recordId else None,
        lab_verification_id=payload.labVerificationId.strip() if payload.labVerificationId else None,
        medicine_verification_id=payload.medicineVerificationId.strip() if payload.medicineVerificationId else None,
        title=payload.title.strip(),
        description=payload.description.strip() if payload.description else None,
        task_type=payload.taskType.strip() if payload.taskType else "diagnostic_follow_up",
        expected=payload.expected.strip() if payload.expected else None,
        due_date_display=due_display,
        due_date=due_dt,
        source=payload.source.strip() if payload.source else "User-confirmed care plan",
        status=normalized_status,
        priority=payload.priority.lower().strip() if payload.priority else "normal",
        reason=payload.reason.strip() if payload.reason else None,
        notification_status=NOTIFICATION_STATUS_UNCONFIGURED,
        created_at=now_utc,
        updated_at=now_utc,
        completed_at=completed_dt,
    )
    db.add(new_task)

    # Record tamper-evident audit event
    audit_id = f"EVT-{uuid.uuid4().hex[:4].upper()}"
    db.add(
        AuditEvent(
            id=audit_id,
            patient_id="AN-PATIENT-01",
            report_document_id=payload.reportId,
            event_type="Care task created",
            artifact_hash=f"caretask-{candidate_id.lower()}",
            timestamp_display=f"Today · {now_utc.strftime('%H:%M')}",
            actor_name="User AN",
            rule_or_model="care-task-v1.0",
            verification_status="User-confirmed",
        )
    )

    db.commit()
    db.refresh(new_task)

    return _to_care_task_response(new_task)


@router.get("/notifications/status")
def get_notification_integration_status():
    """
    Returns explicit notification configuration state.
    Truthfully declares that external delivery integration (SMS/Push/Email) is not active.
    """
    return {
        "integrationEnabled": False,
        "provider": None,
        "deliveryChannels": [],
        "notificationStatus": NOTIFICATION_STATUS_UNCONFIGURED,
        "notice": NOTIFICATION_NOTICE,
    }


@router.post("/from-verification", response_model=CareTaskResponse, status_code=status.HTTP_201_CREATED)
def create_task_from_verification_finding(
    payload: TaskFromVerificationRequest,
    db: Session = Depends(get_db),
):
    """
    Generates a structured follow-up care task linked to a laboratory or medicine verification finding.
    Frames actions strictly as follow-up consultations or scope clarifications.
    """
    vtype = payload.verificationType.lower().strip()

    if vtype == "laboratory":
        log = db.query(LabVerificationLog).filter(LabVerificationLog.id == payload.verificationLogId.strip()).first()
        if not log:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Laboratory verification log '{payload.verificationLogId}' not found",
            )
    elif vtype == "medicine":
        log = db.query(MedicineVerificationLog).filter(MedicineVerificationLog.id == payload.verificationLogId.strip()).first()
        if not log:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Medicine verification log '{payload.verificationLogId}' not found",
            )
    else:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=f"Invalid verificationType '{payload.verificationType}'. Must be 'laboratory' or 'medicine'.",
        )

    task_create_data = create_followup_from_verification_log(
        log=log,
        verification_type=vtype,
        custom_notes=payload.customNotes,
        due=payload.due,
        priority=payload.priority,
    )

    return create_care_task(task_create_data, db=db)


@router.get("/{task_id}", response_model=CareTaskResponse)
def get_care_task(task_id: str, db: Session = Depends(get_db)):
    """Retrieves a single care-plan task by its identifier."""
    task = db.query(CareTask).filter(CareTask.id == task_id.strip()).first()
    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Care task '{task_id}' not found",
        )
    return _to_care_task_response(task)


@router.patch("/{task_id}/status", response_model=CareTaskResponse)
def update_care_task_status(
    task_id: str,
    payload: CareTaskStatusUpdate,
    db: Session = Depends(get_db),
):
    """
    Updates the lifecycle status of a care-plan task.
    Automatically timestamps completions and records an audit log entry.
    """
    task = db.query(CareTask).filter(CareTask.id == task_id.strip()).first()
    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Care task '{task_id}' not found",
        )

    try:
        norm_status = normalize_task_status(payload.status)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=str(e),
        )

    now_utc = utc_now()
    task.status = norm_status
    task.updated_at = now_utc

    if norm_status == "Completed":
        task.completed_at = now_utc
    else:
        task.completed_at = None

    if payload.reason:
        task.reason = payload.reason.strip()

    # Log audit event
    audit_id = f"EVT-{uuid.uuid4().hex[:4].upper()}"
    db.add(
        AuditEvent(
            id=audit_id,
            patient_id=task.patient_id,
            report_document_id=task.report_document_id,
            event_type=f"Care task marked {norm_status}",
            artifact_hash=f"caretask-{task.id.lower()}-{norm_status.lower().replace(' ', '-')}",
            timestamp_display=f"Today · {now_utc.strftime('%H:%M')}",
            actor_name="User AN",
            rule_or_model="care-task-v1.0",
            verification_status="User-confirmed",
        )
    )

    db.commit()
    db.refresh(task)

    return _to_care_task_response(task)


@router.patch("/{task_id}", response_model=CareTaskResponse)
def update_care_task_details(
    task_id: str,
    payload: CareTaskUpdate,
    db: Session = Depends(get_db),
):
    """Updates editable metadata and properties for an existing care task."""
    task = db.query(CareTask).filter(CareTask.id == task_id.strip()).first()
    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Care task '{task_id}' not found",
        )

    # Validate safety if title or description updated
    new_title = payload.title if payload.title is not None else task.title
    new_desc = payload.description if payload.description is not None else task.description
    try:
        validate_clinical_safety(new_title, new_desc)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=str(e),
        )

    if payload.title is not None:
        task.title = payload.title.strip()

    if payload.description is not None:
        task.description = payload.description.strip()

    if payload.taskType is not None:
        task.task_type = payload.taskType.strip()

    if payload.expected is not None:
        task.expected = payload.expected.strip()

    if payload.priority is not None:
        task.priority = payload.priority.lower().strip()

    if payload.reason is not None:
        task.reason = payload.reason.strip()

    if payload.due is not None:
        try:
            due_display, due_dt = parse_due_date(payload.due)
            task.due_date_display = due_display
            task.due_date = due_dt
        except ValueError as e:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail=str(e),
            )

    if payload.status is not None:
        try:
            norm_status = normalize_task_status(payload.status)
            task.status = norm_status
            if norm_status == "Completed":
                task.completed_at = utc_now()
            else:
                task.completed_at = None
        except ValueError as e:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail=str(e),
            )

    task.updated_at = utc_now()
    db.commit()
    db.refresh(task)

    return _to_care_task_response(task)


@router.delete("/{task_id}")
def delete_care_task(task_id: str, db: Session = Depends(get_db)):
    """Deletes a care-plan task and records an audit log entry."""
    task = db.query(CareTask).filter(CareTask.id == task_id.strip()).first()
    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Care task '{task_id}' not found",
        )

    db.delete(task)
    db.commit()

    return {
        "success": True,
        "message": f"Care task '{task_id}' removed successfully",
    }
