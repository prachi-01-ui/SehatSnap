# SehatSnap Frontend-to-Backend Integration Mapping

## 1. Executive Summary & Architecture Overview

This document provides a comprehensive mapping between the existing **SehatSnap** frontend and the proposed backend service architecture for integration.

SehatSnap is a health data workspace and diagnostic integrity platform designed to help patients and clinicians verify health records, track analyte trends across laboratory tests, identify documentation inconsistencies via deterministic rules, and verify laboratory and pharmaceutical credentials against authoritative datasets.

> **Important Safety & Compliance Notice**: SehatSnap supports medical record quality, provenance, and data verification. It does **not** diagnose conditions, prescribe treatments, or replace professional medical judgment. All automated checks and demonstrations use synthetic data.

---

### 1.1 Technical Stack & Runtime Environment

| Layer | Technology | Details |
| :--- | :--- | :--- |
| **Framework** | React 19 (`^19.0.0`), React DOM 19 (`^19.0.0`) | Client-side Single Page Application (SPA) |
| **Build Tooling** | Vite 8 (`^8.0.5`), `@vitejs/plugin-react` (`^6.0.0`) | Fast HMR dev server running on port 8443 |
| **Styling** | Tailwind CSS v4 (`^4.0.0`), `@tailwindcss/vite` | Modern utility classes with `@import "tailwindcss";` in `src/index.css` |
| **Language** | TypeScript 5.7 (`^5.7.0`) | Strict mode typing (`tsconfig.json`) |
| **Formatter** | oxfmt (`^0.2.0`) | Fast code formatting |

---

### 1.2 Application Entry Points

