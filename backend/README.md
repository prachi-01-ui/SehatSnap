# SehatSnap Backend - Clinical Verification Services

This module implements the **Laboratory and Medicine Verification** services for the SehatSnap clinical integrity platform.

## Architecture & Core Principles

1. **Modular Service Layer**:
   - Laboratory Verification: [`backend/app/services/lab_verification.py`](file:///c:/Users/Krish/OneDrive/Desktop/HackShift/SehatSnap/backend/app/services/lab_verification.py)
   - Medicine Verification: [`backend/app/services/medicine_verification.py`](file:///c:/Users/Krish/OneDrive/Desktop/HackShift/SehatSnap/backend/app/services/medicine_verification.py)
   - Transports & API endpoints: [`backend/app/api/verification.py`](file:///c:/Users/Krish/OneDrive/Desktop/HackShift/SehatSnap/backend/app/api/verification.py)

2. **Accreditation vs. Test-Scope Distinction (Laboratory)**:
   - **Accreditation Status**: Confirms whether the laboratory facility holds an active, unexpired, and unsuspended certificate in the directory.
   - **Test-Scope Verification**: Evaluates whether the requested clinical test or discipline falls within the officially accredited testing disciplines cataloged for that facility.

3. **Label Metadata vs. Regulatory Source Comparison (Medicine)**:
   - Compares medicine brand name, active pharmaceutical ingredient (API), strength, dosage form/formulation, and manufacturer against an explicitly identified synthetic demo dataset modeled on CDSCO/SUGAM.
   - **Distinguishes Missing Evidence from Confirmed Mismatches**: Missing fields (e.g., release-type detail not legible or provided) trigger a professional review requirement (`status: "review"`, `verdict: "Possible Match — Human Review"`), while contradictory values trigger a confirmed `mismatch`.
   - **Clinical Safety Guarantee**: The service strictly verifies packaging label metadata against regulatory reference data. It **never** prescribes, recommends medicines, diagnoses medical conditions, or changes prescriptions.

4. **Deterministic Verdict Taxonomy**:
   - `verified`: Facility accreditation or medicine identity verified against source data.
   - `not_verified`: Facility, certificate, or product is not cataloged in the demonstration dataset.
   - `mismatch`: Explicit discrepancy detected (e.g. wrong active ingredient, conflicting strength, or unaccredited test scope).
   - `inconclusive`: Insufficient input provided (e.g. neither name nor certificate/ingredient provided) or simulated source failure.

5. **Safety & Non-Fraud Guarantee**:
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
# Run all backend unit and API tests (50 tests)
.\.venv\Scripts\pytest.exe -v

# Run only medicine verification tests (17 tests)
.\.venv\Scripts\pytest.exe -v backend/tests/test_medicine_verification.py

# Run only lab verification tests (17 tests)
.\.venv\Scripts\pytest.exe -v backend/tests/test_lab_verification.py
```

### Starting the Backend Development Server
```bash
.\.venv\Scripts\uvicorn.exe backend.app.main:app --reload --port 8000
```
Interactive API documentation: `http://localhost:8000/docs`
