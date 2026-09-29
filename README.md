# AyurCTMS — Clinical Trial Management System for Ayurveda, Siddha & Unani (AIIA)

AyurCTMS is a regulatory-grade clinical trial workspace engineered for the **All India Institute of Ayurveda (AIIA)**, New Delhi. The system strictly follows three statutory Indian regulatory rulebooks:
1. **GCP-ASU** (Good Clinical Practice for Ayurveda, Siddha, and Unani Drug Trials, Ministry of AYUSH)
2. **DPDP Act 2023 & DPDP Rules 2025** (Digital Personal Data Protection Act, Ministry of Electronics & IT)
3. **CERT-In Directions 2022** (Cybersecurity and mandatory 6-hour security incident reporting, Indian Computer Emergency Response Team)

---

## 1. Role-Based Dashboards (9 Specialized Workspaces)

Every role gets a dedicated, minimal, Ayurveda-themed dashboard with curated KPIs, charts, and actionable workflow panels.

| Role | Core Purpose | Tailored KPIs | Primary Panels |
|---|---|---|---|
| **Principal Investigator (PI)** | Global trial oversight & site performance | Enrolment vs Target (150/190), Open SAEs (8), Central GCP Compliance (96%), Unacknowledged Reports | Incoming Reports (top priority), Enrolment Trend by Site, Site Compliance Ranking, Urgent Risk Register, Participant Drilldown by Subject Code |
| **Admin** | System governance & compliance oversight | Users Pending Approval (3), Active Studies (6), System Compliance (100%), Unacknowledged Critical Reports | Incoming Reports, 9-Role User Approval Desk, Trial Site Configuration, CERT-In Contact Desk, Audit Log |
| **Research Coordinator** | Site operations & subject tracking | Visits Due This Week (14), Consents Pending Re-consent (3), Doses Scheduled Today (28), Open Reports (1) | Participant Tracker, Visit Calendar, Quick Enrolment (blocked without verified consent), Dose Log |
| **Doctor / Investigator** | Clinical assessments & ADR detection | Active Cohort (42), ADRs Under Watch (5), Visits Scheduled (6), My Open Reports (1) | Subject Code Search, Clinical Profile (Prakriti, diagnoses, visit history, ADR log), "Flag Subject to PI", "Report AE/SAE" |
| **Monitor (CRA)** | Source data verification & GCP compliance | Missing Data Points (7), Overdue Visits (4), Protocol Deviations (3), Open Queries (5) | Site SDV Ranking, Deviations Log, Data Queries, Monitoring Visit Report (MVR) Form, "Report Finding to PI/Admin" |
| **Ethics Committee (EC)** | Ethical oversight & safety monitoring | Approvals Pending (2), Annual Renewals Expiring <30d (1), Amendments Under Review (2), SAEs Received (8) | Approval Workflow, Version History, Expiry Reminders, EC Register with Quorum Rule (≥5 members + ASU expert mandatory) |
| **Pharmacovigilance (PV) Officer** | Pharmacovigilance & signal detection | New AE/SAEs (8), Reports Due <24h (2), Overdue Reports (0), MedDRA Coded (52/60) | 24h Statutory SAE Queue with Countdown, MedDRA & WHODrug Coding Drawer, Dosha Causality Assessment, DSMB Signal Summary |
| **Auditor / Regulator** | Regulatory compliance & data integrity | Total Immutable Logs, Tamper Checks (0 failed), Document Versions (6), Integrity Rating (100%) | SHA-256 Merkle Hash Chain Audit Ledger, "Verify Hash Chain" interactive button, Regulatory Compliance Matrix |
| **Institution Leadership** | Strategic portfolio governance | Active Trials (6), Total Enrolled (150), Serious AEs (8), Portfolio Health Score (93/100) | Portfolio Study Table (health scores, phase, enrollment), Institutional Risk Map, Top 5 Clinical Risks |

---

## 2. Escalation Feature: "Report to Superior"

GCP-ASU Section 3.4 mandates rapid, documented escalation of safety concerns, protocol deviations, and ethical issues from site personnel to the Principal Investigator and Institutional Admin.

### Key Capabilities:
- **Persistent Access**: A dedicated **"⚡ Report to PI / Admin"** button is always visible on every non-Admin dashboard.
- **Categorization**: Safety, Participant, Consent, Protocol deviation, Data issue, Site issue, Ethics, Other.
- **Urgency Levels & SLAs**:
  - **Normal**: Standard protocol workflow.
  - **High**: 24-hour statutory response SLA (amber warning badge).
  - **Critical**: 1-hour statutory response SLA (persistent red warning banner on PI & Admin dashboards until acknowledged).
