# AICTE VerifyAI — Intelligent Document Verification Assistant

> **Smart India Hackathon (SIH) Prototype — Human-in-the-Loop Regulatory Document Screening**  
> **Status:** Production-Ready Demonstration (Phase 09 Final Packaging)  
> **Advisory Notice:** *AICTE VerifyAI produces preliminary advisory screening signals only. All automated cross-document comparisons and authenticity indicators support human review and do not constitute final AICTE regulatory decisions.*

---

## 1. Project Overview

**AICTE VerifyAI** is a regulatory document screening assistant designed to accelerate and standardize the scrutiny of institutional approval applications submitted to the All India Council for Technical Education (AICTE).

Every academic year, hundreds of institutions submit thousands of pages of legal, financial, and infrastructural documents—including Land Deeds, Fire Safety NOCs, Building Approvals, and AICTE Approval Letters. VerifyAI addresses manual verification bottlenecks by providing:

1. **Cross-Document Consistency Analysis:** Automated correlation of critical fields (institution name, land acreage, sanctioned intake, reference IDs, and validity dates) across diverse documents to highlight discrepancies.
2. **Document Authenticity Screening:** Heuristic screening for digital signatures, PDF structural anomalies, creation/modification timestamp inversions, and low-resolution artifacting.
3. **Human-in-the-Loop Review & Decision Persistence:** Authorized officers can review, override, or escalate flagged findings with full justification notes.
4. **Immutable Regulatory Audit Trail:** Append-only ledger recording every application lifecycle event (creation, uploads, automated evaluations, officer decisions) for chain-of-custody transparency.

---

## 2. Architecture & Technology Stack

```
                     ┌────────────────────────────────────────┐
                     │          Vite + React 18 UI            │
                     │  (TypeScript, TailwindCSS, Lucide)     │
                     └───────────────────┬────────────────────┘
                                         │ HTTP / REST (/api/v1)
                                         ▼
                     ┌────────────────────────────────────────┐
                     │         FastAPI 0.115 Backend          │
                     │  (Python 3.11, Pydantic v2, PyMuPDF)   │
                     └───────┬────────────────────────┬───────┘
                             │                        │
                             ▼                        ▼
                ┌───────────────────────┐  ┌───────────────────────┐
                │ SQLite / PostgreSQL   │  │ Local File Storage    │
                │ (SQLAlchemy 2.0 ORM)  │  │ (storage/uploads)     │
                └───────────────────────┘  └───────────────────────┘
```

### Core Technologies
- **Backend:** Python 3.11, FastAPI 0.115.6, SQLAlchemy 2.0.36, Alembic 1.14.0, PyMuPDF (fitz) 1.25.1, Pydantic v2, Pytest 8.3.4.
- **Frontend:** React 18.3.1, TypeScript 5.6.3, Vite 6.4.5, TailwindCSS 3.4.17, Lucide Icons, Recharts 2.15.0, Vitest 2.1.9.
- **Database:** SQLite (`verifyai.db`) for local deterministic demonstration; PostgreSQL-compatible schema via SQLAlchemy.
- **Storage:** Local isolated filesystem storage (`storage/uploads` and `storage/processed`).

---

## 3. Local Setup & Startup Guide (Windows PowerShell)

### Prerequisites
- **Python:** 3.11+ (Python 3.11.9 verified)
- **Node.js:** v18+ or v20+ (Node v20+ verified)
- **PowerShell:** Windows PowerShell 5.1 or PowerShell 7+

### Step 1: Backend Setup
Open a PowerShell terminal and navigate to the backend directory:
```powershell
cd D:\SIH\backend

# Install backend dependencies
python -m pip install -r requirements.txt

# Verify the local configuration file exists (.env)
# DATABASE_URL=sqlite:///verifyai.db
# APP_ENV=development
# SECRET_KEY=verifyai-demo-secret-key-2026-development-only

# Start the FastAPI server on port 8001
python -m uvicorn app.main:app --host 127.0.0.1 --port 8001 --reload
```
*Health Check:* Open `http://127.0.0.1:8001/api/v1/health` in your browser. Expected response:
`{"status":"ok","version":"0.1.0","environment":"development","database":"ok"}`

