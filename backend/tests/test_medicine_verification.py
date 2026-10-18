import pytest
import datetime
from backend.app.schemas import MedicineVerificationRequest
from backend.app.services.medicine_verification import (
    verify_medicine_identity_and_composition,
    SYNTHETIC_SUGAM_REGISTRY,
)
from backend.app.models import MedicineVerificationLog, AuditEvent, MedicalRecord


# ============================================================================
# UNIT TESTS: Medicine Verification Service Logic
# ============================================================================

def test_verified_medicine_exact_match():
    """Matching brand, active ingredient, strength, formulation, and manufacturer returns verified."""
    req = MedicineVerificationRequest(
        brandName="Glycomet 500",
        activeIngredient="Metformin Hydrochloride",
        strength="500 mg",
        dosageForm="Immediate-release uncoated tablet IP",
        manufacturer="USV Private Limited",
        route="Oral",
    )
    res = verify_medicine_identity_and_composition(req)

    assert res.status == "verified"
    assert res.matchConfidence >= 0.90
    assert res.product is not None
    assert res.product.brand == "Glycomet 500"
    assert res.product.standardizedTitle == "Metformin Hydrochloride Tablets IP"
    assert res.sourceReference.isDemonstrationDataset is True
    assert "CDSCO/SUGAM" in res.sourceReference.authority
    assert res.timestamp is not None

    items = {c.item: c for c in res.checks}
    assert items["Active ingredient"].status == "verified"
    assert items["Strength"].status == "verified"
    assert items["Dosage form"].status == "verified"
    assert items["Manufacturer"].status == "verified"
    assert items["Regulatory information"].status == "info"

    # Safety disclaimer guarantee
    assert "does not prescribe" in res.disclaimer.lower()
    assert "does not prescribe" in res.disclaimer


def test_verified_medicine_partial_formulation_human_review():
    """
    When packaging indicates generic dosage form 'Tablet' without release-type detail,
    it returns 'Possible Match — Human Review' with review banner and 88% confidence.
    """
    req = MedicineVerificationRequest(
        brandName="Glycomet 500",
        activeIngredient="Metformin Hydrochloride",
        strength="500 mg",
        dosageForm="Tablet",
        manufacturer="USV Private Limited",
        route="Oral",
    )
    res = verify_medicine_identity_and_composition(req)

    assert res.status == "verified"
    assert res.verdict == "Possible Match — Human Review"
    assert res.matchConfidence == 0.88
    assert res.reviewBanner is not None
    assert "Formulation detail requires review" in res.reviewBanner
    assert "immediate-release tablet" in res.reviewBanner

    dosage_check = next(c for c in res.checks if c.item == "Dosage form")
    assert dosage_check.status == "review"
    assert "partial detail" in dosage_check.details


def test_medicine_active_ingredient_mismatch():
    """A conflicting active ingredient is flagged as a confirmed mismatch with warning check."""
    req = MedicineVerificationRequest(
        brandName="Glycomet 500",
        activeIngredient="Glimepiride",
        strength="500 mg",
    )
    res = verify_medicine_identity_and_composition(req)

    assert res.status == "mismatch"
    assert "Mismatch" in res.verdict
    assert "active ingredient" in res.verdict.lower()

    ing_check = next(c for c in res.checks if c.item == "Active ingredient")
    assert ing_check.status == "warning"
    assert "differs from registered" in ing_check.details


def test_medicine_strength_mismatch():
    """Conflicting strength is flagged as a confirmed mismatch."""
    req = MedicineVerificationRequest(
        brandName="Glycomet 500",
        activeIngredient="Metformin Hydrochloride",
        strength="1000 mg",
    )
    res = verify_medicine_identity_and_composition(req)

    assert res.status == "mismatch"
    assert "strength" in res.verdict.lower()

    str_check = next(c for c in res.checks if c.item == "Strength")
    assert str_check.status == "warning"
    assert "does not match registered" in str_check.details


