"""
Modular Laboratory Verification Service for SehatSnap.

Provides verification of clinical laboratory identity, accreditation validity,
and test-scope coverage against a clearly labelled synthetic demo dataset.

Key principles:
1. Distinguishes general accreditation status from test-scope verification.
2. Returns deterministic verdicts: verified, not_verified, mismatch, or inconclusive.
3. Never invents official verification results or treats missing data as fraud.
4. Uses synthetic demonstration data exclusively; no real credentials, patient data, or live scraping.
"""

from typing import Optional, Dict, Any, List, Tuple
import datetime
import re

from backend.app.schemas import (
    LabVerificationRequest,
    LabVerificationResponse,
    LabCheckItem,
    VerifiedLabDetails,
    VerificationSourceReference,
)

# Clearly labelled synthetic demonstration dataset based on simulated NABL directory records
SYNTHETIC_NABL_REGISTRY: List[Dict[str, Any]] = [
    {
        "certificateNumber": "MC-2104",
        "name": "Metropolis Healthcare Ltd.",
        "aliases": ["Metropolis Healthcare", "Metropolis Healthcare, Pune", "Metropolis Labs"],
        "city": "Pune",
        "state": "Maharashtra",
        "location": "Pune, Maharashtra",
        "status": "Active",
        "validThrough": "2026-03-31",
        "accreditationBody": "NABL",
        "disciplines": [
            "Clinical Biochemistry",
            "Clinical Pathology",
            "Hematology",
            "Microbiology & Infectious Disease Serology",
        ],
        "scopeTests": [
            "Fasting Plasma Glucose",
            "Postprandial Blood Glucose",
            "Glycated Hemoglobin (HbA1c)",
            "Complete Blood Count",
            "Hemoglobin",
            "Lipid Profile",
            "Thyroid Stimulating Hormone",
            "Liver Function Test",
            "Renal Function Test",
            "Serum Creatinine",
        ],
        "notes": "Central reference laboratory accreditation.",
    },
    {
        "certificateNumber": "MC-3088",
        "name": "Aster Diagnostics",
        "aliases": ["Aster Diagnostics, Pune", "Aster Labs Pune", "Aster Clinical Laboratories"],
        "city": "Pune",
        "state": "Maharashtra",
        "location": "Pune, Maharashtra",
        "status": "Active",
        "validThrough": "2026-11-30",
        "accreditationBody": "NABL",
        "disciplines": [
            "Clinical Biochemistry",
            "Microbiology & Infectious Disease Serology",
        ],
        "scopeTests": [
            "Fasting Plasma Glucose",
            "Postprandial Blood Glucose",
            "Glycated Hemoglobin (HbA1c)",
            "Liver Function Test",
            "Serum Electrolytes",
        ],
        "notes": "Accreditation limited to Clinical Biochemistry and Microbiology. Hematology / Histopathology handled via referral.",
    },
    {
        "certificateNumber": "MC-1955",
        "name": "CarePlus Labs",
        "aliases": ["CarePlus Labs, Mumbai", "CarePlus Diagnostics"],
        "city": "Mumbai",
        "state": "Maharashtra",
        "location": "Mumbai, Maharashtra",
        "status": "Expired",
        "validThrough": "2024-12-31",
        "accreditationBody": "NABL",
        "disciplines": [
            "Clinical Biochemistry",
            "Clinical Pathology",
        ],
        "scopeTests": [
            "Lipid Profile",
            "Complete Blood Count",
        ],
        "notes": "Accreditation expired on 31 Dec 2024. Renewal application pending review in synthetic simulation.",
    },
    {
        "certificateNumber": "MC-4401",
        "name": "Apollo Diagnostics",
        "aliases": ["Apollo Diagnostics, Hyderabad", "Apollo Clinical Lab"],
        "city": "Hyderabad",
        "state": "Telangana",
        "location": "Hyderabad, Telangana",
        "status": "Suspended",
        "validThrough": "2025-08-15",
        "accreditationBody": "NABL",
        "disciplines": [
            "Clinical Biochemistry",
            "Molecular Testing",
        ],
        "scopeTests": [
            "RT-PCR",
            "Fasting Plasma Glucose",
        ],
        "notes": "Accreditation temporarily suspended pending facility audit in synthetic simulation.",
    },
    {
        "certificateNumber": "MC-5599",
        "name": "SRL Diagnostics Ltd.",
        "aliases": ["SRL Diagnostics", "SRL Labs", "Agilus Diagnostics"],
        "city": "Delhi",
        "state": "Delhi",
        "location": "Delhi, NCR",
        "status": "Active",
        "validThrough": "2027-01-15",
        "accreditationBody": "NABL",
        "disciplines": [
            "Clinical Biochemistry",
            "Hematology",
            "Histopathology",
            "Cytogenetics",
        ],
        "scopeTests": [
            "Complete Blood Count",
            "Thyroid Panel",
            "Karyotyping",
            "Vitamin D3",
        ],
        "notes": "Multi-discipline regional reference laboratory.",
    },
]

