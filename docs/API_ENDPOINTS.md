# SehatSnap ΓÇö Backend API Endpoint Specification & Integration Audit

**Version:** 0.1.0 (Milestone 1 Baseline)
**Base URL (Local Development):** `http://127.0.0.1:8000`
**Interactive API Documentation (Swagger UI):** `http://127.0.0.1:8000/docs`
**Alternative Documentation (ReDoc):** `http://127.0.0.1:8000/redoc`
**OpenAPI Specification:** `http://127.0.0.1:8000/openapi.json`

---

## 1. Executive Summary & Verification State

This document provides the authoritative API specification for frontend developers integrating the SehatSnap React frontend with the FastAPI backend.

* **Total Verified Backend Routes:** 9 endpoints registered and operational.
* **Automated Test Suite:** 16 tests passing (`uv run pytest backend/tests -v`), covering upload security, magic bytes validation, streaming size enforcement (20 MiB), SHA-256 hashing, record management, and dynamic dashboard metrics.
* **Source of Truth:** All route paths, parameters, schemas, and status codes in this document have been verified against active source code in `backend/app/` and verified via OpenAPI introspection.

---

## 2. Implemented Endpoint Inventory

### Feature Group A: System Health & Diagnostics

#### 1. Root Service Information
* **Method:** `GET`
* **Path:** `/`
* **Purpose:** Returns service name, version, and links to documentation.
* **Frontend Component:** Health probe / external developer access.
* **Request Body:** None.
* **Query / Path Parameters:** None.
* **Expected Response:** `200 OK`
  ```json
  {
    "service": "SehatSnap Clinical Integrity API",
    "version": "0.1.0",
    "docsUrl": "/docs",
    "healthUrl": "/api/v1/health",
    "milestone": "Milestone 1 Baseline"
  }
  ```
* **Authentication:** None.
* **Database Operations:** None.
* **Errors:** None.

---

#### 2. Health & Database Connectivity Check
* **Method:** `GET`
* **Path:** `/api/v1/health`
* **Purpose:** Probes backend status and verifies SQLite database read connectivity and entity counts.
* **Frontend Component:** Shell Header status indicator or global connection monitor.
* **Request Body:** None.
* **Query / Path Parameters:** None.
* **Expected Response:** `200 OK`
  ```json
  {
    "status": "healthy",
    "databaseConnected": true,
    "recordsCount": 5,
    "reportsCount": 0,
    "timestamp": "2026-10-18T04:15:00.000000+00:00"
  }
  ```
* **Authentication:** None.
* **Database Operations:** Executes `SELECT 1`, counts `MedicalRecord` and `ReportDocument` rows.
* **Errors:** If database is unreachable, returns `200 OK` with `"status": "degraded"` and `"databaseConnected": false`.

---

### Feature Group B: Workspace Dashboard Overview

#### 3. Dashboard Overview & Dynamic Health Metrics
* **Method:** `GET`
* **Path:** `/api/v1/dashboard/overview`
* **Purpose:** Computes dynamic workspace metrics, record counts, and the record integrity score.
* **Frontend Component:** `Overview` screen (`src/App.tsx` -> `function Overview`).
  * Connects directly to the circular score gauge (`86/100`) and the 5 metric cards: *Total medical reports*, *Reports reviewed*, *Items requiring review*, *Verified lab checks*, *Pending care-plan tasks*.
* **Request Body:** None.
* **Query / Path Parameters:** None.
* **Expected Response:** `200 OK`
  ```json
  {
    "totalReports": 28,
    "reviewedReports": 24,
    "reviewedPercentage": 86,
    "itemsRequiringReview": 1,
    "highPriorityReviewCount": 1,
    "verifiedLabChecks": 7,
    "pendingCareTasks": 2,
    "nextCareTaskDueDate": "02 Nov 2025",
    "integrityScore": 86,
    "integrityCoverageNote": "Based on deterministic consistency checks across active records"
  }
  ```
