# SehatSnap Backend - Clinical Verification Services

This module implements the **Laboratory and Medicine Verification** services for the SehatSnap clinical integrity platform.

## Architecture & Core Principles

1. **Modular Service Layer**:
   - Laboratory Verification: [`backend/app/services/lab_verification.py`](file:///c:/Users/Krish/OneDrive/Desktop/HackShift/SehatSnap/backend/app/services/lab_verification.py)
   - Medicine Verification: [`backend/app/services/medicine_verification.py`](file:///c:/Users/Krish/OneDrive/Desktop/HackShift/SehatSnap/backend/app/services/medicine_verification.py)
   - Care Tasks & Follow-ups: [`backend/app/services/care_task_service.py`](file:///c:/Users/Krish/OneDrive/Desktop/HackShift/SehatSnap/backend/app/services/care_task_service.py)
   - Transports & API endpoints: [`backend/app/api/verification.py`](file:///c:/Users/Krish/OneDrive/Desktop/HackShift/SehatSnap/backend/app/api/verification.py), [`backend/app/api/care_tasks.py`](file:///c:/Users/Krish/OneDrive/Desktop/HackShift/SehatSnap/backend/app/api/care_tasks.py)

2. **Accreditation vs. Test-Scope Distinction (Laboratory)**:
   - **Accreditation Status**: Confirms whether the laboratory facility holds an active, unexpired, and unsuspended certificate in the directory.
   - **Test-Scope Verification**: Evaluates whether the requested clinical test or discipline falls within the officially accredited testing disciplines cataloged for that facility.

3. **Label Metadata vs. Regulatory Source Comparison (Medicine)**:
   - Compares medicine brand name, active pharmaceutical ingredient (API), strength, dosage form/formulation, and manufacturer against an explicitly identified synthetic demo dataset modeled on CDSCO/SUGAM.
   - **Distinguishes Missing Evidence from Confirmed Mismatches**: Missing fields (e.g., release-type detail not legible or provided) trigger a professional review requirement (`status: "review"`, `verdict: "Possible Match — Human Review"`), while contradictory values trigger a confirmed `mismatch`.
   - **Clinical Safety Guarantee**: The service strictly verifies packaging label metadata against regulatory reference data. It **never** prescribes, recommends medicines, diagnoses medical conditions, or changes prescriptions.

4. **Care-Task & Follow-Up Safety Principles**:
   - **Follow-up Action Enforcement**: Tasks must strictly represent follow-up actions (repeating tests, scheduling consultations, requesting records, clinician review). Autonomous clinical diagnoses and unilateral prescription/dosage alterations are strictly rejected (HTTP 422).
   - **Truthful Notification Disclosures**: The backend does not claim external SMS/Push/Email delivery when no active third-party integration is configured (`notificationStatus: "Not configured (local record only)"`).
   - **Grounded Verification Linking**: Tasks can be generated directly from laboratory or medicine verification findings (`POST /api/v1/care-tasks/from-verification`), linking the follow-up directly to the audit log, report document, and medical record.

5. **Deterministic Verdict Taxonomy**:
   - `verified`: Facility accreditation or medicine identity verified against source data.
   - `not_verified`: Facility, certificate, or product is not cataloged in the demonstration dataset.
   - `mismatch`: Explicit discrepancy detected (e.g. wrong active ingredient, conflicting strength, or unaccredited test scope).
   - `inconclusive`: Insufficient input provided (e.g. neither name nor certificate/ingredient provided) or simulated source failure.

6. **Safety & Non-Fraud Guarantee**:
   - Missing records in demonstration data are **never** treated as evidence of fraud, counterfeit, or falsification. Every negative or inconclusive response includes an explicit disclaimer stating that absence from the demo snapshot must not be interpreted as lack of real-world accreditation or regulatory approval.

---

## API Endpoints

### 1. Laboratory Accreditation Verification
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
- **Response (`200 OK`)**:
  Returns `matchConfidence`, `verdict`, `status`, `accreditationStatus`, `testScopeStatus`, `laboratory` details, structured `checks`, `sourceReference`, and `evidenceLimitations`.

### 2. Medicine Regulatory Verification
- **Route**: `POST /api/v1/verify/medicine`
- **Request Body**:
  ```json
  {
    "brandName": "Glycomet 500",
    "activeIngredient": "Metformin Hydrochloride",
    "strength": "500 mg",
    "dosageForm": "Tablet",
    "manufacturer": "USV Private Limited",
    "route": "Oral"
  }
  ```
  *Note*: Accepts frontend form field aliases `brand`, `ingredient`, `form`.
- **Response (`200 OK`)**:
  ```json
  {
    "matchConfidence": 0.88,
    "verdict": "Possible Match — Human Review",
    "status": "verified",
    "reviewBanner": "Formulation detail requires review: The checked source lists an immediate-release tablet; the uploaded label image does not clearly show release type. Verify with a registered pharmacist or clinician.",
    "product": {
      "brand": "Glycomet 500",
      "standardizedTitle": "Metformin Hydrochloride Tablets IP",
      "activeIngredient": "Metformin Hydrochloride",
      "strength": "500 mg",
      "dosageForm": "Immediate-release uncoated tablet IP",
      "manufacturer": "USV Private Limited"
    },
    "checks": [
      { "item": "Active ingredient", "details": "Metformin Hydrochloride · match", "status": "verified" },
      { "item": "Strength", "details": "500 mg · match", "status": "verified" },
      { "item": "Dosage form", "details": "Tablet · partial detail", "status": "review" },
      { "item": "Manufacturer", "details": "USV Private Limited · match", "status": "verified" },
      { "item": "Regulatory information", "details": "Label record available in demo", "status": "info" }
    ],
    "sourceReference": {
      "authority": "CDSCO/SUGAM demonstration dataset",
      "sourceDate": "2025-08-06",
      "retrievedAt": "2025-10-20",
      "isDemonstrationDataset": true
    },
    "disclaimer": "SehatSnap does not prescribe, recommend medicines, diagnose conditions, or alter prescriptions..."
  }
  ```

### 3. Catalog Inspection Endpoints
- `GET /api/v1/verify/laboratory/demo-labs`: Lists synthetic NABL demo laboratories.
- `GET /api/v1/verify/medicine/demo-medicines`: Lists synthetic CDSCO/SUGAM demo medicines.

### 4. Verification Audit History & Cryptographic Chain Module
- **Tamper-Evident SHA-256 Hash Chaining**: Every actual laboratory and medicine verification check generates a `VerificationAuditRecord` cryptographically linked to the preceding record's SHA-256 digest (or `0`*64 genesis).
- **Accurate Capture of Failures & Inconclusive Checks**: When external source failures or incomplete query parameters occur, they are recorded as structured audit events (`has_source_error=True`, error details, code, and status) rather than omitted.
- **Storage Protection Disclosure**: The system truthfully discloses its cryptographic protections: SHA-256 hash chaining stored in local SQLite provides deterministic tamper-evidence against record alteration and truncation, without falsely claiming hardware WORM immutability or decentralized consensus.
- **Audit Endpoints**:
  - `GET /api/v1/verify/audit-records`: Retrieves paginated verification audit logs with filters (`entity_type`, `status`, `check_type`, `source`, `has_error`, `query`, `report_id`, `record_id`, `sort`, `limit`, `offset`).
  - `GET /api/v1/verify/audit-records/{audit_id}`: Full detail of an audit record by its `VAR-` ID.
  - `GET /api/v1/verify/audit-records/chain/verify`: Cryptographic verification suite that sequentially validates all record hashes and identifies any tampered record ID and position.

### 5. Care-Task & Follow-Up Endpoints
- **List Care Tasks**: `GET /api/v1/care-tasks` (supports `status`, `priority`, `task_type`, `record_id`, `report_id`, `query`, and `sort` query parameters).
- **Create Care Task**: `POST /api/v1/care-tasks` (enforces clinical safety validation, optional due dates, and entity linkage).
- **Get Care Task Detail**: `GET /api/v1/care-tasks/{task_id}`
- **Update Task Status**: `PATCH /api/v1/care-tasks/{task_id}/status` (transitions status between `Needs Review`, `Scheduled`, `Completed`, `Not Applicable`, `Clinician Review` and records audit events).
- **Update Task Details**: `PATCH /api/v1/care-tasks/{task_id}` (updates title, description, due date, expected document, or priority with safety checks).
- **Delete Care Task**: `DELETE /api/v1/care-tasks/{task_id}`
- **Create from Verification Finding**: `POST /api/v1/care-tasks/from-verification` (generates structured follow-up consultation/scope tasks linked to `LabVerificationLog` or `MedicineVerificationLog`).
- **Notification Integration Status**: `GET /api/v1/care-tasks/notifications/status` (truthfully discloses that external SMS/Push/Email delivery is not configured and reminders remain local).

---

## Setup & Testing Instructions

### Local Environment Setup
```bash
# From workspace root
python -m venv .venv
.\.venv\Scripts\Activate.ps1   # On Windows PowerShell

# Install dependencies
pip install "fastapi>=0.115.0" "pydantic>=2.0" "uvicorn[standard]" "sqlalchemy>=2.0" "aiofiles" "python-multipart" "pytest>=8.0" "pytest-asyncio" "httpx" "pymupdf" "pillow" "pytesseract"
```

### Running Tests
```bash
# Run all backend unit and API tests (98 tests)
.\.venv\Scripts\pytest.exe -v

# Run verification audit and tamper-evidence tests (14 tests)
.\.venv\Scripts\pytest.exe -v backend/tests/test_verification_audit.py

# Run care-task and follow-up tests (16 tests)
.\.venv\Scripts\pytest.exe -v backend/tests/test_care_tasks.py

# Run medicine verification tests (17 tests)
.\.venv\Scripts\pytest.exe -v backend/tests/test_medicine_verification.py

# Run lab verification tests (17 tests)
.\.venv\Scripts\pytest.exe -v backend/tests/test_lab_verification.py
```

### Starting the Backend Development Server
```bash
.\.venv\Scripts\uvicorn.exe backend.app.main:app --reload --port 8000
```
Interactive API documentation: `http://localhost:8000/docs`