def test_medicine_manufacturer_mismatch():
    """Conflicting manufacturer is flagged as a confirmed mismatch."""
    req = MedicineVerificationRequest(
        brandName="Glycomet 500",
        manufacturer="Pfizer Healthcare India",
    )
    res = verify_medicine_identity_and_composition(req)

    assert res.status == "mismatch"
    assert "manufacturer" in res.verdict.lower()

    mfg_check = next(c for c in res.checks if c.item == "Manufacturer")
    assert mfg_check.status == "warning"
    assert "does not match registered" in mfg_check.details


def test_distinguish_missing_fields_from_mismatch():
    """
    Omitted / missing packaging details are flagged as 'review' items
    and are NOT treated as confirmed mismatches or fraud.
    """
    req = MedicineVerificationRequest(
        brandName="Augmentin 625 Duo",
        activeIngredient="Amoxicillin and Potassium Clavulanate",
        # strength, dosageForm, manufacturer are deliberately omitted
    )
    res = verify_medicine_identity_and_composition(req)

    # Must NOT be marked as mismatch
    assert res.status != "mismatch"
    assert "Mismatch" not in res.verdict

    items = {c.item: c for c in res.checks}
    assert items["Active ingredient"].status == "verified"
    assert items["Strength"].status == "review"
    assert items["Dosage form"].status == "review"
    assert items["Manufacturer"].status == "review"
    assert "Not specified on query" in items["Strength"].details


def test_unknown_medicine_not_verified_without_fraud_accusation():
    """Uncataloged medicine returns not_verified with non-fraud disclaimer."""
    req = MedicineVerificationRequest(
        brandName="Herbal Panacea Cure 100",
        activeIngredient="Unregistered Botanical Extract",
    )
    res = verify_medicine_identity_and_composition(req)

    assert res.status == "not_verified"
    assert res.product is None
    assert "Not Verified in Demonstration Dataset" in res.verdict
    assert "missing records do not indicate regulatory non-compliance or fraudulent activity" in res.evidenceLimitations


def test_empty_input_inconclusive():
    """Missing both brand and active ingredient returns inconclusive."""
    req = MedicineVerificationRequest()
    res = verify_medicine_identity_and_composition(req)

    assert res.status == "inconclusive"
    assert res.product is None
    assert "Inconclusive" in res.verdict
    assert "Insufficient input data provided" in res.evidenceLimitations


def test_source_failure_simulation():
    """Simulated regulatory source unavailability returns inconclusive with warning."""
    req = MedicineVerificationRequest(
        brandName="Glycomet 500",
        simulateSourceFailure=True,
    )
    res = verify_medicine_identity_and_composition(req)

    assert res.status == "inconclusive"
    assert "Unavailable" in res.verdict

    conn_check = next(c for c in res.checks if c.item == "Source connectivity")
    assert conn_check.status == "warning"
    assert "timed out or failed" in conn_check.details


def test_safety_and_non_prescribing_guarantee():
    """
    The verification service must strictly avoid medical prescribing,
    dosage modification, or therapeutic claims.
    """
    req = MedicineVerificationRequest(
        brandName="Telma 40",
        activeIngredient="Telmisartan",
        strength="40 mg",
    )
    res = verify_medicine_identity_and_composition(req)

    assert "does not prescribe" in res.disclaimer
    assert "recommend medicines" in res.disclaimer
    assert "diagnose conditions" in res.disclaimer
    assert "alter prescriptions" in res.disclaimer

    # Verify no diagnostic or prescribing text in checks or limitations
    for check in res.checks:
        assert "take this" not in check.details.lower()
        assert "prescribe" not in check.details.lower()
        assert "substitute" not in check.details.lower()


# ============================================================================
# API TESTS: Endpoints and DB Integration
# ============================================================================

def test_api_verify_medicine_endpoint_success(client):
    """POST /api/v1/verify/medicine returns 200 with verified product details."""
    payload = {
        "brandName": "Glycomet 500",
        "activeIngredient": "Metformin Hydrochloride",
        "strength": "500 mg",
        "dosageForm": "Tablet",
        "manufacturer": "USV Private Limited",
        "route": "Oral",
    }
    response = client.post("/api/v1/verify/medicine", json=payload)
    assert response.status_code == 200
    data = response.json()

    assert data["status"] == "verified"
    assert data["matchConfidence"] == 0.88
    assert data["verdict"] == "Possible Match — Human Review"
    assert data["reviewBanner"] is not None
    assert data["product"]["brand"] == "Glycomet 500"
    assert data["product"]["standardizedTitle"] == "Metformin Hydrochloride Tablets IP"
    assert len(data["checks"]) >= 5
    assert data["sourceReference"]["isDemonstrationDataset"] is True
    assert "CDSCO/SUGAM" in data["sourceReference"]["authority"]
    assert "timestamp" in data
    assert "disclaimer" in data