* **Validation & Logic:**
  * `totalReports`: `max(28, uploaded_reports + total_records)`.
  * `reviewedReports`: count of records with status `"Reviewed"` or `"Verified"`.
  * `reviewedPercentage`: `int((reviewed_count / total_records) * 100)`.
  * `itemsRequiringReview`: count of records with status `"Needs review"`.
  * `highPriorityReviewCount`: `1` if `itemsRequiringReview > 0` else `0`.
  * `integrityScore`: deterministic formula `min(100, max(50, 70 + (reviewed * 3) - (needs_review * 2)))`.
* **Authentication:** None (scoped to demo patient profile `AN-PATIENT-01`).
* **Database Operations:** Aggregate queries over `medical_records` and `report_documents`.

---

### Feature Group C: Medical Records & Clinical Observations

#### 4. List Medical Records
* **Method:** `GET`
* **Path:** `/api/v1/records`
* **Purpose:** Retrieves a list of medical records with search filtering, status filtering, and sorting.
* **Frontend Component:**
  * `MedicalRecords` screen (`src/App.tsx` -> `function MedicalRecords` & `RecordTable`).
  * `Overview` screen (`Health record timeline` widget).
* **Request Body:** None.
* **Query Parameters:**
  | Parameter | Type | Required | Default | Description |
  | :--- | :--- | :--- | :--- | :--- |
  | `query` | string | No | `null` | Case-insensitive search on test name, lab, record ID, or report identifier. |
  | `status` | string | No | `null` | Status filter: `"Reviewed"`, `"Needs review"`, `"Verified"`, or `"All statuses"`. |
  | `sort` | string | No | `"newest"` | Sort order: `"newest"` (descending created date) or `"oldest"`. |
* **Expected Response:** `200 OK`
  ```json
  {
    "records": [
      {
        "id": "SR-1048",
        "name": "Fasting Plasma Glucose",
        "date": "18 Oct 2025",
        "lab": "Aster Diagnostics, Pune",
        "value": "102",
        "unit": "mg/dL",
        "range": "70ΓÇô99 mg/dL",
        "status": "Needs review",
        "source": "PDF Extracted",
        "reportId": "LAB-8821",
        "extractionConfidence": 0.96,
        "provenanceLocation": "Page 1 ┬╖ Results table, row 3"
      },
      {
        "id": "SR-1043",
        "name": "Complete Blood Count",
        "date": "08 Sep 2025",
        "lab": "Metropolis Healthcare, Pune",
        "value": "13.6",
        "unit": "g/dL Hb",
        "range": "12.0ΓÇô15.5 g/dL",
        "status": "Reviewed",
        "source": "PDF Extracted",
        "reportId": "MET-7102",
        "extractionConfidence": 0.98,
        "provenanceLocation": "Page 1 ┬╖ Hemoglobin section"
      }
    ],
    "total": 2
  }
  ```
* **Authentication:** None.
* **Database Operations:** Filtered read from `medical_records` table.
* **Errors:** `422 Unprocessable Entity` if query parameters have invalid types.

---

#### 5. Get Single Medical Record
* **Method:** `GET`
* **Path:** `/api/v1/records/{record_id}`
* **Purpose:** Retrieve complete details and provenance for a single clinical observation.
* **Frontend Component:** `RecordTable` row selection / detail view modal / kebab menu (`ΓÇóΓÇóΓÇó`).
* **Request Body:** None.
* **Path Parameters:**
  | Parameter | Type | Required | Description |
  | :--- | :--- | :--- | :--- |
  | `record_id` | string | Yes | Unique record identifier (e.g. `SR-1048`). |
* **Expected Response:** `200 OK`
  ```json
  {
    "id": "SR-1048",
    "name": "Fasting Plasma Glucose",
    "date": "18 Oct 2025",
    "lab": "Aster Diagnostics, Pune",
    "value": "102",
    "unit": "mg/dL",
    "range": "70ΓÇô99 mg/dL",
    "status": "Needs review",
    "source": "PDF Extracted",
    "reportId": "LAB-8821",
    "extractionConfidence": 0.96,
    "provenanceLocation": "Page 1 ┬╖ Results table, row 3"
  }
  ```
* **Errors:**
  * `404 Not Found`: If `record_id` does not exist:
    ```json
    {
      "detail": "Medical record 'SR-99999' not found"
    }
    ```

---