- **HTML Host Shell**: [`frontend/index.html`](file:///c:/Users/HP/Desktop/Sehat/frontend/index.html)
  - Provides the `#root` DOM mount point and loads `/src/main.tsx`.
- **Application Bootstrapper**: [`frontend/src/main.tsx`](file:///c:/Users/HP/Desktop/Sehat/frontend/src/main.tsx)
  - Imports `src/index.css` and mounts `<App />` within `<React.StrictMode>`.
- **Primary View Container**: [`frontend/src/App.tsx`](file:///c:/Users/HP/Desktop/Sehat/frontend/src/App.tsx)
  - Contains the app shell, sidebar navigation, topbar header, page routing logic, modals, and screen implementations.

---

### 1.3 Routing Architecture

The current frontend does **not** employ a history-based routing library (such as `react-router-dom`). Instead, it uses **state-based routing** managed at the root component level in `App.tsx`:

```typescript
type Page =
  | "Overview"
  | "Medical Records"
  | "Report Analysis"
  | "Integrity Checks"
  | "Laboratory Verification"
  | "Medicine Verification"
  | "Care Gaps"
  | "Consultation Summary"
  | "Audit Trail"
  | "Settings";
```

Navigation is triggered via `setPage(name: Page)` inside the sidebar and various contextual quick-action buttons throughout the views.

---

### 1.4 Reusable Component Library

The frontend defines lightweight, unified design primitives inside [`src/App.tsx`](file:///c:/Users/HP/Desktop/Sehat/frontend/src/App.tsx):

| Component | Props / Signature | Responsibility |
| :--- | :--- | :--- |
| `Icon` | `{ name: string, size?: number }` | Inline SVG icon renderer supporting 20+ icons (`grid`, `file`, `chart`, `shield`, `flask`, `pill`, `calendar`, `clipboard`, `link`, `settings`, `search`, `bell`, `plus`, `upload`, `check`, `alert`, `eye`, `menu`, `x`, `arrow`, `download`) |
| `Badge` | `{ children: ReactNode, tone?: string }` | Status badge indicator supporting tones: `verified`, `review`, `danger`, `info`, `neutral` |
| `Button` | `{ variant?: string, icon?: string, onClick?: () => void, type?: "button" \| "submit", disabled?: boolean }` | Standardized button supporting variants: `primary`, `secondary`, `ghost` |
| `Card` | `{ children: ReactNode, className?: string }` | Bordered white container card with soft drop-shadow |
| `SectionTitle` | `{ title: string, subtitle?: string, action?: ReactNode }` | Section header with optional trailing action button or segmented control |
| `TrendChart` | `{ kind?: "glucose" \| "haemoglobin" }` | Responsive SVG time-series chart showing reference ranges, trend line, hover tooltips, and data points |
| `PageIntro` | `{ title: string, text: string, actions?: ReactNode }` | Standardized screen hero title with supporting subtitle and top-right CTA action group |
| `Field` | `{ label: string, name: string, placeholder?: string, required?: boolean, defaultValue?: string, badge?: string }` | Labeled form input field with optional confidence/provenance badge |
| `Modal` | `{ title: string, onClose: () => void, children: ReactNode }` | Accessible dialog overlay with backdrop dismiss and header |
| `Drawer` | `{ title: string, onClose: () => void, children: ReactNode }` | Right-side sliding panel for deep contextual inspection (e.g., finding evidence) |
| `RecordTable` | `{ records: RecordItem[] }` | Tabular display of medical records with source tags, status badges, and an empty-search fallback |
| `Header` (TopBar) | `{ page: Page, onMenu: () => void, onAdd: () => void }` | Sticky header with breadcrumb, search bar, notification popover, profile card, and "Add Record" button |
| `Sidebar` | `{ page: Page, setPage: (p: Page) => void, open: boolean, collapse: boolean, setCollapse: (v: boolean) => void }` | Fixed left navigation with brand logo, nav buttons, privacy status indicator, and collapse toggle |

---

## 2. Component Data Dependency & State Inventory

| Component / Screen | Current Data State | Backend Dependency Level | Primary Entity |
| :--- | :--- | :--- | :--- |
| **Topbar (`Header`)** | Static mock name ("Aarav N."), static notification alert count (2) | Medium | Patient Profile, Unread Alerts |
| **Dashboard (`Overview`)** | Static metrics (`28`, `24`, `4`, `7`, `2`), static integrity score (`86/100`), static chart data | High | Integrity Score Summary, Dashboard Metrics, Recent Timeline |
| **`MedicalRecords`** | Local `useState` seeded with 5 mock records (`initialRecords`) | High | Patient Test Records (CRUD) |
| **`UploadModal`** | Simulated OCR/PDF extraction via `setTimeout` (1200ms) with hardcoded fields | Critical | Document Ingestion, OCR / Field Extraction Pipeline |
| **`ReportAnalysis`** | Hardcoded SVG coordinates for Glucose/Hb, static comparison cards | High | Longitudinal Analyte Data, Unit Compatibility Service |
| **`IntegrityChecks`** | Static `findings` array (4 items); status stored in ephemeral local component state | High | Deterministic Rules Engine, Finding Resolution |
| **`LaboratoryVerification`** | Form with simulated 900ms delay, returns static `LabResult` (Metropolis Healthcare) | High | NABL / Registry Lookup Provider |
| **`MedicineVerification`** | Form with simulated 900ms delay, returns static `MedicineResult` (Glycomet 500) | High | CDSCO / SUGAM Product Dataset Provider |
| **`CareGaps`** | Local `useState` seeded with 3 tasks; additions/status changes kept in memory | High | Care Plan Tracker, Clinical Protocol Gap Monitor |
| **`ConsultationSummary`** | Local checkboxes toggling static preview sections; prints via `window.print()` | Medium | Consultation Packet Generator / PDF Exporter |
| **`AuditTrail`** | Static toggle between matching and mismatched hash strings; static 3-event log | High | Tamper-Evident SHA-256 Audit Log Service |
| **`Settings`** | Local toggle state; simulated save timeout | Medium | User Preferences / Workspace Config |

---

## 3. Screen-by-Screen API Mapping Specification

All proposed backend endpoints are marked clearly as **`[PROPOSED]`**.

---

### 3.1 Report Ingestion & Extraction (`UploadModal`)

- **Screen Location**: `App.tsx` (Lines 285–320, triggered via `Header`, `Overview`, `MedicalRecords`)
- **Workflow Stages**:
  1. `choose`: File selection (PDF, PNG, JPG, JPEG up to 20MB) or URL import.
  2. `extract`: Progress animation simulating document parsing and provenance mapping.
  3. `review`: Review of extracted fields, confidence scores, and source location before committing.

#### 3.1.1 Document Extraction Endpoint
- **Endpoint**: `[PROPOSED]` `POST /api/v1/reports/extract`
- **Purpose**: Uploads a medical report document (PDF/Image) and runs OCR + structured medical entity extraction.
- **Request**:
  - `Content-Type`: `multipart/form-data`
  - Body:
    - `file`: Binary file (PDF, PNG, JPG, JPEG, max 20 MB)
- **Response** (`200 OK`):
  ```json
  {
    "extractionId": "ext_98210384",
    "documentHash": "a91f4e80b92c4b5d6e7f8a9b0c1d2e3f4a5b6c7d8e9f0a1b2c3d4e5f6a7b8c9d",
    "pageCount": 1,
    "fields": {
      "test": { "value": "Fasting Plasma Glucose", "confidence": 0.98, "source": "PDF Extracted" },
      "value": { "value": "102", "confidence": 0.96, "source": "PDF Extracted" },
      "unit": { "value": "mg/dL", "confidence": 0.94, "source": "PDF Extracted" },
      "range": { "value": "70–99 mg/dL", "confidence": 0.91, "source": "PDF Extracted" },
      "date": { "value": "2025-10-18", "confidence": 0.67, "source": "OCR Extracted" },
      "reportDate": { "value": "2025-10-19", "confidence": 0.95, "source": "PDF Extracted" },
      "lab": { "value": "Aster Diagnostics, Pune", "confidence": 0.92, "source": "PDF Extracted" },
      "reportId": { "value": "LAB-8821", "confidence": 0.72, "source": "OCR Extracted" }
    },
    "provenance": {
      "pageNumber": 1,
      "region": "Results table, row 3",
      "boundingBox": { "x": 120, "y": 340, "width": 450, "height": 32 }
    }
  }
  ```
- **UI States**:
  - **Loading**: Renders `.extracting` stage with animated icon, progress bar, and step messages ("File validated", "Reading page 1 of 1").
  - **Success**: Transitions to `review` stage, displaying pre-populated editable fields with extraction confidence badges (e.g., `PDF Extracted · 98%`, `OCR Extracted · 67%`).
  - **Empty**: User has not selected a file (dropzone displays placeholder text and upload icon).
  - **Error**: Displays validation toast/alert if file format is invalid, size exceeds 20MB, or OCR parser fails.

#### 3.1.2 Record Confirmation Endpoint
- **Endpoint**: `[PROPOSED]` `POST /api/v1/records/confirm`
- **Purpose**: Persists the user-verified record into the database and generates an audit log entry.
- **Request** (`application/json`):
  ```json
  {
    "extractionId": "ext_98210384",
    "documentHash": "a91f4e80b92c4b5d6e7f8a9b0c1d2e3f4a5b6c7d8e9f0a1b2c3d4e5f6a7b8c9d",
    "testName": "Fasting Plasma Glucose",
    "value": "102",
    "unit": "mg/dL",
    "referenceRange": "70–99 mg/dL",
    "collectionDate": "2025-10-18",
    "reportDate": "2025-10-19",
    "laboratoryName": "Aster Diagnostics, Pune",
    "reportIdentifier": "LAB-8821",
    "userApproved": true
  }
  ```
- **Response** (`201 Created`):
  ```json
  {
    "id": "SR-1054",
    "status": "Reviewed",
    "createdAt": "2026-10-18T02:30:00Z",
    "auditEventId": "EVT-8F24"
  }
  ```

---

### 3.2 Dashboard Screen (`Overview`)

- **Screen Location**: `App.tsx` (Lines 140–172)
- **Key Sections**:
  - Hero Score (`86/100` Record Integrity Score based on deterministic rules)
  - 5 Metric Summary Cards (Total reports, Reviewed count, Requiring review, Verified lab checks, Pending care-plan tasks)
  - Quick Actions (Upload report, Enter test, Verify lab, Verify medicine, Consultation PDF)
  - Measurement Trends Card (segmented toggle: Glucose vs Haemoglobin)
  - Integrity Alerts Card (top 3 alerts)
  - Health Record Timeline Card (top 4 recent records)
  - Care Plan Summary Card (2 upcoming items)

#### 3.2.1 Dashboard Summary Endpoint
- **Endpoint**: `[PROPOSED]` `GET /api/v1/dashboard/summary`
- **Request**: Headers: `Authorization: Bearer <token>`
- **Response** (`200 OK`):
  ```json
  {
    "integrityScore": {
      "score": 86,
      "maxScore": 100,
      "label": "Good coverage",
      "ruleCount": 12
    },
    "metrics": {
      "totalReports": 28,
      "totalReportsDelta": "+3 this month",
      "reportsReviewed": 24,
      "reportsReviewedPercentage": 86,
      "itemsRequiringReview": 4,
      "highPriorityReviewCount": 1,
      "verifiedLabChecks": 7,
      "pendingCarePlanTasks": 2,
      "nextTaskDue": "02 Nov 2025"
    },
    "recentAlerts": [
      {
        "id": "DUP-002",
        "title": "Conflicting report identifiers",
        "severity": "High-Priority Review",
        "report": "SR-1048",
        "when": "Today, 09:42"
      }
    ],
    "timeline": [
      {
        "id": "SR-1048",
        "name": "Fasting Plasma Glucose",
        "date": "18 Oct 2025",
        "lab": "Aster Diagnostics, Pune",
        "value": "102",
        "unit": "mg/dL",
        "range": "70–99 mg/dL",
        "status": "Needs review",
        "source": "PDF Extracted"
      }
    ],
    "upcomingTasks": [
      {
        "id": "task_1",
        "title": "Repeat fasting glucose",
        "dueDate": "02 Nov 2025",
        "reason": "No matching test record found in the available history.",
        "status": "Needs Review"
      }
    ]
  }
  ```
- **UI States**:
  - **Loading**: Skeleton placeholders for score ring, metric cards, and timeline rows.
  - **Success**: Populates score circle, summary cards, trend preview, alert badges, and timeline rows.
  - **Empty**: Zero-state banner: "No health records uploaded yet. Upload your first laboratory report to generate integrity metrics."
  - **Error**: Error banner in hero section: "Unable to load workspace metrics. Retry connection."

---

### 3.3 Medical Records (`MedicalRecords`)

- **Screen Location**: `App.tsx` (Lines 174–193)
- **Features**: Search bar, status filter dropdown (`All statuses`, `Reviewed`, `Needs review`, `Verified`), sort dropdown (`Newest first`, `Oldest first`), count badge, records table with kebab menu, and "Enter test information manually" modal.

#### 3.3.1 Get Records List Endpoint
- **Endpoint**: `[PROPOSED]` `GET /api/v1/records`
- **Request**:
  - Query Parameters:
    - `query`: string (optional search term)
    - `status`: `"All"` | `"Reviewed"` | `"Needs review"` | `"Verified"`
    - `sortBy`: `"newest"` | `"oldest"`
    - `limit`: number (default: 50)
    - `offset`: number (default: 0)
- **Response** (`200 OK`):
  ```json
  {
    "total": 5,
    "records": [
      {
        "id": "SR-1048",
        "name": "Fasting Plasma Glucose",
        "date": "18 Oct 2025",
        "lab": "Aster Diagnostics, Pune",
        "value": "102",
        "unit": "mg/dL",
        "range": "70–99 mg/dL",
        "status": "Needs review",
        "source": "PDF Extracted"
      },
      {
        "id": "SR-1043",
        "name": "Complete Blood Count",
        "date": "08 Sep 2025",
        "lab": "Metropolis Healthcare, Pune",
        "value": "13.6",
        "unit": "g/dL Hb",
        "range": "12.0–15.5 g/dL",
        "status": "Reviewed",
        "source": "PDF Extracted"
      }
    ]
  }
  ```
- **UI States**:
  - **Loading**: Table displays animated skeleton rows.
  - **Success**: Renders table rows with record name, collection date, lab name, bold result, reference range, source badge, and status badge.
  - **Empty**: Renders `.empty` div: "No matching records — Try a different search term or status filter."
  - **Error**: Displays inline error banner with a "Retry" button.

#### 3.3.2 Create Manual Record Endpoint
- **Endpoint**: `[PROPOSED]` `POST /api/v1/records`
- **Request** (`application/json`):
  ```json
  {
    "name": "Thyroid Stimulating Hormone",
    "value": "2.4",
    "unit": "mIU/L",
    "lab": "Metropolis Healthcare, Pune",
    "range": "0.4–4.0 mIU/L",
    "date": "2026-10-18",
    "source": "Manual"
  }
  ```
- **Response** (`201 Created`):
  ```json
  {
    "id": "SR-1055",
    "status": "Reviewed",
    "source": "Manual",
    "createdAt": "2026-10-18T02:35:00Z"
  }
  ```

---

### 3.4 Report Analysis (`ReportAnalysis`)

- **Screen Location**: `App.tsx` (Lines 198–204)
- **Key Sections**:
  - Filter bar: Analyte selector (`Fasting Plasma Glucose` vs `Haemoglobin`), Date range selector (`Last 12 months` vs `All available history`), Units compatible status tag.
  - "Values over time" card with embedded `TrendChart` SVG.
  - "Comparison readiness" card showing deterministic unit check breakdown (comparable values count, supported conversions count, excluded values count).
  - "Side-by-side report comparison" table showing source reports, numerical values, reference ranges, report IDs, and data quality flags.

#### 3.4.1 Analyte Trends & Comparison Endpoint
- **Endpoint**: `[PROPOSED]` `GET /api/v1/analysis/trends`
- **Request**:
  - Query Parameters:
    - `analyte`: `"glucose"` | `"haemoglobin"` | string
    - `dateRange`: `"12m"` | `"all"`
- **Response** (`200 OK`):
  ```json
  {
    "analyte": "glucose",
    "analyteDisplayName": "Fasting Plasma Glucose",
    "baseUnit": "mg/dL",
    "unitsCompatible": true,
    "points": [
      { "date": "2025-02-14", "monthLabel": "Feb", "value": 89, "unit": "mg/dL", "inRange": true },
      { "date": "2025-04-10", "monthLabel": "Apr", "value": 93, "unit": "mg/dL", "inRange": true },
      { "date": "2025-07-12", "monthLabel": "Jul", "value": 96, "unit": "mg/dL", "inRange": true },
      { "date": "2025-09-08", "monthLabel": "Sep", "value": 102, "unit": "mg/dL", "inRange": false },
      { "date": "2025-10-18", "monthLabel": "Oct", "value": 100, "unit": "mg/dL", "inRange": false }
    ],
    "referenceRange": {
      "min": 70,
      "max": 99,
      "unit": "mg/dL"
    },
    "comparisonReadiness": {
      "comparableValuesCount": 5,
      "supportedConversionsCount": 1,
      "supportedConversionNote": "100 mg/dL ≈ 5.55 mmol/L",
      "excludedCount": 1,
      "excludedNote": "Analyte context unavailable"
    },
    "sideBySide": [
      {
        "reportId": "SR-1048",
        "date": "18 Oct 2025",
        "lab": "Aster Diagnostics",
        "valueFormatted": "102 mg/dL",
        "rangeFormatted": "70–99 mg/dL",
        "identifier": "LAB-8821",
        "qualityFlag": "Identifier conflict",
        "qualityTone": "review"
      },
      {
        "reportId": "SR-1031",
        "date": "12 Jul 2025",
        "lab": "Aster Diagnostics",
        "valueFormatted": "96 mg/dL",
        "rangeFormatted": "70–99 mg/dL",
        "identifier": "LAB-8614",
        "qualityFlag": "Reviewed",
        "qualityTone": "verified"
      },
      {
        "reportId": "SR-1022",
        "date": "04 Apr 2025",
        "lab": "CarePlus Labs",
        "valueFormatted": "5.55 mmol/L",
        "rangeFormatted": "3.9–5.5 mmol/L",
        "identifier": "CP-2410",
        "qualityFlag": "Convertible",
        "qualityTone": "info"
      }
    ]
  }
  ```
- **UI States**:
  - **Loading**: Chart container displays pulsating gradient placeholder.
  - **Success**: Renders SVG polyline trend line, reference range box, interactive data point hover titles, and side-by-side comparison cards.
  - **Empty**: "No longitudinal records found for this analyte in the chosen time window."
  - **Error**: "Failed to compute analyte trend. Verify report unit consistency."

---

### 3.5 Diagnostic Integrity Engine (`IntegrityChecks`)

- **Screen Location**: `App.tsx` (Lines 207–216)
- **Key Sections**:
  - Compact metrics: Open findings (`4`), High-priority review (`1`), Resolved this month (`9`), Rules active (`12`).
  - Findings table with severities (`High-Priority Review`, `Review`, `Info`), source report link, detection timestamp, status tag, and recommended action.
  - Slide-out `Drawer` displaying finding evidence, deterministic rule trigger rationale, and action buttons (`Mark reviewed`, `Needs clinician review`, `Resolve`).

#### 3.5.1 Findings List & Integrity Metrics Endpoint
- **Endpoint**: `[PROPOSED]` `GET /api/v1/integrity/findings`
- **Request**:
  - Query Parameters:
    - `severity`: `"all"` | `"High-Priority Review"` | `"Review"` | `"Info"`
    - `status`: `"open"` | `"resolved"` | `"all"`
- **Response** (`200 OK`):
  ```json
  {
    "summary": {
      "openFindings": 4,
      "highPriorityReview": 1,
      "resolvedThisMonth": 9,
      "rulesActive": 12,
      "lastScanTimestamp": "Today, 09:42"
    },
    "findings": [
      {
        "id": "DUP-002",
        "title": "Conflicting report identifiers",
        "severity": "High-Priority Review",
        "reportId": "SR-1048",
        "detectedAt": "Today, 09:42",
        "status": "Inconclusive",
        "evidence": "Report ID LAB-8821 appears on two files with different glucose values.",
        "ruleRationale": "The deterministic rule compared report metadata and observed a condition outside the configured consistency criteria.",
        "recommendedAction": "Compare both originals with the issuing laboratory."
      },
      {
        "id": "OCR-014",
        "title": "Low-confidence OCR extraction",
        "severity": "Review",
        "reportId": "SR-1022",
        "detectedAt": "Today, 09:41",
        "status": "Inconclusive",
        "evidence": "Collection date extracted at 67% confidence from page 1, upper-right region.",
        "ruleRationale": "Field confidence fell below the 80% threshold required for automated verification.",
        "recommendedAction": "Review the source image and confirm the date."
      }
    ]
  }
  ```

#### 3.5.2 Update Finding Resolution Endpoint
- **Endpoint**: `[PROPOSED]` `PATCH /api/v1/integrity/findings/{findingId}`
- **Request** (`application/json`):
  ```json
  {
    "status": "Reviewed"
  }
  ```
  *(Allowed statuses: `"Reviewed"`, `"Needs clinician review"`, `"Resolved"`)*
- **Response** (`200 OK`):
  ```json
  {
    "id": "DUP-002",
    "status": "Reviewed",
    "updatedAt": "2026-10-18T02:40:00Z",
    "updatedBy": "User AN"
  }
  ```
- **UI States**:
  - **Loading**: Drawer actions disable with a miniature spinner.
  - **Success**: Status badge in table updates to `"Reviewed"`, `"Needs clinician review"`, or `"Resolved"`. If resolved, drawer automatically closes.
  - **Empty**: "No open integrity findings detected across current records."
  - **Error**: Inline drawer alert: "Unable to update finding status. Please try again."

---

### 3.6 Laboratory Verification (`LaboratoryVerification`)

- **Screen Location**: `App.tsx` (Lines 218–235, rendered via `VerificationPage` with `medicine=false`)
- **Key Sections**:
  - Search Form: Laboratory name, City/location, Accreditation / certificate number, Test name or discipline.
  - Demonstration disclaimer notice: Synthetic official-source snapshot.
  - Result Card (`LabResult`): Verified badge, match confidence (`96%`), matched criteria breakdown list, official source reference (`NABL directory demonstration snapshot`), expandable evidence panel.

#### 3.6.1 Laboratory Accreditation Verification Endpoint
- **Endpoint**: `[PROPOSED]` `POST /api/v1/verify/laboratory`
- **Request** (`application/json`):
  ```json
  {
    "laboratoryName": "Metropolis Healthcare Ltd.",
    "city": "Pune, Maharashtra",
    "certificateNumber": "MC-2104",
    "discipline": "Clinical Biochemistry"
  }
  ```
- **Response** (`200 OK`):
  ```json
  {
    "matchConfidence": 0.96,
    "verdict": "Verified Against Official Source",
    "laboratory": {
      "name": "Metropolis Healthcare Ltd.",
      "location": "Pune, Maharashtra",
      "certificateNumber": "MC-2104",
      "validThrough": "2026-03-31"
    },
    "checks": [
      { "item": "Laboratory identity", "details": "Exact name match", "status": "verified" },
      { "item": "Location", "details": "Pune location matched", "status": "verified" },
      { "item": "Accreditation status", "details": "Active in demo dataset", "status": "verified" },
      { "item": "Certificate validity", "details": "Valid through 31 Mar 2026", "status": "verified" },
      { "item": "Requested scope", "details": "Clinical Biochemistry listed", "status": "verified" },
      { "item": "Outstanding questions", "details": "Collection centre relationship not checked", "status": "review" }
    ],
    "sourceReference": {
      "authority": "NABL directory demonstration snapshot",
      "retrievedAt": "2025-10-20T10:14:00+05:30",
      "isDemonstrationDataset": true
    },
    "evidenceLimitations": "Matched on laboratory name, city, certificate number, validity date, and discipline. Scope can vary by collection site."
  }
  ```
- **UI States**:
  - **Loading**: Renders `.loading-card` with animated spinner: "Comparing checked fields: Reviewing identity, scope, validity, and source metadata…"
  - **Success**: Displays `LabResult` card with match confidence percentage, check badges, and toggleable evidence panel.
  - **Empty**: Renders `.empty-result` card with flask icon: "No verification run yet — Complete the search form to view a transparent, synthetic demonstration result."
  - **Error**: Shows alert banner: "Verification lookup service unreachable. Verify laboratory identifier manually."

---

### 3.7 Medicine Verification (`MedicineVerification`)

- **Screen Location**: `App.tsx` (Lines 218–238, rendered via `VerificationPage` with `medicine=true`)
- **Key Sections**:
  - Search Form: Brand/product name, Active ingredient, Strength, Dosage form, Manufacturer, Route.
  - Result Card (`MedicineResult`): Status badge ("Possible Match — Human Review"), match confidence (`88%`), review warning banner ("Formulation detail requires review"), match criteria list, official reference (`CDSCO/SUGAM demonstration dataset`).

#### 3.7.1 Medicine Regulatory Verification Endpoint
- **Endpoint**: `[PROPOSED]` `POST /api/v1/verify/medicine`
- **Request** (`application/json`):
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
- **Response** (`200 OK`):
  ```json
  {
    "matchConfidence": 0.88,
    "verdict": "Possible Match — Human Review",
    "reviewBanner": "Formulation detail requires review: The checked source lists an immediate-release tablet; the uploaded label image does not clearly show release type. Verify with a registered pharmacist or clinician.",
    "product": {
      "brand": "Glycomet 500",
      "standardizedTitle": "Metformin Hydrochloride Tablets IP"
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
    }
  }
  ```
- **UI States**:
  - **Loading**: Renders `.loading-card` with spinner and loading message.
  - **Success**: Displays `MedicineResult` card with review warning box, percentage score, and check items.
  - **Empty**: `.empty-result` card with pill icon: "No verification run yet."
  - **Error**: "Regulatory catalogue check unavailable. Consult official CDSCO gazette."

---

### 3.8 Care-Gap Early Warning (`CareGaps`)

- **Screen Location**: `App.tsx` (Lines 240–253)
- **Key Sections**:
  - Safety strip: "A missing record means only that no matching test record was found in the available history. It does not mean the test was not performed."
  - Task List with status badges (`Needs Review`, `Scheduled`, `Completed`), expected record, care-plan source, and records checked counter.
  - Task action buttons (`Completed elsewhere`, `Mark scheduled`, `Not applicable`, `Request clinician review`).
  - "Add documented care-plan task" modal with user-confirmation consent checkbox.

#### 3.8.1 Care Gaps List Endpoint
- **Endpoint**: `[PROPOSED]` `GET /api/v1/care-gaps`
- **Request**: Headers: `Authorization: Bearer <token>`
- **Response** (`200 OK`):
  ```json
  {
    "recordsCheckedCount": 28,
    "lastCheckedDate": "Today",
    "tasks": [
      {
        "id": "gap_001",
        "title": "Repeat fasting glucose",
        "expected": "Fasting Plasma Glucose report",
        "due": "02 Nov 2025",
        "source": "Dr. Mehta visit note · 18 Oct",
        "status": "Needs Review",
        "reason": "No matching test record found in the available history."
      },
      {
        "id": "gap_002",
        "title": "Review lipid profile",
        "expected": "Consultation note",
        "due": "18 Nov 2025",
        "source": "Discharge plan · 20 Sep",
        "status": "Scheduled",
        "reason": "Appointment is recorded; no completion document is available yet."
      },
      {
        "id": "gap_003",
        "title": "Share CBC with consultant",
        "expected": "Shared consultation summary",
        "due": "22 Oct 2025",
        "source": "User-confirmed plan · 08 Sep",
        "status": "Completed",
        "reason": "Completion was confirmed by the user."
      }
    ]
  }
  ```

#### 3.8.2 Add Care Plan Task Endpoint
- **Endpoint**: `[PROPOSED]` `POST /api/v1/care-gaps`
- **Request** (`application/json`):
  ```json
  {
    "title": "Repeat HbA1c",
    "expected": "Glycated Haemoglobin report",
    "due": "15 Dec 2025",
    "userConfirmed": true
  }
  ```
- **Response** (`201 Created`):
  ```json
  {
    "id": "gap_004",
    "title": "Repeat HbA1c",
    "expected": "Glycated Haemoglobin report",
    "due": "15 Dec 2025",
    "source": "User-confirmed care plan",
    "status": "Needs Review",
    "reason": "No matching test record found in the available history."
  }
  ```

#### 3.8.3 Update Task Status Endpoint
- **Endpoint**: `[PROPOSED]` `PATCH /api/v1/care-gaps/{taskId}`
- **Request** (`application/json`):
  ```json
  {
    "status": "Completed"
  }
  ```
  *(Allowed statuses: `"Completed"`, `"Scheduled"`, `"Not Applicable"`, `"Clinician Review"`)*
- **Response** (`200 OK`):
  ```json
  {
    "id": "gap_001",
    "status": "Completed",
    "updatedAt": "2026-10-18T02:42:00Z"
  }
  ```
- **UI States**:
  - **Loading**: Task card action buttons disable with inline status indicator.
  - **Success**: Task badge updates to new status color and reason text.
  - **Empty**: "No pending care-plan tasks documented."
  - **Error**: "Failed to update task. Changes not saved."

---

### 3.9 Consultation Summary & PDF Export (`ConsultationSummary`)

- **Screen Location**: `App.tsx` (Lines 255–264)
- **Key Sections**:
  - Report Contents Checklist (8 toggleable sections: Medical records, Measurement charts, Integrity flags, Lab verification, Medicine verification, Care-gap tasks, Source references, Uncertainty notes).
  - Date Range input.
  - Live document preview (`ReportPreview`) showing branded header, metadata banner, record table, trend chart, findings, and disclaimer.
  - Action buttons: "Edit selection" / "Preview PDF" toggle, "Download PDF" (invokes `window.print()`).

#### 3.9.1 Consultation Packet Aggregation Endpoint
- **Endpoint**: `[PROPOSED]` `POST /api/v1/consultation/summary`
- **Request** (`application/json`):
  ```json
  {
    "dateRange": {
      "from": "2025-02-01",
      "to": "2025-10-20"
    },
    "includedSections": {
      "medicalRecords": true,
      "measurementCharts": true,
      "integrityFlags": true,
      "laboratoryVerification": true,
      "medicineVerification": false,
      "careGapTasks": true,
      "sourceReferences": true,
      "uncertaintyNotes": true
    }
  }
  ```
- **Response** (`200 OK`):
  ```json
  {
    "generatedAt": "2025-10-20T10:42:00+05:30",
    "patientName": "Aarav N.",
    "dateRangeLabel": "01 Feb – 20 Oct 2025",
    "recordsReviewedCount": 5,
    "records": [...],
    "measurementTrend": {...},
    "integrityFindings": [...],
    "verificationSummary": {...},
    "medicineVerification": null,
    "disclaimer": "SehatSnap Integrity supports record quality and verification. It does not diagnose, prescribe, or replace professional medical judgment."
  }
  ```
- **UI States**:
  - **Loading**: Preview pane shows loading skeleton.
  - **Success**: Previews complete print-ready consultation packet formatted for A4 paper.
  - **Empty**: Renders `.selection-state` card when preview is toggled off.
  - **Error**: Error toast: "Could not compile consultation packet. Check selected date range."

---

### 3.10 Audit Trail (`AuditTrail`)

- **Screen Location**: `App.tsx` (Lines 266–271)
- **Key Sections**:
  - "Local Hash-Linked Audit Log" header badge.
  - Report Integrity Verification card: Sample report SR-1048, demo scenario select (`Original sample report` vs `Altered copy (demonstration)`), Recorded SHA-256 vs Current file hash, and "Verify integrity" button with matching/mismatch alert box.
  - Event history hash-linked timeline for SR-1048.
  - Recent audit events table with Event ID, Event type, Artifact hash, Timestamp, Actor reference, Rule/model, and Verification badge.

#### 3.10.1 Verify File Hash Endpoint
- **Endpoint**: `[PROPOSED]` `POST /api/v1/audit/verify-file`
- **Request** (`application/json`):
  ```json
  {
    "reportId": "SR-1048",
    "clientComputedHash": "a91f4e80b92c4b5d6e7f8a9b0c1d2e3f4a5b6c7d8e9f0a1b2c3d4e5f6a7b8c9d"
  }
  ```
- **Response** (`200 OK`):
  ```json
  {
    "reportId": "SR-1048",
    "fileName": "fasting-glucose-oct-2025.pdf",
    "recordedHash": "a91f4e80b92c4b5d6e7f8a9b0c1d2e3f4a5b6c7d8e9f0a1b2c3d4e5f6a7b8c9d",
    "providedHash": "a91f4e80b92c4b5d6e7f8a9b0c1d2e3f4a5b6c7d8e9f0a1b2c3d4e5f6a7b8c9d",
    "isMatch": true,
    "message": "Integrity of this file matches the recorded hash. A matching hash confirms the file is unchanged; it does not prove medical correctness or authenticity."
  }
  ```

#### 3.10.2 Audit Event History Endpoint
- **Endpoint**: `[PROPOSED]` `GET /api/v1/audit/events`
- **Request**:
  - Query Parameters:
    - `reportId`: string (optional filter, e.g. `"SR-1048"`)
    - `limit`: number (default: 20)
- **Response** (`200 OK`):
  ```json
  {
    "events": [
      {
        "eventId": "EVT-8F21",
        "eventType": "Report confirmed",
        "artifactHash": "a91f…7cd2",
        "fullHash": "a91f4e80b92c4b5d6e7f8a9b0c1d2e3f4a5b6c7d8e9f0a1b2c3d4e5f6a7b8c9d",
        "timestamp": "20 Oct 2025 · 09:42",
        "actor": "User AN",
        "ruleOrModel": "rules-v1.4",
        "verification": "Hash-linked"
      },
      {
        "eventId": "EVT-8F18",
        "eventType": "OCR extraction reviewed",
        "artifactHash": "c083…91aa",
        "fullHash": "c083b42a1f09d8376483921fa839c083b42a1f09d8376483921fa83991aa",
        "timestamp": "20 Oct 2025 · 09:39",
        "actor": "User AN",
        "ruleOrModel": "ocr-demo-v2",
        "verification": "Hash-linked"
      },
      {
        "eventId": "EVT-8F11",
        "eventType": "File added",
        "artifactHash": "a91f…7cd2",
        "fullHash": "a91f4e80b92c4b5d6e7f8a9b0c1d2e3f4a5b6c7d8e9f0a1b2c3d4e5f6a7b8c9d",
        "timestamp": "20 Oct 2025 · 09:36",
        "actor": "Local upload",
        "ruleOrModel": "ingest-v1.2",
        "verification": "Hash-linked"
      }
    ]
  }
  ```
- **UI States**:
  - **Loading**: Skeleton animation over event timeline and audit table.
  - **Success**: Verified green check or red alert box depending on hash equality; event timeline populated with sequential dots and hashes.
  - **Empty**: "No audit events recorded for this artifact."
  - **Error**: "Audit log service unavailable. Tamper check could not be performed."

---

### 3.11 User Preferences & Settings (`Settings`)

- **Screen Location**: `App.tsx` (Lines 273–276)
- **Settings Fields**:
  - Date format (`DD MMM YYYY` vs `DD/MM/YYYY`)
  - Default units (`Preserve source units` vs `Metric where compatible`)
  - Simulated-data labels toggle
  - Review reminders toggle
  - Connected data sources modal / info
  - Data retention controls

#### 3.11.1 User Settings Endpoint
- **Endpoint**: `[PROPOSED]` `GET /api/v1/settings`
- **Response** (`200 OK`):
  ```json
  {
    "dateFormat": "DD MMM YYYY",
    "defaultUnits": "Preserve source units",
    "showSimulatedLabels": true,
    "reviewReminders": true,
    "connectedSourcesCount": 0
  }
  ```

#### 3.11.2 Save User Settings Endpoint
- **Endpoint**: `[PROPOSED]` `PUT /api/v1/settings`
- **Request** (`application/json`):
  ```json
  {
    "dateFormat": "DD MMM YYYY",
    "defaultUnits": "Preserve source units",
    "showSimulatedLabels": true,
    "reviewReminders": true
  }
  ```
- **Response** (`200 OK`):
  ```json
  {
    "updated": true,
    "savedAt": "2026-10-18T02:44:00Z"
  }
  ```
- **UI States**:
  - **Loading**: Save button text changes to "Saving preferences…".
  - **Success**: Button changes to "Preferences saved" for 2 seconds.
  - **Error**: Inline error text: "Preferences could not be saved."

---

### 3.12 Topbar Shell (`Header`)

- **Screen Location**: `App.tsx` (Lines 113–127)
- **Features**:
  - Global Search input: Instant search filter.
  - Notification Bell & Popover: Counter badge and expandable list of unresolved review items.
  - User Profile: Avatar initials and name.

#### 3.12.1 Global Search Endpoint
- **Endpoint**: `[PROPOSED]` `GET /api/v1/search`
- **Request**: Query `q`: string
- **Response** (`200 OK`):
  ```json
  {
    "query": "glucose",
    "results": [
      { "type": "record", "id": "SR-1048", "title": "Fasting Plasma Glucose", "subtitle": "Aster Diagnostics, Pune" },
      { "type": "finding", "id": "DUP-002", "title": "Conflicting report identifiers", "subtitle": "SR-1048" }
    ]
  }
  ```

#### 3.12.2 Active Notifications Endpoint
- **Endpoint**: `[PROPOSED]` `GET /api/v1/notifications`
- **Response** (`200 OK`):
  ```json
  {
    "unreadCount": 2,
    "items": [
      { "id": "notif_1", "text": "Conflicting report identifier detected.", "severity": "danger", "linkPage": "Integrity Checks" },
      { "id": "notif_2", "text": "Care-plan task due in 8 days.", "severity": "info", "linkPage": "Care Gaps" }
    ]
  }
  ```

---

## 4. Synthesis: Summary Mapping Table

| Screen / UI Component | Action / User Flow | Proposed API Route | HTTP Method | Expected Request Payload / Params | Expected Response Data |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **UploadModal** | Upload PDF / image | `/api/v1/reports/extract` | `POST` | `multipart/form-data` (`file`) | Structured fields, OCR confidence scores, source provenance |
| **UploadModal** | Confirm extracted fields | `/api/v1/records/confirm` | `POST` | Verified field key-values, user approved flag | Created record ID (`SR-xxxx`), audit event ID |
| **Overview** | Load dashboard metrics | `/api/v1/dashboard/summary` | `GET` | None (Auth token) | Integrity score, 5 metrics, top alerts, recent timeline, upcoming care tasks |
| **MedicalRecords** | Fetch list of records | `/api/v1/records` | `GET` | `query`, `status`, `sortBy`, `limit`, `offset` | List of `RecordItem` objects, total count |
| **MedicalRecords** | Enter test manually | `/api/v1/records` | `POST` | `name`, `value`, `unit`, `lab`, `range`, `date` | Created `RecordItem` with generated ID |
| **ReportAnalysis** | Fetch analyte time-series | `/api/v1/analysis/trends` | `GET` | `analyte`, `dateRange` | Data points array, reference range limits, unit comparison metrics, side-by-side records |
| **IntegrityChecks** | Fetch diagnostic findings | `/api/v1/integrity/findings` | `GET` | `severity`, `status` | Summary metrics, findings array with rule rationale and recommendations |
| **IntegrityChecks (Drawer)**| Resolve / Review finding | `/api/v1/integrity/findings/{id}` | `PATCH` | `{ status: "Reviewed" \| "Resolved" \| ... }` | Updated finding object |
| **LaboratoryVerification** | Verify lab credentials | `/api/v1/verify/laboratory` | `POST` | `laboratoryName`, `city`, `certificateNumber`, `discipline` | Match score, verification checks array, official registry metadata |
| **MedicineVerification** | Verify medicine label | `/api/v1/verify/medicine` | `POST` | `brandName`, `activeIngredient`, `strength`, `dosageForm`, `manufacturer` | Match score, review warning banner, regulatory checks array |
| **CareGaps** | Fetch care plan tasks | `/api/v1/care-gaps` | `GET` | None | Active tasks array, records checked count |
| **CareGaps** | Add documented task | `/api/v1/care-gaps` | `POST` | `title`, `expected`, `due`, `userConfirmed` | Created task object with `Needs Review` status |
| **CareGaps** | Update task progress | `/api/v1/care-gaps/{id}` | `PATCH` | `{ status: "Completed" \| "Scheduled" \| ... }` | Updated task object |
| **ConsultationSummary** | Compile export packet | `/api/v1/consultation/summary`| `POST` | `dateRange`, `includedSections` map | Aggregated consultation report data |
| **AuditTrail** | Verify file SHA-256 | `/api/v1/audit/verify-file` | `POST` | `reportId`, `clientComputedHash` | Match boolean, comparison details |
| **AuditTrail** | Fetch audit log events | `/api/v1/audit/events` | `GET` | `reportId`, `limit` | Chronological list of hash-linked audit events |
| **Settings** | Load & update preferences | `/api/v1/settings` | `GET` / `PUT` | Preference key-values | Updated preferences confirmation |
| **Header** | Search & notifications | `/api/v1/search`, `/api/v1/notifications` | `GET` | Search query `q` | Search results array, unread notifications |

---

## 5. Non-Functional & Safety Constraints

1. **No Diagnosis or Prescribing**:
   - The platform strictly identifies documentation anomalies, missing records from confirmed care plans, and unit mismatches.
   - It **must never** suggest clinical diagnoses, drug substitutions, or dosage adjustments.
2. **Provenance & Source Linking**:
   - Every extracted value displayed in the UI must maintain a reference back to its originating document hash, page number, and bounding box.
   - Any manual edit made by the user must be flagged as `Manual` or `User Confirmed` and recorded in the audit trail.
3. **Synthetic Demo Data Integrity**:
   - Until live NABL and CDSCO official API access is provisioned, verification lookups must return clearly labeled synthetic demonstration responses.
4. **Local Audit Log**:
   - Tamper-evident logging uses local SHA-256 hash chains. Patient Health Information (PHI) is never broadcast to public distributed ledgers.

---

## 6. Integration Roadmap & Recommendations

To prepare the frontend code for production backend calls without redesigning the UI or breaking existing local behavior:

1. **Introduce an API Client Layer**:
   - Create a typed API client in `frontend/src/services/api.ts` wrapping native `fetch` or Axios with base URL configuration (`VITE_API_BASE_URL`).
2. **Abstract State into Custom Hooks**:
   - Extract data handling from `App.tsx` into domain hooks (e.g., `useRecords()`, `useIntegrityFindings()`, `useLabVerification()`, `useAuditEvents()`).
   - Allow fallback to current synthetic initial records if backend is offline or in demo mode.
3. **Replace `setTimeout` Stubs**:
   - Replace the `window.setTimeout` timers in `UploadModal`, `VerificationPage`, and `Settings` with real API promise calls.
4. **Preserve Error Boundaries & Fallbacks**:
   - Ensure the empty and error states documented above are rendered with user-friendly notices adhering to the healthcare disclaimer guidelines.
