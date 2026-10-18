import pytest
from backend.app.models import CareTask, LabVerificationLog, MedicineVerificationLog, MedicalRecord


@pytest.fixture(autouse=True)
def clean_created_care_tasks(db_session):
    yield
    # Cleanup any non-seeded care tasks after each test in this module
    seeded_ids = {"TSK-1001", "TSK-1002", "TSK-1003"}
    db_session.query(CareTask).filter(~CareTask.id.in_(seeded_ids)).delete(synchronize_session=False)
    # Restore seeded tasks status if altered
    t1 = db_session.query(CareTask).filter(CareTask.id == "TSK-1001").first()
    if t1:
        t1.status = "Needs Review"
        t1.completed_at = None
        t1.due_date_display = "02 Nov 2025"
    t2 = db_session.query(CareTask).filter(CareTask.id == "TSK-1002").first()
    if t2:
        t2.status = "Scheduled"
        t2.completed_at = None
        t2.due_date_display = "18 Nov 2025"
    db_session.commit()


def test_list_care_tasks_seeded(client):

    """Verifies seeded care-plan tasks are returned with proper aggregate counts."""
    response = client.get("/api/v1/care-tasks")
    assert response.status_code == 200
    data = response.json()

    assert "tasks" in data
    assert data["total"] >= 3
    assert data["pendingCount"] >= 2
    assert data["completedCount"] >= 1

    task_ids = [t["id"] for t in data["tasks"]]
    assert "TSK-1001" in task_ids
    assert "TSK-1002" in task_ids
    assert "TSK-1003" in task_ids

    # Verify notification disclosure
    for t in data["tasks"]:
        assert "Not configured" in t["notificationStatus"]
        assert "No external delivery integration" in t["notificationNotice"]


def test_list_care_tasks_filter_by_status(client):
    """Verifies filtering tasks by lifecycle status."""
    # Filter pending
    res_pending = client.get("/api/v1/care-tasks?status=pending")
    assert res_pending.status_code == 200
    pending_tasks = res_pending.json()["tasks"]
    assert len(pending_tasks) >= 2
    for t in pending_tasks:
        assert t["status"] in ["Needs Review", "Scheduled", "Clinician Review"]

    # Filter Completed
    res_completed = client.get("/api/v1/care-tasks?status=Completed")
    assert res_completed.status_code == 200
    completed_tasks = res_completed.json()["tasks"]
    assert len(completed_tasks) >= 1
    for t in completed_tasks:
        assert t["status"] == "Completed"


def test_list_care_tasks_search_and_sort(client):
    """Verifies search query across task text and sorting options."""
    # Search for glucose
    res_search = client.get("/api/v1/care-tasks?query=glucose")
    assert res_search.status_code == 200
    tasks = res_search.json()["tasks"]
    assert len(tasks) >= 1
    assert any("glucose" in t["title"].lower() for t in tasks)

    # Sort options
    res_due_asc = client.get("/api/v1/care-tasks?sort=due_asc")
    assert res_due_asc.status_code == 200

    res_newest = client.get("/api/v1/care-tasks?sort=newest")
    assert res_newest.status_code == 200


def test_get_single_care_task(client):
    """Verifies retrieving a specific care task by ID."""
    response = client.get("/api/v1/care-tasks/TSK-1001")
    assert response.status_code == 200
    task = response.json()
    assert task["id"] == "TSK-1001"
    assert task["title"] == "Repeat fasting glucose"
    assert task["expected"] == "Fasting Plasma Glucose report"
    assert task["due"] == "02 Nov 2025"
    assert task["source"] == "Dr. Mehta visit note · 18 Oct"
    assert task["status"] == "Needs Review"
    assert task["linkedEntities"]["recordId"] == "SR-1048"


def test_get_nonexistent_care_task_404(client):
    """Verifies 404 response on missing task identifier."""
    response = client.get("/api/v1/care-tasks/TSK-99999")
    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()