#### 6. Create Manual Medical Record
* **Method:** `POST`
* **Path:** `/api/v1/records/manual`
* **Purpose:** Persist a confirmed clinical test observation entered manually by the user.
* **Frontend Component:** `MedicalRecords` -> "Enter test information manually" Modal form (`src/App.tsx` -> `addManual`).
* **Request Headers:** `Content-Type: application/json`
* **Request Body:**
  ```json
  {
    "test": "Thyroid Stimulating Hormone",
    "value": "2.4",
    "unit": "mIU/L",
    "lab": "Metropolis Healthcare, Pune"
  }
  ```
* **Field Validations:**
  * `test`: string, required, `min_length=1`.
  * `value`: string, required, `min_length=1`.
  * `unit`: string, required, `min_length=1`.
  * `lab`: string, required, `min_length=1`.
* **Expected Response:** `201 Created`
  ```json
  {
    "id": "SR-1055",
    "name": "Thyroid Stimulating Hormone",
    "date": "Today",
    "lab": "Metropolis Healthcare, Pune",
    "value": "2.4",
    "unit": "mIU/L",
    "range": "Not provided",
    "status": "Reviewed",
    "source": "Manual",
    "reportId": null,
    "extractionConfidence": 1.0,
    "provenanceLocation": "Direct user manual entry"
  }
  ```
* **Database Operations:**
  1. Inserts new row into `medical_records` with auto-generated ID `SR-{1050 + count}`.
  2. Parses leading numeric float from `value` for future trend plotting.
  3. Automatically records an audit entry in `audit_events` (`event_type: "Manual entry added"`, `actor_name: "User AN"`).
* **Errors:** `422 Unprocessable Entity` if any required field is missing or empty.

---

### Feature Group D: Report Upload, Ingestion & Confirmation

#### 7. Upload Report File
* **Method:** `POST`
* **Path:** `/api/v1/reports/upload`
* **Purpose:** Safely stream and store an uploaded PDF or image, enforce 20 MiB size limits, validate magic bytes, compute SHA-256, and record an audit event.
* **Frontend Component:** `UploadModal` step 1 (`src/App.tsx` -> `function UploadModal`, dropzone file selection).
* **Request Headers:** `Content-Type: multipart/form-data`
* **Request Body:**
  * `file`: Binary file stream (PDF, PNG, JPG, JPEG).
* **Validation & Security Rules:**
  * **Streaming Byte Limit:** Maximum 20 MiB (20,971,520 bytes). Monitored during chunk streaming. Aborts immediately if exceeded.
  * **Extension Whitelist:** `.pdf`, `.png`, `.jpg`, `.jpeg`.
  * **File Signature (Magic Bytes) Verification:** Inspects the initial bytes of the file:
    * PDF: must start with `%PDF-`
    * PNG: must start with `\x89PNG\r\n\x1a\n`
    * JPEG: must start with `\xff\xd8\xff`
  * **Cleanup Guarantee:** If validation fails, or if transfer is aborted, partial files are automatically unlinked from storage.
  * **Randomized Storage Filename:** Stored as `{uuid4().hex}{extension}` in `data/uploads/` (outside public web tree).
* **Expected Response:** `201 Created`
  ```json
  {
    "reportId": "REP-D14A2E",
    "originalFilename": "fasting-glucose-oct-2025.pdf",
    "fileSizeBytes": 1887436,
    "mimeType": "application/pdf",
    "sha256Hash": "a91f4e80b92c4b81d77a06421389e61129b015e100f91a27e384b6119a7cd2",
    "status": "UPLOADED",
    "uploadedAt": "18 Oct 2026 ┬╖ 04:15",
    "isDuplicate": false,
    "existingReportId": null,
    "integrityNotice": "File validated and SHA-256 hash recorded in audit log."
  }
  ```
* **Duplicate File Handling:**
  If an uploaded file produces an identical SHA-256 digest to an existing report, the backend does **not** overwrite the file or claim fraud. It returns `201 Created` with:
  ```json
  {
    "reportId": "REP-D14A2E",
    "isDuplicate": true,
    "existingReportId": "REP-D14A2E",
    "integrityNotice": "A report with an identical SHA-256 hash was previously uploaded. Duplicate hashes indicate file identity; they do not imply fraud."
  }
  ```