- **Auto-Copy to PV Officer**: When a Doctor or Coordinator files a Safety or AE/SAE report, it is auto-forwarded to the PV Officer queue.
- **Expedited EC Notification**: Critical SAEs automatically dispatch expedited regulatory notices to the Ethics Committee with an immutable sent timestamp.
- **Full Thread Lifecycle**:
  - `Sent` $\rightarrow$ `Acknowledged` $\rightarrow$ `In progress` (Assigned) $\rightarrow$ `Resolved`.
  - Threaded replies with actor names, roles, and timestamps.
  - Senders track live status and PI replies on their own "My Reports" tab.
- **Append-Only Immutability**: Escalation reports and thread events cannot be deleted (`DELETE` operations are rejected by database triggers and API route guards).

---

## 3. Data Integrity & DPDP 2023 Zero-PII Standard

Under the **Digital Personal Data Protection Act (DPDP) 2023** and GCP-ASU confidentiality requirements:
- **Zero Participant Names**: No participant names, phone numbers, email addresses, or government IDs appear anywhere in the UI or synthetic datasets.
- **Standardized Subject Codes**: Participants are strictly referenced by anonymized subject codes:
  - Format: `SUB-AIIA-{SiteNumber}-{SubjectID}` (e.g., `SUB-AIIA-01-042`).
- **Access Boundary Enforcement**:
  - Admin & PI have global multi-site visibility and a **"View as role"** switcher.
  - Research Coordinators and Doctors see only subjects at their assigned site.
  - Leadership and Regulators view de-identified aggregated summaries.

---

## 4. Real vs Mocked Breakdown

| Component | Status | Details |
|---|---|---|
| **FastAPI Backend Endpoints** | **REAL** | Fully functional REST API mounted at `/api/escalations`, `/api/escalations/study-data`, `/api/auth`, `/api/audit`, etc. |
| **Escalation Lifecycle & Actions** | **REAL** | Acknowledge, Reply, Assign, Resolve, and Notification workflows executed live and persisted in memory/database. |
| **Audit Chain & SHA-256 Merkle Verification** | **REAL** | Real cryptographic SHA-256 hash chaining on all events; interactive tampering simulation and tamper detection. |
| **GCP-ASU Illiterate Witness Gating** | **REAL** | Backend rejects illiterate participant enrollment unless impartial witness name & signature are recorded. |
| **Ethics Committee Composition Validation** | **REAL** | Validates statutory minimum of 5 members and mandatory presence of an ASU expert. |
| **Automated Test Suite (25 Tests)** | **REAL** | Pytest suite covering security, compliance, Supabase RLS, and escalation workflows with 100% pass rate. |
| **Supabase SQL Schema & RLS Policies** | **REAL** | `006_escalations.sql` defines production PostgreSQL tables, delete-prevention triggers, RLS policies, and realtime publication. |
| **Clinical Trial Participants & AEs** | **SYNTHETIC** | 6 studies, 4 sites, 150 subject codes, 60 adverse events (8 SAEs), and 15 sample escalations generated for demonstration. |
| **SMS/Email OTP Delivery** | **SYNTHETIC** | Deterministic demonstration 2FA code (`123456`) provided in response payload for seamless offline evaluation. |

---

## 5. Verification Against Acceptance Criteria

1. **Nine Visibly Different Dashboards**:
   - Each role workspace renders a customized suite of 4 KPIs, specialized tables, and interactive panels matching GCP-ASU clinical duties.
2. **Instant Critical Alert & Red SLA Banner**:
   - Doctor submits a Critical escalation on `SUB-AIIA-001-042`.
   - PI & Admin dashboards immediately display the persistent red warning banner, increment the bell counter, and place the report at the top of "Incoming Reports".
3. **Acknowledge & Reply Feedback Loop**:
   - PI acknowledges with notes and replies in the modal thread.
   - The Doctor immediately sees the updated status (`Acknowledged`) and the PI's reply in their "My Reports" view.
4. **Access Control & Route Protection**:
   - Route guards and RLS policies restrict non-Admin/non-PI roles to their own site and submitted reports.
   - Admin and PI can preview any role workspace using the top bar "View as role" preview switcher.
5. **Zero Participant Names**:
   - Confirmed across all 150 participants and 60 adverse events: zero PII, 100% subject codes. Landing page, login modal, and registration flows remain completely untouched.

---

## 6. Running Tests & Starting the Application

### Run Automated Compliance & Escalation Tests:
```powershell
python -m pytest backend/tests -v -o pythonpath=backend
```
*Expected: 25 passed in ~2.5s.*

### Launch the Full Application:
```powershell
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```
Open [http://127.0.0.1:8000](http://127.0.0.1:8000) in your web browser.