def test_create_care_task_success(client):
    """Verifies creating a documented follow-up care task."""
    payload = {
        "title": "Schedule specialist consultation with endocrinologist",
        "description": "Patient review recommended following high fasting glucose reading.",
        "taskType": "specialist_consultation",
        "expected": "Endocrine consultation summary",
        "due": "25 Nov 2025",
        "source": "Clinician recommendation · 20 Oct",
        "status": "Scheduled",
        "priority": "high",
        "reason": "Elevated fasting plasma glucose requiring specialist consultation.",
    }
    response = client.post("/api/v1/care-tasks", json=payload)
    assert response.status_code == 201
    created = response.json()

    assert created["id"].startswith("TSK-")
    assert created["title"] == payload["title"]
    assert created["due"] == "25 Nov 2025"
    assert created["dueDateIso"] is not None
    assert created["status"] == "Scheduled"
    assert created["priority"] == "high"
    assert "Not configured" in created["notificationStatus"]


def test_create_care_task_clinical_safety_guardrails(client):
    """
    CRITICAL: Validates clinical safety boundaries.
    Tasks MUST represent follow-up actions, NOT autonomous diagnoses or medication/dosage changes.
    """
    # 1. Reject autonomous prescription / dosage modification
    prohibited_prescriptions = [
        {"title": "Increase dosage of Metformin to 1000 mg daily"},
        {"title": "Prescribe 500mg Amoxicillin for respiratory infection"},
        {"title": "Stop taking blood pressure medication immediately"},
        {"title": "Alter dose of insulin glargine to 20 units"},
    ]
    for bad_payload in prohibited_prescriptions:
        res = client.post("/api/v1/care-tasks", json=bad_payload)
        assert res.status_code == 422
        assert "medication" in res.json()["detail"].lower() or "prohibited" in res.json()["detail"].lower()

    # 2. Reject autonomous clinical diagnosis
    prohibited_diagnoses = [
        {"title": "Diagnose patient with Type 2 Diabetes Mellitus"},
        {"title": "Confirm diagnosis of Stage 2 Hypertension"},
        {"title": "Patient has clinical cardiovascular disease"},
    ]
    for bad_payload in prohibited_diagnoses:
        res = client.post("/api/v1/care-tasks", json=bad_payload)
        assert res.status_code == 422
        assert "diagnos" in res.json()["detail"].lower() or "prohibited" in res.json()["detail"].lower()

    # 3. Permitted follow-up consultations (e.g. requesting review from physician) MUST succeed
    permitted_consultations = [
        {"title": "Consult doctor regarding dosage review"},
        {"title": "Discuss blood pressure reading with treating physician"},
        {"title": "Request clinician review for prescription query"},
    ]
    for safe_payload in permitted_consultations:
        res = client.post("/api/v1/care-tasks", json=safe_payload)
        assert res.status_code == 201
        assert res.json()["id"].startswith("TSK-")


def test_create_care_task_optional_due_dates(client):
    """Verifies due date parsing flexibility and optionality."""
    # 1. Task with no due date (optional)
    no_due_payload = {
        "title": "Request previous lab records from Pune facility",
        "taskType": "record_request",
    }
    res_no_due = client.post("/api/v1/care-tasks", json=no_due_payload)
    assert res_no_due.status_code == 201
    task_no_due = res_no_due.json()
    assert task_no_due["due"] is None
    assert task_no_due["dueDateIso"] is None

    # 2. Task with ISO date string (YYYY-MM-DD)
    iso_payload = {
        "title": "Follow up on complete blood count trend",
        "due": "2025-12-10",
    }
    res_iso = client.post("/api/v1/care-tasks", json=iso_payload)
    assert res_iso.status_code == 201
    assert res_iso.json()["due"] == "10 Dec 2025"
    assert "2025-12-10" in res_iso.json()["dueDateIso"]

    # 3. Invalid date format returns 422
    bad_date_payload = {
        "title": "Repeat liver function panel",
        "due": "not-a-valid-date-string",
    }
    res_bad_date = client.post("/api/v1/care-tasks", json=bad_date_payload)
    assert res_bad_date.status_code == 422
    assert "due date" in res_bad_date.json()["detail"].lower()