def test_api_verify_medicine_form_aliases(client):
    """POST /api/v1/verify/medicine accepts frontend form field aliases ('brand', 'ingredient', 'form')."""
    payload = {
        "brand": "Glycomet 500",
        "ingredient": "Metformin Hydrochloride",
        "strength": "500 mg",
        "form": "Tablet",
        "manufacturer": "USV Private Limited",
    }
    response = client.post("/api/v1/verify/medicine", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "verified"
    assert data["product"]["brand"] == "Glycomet 500"


def test_api_verify_medicine_mismatch(client):
    """POST /api/v1/verify/medicine detects confirmed strength mismatch."""
    payload = {
        "brandName": "Glycomet 500",
        "activeIngredient": "Metformin Hydrochloride",
        "strength": "1000 mg",
    }
    response = client.post("/api/v1/verify/medicine", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "mismatch"
    assert "strength" in data["verdict"].lower()


def test_api_verify_medicine_missing_data(client):
    """POST /api/v1/verify/medicine with empty payload returns 200 with inconclusive status."""
    response = client.post("/api/v1/verify/medicine", json={})
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "inconclusive"
    assert data["product"] is None


def test_api_verify_medicine_simulated_source_failure(client):
    """POST /api/v1/verify/medicine with simulateSourceFailure=true returns inconclusive."""
    payload = {
        "brandName": "Glycomet 500",
        "simulateSourceFailure": True,
    }
    response = client.post("/api/v1/verify/medicine", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "inconclusive"
    assert any(c["item"] == "Source connectivity" for c in data["checks"])


def test_api_verify_medicine_with_audit_linkage(client, db_session):
    """POST /api/v1/verify/medicine with recordId links audit event and writes MedicineVerificationLog."""
    test_record = MedicalRecord(
        id="SR-MED-TEST-01",
        patient_id="AN-PATIENT-01",
        name="Metformin Glycemic Control",
        date_display="19 Oct 2025",
        laboratory_name="Aster Diagnostics, Pune",
        value_display="500 mg daily",
        unit="mg",
        reference_range="Not provided",
        status="Needs review",
        source="Manual",
    )
    db_session.add(test_record)
    db_session.commit()

    payload = {
        "brandName": "Glycomet 500",
        "activeIngredient": "Metformin Hydrochloride",
        "strength": "500 mg",
        "recordId": "SR-MED-TEST-01",
    }
    response = client.post("/api/v1/verify/medicine", json=payload)
    assert response.status_code == 200
    data = response.json()

    assert data["status"] == "verified"
    assert data["auditEventId"] is not None
    assert data["auditEventId"].startswith("EVT-")

    # Verify audit event in database
    audit = db_session.query(AuditEvent).filter(AuditEvent.id == data["auditEventId"]).first()
    assert audit is not None
    assert audit.event_type == "Medicine verification check"

    # Verify MedicineVerificationLog in database
    log = db_session.query(MedicineVerificationLog).filter(
        MedicineVerificationLog.medical_record_id == "SR-MED-TEST-01"
    ).first()
    assert log is not None
    assert log.overall_status == "verified"
    assert log.matched_brand == "Glycomet 500"


def test_api_list_demo_medicines(client):
    """GET /api/v1/verify/medicine/demo-medicines returns available synthetic demo medicines."""
    response = client.get("/api/v1/verify/medicine/demo-medicines")
    assert response.status_code == 200
    meds = response.json()
    assert len(meds) >= 5
    brands = [m["brand"] for m in meds]
    assert "Glycomet 500" in brands
    assert "Augmentin 625 Duo" in brands
    assert "Telma 40" in brands
    assert "Thyronorm 50" in brands
    assert "Pan 40" in brands
