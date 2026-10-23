# AICTE VerifyAI — Evaluator Demo Guide (Quick-Pitch Playbook)

> **Designed for Hackathon Juries & Technical Evaluators**  
> **Duration:** 5–7 Minutes  
> **Target Audience:** AICTE Reviewers, Regulatory Technologists, Hackathon Evaluators

---

## Pre-Flight Check (30 Seconds)

1. Verify backend is active on port 8001:
   ```powershell
   curl.exe http://127.0.0.1:8001/api/v1/health
   # Expected: {"status":"ok","database":"ok",...}
   ```
2. Verify frontend is active on port 5173:
   - Open browser to `http://localhost:5173`

---

## 5-Minute Evaluator Journey

### Step 1: Login & Role-Based Access Control (30s)
- **Action:** On the Login page, demonstrate the three pre-configured role shortcuts:
  - Click **"Verification Officer"** (`officer@aicte.gov.in`).
  - Click **Sign In**.
- **Talking Point:** *"VerifyAI enforces strict role-based access control. Officers have full review and escalation authority; public viewers have read-only audit capabilities; administrators manage compliance rules."*

---

### Step 2: Regulatory Executive Dashboard (45s)
- **Action:** Point out the top-level analytical metrics:
  - Total Applications, Processing Status breakdown, Flagged Discrepancies, and Authenticity Screening totals.
  - Highlight the **"Hackathon Showcase: Key Demonstration Scenarios"** cards.
- **Talking Point:** *"Rather than sifting through spreadsheets or paper files, AICTE leadership gets immediate visibility into institutional compliance posture and identified anomalies across all ongoing approval cycles."*

---

### Step 3: Flagship Scenario A — Cross-Document Consistency Graph (90s)
- **Action:** Click **"Launch Consistency Scenario"** on the `Demo Institute of Technology` card.
- **Action:** Show the graph view:
  - 4 evaluated cross-document comparisons.
  - 2 confirmed matches (Academic Year, Institution Name).
  - 2 high-severity discrepancies (Land Area and Reference Number).
- **Action:** Click on the **Land Area Discrepancy**:
  - Open the side-by-side evidence inspection drawer.
  - Point out that the Land Deed claims **5.00 Acres**, while the Fire NOC specifies only **2.50 Acres**.
- **Talking Point:** *"This is the core innovation of VerifyAI. Manual inspectors often miss when an institution submits a valid 5-acre land deed alongside a fire safety clearance that only covers 2.5 acres. Our normalization engine standardizes units (hectares, acres, sq meters) and detects conflicting representations instantly."*

---

### Step 4: Scenario B — Authenticity Screening & Advisory Scope (60s)
- **Action:** Navigate back to Applications list, and click **"Launch Authenticity Scenario"** (`MIT academy of engineering [DEMO]`).
- **Action:** Click the **"🛡️ Authenticity Screening"** tab.
  - Review the summary risk metrics (18 security checks performed).
  - Expand document cards showing digital signature status, PDF structural integrity, and image resolution indicators.
- **Action:** Switch to the **Consistency Graph** tab on this application:
  - Point out the prominent amber **Deferred OCR Advisory Banner**.
- **Talking Point:** *"VerifyAI acts as a preliminary forensic filter. Notice our honest regulatory posture: we clearly signal that image resolution or compression artifacts are screening cues for human inspection, not absolute proof of fraud. Furthermore, when documents lack extracted text, we clearly state that zero comparisons means pending extraction, not confirmed consistency."*

---

### Step 5: Human-in-the-Loop Review Action (45s)
- **Action:** On the same application, open the **"⚠️ Validation Findings"** tab.
- **Action:** Select an unreviewed finding, click **"Review"**.
  - Choose `Verified` or `Overridden`.
  - Enter reviewer rationale: *"Inspected certified physical land survey certificate dated 2026-03-15. Discrepancy reconciled."*
  - Click **Submit Review**.
- **Talking Point:** *"VerifyAI NEVER makes automated approval or rejection decisions. The AI assists; the human AICTE officer decides and provides regulatory accountability."*

---

### Step 6: Immutable Regulatory Audit Trail (45s)
- **Action:** Click the **"📜 Audit Trail"** tab on the application.
- **Action:** Scroll through the reverse-chronological event timeline:
  - Point out the newly recorded `finding.reviewed` event with the officer's email, timestamp, and rationale.
  - Point out previous events (`application.created`, `document.uploaded`, `application.validated`, `authenticity.screened`).
- **Talking Point:** *"Every single action—from document ingestion to officer determinations—is committed to an append-only, tamper-evident audit ledger. This ensures total institutional transparency and legal defensibility for AICTE."*

---

## Evaluator Q&A Reference

- **Q: Does VerifyAI replace the AICTE Scrutiny Committee?**  
  *A:* No. VerifyAI is an assistive screening tool. It flags discrepancies and anomalies to reduce scrutiny time from days to minutes, but all official decisions remain strictly in the hands of authorized human officers.

- **Q: How does VerifyAI handle different units of measurement?**  
  *A:* The backend validation engine features an automated unit normalizer that converts square meters, square feet, hectares, and bighas into standardized acres with configurable regulatory tolerance thresholds (typically ±2%).

- **Q: Can the audit trail be altered if an applicant contests a finding?**  
  *A:* No. The audit trail is architecturally append-only. No UPDATE or DELETE operations exist on the audit table. Any reversal requires a new, subsequent audit event with officer rationale.