def test_create_care_task_linked_to_entities(client):
    """Verifies linking care tasks to existing medical records and reports."""
    payload = {
        "title": "Confirm repeat fasting blood glucose with laboratory",
        "recordId": "SR-1048",
        "due": "05 Nov 2025",
    }
    response = client.post("/api/v1/care-tasks", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert data["linkedEntities"]["recordId"] == "SR-1048"
    assert data["linkedEntities"]["recordName"] == "Fasting Plasma Glucose"

    # Non-existent record ID -> 404
    bad_rec_payload = {
        "title": "Confirm repeat test",
        "recordId": "SR-99999",
    }
    res_bad_rec = client.post("/api/v1/care-tasks", json=bad_rec_payload)
    assert res_bad_rec.status_code == 404
    assert "medical record" in res_bad_rec.json()["detail"].lower()

    # Non-existent report document ID -> 404
    bad_rep_payload = {
        "title": "Confirm repeat test",
        "reportId": "REP-99999",
    }
    res_bad_rep = client.post("/api/v1/care-tasks", json=bad_rep_payload)
    assert res_bad_rep.status_code == 404
    assert "report document" in res_bad_rep.json()["detail"].lower()


def test_update_care_task_status_lifecycle(client):
    """Verifies status transitions, completion timestamping, and reason logging."""
    # Create task
    task = client.post("/api/v1/care-tasks", json={"title": "Repeat serum creatinine test"}).json()
    task_id = task["id"]

    # Mark Scheduled
    res_sched = client.patch(f"/api/v1/care-tasks/{task_id}/status", json={"status": "Scheduled"})
    assert res_sched.status_code == 200
    assert res_sched.json()["status"] == "Scheduled"
    assert res_sched.json()["completedAt"] is None

    # Mark Completed
    res_comp = client.patch(
        f"/api/v1/care-tasks/{task_id}/status",
        json={"status": "Completed", "reason": "Patient completed repeat blood draw at verified lab."},
    )
    assert res_comp.status_code == 200
    assert res_comp.json()["status"] == "Completed"
    assert res_comp.json()["completedAt"] is not None
    assert "Patient completed" in res_comp.json()["reason"]

    # Mark Not Applicable
    res_na = client.patch(f"/api/v1/care-tasks/{task_id}/status", json={"status": "Not Applicable"})
    assert res_na.status_code == 200
    assert res_na.json()["status"] == "Not Applicable"
    assert res_na.json()["completedAt"] is None

    # Invalid status -> 422
    res_inv = client.patch(f"/api/v1/care-tasks/{task_id}/status", json={"status": "ArbitraryInvalidStatus"})
    assert res_inv.status_code == 422
    assert "allowed statuses" in res_inv.json()["detail"].lower()


def test_update_care_task_details(client):
    """Verifies editing task properties and clinical safety on edits."""
    task = client.post("/api/v1/care-tasks", json={"title": "Follow-up consultation"}).json()
    task_id = task["id"]

    # Valid edit
    update_payload = {
        "title": "Follow-up consultation with Dr. Mehta",
        "due": "30 Nov 2025",
        "priority": "high",
        "expected": "Signed consultation note",
    }
    res_up = client.patch(f"/api/v1/care-tasks/{task_id}", json=update_payload)
    assert res_up.status_code == 200
    updated = res_up.json()
    assert updated["title"] == "Follow-up consultation with Dr. Mehta"
    assert updated["due"] == "30 Nov 2025"
    assert updated["priority"] == "high"

    # Attempting to update title with autonomous prescription modification -> 422
    bad_edit = {"title": "Increase dosage to 850mg"}
    res_bad_edit = client.patch(f"/api/v1/care-tasks/{task_id}", json=bad_edit)
    assert res_bad_edit.status_code == 422


def test_delete_care_task(client):
    """Verifies deleting a care task."""
    task = client.post("/api/v1/care-tasks", json={"title": "Temporary task to delete"}).json()
    task_id = task["id"]

    res_del = client.delete(f"/api/v1/care-tasks/{task_id}")
    assert res_del.status_code == 200
    assert res_del.json()["success"] is True

    # Subsequent fetch should be 404
    res_get = client.get(f"/api/v1/care-tasks/{task_id}")
    assert res_get.status_code == 404


def test_create_task_from_lab_verification_finding(client, db_session):
    """
    Verifies linking a care task to a laboratory verification check finding.
    Where a verification check is performed, generate a grounded follow-up task.
    """
    # 1. Run a laboratory verification check
    verif_res = client.post(
        "/api/v1/verify/laboratory",
        json={
            "laboratoryName": "CarePlus Diagnostic Center",
            "city": "Mumbai",
            "testName": "Specialized Genetic Sequencing",
            "recordId": "SR-1022",
        },
    )
    assert verif_res.status_code == 200

    # Retrieve the recorded log from DB
    lab_log = db_session.query(LabVerificationLog).filter(
        LabVerificationLog.queried_lab_name == "CarePlus Diagnostic Center"
    ).order_by(LabVerificationLog.created_at.desc()).first()
    assert lab_log is not None

    # 2. Create follow-up task from this verification finding
    task_res = client.post(
        "/api/v1/care-tasks/from-verification",
        json={
            "verificationType": "laboratory",
            "verificationLogId": lab_log.id,
            "due": "15 Nov 2025",
            "priority": "high",
            "customNotes": "Request accreditation scope certificate from laboratory administrator.",
        },
    )
    assert task_res.status_code == 201
    task_data = task_res.json()

    assert task_data["id"].startswith("TSK-")
    assert "laboratory" in task_data["title"].lower() or "clarify" in task_data["title"].lower()
    assert task_data["linkedEntities"]["labVerificationId"] == lab_log.id
    assert task_data["priority"] == "high"
    assert "NABL" in task_data["source"]


def test_create_task_from_medicine_verification_finding(client, db_session):
    """
    Verifies linking a care task to a medicine packaging verification finding.
    Frames task as a pharmacist consultation, not an autonomous medication alteration.
    """
    # 1. Run medicine verification check
    med_res = client.post(
        "/api/v1/verify/medicine",
        json={
            "brandName": "Glycomet",
            "dosageForm": "Syrup",
            "activeIngredient": "Metformin Hydrochloride",
        },
    )
    assert med_res.status_code == 200

    # Retrieve recorded log from DB
    med_log = db_session.query(MedicineVerificationLog).filter(
        MedicineVerificationLog.queried_brand == "Glycomet"
    ).order_by(MedicineVerificationLog.created_at.desc()).first()
    assert med_log is not None

    # 2. Create follow-up care task from finding
    task_res = client.post(
        "/api/v1/care-tasks/from-verification",
        json={
            "verificationType": "medicine",
            "verificationLogId": med_log.id,
            "due": "08 Nov 2025",
            "priority": "high",
        },
    )
    assert task_res.status_code == 201
    task_data = task_res.json()

    assert task_data["id"].startswith("TSK-")
    assert "pharmacist" in task_data["title"].lower() or "formulation" in task_data["title"].lower()
    assert task_data["linkedEntities"]["medicineVerificationId"] == med_log.id
    assert task_data["priority"] == "high"


def test_notifications_endpoint_disclosure(client):
    """
    Truthful disclosure: Ensures backend does not claim push/SMS notifications are delivered
    when no live integration exists.
    """
    response = client.get("/api/v1/care-tasks/notifications/status")
    assert response.status_code == 200
    data = response.json()
    assert data["integrationEnabled"] is False
    assert data["provider"] is None
    assert data["deliveryChannels"] == []
    assert "Not configured" in data["notificationStatus"]
    assert "No external delivery integration" in data["notice"]


def test_dashboard_metrics_reflect_care_tasks(client):
    """Verifies dashboard overview dynamically reflects pending care tasks."""
    response = client.get("/api/v1/dashboard/overview")
    assert response.status_code == 200
    data = response.json()
    assert data["pendingCareTasks"] >= 2
    assert data["nextCareTaskDueDate"] != ""
