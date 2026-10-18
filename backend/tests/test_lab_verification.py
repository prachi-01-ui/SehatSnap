import pytest
import datetime
from backend.app.schemas import LabVerificationRequest
from backend.app.services.lab_verification import (
    verify_laboratory_identity_and_scope,
    SYNTHETIC_NABL_REGISTRY,
)
from backend.app.models import LabVerificationLog, AuditEvent, MedicalRecord


# ============================================================================
# UNIT TESTS: Verification Service Logic
# ============================================================================

def test_verified_lab_and_test_scope():
    """Valid lab identity and in-scope test should return verified status."""
    req = LabVerificationRequest(
        laboratoryName="Metropolis Healthcare Ltd.",
        city="Pune, Maharashtra",
        certificateNumber="MC-2104",
        discipline="Clinical Biochemistry",
        testName="Fasting Plasma Glucose",
    )
    res = verify_laboratory_identity_and_scope(req)

    assert res.status == "verified"
    assert res.accreditationStatus == "verified"
    assert res.testScopeStatus == "verified"
    assert res.matchConfidence >= 0.90
    assert res.laboratory is not None
    assert res.laboratory.certificateNumber == "MC-2104"
    assert res.laboratory.name == "Metropolis Healthcare Ltd."
    assert res.sourceReference.isDemonstrationDataset is True
    assert "NABL" in res.sourceReference.authority
    assert res.timestamp is not None

    items = [c.item for c in res.checks]
    assert "Laboratory identity" in items
    assert "Location" in items
    assert "Accreditation status" in items
    assert "Certificate validity" in items
    assert "Requested scope" in items


def test_distinguish_accreditation_from_scope_out_of_scope():
    """
    Lab accreditation status should be verified (Active),
    while test-scope verification evaluates to not_verified when
    the requested test is outside the accredited scope.
    """
    req = LabVerificationRequest(
        laboratoryName="Aster Diagnostics",
        city="Pune, Maharashtra",
        certificateNumber="MC-3088",
        discipline="Histopathology",
        testName="Bone Marrow Biopsy",
    )
    res = verify_laboratory_identity_and_scope(req)

    # Accreditation itself is Active and verified
    assert res.accreditationStatus == "verified"
    # But the specific test scope is NOT in Aster's accredited scope
    assert res.testScopeStatus == "not_verified"
    # Overall status flags scope mismatch
    assert res.status == "mismatch"
    assert "Scope Unverified" in res.verdict or "out of scope" in res.verdict.lower()

    # Verify check items reflect the distinction
    scope_check = next(c for c in res.checks if c.item == "Requested scope")
    assert scope_check.status == "warning"
    assert "not cataloged in the accredited scope" in scope_check.details

    accreditation_check = next(c for c in res.checks if c.item == "Accreditation status")
    assert accreditation_check.status == "verified"


def test_distinguish_accreditation_from_scope_unspecified():
    """When no test name or discipline is specified, accreditation is verified but scope is unspecified."""
    req = LabVerificationRequest(
        laboratoryName="Metropolis Healthcare Ltd.",
        certificateNumber="MC-2104",
    )
    res = verify_laboratory_identity_and_scope(req)

    assert res.accreditationStatus == "verified"
    assert res.testScopeStatus == "unspecified"
    assert res.status == "verified"
    assert "Scope Unspecified" in res.verdict

    scope_check = next(c for c in res.checks if c.item == "Requested scope")
    assert scope_check.status == "review"
    assert "No specific test name or discipline queried" in scope_check.details


def test_expired_accreditation():
    """Expired accreditation should be reported with warning and not_verified status."""
    req = LabVerificationRequest(
        laboratoryName="CarePlus Labs",
        certificateNumber="MC-1955",
        city="Mumbai, Maharashtra",
    )
    res = verify_laboratory_identity_and_scope(req)

    assert res.accreditationStatus == "expired"
    assert res.status == "not_verified"
    assert "Expired" in res.verdict

    val_check = next(c for c in res.checks if c.item == "Certificate validity")
    assert val_check.status == "warning"
    assert "Expired" in val_check.details


def test_suspended_accreditation():
    """Suspended accreditation should be flagged with warning."""
    req = LabVerificationRequest(
        laboratoryName="Apollo Diagnostics",
        certificateNumber="MC-4401",
    )
    res = verify_laboratory_identity_and_scope(req)

    assert res.accreditationStatus == "suspended"
    assert res.status == "not_verified"
    assert "Suspended" in res.verdict