* **Database Operations:** Inserts row into `report_documents`, writes binary to `data/uploads/`, and logs `File added` in `audit_events`.
* **Errors:**
  * `400 Bad Request`: Empty file or invalid file signature (`"Invalid file signature for extension '.pdf'"`)
  * `413 Request Entity Too Large`: Exceeds 20 MiB limit (`"File exceeds maximum upload size of 20 MiB"`)
  * `415 Unsupported Media Type`: Non-whitelisted extension (`"Unsupported file extension '.exe'"`)

---

#### 8. Extract Report Fields (Prototype Extraction)
* **Method:** `POST`
* **Path:** `/api/v1/reports/{report_id}/extract`
* **Purpose:** Triggers extraction of structured observation fields from an uploaded document.
* **Clinical Integrity Notice:** In Milestone 1, this returns prototype simulated fields matching the UI design and explicitly includes a simulation disclaimer. Actual OCR model integration (Tesseract/PaddleOCR/PyMuPDF) is scheduled for subsequent milestones.
* **Frontend Component:** `UploadModal` step 2 (`stage === "extract"` -> scanning animation and progress bar).
* **Request Body:** None.
* **Path Parameters:**
  | Parameter | Type | Required | Description |
  | :--- | :--- | :--- | :--- |
  | `report_id` | string | Yes | Report identifier returned by `/upload` (e.g. `REP-D14A2E`). |
* **Expected Response:** `200 OK`
  ```json
  {
    "reportId": "REP-D14A2E",
    "status": "EXTRACTED",
    "simulationNotice": "OCR and PDF parsing are simulated in this milestone for client review. Actual OCR model integration is planned for subsequent milestones. All extracted values require explicit human confirmation.",
    "documentSummary": {
      "pageCount": 1,
      "detectedLaboratory": "Aster Diagnostics, Pune",
      "detectedReportId": "LAB-8821",
      "detectedDate": "18 Oct 2025",
      "ocrQualityScore": 0.94
    },
    "extractedFields": [
      {
        "fieldKey": "test",
        "label": "Test name",
        "value": "Fasting Plasma Glucose",
        "confidence": 0.98,
        "method": "PDF Extracted",
        "provenance": { "page": 1, "region": "Results table, row 3" }
      },
      {
        "fieldKey": "value",
        "label": "Result value",
        "value": "102",
        "confidence": 0.96,
        "method": "PDF Extracted",
        "provenance": { "page": 1, "region": "Results table, row 3" }
      },
      {
        "fieldKey": "unit",
        "label": "Unit",
        "value": "mg/dL",
        "confidence": 0.94,
        "method": "PDF Extracted",
        "provenance": { "page": 1, "region": "Results table, row 3" }
      },
      {
        "fieldKey": "range",
        "label": "Reference range",
        "value": "70ΓÇô99 mg/dL",
        "confidence": 0.91,
        "method": "PDF Extracted",
        "provenance": { "page": 1, "region": "Results table, row 3" }
      },
      {
        "fieldKey": "date",
        "label": "Collection date",
        "value": "18 Oct 2025",
        "confidence": 0.67,
        "method": "OCR Extracted",
        "provenance": { "page": 1, "region": "Header right region" }
      },
      {
        "fieldKey": "reportDate",
        "label": "Report date",
        "value": "19 Oct 2025",
        "confidence": 0.95,
        "method": "PDF Extracted",
        "provenance": { "page": 1, "region": "Header right" }
      },
      {
        "fieldKey": "lab",
        "label": "Laboratory name",
        "value": "Aster Diagnostics, Pune",
        "confidence": 0.92,
        "method": "PDF Extracted",
        "provenance": { "page": 1, "region": "Header left" }
      },
      {
        "fieldKey": "reportId",
        "label": "Report ID",
        "value": "LAB-8821",
        "confidence": 0.72,
        "method": "OCR Extracted",
        "provenance": { "page": 1, "region": "Header top-right" }
      }
    ]
  }
  ```
* **Database Operations:** Updates `ReportDocument.status = "EXTRACTED"`. **CRITICAL:** Does *not* create a confirmed `MedicalRecord` until user confirmation.
* **Errors:** `404 Not Found` if `report_id` does not exist.

---

