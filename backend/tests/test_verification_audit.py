import pytest
from sqlalchemy.orm import Session
from starlette.testclient import TestClient

from backend.app.models import (
    VerificationAuditRecord,
    LabVerificationLog,
    MedicineVerificationLog,
    AuditEvent,
)
from backend.app.services.verification_audit_service import (
    verify_verification_audit_chain,
    GENESIS_HASH,
)


@pytest.fixture(autouse=True)
def clean_audit_records_after_test(db_session: Session):
    """Ensure non-seeded audit and verification records created during tests are cleaned up both before and after."""
    db_session.query(VerificationAuditRecord).delete()
    db_session.query(LabVerificationLog).delete()
    db_session.query(MedicineVerificationLog).delete()
    db_session.query(AuditEvent).filter(AuditEvent.id.like("EVT-%")).delete()
    db_session.commit()
    yield
    db_session.query(VerificationAuditRecord).delete()
    db_session.query(LabVerificationLog).delete()
    db_session.query(MedicineVerificationLog).delete()
    db_session.query(AuditEvent).filter(AuditEvent.id.like("EVT-%")).delete()
    db_session.commit()


# ============================================================================
# 1. Laboratory Verification Audit Recording Tests
# ============================================================================

def test_lab_verification_successful_audit_recorded(client: TestClient, db_session: Session):
    """A successful lab verification check creates a cryptographically hash-linked audit record."""
    response = client.post(
        "/api/v1/verify/laboratory",
        json={
            "laboratoryName": "Metropolis Healthcare Ltd.",
            "city": "Pune",
            "certificateNumber": "MC-2104",
            "discipline": "Clinical Biochemistry",
            "testName": "Lipid Profile",
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "verified"
    audit_id = data.get("verificationAuditId")
    assert audit_id is not None
    assert audit_id.startswith("VAR-")

    # Verify audit record in database
    audit_rec = db_session.query(VerificationAuditRecord).filter(VerificationAuditRecord.id == audit_id).first()
    assert audit_rec is not None
    assert audit_rec.entity_type == "laboratory"
    assert audit_rec.check_type == "accreditation_and_scope"
    assert audit_rec.status == "verified"
    assert audit_rec.has_source_error is False
    assert audit_rec.previous_record_hash == GENESIS_HASH
    assert len(audit_rec.record_hash) == 64
    assert audit_rec.verification_status == "hash_linked"
    assert "MC-2104" in audit_rec.entity_identifier or "Metropolis" in audit_rec.entity_identifier


def test_lab_verification_mismatched_scope_audit_recorded(client: TestClient, db_session: Session):
    """An out-of-scope lab test creates a mismatch audit record with structured findings."""
    response = client.post(
        "/api/v1/verify/laboratory",
        json={
            "laboratoryName": "Aster Diagnostics",
            "city": "Pune",
            "certificateNumber": "MC-3088",
            "testName": "Histopathology Biopsy",
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "mismatch"
    assert data["testScopeStatus"] == "not_verified"
    audit_id = data.get("verificationAuditId")
    assert audit_id is not None

    audit_rec = db_session.query(VerificationAuditRecord).filter(VerificationAuditRecord.id == audit_id).first()
    assert audit_rec is not None
    assert audit_rec.status == "mismatch"
    assert "Requested Test Scope Unverified" in audit_rec.verdict
    assert "Histopathology Biopsy" in audit_rec.input_payload


def test_lab_verification_inconclusive_audit_recorded(client: TestClient, db_session: Session):
    """Missing lab identifiers result in an inconclusive audit record without fabricating data."""
    response = client.post(
        "/api/v1/verify/laboratory",
        json={
            "laboratoryName": "",
            "certificateNumber": "",
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "inconclusive"
    audit_id = data.get("verificationAuditId")
    assert audit_id is not None

    audit_rec = db_session.query(VerificationAuditRecord).filter(VerificationAuditRecord.id == audit_id).first()
    assert audit_rec is not None
    assert audit_rec.status == "inconclusive"
    assert audit_rec.match_confidence == 0.0


def test_lab_verification_failed_source_audit_recorded(client: TestClient, db_session: Session):
    """A simulated source failure is accurately recorded with source error details."""
    response = client.post(
        "/api/v1/verify/laboratory",
        json={
            "laboratoryName": "Metropolis Healthcare Ltd.",
            "simulateSourceFailure": True,
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "inconclusive"
    audit_id = data.get("verificationAuditId")
    assert audit_id is not None

    audit_rec = db_session.query(VerificationAuditRecord).filter(VerificationAuditRecord.id == audit_id).first()
    assert audit_rec is not None
    assert audit_rec.has_source_error is True
    assert audit_rec.source_error_details is not None
    assert "SOURCE_UNAVAILABLE" in audit_rec.source_error_details
    assert "timed out or failed" in audit_rec.source_error_details


# ============================================================================
# 2. Medicine Verification Audit Recording Tests
# ============================================================================

def test_medicine_verification_successful_audit_recorded(client: TestClient, db_session: Session):
    """A verified medicine check records full composition findings in audit history."""
    response = client.post(
        "/api/v1/verify/medicine",
        json={
            "brandName": "Glycomet 500",
            "activeIngredient": "Metformin Hydrochloride",
            "strength": "500 mg",
            "dosageForm": "Immediate-release uncoated tablet IP",
            "manufacturer": "USV Private Limited",
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "verified"
    audit_id = data.get("verificationAuditId")
    assert audit_id is not None
    assert audit_id.startswith("VAR-")

    audit_rec = db_session.query(VerificationAuditRecord).filter(VerificationAuditRecord.id == audit_id).first()
    assert audit_rec is not None
    assert audit_rec.entity_type == "medicine"
    assert audit_rec.check_type == "composition_and_regulatory"
    assert audit_rec.status == "verified"
    assert audit_rec.has_source_error is False
    assert "Glycomet" in audit_rec.entity_identifier


def test_medicine_verification_mismatched_audit_recorded(client: TestClient, db_session: Session):
    """A strength conflict records a mismatch audit entry distinguishing mismatch from fraud."""
    response = client.post(
        "/api/v1/verify/medicine",
        json={
            "brandName": "Augmentin 625 Duo",
            "activeIngredient": "Amoxicillin and Potassium Clavulanate",
            "strength": "1000 mg",  # Mismatched strength
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "mismatch"
    audit_id = data.get("verificationAuditId")
    assert audit_id is not None

    audit_rec = db_session.query(VerificationAuditRecord).filter(VerificationAuditRecord.id == audit_id).first()
    assert audit_rec is not None
    assert audit_rec.status == "mismatch"
    assert "strength" in audit_rec.verdict.lower()


def test_medicine_verification_inconclusive_audit_recorded(client: TestClient, db_session: Session):
    """Incomplete medicine input records an inconclusive check."""
    response = client.post(
        "/api/v1/verify/medicine",
        json={
            "brandName": "",
            "activeIngredient": "",
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "inconclusive"
    audit_id = data.get("verificationAuditId")
    assert audit_id is not None

    audit_rec = db_session.query(VerificationAuditRecord).filter(VerificationAuditRecord.id == audit_id).first()
    assert audit_rec is not None
    assert audit_rec.status == "inconclusive"


def test_medicine_verification_failed_source_audit_recorded(client: TestClient, db_session: Session):
    """A simulated regulatory catalogue error records has_source_error=True with code."""
    response = client.post(
        "/api/v1/verify/medicine",
        json={
            "brandName": "Telma 40",
            "simulateSourceFailure": True,
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "inconclusive"
    audit_id = data.get("verificationAuditId")
    assert audit_id is not None

    audit_rec = db_session.query(VerificationAuditRecord).filter(VerificationAuditRecord.id == audit_id).first()
    assert audit_rec is not None
    assert audit_rec.has_source_error is True
    assert "SOURCE_UNAVAILABLE" in audit_rec.source_error_details


# ============================================================================
# 3. Audit Retrieval API Endpoint Tests
# ============================================================================

def test_list_verification_audit_records(client: TestClient):
    """Tests the GET /api/v1/verify/audit-records endpoint and summary counts."""
    # Perform several checks
    client.post("/api/v1/verify/laboratory", json={"laboratoryName": "Metropolis Healthcare Ltd."})
    client.post("/api/v1/verify/medicine", json={"brandName": "Glycomet 500"})
    client.post("/api/v1/verify/laboratory", json={"laboratoryName": "Aster Diagnostics", "testName": "Biopsy"})
    client.post("/api/v1/verify/medicine", json={"brandName": "UnknownBrandXYZ"})

    response = client.get("/api/v1/verify/audit-records")
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 4
    assert len(data["records"]) == 4
    assert data["verifiedCount"] >= 1
    assert data["mismatchCount"] >= 1


def test_audit_records_filtering(client: TestClient):
    """Tests filtering audit records by entity_type, status, has_error, and search query."""
    # Lab check (verified)
    client.post("/api/v1/verify/laboratory", json={"laboratoryName": "Metropolis Healthcare Ltd."})
    # Medicine check (verified)
    client.post("/api/v1/verify/medicine", json={"brandName": "Glycomet 500"})
    # Failed source check
    client.post("/api/v1/verify/laboratory", json={"laboratoryName": "Metropolis Healthcare Ltd.", "simulateSourceFailure": True})

    # 1. Filter by entity_type=medicine
    res_med = client.get("/api/v1/verify/audit-records?entity_type=medicine")
    assert res_med.status_code == 200
    data_med = res_med.json()
    assert data_med["total"] == 1
    assert data_med["records"][0]["entityType"] == "medicine"

    # 2. Filter by entity_type=laboratory
    res_lab = client.get("/api/v1/verify/audit-records?entity_type=laboratory")
    assert res_lab.status_code == 200
    assert res_lab.json()["total"] == 2

    # 3. Filter by has_error=true
    res_err = client.get("/api/v1/verify/audit-records?has_error=true")
    assert res_err.status_code == 200
    data_err = res_err.json()
    assert data_err["total"] == 1
    assert data_err["records"][0]["errorDetails"]["hasSourceError"] is True

    # 4. Filter by query
    res_q = client.get("/api/v1/verify/audit-records?query=Glycomet")
    assert res_q.status_code == 200
    assert res_q.json()["total"] == 1


def test_audit_records_pagination_and_sorting(client: TestClient):
    """Tests pagination (limit, offset) and sort order parameter validation."""
    client.post("/api/v1/verify/laboratory", json={"laboratoryName": "Metropolis Healthcare Ltd."})
    client.post("/api/v1/verify/medicine", json={"brandName": "Glycomet 500"})
    client.post("/api/v1/verify/medicine", json={"brandName": "Telma 40"})

    # Page 1 (limit 2)
    res_p1 = client.get("/api/v1/verify/audit-records?limit=2&offset=0&sort=desc")
    assert res_p1.status_code == 200
    data_p1 = res_p1.json()
    assert data_p1["total"] == 3
    assert len(data_p1["records"]) == 2
    assert data_p1["limit"] == 2
    assert data_p1["offset"] == 0

    # Page 2 (offset 2)
    res_p2 = client.get("/api/v1/verify/audit-records?limit=2&offset=2&sort=desc")
    assert res_p2.status_code == 200
    data_p2 = res_p2.json()
    assert len(data_p2["records"]) == 1

    # Ascending sort
    res_asc = client.get("/api/v1/verify/audit-records?sort=asc")
    assert res_asc.status_code == 200

    # Invalid sort
    res_bad = client.get("/api/v1/verify/audit-records?sort=sideways")
    assert res_bad.status_code == 400


def test_get_single_verification_audit_record(client: TestClient):
    """Tests fetching a single audit record by its VAR- ID."""
    verify_res = client.post(
        "/api/v1/verify/laboratory",
        json={"laboratoryName": "Metropolis Healthcare Ltd."},
    )
    audit_id = verify_res.json()["verificationAuditId"]

    # Valid fetch
    res = client.get(f"/api/v1/verify/audit-records/{audit_id}")
    assert res.status_code == 200
    data = res.json()
    assert data["id"] == audit_id
    assert data["entityType"] == "laboratory"
    assert data["status"] == "verified"
    assert len(data["recordHash"]) == 64
    assert len(data["findings"]["checks"]) > 0

    # 404 for unknown ID
    res_404 = client.get("/api/v1/verify/audit-records/VAR-NONEXISTENT")
    assert res_404.status_code == 404


# ============================================================================
# 4. Cryptographic Hash Chain and Tamper-Evidence Tests
# ============================================================================

def test_audit_chain_valid_when_untampered(client: TestClient):
    """The audit chain passes cryptographic validation when all sequential records are intact."""
    client.post("/api/v1/verify/laboratory", json={"laboratoryName": "Metropolis Healthcare Ltd."})
    client.post("/api/v1/verify/medicine", json={"brandName": "Glycomet 500"})
    client.post("/api/v1/verify/medicine", json={"brandName": "Telma 40"})

    res = client.get("/api/v1/verify/audit-records/chain/verify")
    assert res.status_code == 200
    data = res.json()
    assert data["chainValid"] is True
    assert data["totalRecordsEvaluated"] == 3
    assert data["tamperedRecordId"] is None
    assert "cryptographically validated" in data["message"].lower()
    assert "local SQLite" in data["storageProtection"]


def test_audit_chain_detects_tampered_record(client: TestClient, db_session: Session):
    """Artificially modifying a record's status in the database triggers chain invalidation."""
    client.post("/api/v1/verify/laboratory", json={"laboratoryName": "Metropolis Healthcare Ltd."})
    client.post("/api/v1/verify/medicine", json={"brandName": "Glycomet 500"})
    client.post("/api/v1/verify/medicine", json={"brandName": "Telma 40"})

    # Fetch the middle record and tamper with its status directly in the DB
    records = db_session.query(VerificationAuditRecord).order_by(VerificationAuditRecord.created_at.asc()).all()
    assert len(records) == 3
    target_record = records[1]
    tampered_id = target_record.id

    # Tamper with the record's status directly in the DB
    target_record.status = "mismatch"
    db_session.commit()

    # Now verify the chain
    res = client.get("/api/v1/verify/audit-records/chain/verify")
    assert res.status_code == 200
    data = res.json()
    assert data["chainValid"] is False
    assert data["tamperedRecordId"] == tampered_id
    assert data["tamperedIndex"] == 1
    assert "Content integrity mismatch" in data["message"]
