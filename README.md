# SehatSnap Integrity 🛡️🩺

**SehatSnap Integrity** is a full-stack health data workspace designed to verify medical records, laboratory accreditation, and pharmaceutical product details while preserving source provenance and auditing document integrity.

---

## 🌟 Key Features

- **🏥 Laboratory Verification:** Search and verify health laboratory identities and accreditation scopes against official regulatory datasets (e.g., NABL).
- **💊 Medicine Verification:** Cross-check product label details, active ingredients, dosage strengths, and manufacturers.
- **📄 Medical Record Extraction:** Extract, review, and confirm diagnostic values from uploaded medical reports (PDFs/images) with confidence scoring.
- **📈 Measurement Trends:** Compare historical diagnostic values over time with unit validation and automatic unit conversions.
- **🚨 Integrity & Diagnostic Engine:** Deterministic rule engine to highlight data conflicts, missing collection metadata, or low-confidence OCR extractions.
- **🔗 Hash-Linked Audit Log:** Tamper-evident event history recording artifact SHA-256 hashes for data provenance.
- **📋 Consultation Summary Export:** Build clinician-ready PDF consultation packets with configurable privacy controls.

---

## 🏗️ Tech Stack

### Frontend
- **Framework:** React + TypeScript + Vite
- **Styling:** CSS3 (custom responsive shell and UI components)
- **Icons:** Custom SVG icon engine

### Backend
- **Framework:** FastAPI (Python)
- **Database & ORM:** SQLAlchemy + SQLite / PostgreSQL
- **Document Processing:** PyMuPDF (`fitz`), PyPDF

---

## 📁 Repository Structure

```text
SehatSnap/
├── backend/
│   ├── app/
│   │   ├── main.py            # FastAPI entry point and API endpoints
│   │   ├── database.py        # SQLAlchemy database setup
│   │   ├── models.py          # Database schemas and models
│   │   └── routers/           # API routes (verification, extraction, records)
│   ├── tests/                 # Backend test suite
│   └── requirements.txt       # Python dependencies
├── frontend/
│   ├── src/
│   │   ├── App.tsx            # Core React dashboard workspace
│   │   ├── api.ts             # Client API service handlers
│   │   └── main.tsx           # Application entry point
│   ├── package.json           # Frontend dependencies
│   └── vite.config.ts         # Vite server and proxy configuration
└── README.md
```

---

## 🚀 Getting Started

### Prerequisites

- **Node.js** (v18 or higher)
- **Python** (v3.10 or higher)
- **Git**

### 1. Backend Setup (FastAPI)

1. Open a terminal in the repository root (`Sehat`).

2. Install backend dependencies:

   ```bash
   pip install -r backend/requirements.txt
   ```

3. Start the FastAPI development server.

   **Windows Command Prompt:**

   ```bat
   set PYTHONPATH=.
   uvicorn backend.app.main:app --reload --port 8000
   ```

   **PowerShell:**

   ```powershell
   $env:PYTHONPATH = "."
   uvicorn backend.app.main:app --reload --port 8000
   ```

The backend API will be available at `http://127.0.0.1:8000`. Interactive API documentation is available at `http://127.0.0.1:8000/docs`.

### 2. Frontend Setup (React + Vite)

1. Open a **new terminal** and navigate to the frontend folder:

   ```bash
   cd frontend
   ```

2. Install frontend packages:

   ```bash
   npm install
   ```

3. Start the Vite development server:

   ```bash
   npm run dev
   ```

The frontend dashboard will usually be available at `http://localhost:5173`.

---

## 🧪 Testing

Run the backend tests from the repository root:

```bash
pytest backend/tests
```

If `pytest` is not installed in your active Python environment, install the project's backend requirements first.

---

## ⚠️ Disclaimer

SehatSnap Integrity supports medical-record quality, provenance tracking, and data verification. It does not diagnose conditions, prescribe treatments, or replace professional medical judgment.