def test_certificate_and_name_mismatch():
    """Querying certificate MC-2104 (Metropolis) with a conflicting lab name should detect mismatch."""
    req = LabVerificationRequest(
        laboratoryName="Apollo Diagnostics",
        certificateNumber="MC-2104",
    )
    res = verify_laboratory_identity_and_scope(req)

    assert res.status == "mismatch"
    assert res.accreditationStatus == "mismatch"
    assert "Mismatch" in res.verdict

    id_check = next(c for c in res.checks if c.item == "Laboratory identity")
    assert id_check.status == "warning"
    assert "differs from registered entity" in id_check.details


def test_location_mismatch():
    """Location mismatch for a recognized facility should be flagged as mismatch."""
    req = LabVerificationRequest(
        laboratoryName="Metropolis Healthcare Ltd.",
        certificateNumber="MC-2104",
        city="Chennai, Tamil Nadu",
    )
    res = verify_laboratory_identity_and_scope(req)

    assert res.status == "mismatch"
    assert "Location Mismatch" in res.verdict

    loc_check = next(c for c in res.checks if c.item == "Location")
    assert loc_check.status == "warning"
    assert "differs from registered site" in loc_check.details


def test_unknown_lab_not_verified_without_fraud_accusation():
    """
    Uncataloged facility returns not_verified with explicit non-fraud disclaimer,
    ensuring missing demo data is never treated as fraud or forgery.
    """
    req = LabVerificationRequest(
        laboratoryName="Neighborhood Clinical Diagnostic Care",
        certificateNumber="MC-9999",
    )
    res = verify_laboratory_identity_and_scope(req)

    assert res.status == "not_verified"
    assert res.accreditationStatus == "not_verified"
    assert res.laboratory is None
    assert "Not Verified in Demonstration Dataset" in res.verdict

    # Check non-fraud guarantee
    assert "fraudulent" in res.evidenceLimitations.lower()
    assert "missing records do not indicate unaccredited status or fraudulent activity" in res.evidenceLimitations
    missing_notice = next(c for c in res.checks if c.item == "Missing data notice")
    assert "Absence from demonstration records must not be interpreted as lack of official accreditation" in missing_notice.details


def test_missing_data_inconclusive():
    """When neither lab name nor certificate is provided, verdict is inconclusive."""
    req = LabVerificationRequest()
    res = verify_laboratory_identity_and_scope(req)

    assert res.status == "inconclusive"
    assert res.accreditationStatus == "inconclusive"
    assert res.testScopeStatus == "inconclusive"
    assert res.laboratory is None
    assert "Inconclusive" in res.verdict
    assert "Insufficient data supplied" in res.evidenceLimitations


def test_source_failure_simulation():
    """When external source failure is simulated, returns inconclusive with diagnostic warnings."""
    req = LabVerificationRequest(
        laboratoryName="Metropolis Healthcare Ltd.",
        simulateSourceFailure=True,
    )
    res = verify_laboratory_identity_and_scope(req)

    assert res.status == "inconclusive"
    assert res.accreditationStatus == "inconclusive"
    assert res.testScopeStatus == "inconclusive"
    assert "Unavailable" in res.verdict

    conn_check = next(c for c in res.checks if c.item == "Source connectivity")
    assert conn_check.status == "warning"
    assert "timed out or failed" in conn_check.details


# ============================================================================
# API TESTS: Endpoints and DB Integration
# ============================================================================

def test_api_verify_laboratory_endpoint_success(client):
    """POST /api/v1/verify/laboratory returns 200 with verified response matching API contract."""
    payload = {
        "laboratoryName": "Metropolis Healthcare Ltd.",
        "city": "Pune, Maharashtra",
        "certificateNumber": "MC-2104",
        "discipline": "Clinical Biochemistry",
    }
    response = client.post("/api/v1/verify/laboratory", json=payload)
    assert response.status_code == 200
    data = response.json()

    assert data["status"] == "verified"
    assert data["accreditationStatus"] == "verified"
    assert data["testScopeStatus"] == "verified"
    assert data["matchConfidence"] >= 0.90
    assert data["laboratory"]["name"] == "Metropolis Healthcare Ltd."
    assert data["laboratory"]["certificateNumber"] == "MC-2104"
    assert len(data["checks"]) >= 5
    assert data["sourceReference"]["isDemonstrationDataset"] is True
    assert "NABL" in data["sourceReference"]["authority"]
    assert "timestamp" in data