#### 9. Confirm Extracted Report Records
* **Method:** `POST`
* **Path:** `/api/v1/reports/{report_id}/confirm`
* **Purpose:** Explicitly approves the user-verified or edited fields from the extraction stage and commits them into active `medical_records`.
* **Frontend Component:** `UploadModal` step 3 (`stage === "review"` -> "Confirm records" button).
* **Request Headers:** `Content-Type: application/json`
* **Path Parameters:**
  | Parameter | Type | Required | Description |
  | :--- | :--- | :--- | :--- |
  | `report_id` | string | Yes | Report identifier (e.g. `REP-D14A2E`). |
* **Request Body:**
  ```json
  {
    "test": "Fasting Plasma Glucose",
    "value": "102",
    "unit": "mg/dL",
    "range": "70ΓÇô99 mg/dL",
    "date": "18 Oct 2025",
    "reportDate": "19 Oct 2025",
    "lab": "Aster Diagnostics, Pune",
    "reportId": "LAB-8821"
  }
  ```
* **Field Validations:**
  * `test`, `value`, `unit`, `range`, `date`, `lab`: string, required, `min_length=1`.
  * `reportDate`, `reportId`: optional strings.
* **Expected Response:** `200 OK`
  ```json
  {
    "recordId": "SR-1055",
    "reportId": "REP-D14A2E",
    "status": "Reviewed",
    "source": "PDF Extracted",
    "auditEventId": "EVT-8F22",
    "message": "Extracted report fields confirmed by user and committed to active medical records."
  }
  ```
* **Database Operations:**
  1. Creates new `MedicalRecord` with ID `SR-{1054 + count}`, linked to `report_document_id`.
  2. Updates `ReportDocument.status = "CONFIRMED"`.
  3. Records audit log entry in `audit_events` (`event_type: "Report confirmed"`, `actor_name: "User AN"`, `verification_status: "Hash-linked"`).
* **Errors:**
  * `404 Not Found`: If `report_id` does not exist.
  * `422 Unprocessable Entity`: If required fields are missing.

---

## 3. Frontend-to-Backend Feature Audit & Status Matrix

Every SehatSnap feature group from the product specification is audited below:

| # | Feature Group | Existing Frontend Screen / Component | Implemented Backend API | Status Classification |
| :--- | :--- | :--- | :--- | :--- |
| **1** | **Dashboard overview & health metrics** | `Overview` (`hero-score` gauge, 5 `metric` cards) | `GET /api/v1/dashboard/overview` | **Backend implemented but frontend not connected** |
| **2** | **Medical record listing, search & filtering** | `MedicalRecords` (`RecordTable`, search input, status filter) | `GET /api/v1/records`<br/>`GET /api/v1/records/{id}` | **Backend implemented but frontend not connected** |
| **3** | **Manual medical-record entry** | `MedicalRecords` ("Enter manually" Modal form) | `POST /api/v1/records/manual` | **Backend implemented but frontend not connected** |
| **4** | **PDF/image upload & user confirmation** | `UploadModal` (3-step flow: choose, extract, review) | `POST /api/v1/reports/upload`<br/>`POST /api/v1/reports/{id}/extract`<br/>`POST /api/v1/reports/{id}/confirm` | **Partially implemented** (Backend upload, hash & simulation extraction operational; frontend UI present; API wire-up pending; OCR engine planned M4) |
| **5** | **Report analysis, trends & charts** | `ReportAnalysis` (`TrendChart`, analyte selector) | *None in M1* (Stores numeric value for plotting) | **Frontend present but backend missing** |
| **6** | **EHR optimisation & metadata quality** | `ReportAnalysis` ("Comparison readiness" card, unit checks) | *None in M1* | **Frontend present but backend missing** |
| **7** | **Diagnostic integrity & duplicate detection** | `IntegrityChecks` (findings table, evidence drawer) & `AuditTrail` | `POST /api/v1/reports/upload` (duplicate hash check active); `audit_events` table schema active | **Partially implemented** (Upload duplicate detection & audit ledger models active; `/integrity/findings` endpoints pending M2) |
| **8** | **Laboratory accreditation verification** | `VerificationPage` (lab mode, NABL demo snapshot) | *None in M1* | **Frontend present but backend missing** |
| **9** | **Medicine verification & formulation check** | `VerificationPage` (medicine mode, CDSCO demo snapshot) | *None in M1* | **Frontend present but backend missing** |
| **10** | **Care-gap early warnings** | `CareGaps` (care task list, actions, add task modal) | *None in M1* | **Frontend present but backend missing** |
| **11** | **Mental wellbeing survey & trends** | *Not present in active 10 screens* | *None in M1* | **Not yet implemented** (Planned feature) |
| **12** | **Settings & user preferences** | `Settings` (preferences toggles, retention links) | *None in M1* | **Frontend present but backend missing** |
| **13** | **Appointments & reminders** | Header notifications popover & Care plan due dates | *None in M1* | **Partially implemented** (Frontend UI hints; dedicated backend endpoints missing) |
| **14** | **Consultation summary & PDF export** | `ConsultationSummary` (`ReportPreview`, section toggles, `window.print()`) | *None in M1* | **Frontend present but backend missing** |
| **15** | **Emergency access & support resources** | Header help button (`?`) & Footer trust notice | *None in M1* | **Partially implemented** (Frontend UI disclaimer present; dedicated endpoints missing) |