### Step 2: Frontend Setup
Open a second PowerShell terminal and navigate to the frontend directory:
```powershell
cd D:\SIH\frontend

# Install frontend dependencies
npm install

# Start Vite dev server on port 5173
npm run dev
```
*Application URL:* Open `http://localhost:5173` in your browser.

---

## 4. Pre-Configured Demonstration Accounts

The prototype includes three role-based accounts pre-seeded for demonstration purposes:

| Role | Email | Password | Access Privileges |
| :--- | :--- | :--- | :--- |
| **Verification Officer** | `officer@aicte.gov.in` | `Officer@123` | Authorized review, decision overrides, validation execution, screening, audit trail inspection. |
| **Public Auditor / Viewer** | `viewer@aicte.gov.in` | `Viewer@123` | Read-only inspection of applications, findings, graph, and audit records. Cannot modify decisions or upload files. |
| **AICTE Administrator** | `admin@aicte.gov.in` | `Admin@123` | Administrative oversight, user management, rule configuration, audit log review. |

> [!NOTE]
> Demo account shortcuts are accessible directly on the Login screen for rapid evaluator testing.

---

## 5. Hackathon Demonstration Scenarios

Two deterministic synthetic applications are available directly from the Dashboard:

### Scenario A: Cross-Document Consistency Graph (Discrepancy Detection)
- **Institution:** `Demo Institute of Technology` (`APP-2026-1CF169`)
- **Evaluator Focus:** Flagship cross-document comparison engine.
- **Highlights:**
  - Evaluates 4 cross-document field pairs across Land Documents, Fire NOC, and AICTE Approval Letter.
  - Correctly detects **2 Confirmed Matches** (Institution Name, Academic Year).
  - Flags **2 High-Severity Discrepancies** (Land Area 5.0 acres in deed vs 2.5 acres in NOC; Reference Number mismatch).
  - Interactive side-by-side evidence inspection drawer.
  - 7 immutable audit events recorded in the chain of custody.

### Scenario B: Authenticity Screening & Advisory Scope
- **Institution:** `MIT academy of engineering [DEMO]` (`APP-2026-CDC390`)
- **Evaluator Focus:** Forensic authenticity screening and deferred OCR handling.
- **Highlights:**
  - 18 automated security checks across 3 uploaded institutional documents.
  - Heuristic risk breakdown: image resolution warnings, compression artifact signals, digital signature detection.
  - Prominent **Deferred OCR Advisory Banner** explaining that cross-document comparisons depend on extracted fields, and zero comparisons indicates pending extraction rather than guaranteed consistency.
  - 20 immutable audit events reflecting past officer reviews.

---

## 6. Evaluator Demonstration Script (5-Minute Tour)

1. **Login (0:00 - 0:30):** Sign in as `officer@aicte.gov.in` using the quick-fill button.
2. **Dashboard Overview (0:30 - 1:15):** Inspect the summary metrics (Total Applications, Flagged Discrepancies, Authenticity Checks) and the "Hackathon Showcase" cards.
3. **Scenario A — Consistency Graph (1:15 - 2:30):** Click **Launch Consistency Scenario**. Review the visual graph nodes, filter by "Discrepancies", and click on the "Land Area" node to inspect the side-by-side evidence modal.
4. **Scenario B — Authenticity Screening (2:30 - 3:30):** Navigate to Applications, launch Scenario B, and open the **Authenticity Screening** tab. Review the 18 security checks and explain how heuristic screening protects AICTE from tampered files.
5. **Human Review Action (3:30 - 4:15):** In Scenario B, open **Validation Findings**, select an unreviewed finding, click **Review**, enter an officer justification note, and submit.
6. **Audit Trail Verification (4:15 - 5:00):** Switch to the **Audit Trail** tab. Point out the freshly recorded `finding.reviewed` event, illustrating the end-to-end regulatory chain of custody.