def test_api_verify_laboratory_form_aliases(client):
    """POST /api/v1/verify/laboratory accepts frontend form field aliases ('lab', 'certificate', 'test')."""
    payload = {
        "lab": "Metropolis Healthcare Ltd.",
        "city": "Pune, Maharashtra",
        "certificate": "MC-2104",
        "test": "Fasting Plasma Glucose",
    }
    response = client.post("/api/v1/verify/laboratory", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "verified"
    assert data["laboratory"]["certificateNumber"] == "MC-2104"


def test_api_verify_laboratory_scope_mismatch(client):
    """POST /api/v1/verify/laboratory distinguishes active lab from out-of-scope test."""
    payload = {
        "laboratoryName": "Aster Diagnostics",
        "certificateNumber": "MC-3088",
        "discipline": "Histopathology",
    }
    response = client.post("/api/v1/verify/laboratory", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "mismatch"
    assert data["accreditationStatus"] == "verified"
    assert data["testScopeStatus"] == "not_verified"


def test_api_verify_laboratory_missing_data(client):
    """POST /api/v1/verify/laboratory with empty input returns 200 with inconclusive status."""
    response = client.post("/api/v1/verify/laboratory", json={})
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "inconclusive"
    assert data["laboratory"] is None


def test_api_verify_laboratory_simulated_source_failure(client):
    """POST /api/v1/verify/laboratory with simulateSourceFailure=true returns inconclusive."""
    payload = {
        "laboratoryName": "Metropolis Healthcare Ltd.",
        "simulateSourceFailure": True,
    }
    response = client.post("/api/v1/verify/laboratory", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "inconclusive"
    assert any(c["item"] == "Source connectivity" for c in data["checks"])


def test_api_verify_with_record_linkage(client, db_session):
    """POST /api/v1/verify/laboratory with recordId links audit event and updates record status."""
    # Create isolated test record to avoid mutating shared seeded records
    test_record = MedicalRecord(
        id="SR-LINK-TEST",
        patient_id="AN-PATIENT-01",
        name="Fasting Plasma Glucose",
        date_display="19 Oct 2025",
        laboratory_name="Metropolis Healthcare Ltd.",
        value_display="100",
        unit="mg/dL",
        reference_range="70–99 mg/dL",
        status="Needs review",
        source="PDF Extracted",
    )
    db_session.add(test_record)
    db_session.commit()

    payload = {
        "laboratoryName": "Metropolis Healthcare Ltd.",
        "certificateNumber": "MC-2104",
        "discipline": "Clinical Biochemistry",
        "recordId": "SR-LINK-TEST",
    }
    response = client.post("/api/v1/verify/laboratory", json=payload)
    assert response.status_code == 200
    data = response.json()

    assert data["status"] == "verified"
    assert data["auditEventId"] is not None
    assert data["auditEventId"].startswith("EVT-")

    # Verify audit event in database
    audit = db_session.query(AuditEvent).filter(AuditEvent.id == data["auditEventId"]).first()
    assert audit is not None
    assert audit.event_type == "Lab verification check"

    # Verify medical record updated to Verified
    rec = db_session.query(MedicalRecord).filter(MedicalRecord.id == "SR-LINK-TEST").first()
    assert rec is not None
    assert rec.status == "Verified"

    # Verify LabVerificationLog written
    log = db_session.query(LabVerificationLog).filter(LabVerificationLog.medical_record_id == "SR-LINK-TEST").first()
    assert log is not None
    assert log.overall_status == "verified"



def test_api_list_demo_labs(client):
    """GET /api/v1/verify/laboratory/demo-labs returns list of available synthetic labs."""
    response = client.get("/api/v1/verify/laboratory/demo-labs")
    assert response.status_code == 200
    labs = response.json()
    assert len(labs) >= 5
    cert_numbers = [l["certificateNumber"] for l in labs]
    assert "MC-2104" in cert_numbers
    assert "MC-3088" in cert_numbers
    assert "MC-1955" in cert_numbers