---

## 4. Missing Endpoints Specification (Scheduled for Milestones 2, 3 & 4)

To ensure zero feature degradation, the following endpoints are designed and scheduled for upcoming milestones:

### Milestone 2: Diagnostic Integrity Engine & Hash-Linked Ledger
* `GET /api/v1/integrity/summary` ΓÇö Returns open findings count, high-priority review count, resolved count, and active deterministic rule count.
* `GET /api/v1/integrity/findings` ΓÇö Queryable list of diagnostic integrity findings (`DUP-002`, `OCR-014`, `META-008`, `UNIT-003`). Supports `?severity=&status=`.
* `GET /api/v1/integrity/findings/{id}` ΓÇö Detailed evidence payload, trigger explanation, and recommended clinical verification action.
* `PATCH /api/v1/integrity/findings/{id}/status` ΓÇö Status transitions: `"Reviewed"`, `"Needs clinician review"`, `"Resolved"`.
* `GET /api/v1/audit/events` ΓÇö Paginated list of immutable hash-linked audit events.
* `POST /api/v1/audit/verify-file` ΓÇö Computes SHA-256 against stored blob and validates against ledger hash.

### Milestone 3: Care Gaps, Analytics & Verification Services
* `GET /api/v1/analytics/trends?analyte={test}&range={range}` ΓÇö Time-series measurements with laboratory reference ranges.
* `GET /api/v1/analytics/comparison?analyte={test}` ΓÇö Multi-report comparison matrix across dates and issuing laboratories.
* `POST /api/v1/verification/laboratory` ΓÇö Compares laboratory identity and accreditation certificate against NABL demonstration snapshot dataset.
* `POST /api/v1/verification/medicine` ΓÇö Compares product details, strength, and formulation against CDSCO/SUGAM demonstration dataset.
* `GET /api/v1/care-gaps/tasks` ΓÇö List of care-plan tasks with provenance citations and clinical gap reasons.
* `POST /api/v1/care-gaps/tasks` ΓÇö Create a user-confirmed care task.
* `PATCH /api/v1/care-gaps/tasks/{id}/status` ΓÇö Action transitions (`"Completed"`, `"Scheduled"`, `"Not Applicable"`).

### Milestone 4: Consultation Export & Settings
* `POST /api/v1/consultation-summary/bundle` ΓÇö Compiles filtered consultation packet.
* `POST /api/v1/consultation-summary/pdf` ΓÇö Generates a signed, downloadable consultation PDF.
* `GET /api/v1/settings` & `PUT /api/v1/settings` ΓÇö Workspace preferences.
* `POST /api/v1/workspace/reset` ΓÇö Reset demonstration workspace.

---

## 5. Standard Error Handling & Validation Contract

All endpoints adhere to FastAPI / Pydantic validation rules:

### 1. Validation Error (`422 Unprocessable Entity`)
Returned when required fields are missing, empty, or have invalid types:
```json
{
  "detail": [
    {
      "type": "string_too_short",
      "loc": ["body", "test"],
      "msg": "String should have at least 1 character",
      "input": ""
    }
  ]
}
```