---

## 7. Automated Test Suite & Build Verification

### Backend Tests (Pytest)
```powershell
cd D:\SIH\backend
python -m pytest tests/ -v
```
- **Result:** **127 passed**, 0 failed across 8 test suites:
  - `tests/test_health.py` (3 tests)
  - `tests/test_auth.py` (11 tests)
  - `tests/test_rbac.py` (10 tests)
  - `tests/test_applications.py` (16 tests)
  - `tests/test_validation.py` (22 tests)
  - `tests/test_authenticity.py` (15 tests)
  - `tests/test_documents.py` (24 tests)
  - `tests/test_processing.py` (26 tests)

### Frontend Tests (Vitest)
```powershell
cd D:\SIH\frontend
npm run test -- --run
```
- **Result:** **5 test files passed, 13 tests passed**, 0 failed.

### Production Build (Vite)
```powershell
cd D:\SIH\frontend
npm run build
```
- **Result:** Compiles cleanly with TypeScript strict checks (`tsc && vite build`) in under 3.0s with 0 errors.

---

## 8. Deployment Readiness & Production Checklist

VerifyAI is architected for straightforward containerized or cloud deployment:

### Production Environment Variables
| Variable | Production Requirement | Example |
| :--- | :--- | :--- |
| `DATABASE_URL` | PostgreSQL 15+ connection string | `postgresql://user:pass@db-host:5432/verifyai` |
| `APP_ENV` | Must be set to `production` | `production` |
| `SECRET_KEY` | Explicit cryptographically random string (min 32 chars) | *Auto-validated at startup* |
| `ALLOWED_ORIGINS` | AICTE portal production domain(s) | `https://verifyai.aicte-india.org` |
| `VITE_API_BASE_URL` | Frontend API gateway base path | `/api/v1` or `https://api.verifyai.aicte-india.org/api/v1` |
| `UPLOAD_DIR` | Persistent volume or S3-backed mount | `/var/verifyai/storage/uploads` |

### Production Security Protections
- **Startup Enforcement:** The application validates at startup that `SECRET_KEY` is not using default development placeholders when `APP_ENV=production`.
- **Demo Seeding Guard:** Default user auto-seeding is gated behind `APP_ENV=development` and disabled in production.
- **Append-Only Auditing:** Audit trail records cannot be edited or deleted through any API endpoint.

---

## 9. Known System Limitations

1. **OCR / Text Extraction Deferred:** As scoped during prototype sprints, automated optical character recognition on unstructured scanned images is deferred. Synthetic applications utilize pre-extracted structured metadata fields.
2. **Advisory Scope:** Automated findings, consistency matches, and authenticity screening signals are decision-support indicators. They do not constitute official AICTE accreditation, legal approval, or definitive evidence of forgery.
3. **Synthetic Demonstration Data:** All applicant institutions, addresses, and document scans represent synthetic demonstration scenarios and do not correspond to actual institutional records.

---

## 10. Troubleshooting

| Symptom | Cause | Solution |
| :--- | :--- | :--- |
| **Backend 500 on startup (PostgreSQL)** | Defaulting to PostgreSQL when DB daemon is off | Ensure `backend/.env` contains `DATABASE_URL=sqlite:///verifyai.db`. |
| **Dashboard shows 404** | Vite proxy misconfigured or backend not on 8001 | Confirm backend is running on port 8001 (`http://127.0.0.1:8001/api/v1/health`). |
| **401 Unauthorized during review** | Token expired or logged in as Viewer | Click Logout and sign in using the `Verification Officer` shortcut. |
| **0 evaluated pairs in Graph** | Document text extraction pending | Normal for unextracted PDFs. Refer to the amber advisory banner. |
