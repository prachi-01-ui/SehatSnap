# SehatSnap Backend - Laboratory Verification Service (Member 4)

This service implements the **Laboratory Verification and Integrity Audit** component for the SehatSnap clinical integrity platform.

## Architecture & Core Principles

1. **Modular Service Layer** (`backend/app/services/lab_verification.py`):
   - Separates clinical verification logic from transport/HTTP routing.
   - Evaluates laboratory identity and active accreditation independently from specific test-scope authorization.
   - Uses a clearly labelled, synthetic demonstration dataset modeled on ISO 15189 / NABL directory records.

2. **Accreditation vs. Test-Scope Distinction**:
   - **Accreditation Status**: Confirms whether the laboratory facility holds an active, unexpired, and unsuspended certificate in the directory.
   - **Test-Scope Verification**: Evaluates whether the requested clinical test (or discipline) falls within the officially accredited testing disciplines cataloged for that facility.
   - *Example*: A facility may hold active accreditation for Clinical Biochemistry, but requested Histopathology testing will be reported as out-of-scope (`mismatch` / `testScopeStatus="not_verified"`).

3. **Deterministic Verdict Taxonomy**:
   - `verified`: Facility accreditation confirmed active and requested test is within verified scope (or scope unspecified).
   - `not_verified`: Facility or certificate is not cataloged in the demonstration snapshot, or accreditation is expired/suspended.
   - `mismatch`: Discrepancy detected (e.g. certificate number registered to another entity, site location mismatch, or requested test is explicitly unaccredited).
   - `inconclusive`: Insufficient identification provided (e.g., neither facility name nor certificate provided) or simulated source failure.

4. **Safety & Non-Fraud Guarantee**:
   - Missing records in demonstration data are **never** treated as evidence of fraud or falsification. Every negative or inconclusive response includes an explicit disclaimer stating that absence from the demo snapshot must not be interpreted as lack of real-world accreditation.

---

## API Endpoints

### 1. Verify Laboratory Accreditation & Scope
- **Route**: `POST /api/v1/verify/laboratory`
- **Request Body**:
  ```json
  {
    "laboratoryName": "Metropolis Healthcare Ltd.",
    "city": "Pune, Maharashtra",
    "certificateNumber": "MC-2104",
    "discipline": "Clinical Biochemistry",
    "testName": "Fasting Plasma Glucose",
    "recordId": "SR-1048"
  }
  ```
  *Note*: Accepts field aliases `lab`, `certificate`, and `test` for direct frontend form compatibility.

- **Response (`200 OK`)**:
  ```json
  {
    "matchConfidence": 0.96,
    "verdict": "Verified Against Official Source",
    "status": "verified",
    "accreditationStatus": "verified",
    "testScopeStatus": "verified",
    "laboratory": {
      "name": "Metropolis Healthcare Ltd.",
      "location": "Pune, Maharashtra",
      "certificateNumber": "MC-2104",
      "validThrough": "2026-03-31",
      "accreditationBody": "NABL",
      "disciplines": ["Clinical Biochemistry", "Clinical Pathology", "Hematology", "Microbiology & Infectious Disease Serology"],
      "scopeTests": ["Fasting Plasma Glucose", "Complete Blood Count", "Lipid Profile", "..."]
    },
    "checks": [
      { "item": "Laboratory identity", "details": "Exact name match with 'Metropolis Healthcare Ltd.'", "status": "verified" },
      { "item": "Location", "details": "Pune location matched", "status": "verified" },
      { "item": "Accreditation status", "details": "Active in demo dataset (NABL)", "status": "verified" },
      { "item": "Certificate validity", "details": "Valid through 2026-03-31", "status": "verified" },
      { "item": "Requested scope", "details": "'Fasting Plasma Glucose' confirmed within accredited testing scope", "status": "verified" },
      { "item": "Outstanding questions", "details": "Collection centre relationship and peripheral phlebotomy site not checked", "status": "review" }
    ],
    "sourceReference": {
      "authority": "NABL directory demonstration snapshot",
      "retrievedAt": "2025-10-20T10:14:00+05:30",
      "isDemonstrationDataset": true,
      "sourceNotes": "Synthetic demonstration dataset modeled on ISO 15189 / NABL directory records. Never queries live portals."
    },
    "evidenceLimitations": "Matched against synthetic demonstration dataset with 96% confidence...",
    "timestamp": "2026-10-18T04:55:00Z",
    "auditEventId": "EVT-8A12"
  }
  ```

### 2. List Demo Laboratories
- **Route**: `GET /api/v1/verify/laboratory/demo-labs`
- Returns all synthetic laboratories currently configured in the demonstration registry.

---

## Setup & Testing Instructions

### Local Environment Setup
```bash
# From workspace root
python -m venv .venv
.\.venv\Scripts\Activate.ps1   # On Windows PowerShell

# Install dependencies
pip install "fastapi>=0.115.0" "pydantic>=2.0" "uvicorn[standard]" "sqlalchemy>=2.0" "aiofiles" "python-multipart" "pytest>=8.0" "pytest-asyncio" "httpx"
```

### Running Tests
```bash
# Run all backend unit and API tests
.\.venv\Scripts\pytest.exe -v

# Run only the lab verification tests
.\.venv\Scripts\pytest.exe -v backend/tests/test_lab_verification.py
```

### Starting the Backend Development Server
```bash
.\.venv\Scripts\uvicorn.exe backend.app.main:app --reload --port 8000
```
API Documentation will be accessible at: `http://localhost:8000/docs`