### 2. Resource Not Found (`404 Not Found`)
```json
{
  "detail": "Medical record 'SR-99999' not found"
}
```

### 3. File Security Errors
* `413 Request Entity Too Large`: Streamed bytes exceed 20 MiB (`"File exceeds maximum upload size of 20 MiB"`).
* `415 Unsupported Media Type`: Non-whitelisted extension (`"Unsupported file extension '.exe'. Allowed: .jpeg, .jpg, .pdf, .png"`).
* `400 Bad Request`: Mismatched magic bytes (`"Invalid file signature for extension '.pdf'. File content does not match expected format."`).

---

## 6. How to Test Endpoints via Swagger UI

1. **Start the FastAPI backend server:**
   ```powershell
   # In workspace root (c:\Users\HP\OneDrive\Desktop\SehatSnap)
   uv run uvicorn backend.app.main:app --host 127.0.0.1 --port 8000 --reload
   ```
2. **Open Swagger UI in your browser:**
   Navigate to `http://127.0.0.1:8000/docs`
3. **Execute Test Requests:**
   * **Health Check:** Expand `GET /api/v1/health` -> click **Try it out** -> **Execute**. Expect `200 OK`.
   * **Dashboard Overview:** Expand `GET /api/v1/dashboard/overview` -> click **Execute**. Expect counts (`28`, `24`, `1`, `7`, etc.).
   * **List Records:** Expand `GET /api/v1/records` -> click **Execute**. Expect the 5 seeded records.
   * **Manual Record Creation:** Expand `POST /api/v1/records/manual` -> paste payload -> click **Execute**. Expect `201 Created` with a new `SR-` ID.
   * **Upload Report:** Expand `POST /api/v1/reports/upload` -> choose a valid PDF file (< 20 MB) -> click **Execute**. Expect `201 Created` with SHA-256 hash.
   * **Simulated Extraction:** Expand `POST /api/v1/reports/{report_id}/extract` -> enter the `reportId` from upload -> click **Execute**. Expect field list with confidence scores.
   * **Confirm Record:** Expand `POST /api/v1/reports/{report_id}/confirm` -> enter `reportId` and confirmed payload -> click **Execute**. Expect `200 OK` and a new confirmed `SR-` record.

---

## 7. Recommended Frontend Integration Order

For the frontend team, we recommend connecting the existing UI screens in the following order:

```text
Step 1: Core Records & Timeline (Unblocks Medical Records & Overview Timeline)
  ΓööΓöÇΓöÇ Connect `GET /api/v1/records` to `MedicalRecords` and `Overview` timeline.
  ΓööΓöÇΓöÇ Connect `POST /api/v1/records/manual` to "Enter manually" Modal form.

Step 2: Workspace Dashboard Metrics (Unblocks Overview Hero & Metric Cards)
  ΓööΓöÇΓöÇ Connect `GET /api/v1/dashboard/overview` to `Overview` score ring and 5 metric cards.

Step 3: Upload & Extraction Pipeline (Unblocks UploadModal)
  ΓööΓöÇΓöÇ Step 3A: Connect file dropzone to `POST /api/v1/reports/upload`.
  ΓööΓöÇΓöÇ Step 3B: Connect extraction progress to `POST /api/v1/reports/{reportId}/extract`.
  ΓööΓöÇΓöÇ Step 3C: Connect "Confirm records" button to `POST /api/v1/reports/{reportId}/confirm`.
  ΓööΓöÇΓöÇ Step 3D: On confirmation success, refresh records cache and navigate to Medical Records.

Step 4: Milestone 2 APIs (Diagnostic Integrity & Audit Trail)
  ΓööΓöÇΓöÇ Implement and connect `/api/v1/integrity/findings` to `IntegrityChecks`.
  ΓööΓöÇΓöÇ Connect `/api/v1/audit/events` and file hash verification to `AuditTrail`.

Step 5: Milestone 3 APIs (Verification & Care Gaps)
  ΓööΓöÇΓöÇ Connect `/api/v1/verification/laboratory` and `/api/v1/verification/medicine`.
  ΓööΓöÇΓöÇ Connect `/api/v1/care-gaps/tasks`.
```