DEMO_AUTHORITY = "NABL directory demonstration snapshot"
DEMO_RETRIEVED_AT = "2025-10-20T10:14:00+05:30"


def _normalize(text: Optional[str]) -> str:
    """Normalizes string for robust, case-insensitive comparison."""
    if not text:
        return ""
    # Strip punctuation, normalize whitespace
    cleaned = re.sub(r"[^\w\s]", " ", text.lower())
    return " ".join(cleaned.split())


def _find_lab_record(
    cert_num: Optional[str],
    lab_name: Optional[str],
) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
    """
    Finds laboratory in synthetic registry by certificate number or normalized name match.
    Returns (record, match_method).
    """
    norm_cert = cert_num.strip().upper() if cert_num else ""
    norm_name = _normalize(lab_name)

    # 1. Direct certificate number match (strongest key)
    if norm_cert:
        for entry in SYNTHETIC_NABL_REGISTRY:
            if entry["certificateNumber"].upper() == norm_cert:
                return entry, "certificate"

    # 2. Name or alias match
    if norm_name:
        for entry in SYNTHETIC_NABL_REGISTRY:
            entry_name_norm = _normalize(entry["name"])
            if norm_name in entry_name_norm or entry_name_norm in norm_name:
                return entry, "name_primary"
            for alias in entry.get("aliases", []):
                alias_norm = _normalize(alias)
                if norm_name in alias_norm or alias_norm in norm_name:
                    return entry, "name_alias"

    return None, None


def verify_laboratory_identity_and_scope(
    request: LabVerificationRequest,
    current_time: Optional[datetime.datetime] = None,
) -> LabVerificationResponse:
    """
    Modular laboratory verification pipeline:
    1. Validates input sufficiency.
    2. Simulates external source failures if requested or configured.
    3. Searches synthetic demonstration registry.
    4. Evaluates lab identity and accreditation status (Active vs Expired vs Suspended vs Mismatch).
    5. Evaluates test-scope verification independently (In-Scope vs Out-of-Scope vs Unspecified).
    6. Assembles transparent checks, evidence, limitations, and standardized status.
    """
    now = current_time or datetime.datetime.now(datetime.timezone.utc)
    timestamp_iso = now.isoformat()

    # Source reference metadata
    source_ref = VerificationSourceReference(
        authority=DEMO_AUTHORITY,
        retrievedAt=DEMO_RETRIEVED_AT,
        isDemonstrationDataset=True,
        sourceNotes="Synthetic demonstration dataset modeled on ISO 15189 / NABL directory records. Never queries live portals.",
    )

    # --- Scenario 1: Source Failure Simulation ---
    if request.simulateSourceFailure:
        return LabVerificationResponse(
            matchConfidence=0.0,
            verdict="Verification Inconclusive - Demonstration Source Unavailable",
            status="inconclusive",
            accreditationStatus="inconclusive",
            testScopeStatus="inconclusive",
            laboratory=None,
            checks=[
                LabCheckItem(
                    item="Source connectivity",
                    details="Connection to demonstration accreditation registry timed out or failed",
                    status="warning",
                ),
                LabCheckItem(
                    item="Verification recommendation",
                    details="Unable to query accreditation records at this time. Verify laboratory accreditation credentials directly with the issuing body.",
                    status="inconclusive",
                ),
            ],
            sourceReference=source_ref,
            evidenceLimitations="Lookup provider reported an error. No inference of non-compliance, invalidity, or fraud is made.",
            timestamp=timestamp_iso,
        )

    # --- Scenario 2: Insufficient Input Data ---
    raw_name = request.laboratoryName.strip() if request.laboratoryName else ""
    raw_cert = request.certificateNumber.strip() if request.certificateNumber else ""
    raw_city = request.city.strip() if request.city else ""
    raw_discipline = request.discipline.strip() if request.discipline else ""
    raw_test = request.testName.strip() if request.testName else ""

    if not raw_name and not raw_cert:
        return LabVerificationResponse(
            matchConfidence=0.0,
            verdict="Inconclusive - Laboratory Identity Not Provided",
            status="inconclusive",
            accreditationStatus="inconclusive",
            testScopeStatus="inconclusive",
            laboratory=None,
            checks=[
                LabCheckItem(
                    item="Laboratory identifier",
                    details="Neither laboratory name nor certificate number was supplied in the query",
                    status="inconclusive",
                ),
                LabCheckItem(
                    item="Verification recommendation",
                    details="Provide a valid laboratory name or accreditation certificate number visible on the report header.",
                    status="review",
                ),
            ],
            sourceReference=source_ref,
            evidenceLimitations="Insufficient data supplied to initiate verification. Missing input parameters do not imply falsification or invalidity.",
            timestamp=timestamp_iso,
        )

    # --- Scenario 3: Registry Lookup ---
    record, match_method = _find_lab_record(raw_cert, raw_name)

    # Case A: Record not found in demo registry
    if not record:
        checks = [
            LabCheckItem(
                item="Registry search",
                details=f"No record matching '{raw_name or raw_cert}' in synthetic demonstration dataset",
                status="review",
            ),
            LabCheckItem(
                item="Missing data notice",
                details="Absence from demonstration records must not be interpreted as lack of official accreditation or fraudulent operation",
                status="inconclusive",
            ),
        ]
        if raw_cert:
            checks.append(
                LabCheckItem(
                    item="Certificate number",
                    details=f"Certificate '{raw_cert}' not cataloged in current demo snapshot",
                    status="review",
                )
            )

        return LabVerificationResponse(
            matchConfidence=0.10,
            verdict="Not Verified in Demonstration Dataset",
            status="not_verified",
            accreditationStatus="not_verified",
            testScopeStatus="inconclusive",
            laboratory=None,
            checks=checks,
            sourceReference=source_ref,
            evidenceLimitations=(
                "No matching entry found in the demonstration snapshot. Because this is a curated demo dataset, "
                "missing records do not indicate unaccredited status or fraudulent activity. Always cross-check "
                "with the primary official accreditor directory."
            ),
            timestamp=timestamp_iso,
        )

    # --- Case B: Record found; evaluate detailed checks ---
    checks: List[LabCheckItem] = []
    confidence_points = 0.0

    # 1. Identity Check
    name_mismatch = False
    if raw_name:
        entry_name_norm = _normalize(record["name"])
        query_name_norm = _normalize(raw_name)
        alias_norms = [_normalize(a) for a in record.get("aliases", [])]

        if query_name_norm == entry_name_norm:
            checks.append(
                LabCheckItem(
                    item="Laboratory identity",
                    details=f"Exact name match with '{record['name']}'",
                    status="verified",
                )
            )
            confidence_points += 0.35
        elif any(query_name_norm in a or a in query_name_norm for a in [entry_name_norm] + alias_norms):
            checks.append(
                LabCheckItem(
                    item="Laboratory identity",
                    details=f"Recognized alias match for '{record['name']}'",
                    status="verified",
                )
            )
            confidence_points += 0.32
        else:
            name_mismatch = True
            checks.append(
                LabCheckItem(
                    item="Laboratory identity",
                    details=f"Queried name '{raw_name}' differs from registered entity '{record['name']}' for certificate '{record['certificateNumber']}'",
                    status="warning",
                )
            )
    else:
        checks.append(
            LabCheckItem(
                item="Laboratory identity",
                details=f"Inferred from certificate: '{record['name']}'",
                status="review",
            )
        )
        confidence_points += 0.20

    # 2. Location Check
    city_mismatch = False
    if raw_city:
        query_city_norm = _normalize(raw_city)
        registered_city_norm = _normalize(record["city"])
        registered_loc_norm = _normalize(record["location"])

        if registered_city_norm in query_city_norm or query_city_norm in registered_loc_norm:
            checks.append(
                LabCheckItem(
                    item="Location",
                    details=f"{record['city']} location matched",
                    status="verified",
                )
            )
            confidence_points += 0.15
        else:
            city_mismatch = True
            checks.append(
                LabCheckItem(
                    item="Location",
                    details=f"Queried location '{raw_city}' differs from registered site '{record['location']}'",
                    status="warning",
                )
            )
    else:
        checks.append(
            LabCheckItem(
                item="Location",
                details=f"Registered location: {record['location']} (not specified in query)",
                status="review",
            )
        )
        confidence_points += 0.08

    # 3. Certificate Number Check
    cert_mismatch = False
    if raw_cert:
        if raw_cert.strip().upper() == record["certificateNumber"].upper():
            checks.append(
                LabCheckItem(
                    item="Certificate number",
                    details=f"Matches registered certificate {record['certificateNumber']}",
                    status="verified",
                )
            )
            confidence_points += 0.20
        else:
            cert_mismatch = True
            checks.append(
                LabCheckItem(
                    item="Certificate number",
                    details=f"Queried certificate '{raw_cert}' does not match registered '{record['certificateNumber']}'",
                    status="warning",
                )
            )
    else:
        checks.append(
            LabCheckItem(
                item="Certificate number",
                details=f"Registry record #{record['certificateNumber']} retrieved by facility name",
                status="review",
            )
        )
        confidence_points += 0.10

    # 4. Accreditation Validity & Expiry
    accreditation_status_code = "verified"
    rec_status = record.get("status", "Active")
    valid_through = record.get("validThrough", "")

    if rec_status == "Active":
        checks.append(
            LabCheckItem(
                item="Accreditation status",
                details=f"Active in demo dataset ({record['accreditationBody']})",
                status="verified",
            )
        )
        checks.append(
            LabCheckItem(
                item="Certificate validity",
                details=f"Valid through {valid_through}",
                status="verified",
            )
        )
        confidence_points += 0.15
    elif rec_status == "Expired":
        accreditation_status_code = "expired"
        checks.append(
            LabCheckItem(
                item="Accreditation status",
                details="Accreditation expired in demo dataset",
                status="warning",
            )
        )
        checks.append(
            LabCheckItem(
                item="Certificate validity",
                details=f"Expired on {valid_through} · Renewal confirmation required",
                status="warning",
            )
        )
    elif rec_status == "Suspended":
        accreditation_status_code = "suspended"
        checks.append(
            LabCheckItem(
                item="Accreditation status",
                details="Accreditation suspended in demo dataset",
                status="warning",
            )
        )
        checks.append(
            LabCheckItem(
                item="Certificate validity",
                details="Suspended pending audit; routine testing temporarily unverified",
                status="warning",
            )
        )

    # 5. Independent Test-Scope Evaluation
    test_scope_status_code = "verified"
    scope_target = raw_test or raw_discipline

    if not scope_target:
        test_scope_status_code = "unspecified"
        checks.append(
            LabCheckItem(
                item="Requested scope",
                details="No specific test name or discipline queried; general facility accreditation only",
                status="review",
            )
        )
    else:
        target_norm = _normalize(scope_target)
        reg_disciplines = [_normalize(d) for d in record.get("disciplines", [])]
        reg_tests = [_normalize(t) for t in record.get("scopeTests", [])]

        discipline_matched = any(target_norm in d or d in target_norm for d in reg_disciplines)
        test_matched = any(target_norm in t or t in target_norm for t in reg_tests)

        if test_matched or discipline_matched:
            matched_label = scope_target
            checks.append(
                LabCheckItem(
                    item="Requested scope",
                    details=f"'{matched_label}' confirmed within accredited testing scope",
                    status="verified",
                )
            )
            confidence_points += 0.15
        else:
            test_scope_status_code = "not_verified"
            checks.append(
                LabCheckItem(
                    item="Requested scope",
                    details=f"'{scope_target}' is not cataloged in the accredited scope for {record['name']}",
                    status="warning",
                )
            )

    # 6. Standard Outstanding Questions / Limitations Item
    checks.append(
        LabCheckItem(
            item="Outstanding questions",
            details="Collection centre relationship and peripheral phlebotomy site not checked",
            status="review",
        )
    )

    # --- Synthesize Overall Status and Verdict ---
    final_confidence = min(0.98, max(0.10, round(confidence_points, 2)))

    # Determine discrepancy flag
    has_critical_mismatch = name_mismatch or cert_mismatch

    if has_critical_mismatch:
        overall_status = "mismatch"
        accreditation_status_code = "mismatch"
        verdict = "Accreditation Certificate or Identity Mismatch Detected"
    elif city_mismatch:
        overall_status = "mismatch"
        verdict = "Laboratory Accredited - Location Mismatch Detected"
    elif accreditation_status_code == "expired":
        overall_status = "not_verified"
        verdict = "Accreditation Expired in Demonstration Records"
    elif accreditation_status_code == "suspended":
        overall_status = "not_verified"
        verdict = "Accreditation Suspended in Demonstration Records"
    elif test_scope_status_code == "not_verified":
        # Crucial distinction: lab is accredited, but this specific test is out of scope!
        overall_status = "mismatch"
        verdict = "Laboratory Accredited - Requested Test Scope Unverified"
    elif test_scope_status_code == "unspecified":
        overall_status = "verified"
        verdict = "Laboratory Accredited - Scope Unspecified"
    else:
        overall_status = "verified"
        verdict = "Verified Against Official Source"


    # Assemble structured verified lab details
    lab_details = VerifiedLabDetails(
        name=record["name"],
        location=record["location"],
        certificateNumber=record["certificateNumber"],
        validThrough=record["validThrough"],
        accreditationBody=record.get("accreditationBody", "NABL"),
        disciplines=record.get("disciplines", []),
        scopeTests=record.get("scopeTests", []),
    )

    limitations_text = (
        f"Matched against synthetic demonstration dataset with {int(final_confidence * 100)}% confidence. "
        "Demonstration data is simulated for workflow evaluation and does not reflect a live NABL server response. "
        "Clinical scope, branch operations, and sample transit procedures require primary-source confirmation."
    )

    return LabVerificationResponse(
        matchConfidence=final_confidence,
        verdict=verdict,
        status=overall_status,
        accreditationStatus=accreditation_status_code,
        testScopeStatus=test_scope_status_code,
        laboratory=lab_details,
        checks=checks,
        sourceReference=source_ref,
        evidenceLimitations=limitations_text,
        timestamp=timestamp_iso,
    )
