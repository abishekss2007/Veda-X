# AyurCTMS — Clinical Trial Management System for Ayurveda (AIIA)

<div align="center">
  <img src="frontend/aiia-logo.jpg" alt="All India Institute of Ayurveda" width="120" style="border-radius: 50%;" />
  <p><strong>Ministry of AYUSH | All India Institute of Ayurveda (AIIA), New Delhi</strong></p>
  <p><em>Statutory Clinical Trial Workspace engineered for Ayurveda, Siddha & Unani Research</em></p>
  <p>
    <a href="https://github.com/abishekss2007/Veda-X/actions/workflows/ci.yml"><img src="https://github.com/abishekss2007/Veda-X/actions/workflows/ci.yml/badge.svg" alt="CI/CD Pipeline" /></a>
    <img src="https://img.shields.io/badge/Python-3.11-3776AB?logo=python&logoColor=white" alt="Python 3.11" />
    <img src="https://img.shields.io/badge/FastAPI-0.110+-009688?logo=fastapi&logoColor=white" alt="FastAPI" />
    <img src="https://img.shields.io/badge/License-Proprietary%20%2F%20AIIA-blue" alt="License" />
  </p>
</div>

---

## 1. Problem Statement

Clinical research in traditional Ayurvedic medicine faces critical compliance and operational hurdles:
- **Scattered Data Sinks**: Patient visits, Deha Prakriti assessments, and dosing logs remain dispersed across unstandardized paper records and unprotected spreadsheets.
- **Delayed Adverse Event Escalation**: Pharmacovigilance reporting often fails statutory 24-hour serious adverse event (SAE) reporting windows mandated by regulatory bodies.
- **Data Privacy Violations**: PII leakage in clinical registries conflicts with Indian data sovereignty and DPDP regulations.
- **Audit Deficiencies**: Conventional trial systems lack immutable, cryptographically verifiable audit trails to resist post-facto clinical record tampering.

---

## 2. Solution Overview

**AyurCTMS** provides an end-to-end, regulatory-grade clinical trial management system tailored for the **All India Institute of Ayurveda (AIIA)**. The platform integrates:
- **9 Tailored Role Dashboards** delivering specialized KPI workspaces for every clinical trial actor.
- **GCP-ASU Regulatory Gates** enforcing statutory informed consent rules, including mandatory independent witness verification for illiterate trial participants.
- **Hierarchical Escalation Engine ("Report to Superior")** providing instantaneous critical notifications, auto-copy to Pharmacovigilance, and expedited Ethics Committee alerts.
- **Cryptographic SHA-256 Merkle Audit Ledger** binding all clinical events into an immutable, verifiable hash chain.
- **Zero-PII Subject ID Standard** protecting all participant identities under DPDP Act 2023 guidelines.

---

## 3. Features by Role (9 Workspaces)

Every trial stakeholder accesses a dedicated, role-tailored dashboard with specialized key performance indicators and actionable clinical tools:

| Role | Core Purpose | Tailored KPIs | Primary Panels |
|---|---|---|---|
| **Principal Investigator (PI)** | Global trial oversight & site governance | Enrolment vs Target, Open SAEs, Central GCP Compliance, Unacknowledged Reports | Incoming Urgent Escalations, Multi-Site Enrolment Trend, Site Compliance Ranking, Participant Drilldown |
| **Admin** | System administration & compliance oversight | Pending User Approvals, Active Studies, System Compliance, Critical Alerts | User Approval Desk, Trial Site Configuration, CERT-In Security Desk, Immutable Audit Log |
| **Research Coordinator** | Site operations & subject tracking | Visits Due This Week, Pending Consents, Doses Scheduled Today, Active Participants | Participant Tracker, Visit Calendar, Quick Enrolment (GCP-ASU Consent Gated), Medication Dispense Log |
| **Doctor / Investigator** | Clinical assessments & ADR diagnosis | Active Cohort, ADRs Under Observation, Scheduled Clinical Visits, Open Reports | Subject Code Lookup, Prakriti & Dosha Assessment, Diagnostic Log, Flag Subject to PI, Report AE/SAE |
| **Monitor (CRA)** | Source Data Verification (SDV) & GCP monitoring | Missing Data Points, Overdue Protocol Visits, Protocol Deviations, Open Queries | Site SDV Progress Table, Protocol Deviations Register, Data Query Workflow, Monitoring Visit Report (MVR) Form |
| **Ethics Committee (EC)** | Ethical governance & participant rights | Pending Protocol Approvals, Renewals Due <30 Days, Amendments Under Review, SAEs Received | Protocol Approval Workflow, Version History, Statutory Quorum Rule Validation (≥5 members + mandatory ASU expert) |
| **Pharmacovigilance (PV) Officer** | Drug safety signals & adverse event triage | New AE/SAEs, Reports Due <24 Hours, Overdue Regulatory Reports, MedDRA Coded Events | 24h Statutory Countdown Queue, MedDRA & WHODrug Coding Drawer, Dosha Causality Assessment, DSMB Safety Signal Summary |
| **Auditor / Regulator** | Independent compliance & ledger inspection | Total Immutable Logs, Tamper Checks (0 Failed), Document Versions, Integrity Rating | SHA-256 Merkle Hash Chain Audit Ledger, Interactive "Verify Hash Chain" Engine, Regulatory Compliance Matrix |
| **Institution Leadership** | High-level portfolio oversight | Active AYUSH Studies, Total Enrolled Cohort, Serious Adverse Events, Portfolio Health Score | Multi-Trial Study Matrix, Institutional Risk Map, Phase & Budget Allocation Summaries |

---

## 4. System Architecture

AyurCTMS is built on a high-throughput, decoupled architecture combining a lightweight, responsive vanilla JavaScript frontend with a hardened FastAPI asynchronous backend and Supabase PostgreSQL services.

```mermaid
flowchart TD
    User["Clinical User / Browser"] -->|"HTTPS / UI Navigation"| Vercel["Vercel Frontend (Vanilla JS / CSS)"]
    Vercel -->|"/api/* Proxy Rewrite"| Render["Render FastAPI Backend"]
    Render -->|"PostgreSQL Connection / RLS"| SupaDB[("Supabase Postgres Database")]
    Render -->|"Auth & Storage APIs"| SupaAuth["Supabase Auth & S3 Storage"]
    Render -->|"Cryptographic Chaining"| AuditLog[("SHA-256 Tamper-Proof Audit Log")]
```

### Authentication & Role Switch Security Flow

Role changes within the UI require full re-authentication with mandatory step-up verification. The target role credentials must be verified on the server before a new session is granted:

```mermaid
sequenceDiagram
    autonumber
    actor User as Clinical User
    participant UI as Frontend App
    participant Auth as FastAPI / Supabase Auth
    participant Audit as Cryptographic Audit Log

    User->>UI: Select Role & Enter Credentials
    UI->>Auth: POST /api/auth/login (email, password, role)
    Auth-->>UI: 200 OK (requires_otp: true, challenge_id)
    User->>UI: Enter 6-digit OTP (demo: 123456)
    UI->>Auth: POST /api/auth/verify-otp (code, challenge_id)
    Auth->>Audit: Log LOGIN_SUCCESS (role, timestamp)
    Auth-->>UI: 200 OK (Set HttpOnly JWT Cookie)
    UI-->>User: Open Role Dashboard

    Note over User,UI: Role Switch via Preview Dropdown
    User->>UI: Select New Role in Dropdown
    UI->>UI: Lock Target Role & Show Re-auth Modal (Preserve Session)
    User->>UI: Enter Credentials for New Role + OTP
    UI->>Auth: Verify Target Role Credentials & OTP
    alt Success
        Auth->>Audit: Log ROLE_SWITCH_SUCCESS (from_role, to_role, user)
        Auth-->>UI: Issue New Session Token (Role Switched)
        UI-->>User: Discard Old Tokens & Open New Dashboard
    else Failure / Cancel
        Auth->>Audit: Log ROLE_SWITCH_FAILED (reason)
        UI-->>User: Revert Dropdown to Previous Role & Keep Dashboard
    end
```

---

## 5. Escalation Lifecycle ("Report to Superior")

GCP-ASU Section 3.4 mandates rapid, documented escalation of safety concerns, protocol deviations, and ethical issues to the Principal Investigator and Institutional Admin:

```mermaid
sequenceDiagram
    autonumber
    actor Reporter as Doctor / Coordinator
    participant System as Escalation Router
    actor PV as PV Officer
    actor EC as Ethics Committee
    actor PI as Principal Investigator / Admin

    Reporter->>System: Submit "Report to Superior" (Category, Urgency, Notes)
    System->>PI: New Escalation (Urgent Alert & Red Banner if Critical)
    opt If Safety or AE/SAE Report
        System->>PV: Auto-copy to Pharmacovigilance Queue
    end
    opt If Critical Urgency / Protocol Violation
        System->>EC: Dispatch Expedited EC Notification
    end

    PI->>System: Acknowledge Report (Status: Acknowledged)
    System-->>Reporter: Notification & Status Update on "My Reports"
    PI->>System: Assign Action / Investigation (Status: In progress)
    PI->>System: Submit Resolution Notes (Status: Resolved)
    System->>System: Append Resolution to Tamper-Proof Event Log
    System-->>Reporter: Final Resolution Notification
```

---

## 6. Role-Based Access Control (RBAC) Matrix

Server-side permissions strictly isolate tenant and role data. Client-side hiding is used only for usability; all route guards verify the caller's server-issued JWT token:

```mermaid
flowchart TD
    subgraph Global_Access["Global Multi-Site Governance"]
        PI["Principal Investigator"] -->|"View All Studies, Sites & Reports"| AllData["Full Multi-Site Clinical Data"]
        Admin["System Administrator"] -->|"System Settings, Users, Compliance"| AllData
    end

    subgraph Site_Restricted["Site-Specific Tenancy"]
        Coord["Research Coordinator"] -->|"Create & Track Site Subjects"| SiteData["Site-Specific Enrolled Cohort"]
        Doctor["Doctor / Investigator"] -->|"Clinical Assessments & ADR Logging"| SiteData
    end

    subgraph Specialized_Review["Governance & Oversight"]
        EC["Ethics Committee Member"] -->|"Review Protocols & Safety SAEs"| EthicsData["Ethics Approvals & Safety Queue"]
        PV["Pharmacovigilance Officer"] -->|"Safety Signals, MedDRA & WHODrug"| PVData["Adverse Events & Signal Register"]
        Auditor["Auditor / Regulator"] -->|"Inspect Cryptographic Ledger"| AuditData["Read-Only Audit Trail & Hash Chain"]
        Leader["Institution Leadership"] -->|"Aggregated Risk Analytics"| MacroData["De-identified Portfolio KPI Dashboards"]
        Monitor["Monitor / CRA"] -->|"Source Data Verification"| MaskedData["Masked PII Subject Verification"]
    end
```

---

## 7. Security, Regulatory Alignment & Immutability

> **Regulatory Status Notice**: This prototype is **designed to align with GCP-ASU guidelines, DPDP Act 2023, and CERT-In directions**. It is a demonstration platform and has **not yet received formal regulatory certification or accreditation**.

### Statutory Consent Gate & Merkle Hash-Chain
Enrolment requires verified consent. In cases of illiterate trial participants, an impartial witness signature must be validated on the backend before the system allows enrolment:

```mermaid
flowchart TD
    subgraph Consent_Enforcement["GCP-ASU Statutory Consent Gate"]
        Consent["Informed Consent Verification"]
        LiteracyCheck{"Participant Illiterate?"}
        Consent --> LiteracyCheck
        LiteracyCheck -->|"Yes"| WitnessCheck{"Witness Signed & Documented?"}
        LiteracyCheck -->|"No"| DirectConsent["Digital Written Consent Confirmed"]
        WitnessCheck -->|"Yes"| ValidConsent["Consent Statutory Gate Passed"]
        WitnessCheck -->|"No"| RejectEnroll["403 Forbidden: Enrolment Blocked"]
        DirectConsent --> ValidConsent
        ValidConsent --> EnrolAction["Allow Participant Enrolment & Dosing"]
    end

    subgraph Hash_Chain["Cryptographic Merkle Audit Hash Chain"]
        EnrolAction --> RecordEvent["Capture Clinical Event"]
        RecordEvent --> HashPrev["Retrieve Previous Block SHA-256 Hash"]
        HashPrev --> ComputeHash["Compute SHA-256(prev_hash + payload + timestamp)"]
        ComputeHash --> SaveBlock["Append Immutable Audit Entry"]
        SaveBlock --> Verify["Interactive Recalculation Engine (Detects any DB Tampering)"]
    end
```

---

## 8. Database Schema (Entity-Relationship Diagram)

The production Supabase PostgreSQL database enforces foreign keys, Row-Level Security (RLS), and append-only triggers:

```mermaid
erDiagram
    PROFILES ||--o{ SUBMISSIONS : "creates"
    PROFILES ||--o{ ESCALATION_REPORTS : "reports"
    PROFILES ||--o{ AUDIT_LOGS : "triggers"
    SUBMISSIONS ||--o{ SUBMISSION_VERSIONS : "has"
    SUBMISSIONS ||--o{ VERIFICATIONS : "receives"
    ESCALATION_REPORTS ||--o{ ESCALATION_TIMELINE_EVENTS : "contains"

    PROFILES {
        uuid id PK
        string email
        string full_name
        string role
        string site
        string status
        timestamp created_at
    }

    SUBMISSIONS {
        uuid id PK
        string title
        string type
        string status
        uuid owner_id FK
        string study_id
        timestamp created_at
    }

    SUBMISSION_VERSIONS {
        uuid id PK
        uuid submission_id FK
        int version_number
        string change_summary
        timestamp created_at
    }

    VERIFICATIONS {
        uuid id PK
        uuid submission_id FK
        string verifier_role
        string status
        timestamp verified_at
    }

    ESCALATION_REPORTS {
        uuid id PK
        string from_role
        string from_user
        string category
        string urgency
        string status
        timestamp created_at
    }

    ESCALATION_TIMELINE_EVENTS {
        uuid id PK
        uuid escalation_id FK
        string actor_role
        string message
        timestamp created_at
    }

    AUDIT_LOGS {
        uuid id PK
        int entry_index
        string user_email
        string role
        string action
        string entity_type
        string current_hash
        string previous_hash
        timestamp created_at
    }

    TRIAL_DOCUMENTS {
        uuid id PK
        string title
        string doc_type
        string study_id
        string file_path
        string version_tag
        timestamp created_at
    }
```

---

## 9. Real vs Synthetic / Mocked Breakdown

| Component | Status | Details |
|---|---|---|
| **FastAPI REST Endpoints** | **REAL** | 100% functional Python endpoints covering authentication, participants, consent, escalations, ethics, and audit. |
| **Escalation & Notification Engine** | **REAL** | Real acknowledge, reply, auto-copy to PV, EC broadcast, and resolution tracking. |
| **Audit Chain & SHA-256 Merkle Verification** | **REAL** | Cryptographic hash chaining on all transactions with interactive tamper simulation. |
| **GCP-ASU Consent & Quorum Enforcement** | **REAL** | Backend rejects invalid consent attempts and enforces EC composition quorum rules. |
| **Automated Pytest Suite (28 Tests)** | **REAL** | Automated tests verifying authentication, BOLA/IDOR prevention, RLS policies, and escalations. |
| **Supabase SQL Schema & RLS Policies** | **REAL** | PostgreSQL migrations with Row-Level Security, delete prevention triggers, and versioning. |
| **Clinical Trial Participants & AEs** | **SYNTHETIC** | Demonstration datasets (6 studies, 4 sites, 150 subject codes, 60 adverse events) with zero real PII. |
| **SMS / Email OTP Verification** | **SYNTHETIC** | Demonstration code (`123456`) provided for zero-friction evaluation in prototype mode. |

---

## 10. Project Structure

```
Veda-X/
├── .github/
│   ├── dependabot.yml              # Weekly dependency updates
│   ├── pull_request_template.md    # Pull request quality & security template
│   └── workflows/
│       └── ci.yml                  # Continuous Integration & Delivery workflow
├── backend/
│   ├── app/
│   │   ├── api/                    # REST route controllers (auth, escalations, deps)
│   │   ├── core/                   # Security, middleware, audit, configuration
│   │   ├── db/                     # SQLAlchemy models and database connection
│   │   └── schemas/                # Pydantic schemas and request validators
│   ├── sql/                        # RLS policies & PostgreSQL triggers
│   ├── supabase/
│   │   └── migrations/             # 6 production SQL migration files
│   └── tests/                      # 28 Pytest automated compliance test suites
├── frontend/
│   ├── aiia-logo.jpg               # Official AIIA institute emblem
│   ├── app.js                      # Core SPA router, authentication & role controller
│   ├── chart-card.js               # Clinical data visualization components
│   ├── chart-data-helper.js        # Clinical metrics aggregator
│   ├── index.css                   # Custom responsive design system
│   ├── index.html                  # Semantic single-page application shell
│   └── vercel.json                 # Frontend deployment configuration & API rewrites
├── .env.example                    # Placeholder environment variable templates
├── pytest.ini                      # Pytest runner configuration
└── requirements.txt                # Python backend dependencies
```

---

## 11. Local Setup Guide

### Environment Variables
Configure the following variable names in your `.env` (never commit active secrets to Git):

- `DATABASE_URL`
- `SECRET_KEY`
- `ENVIRONMENT`
- `SUPABASE_URL`
- `SUPABASE_ANON_KEY`
- `SUPABASE_SECRET_KEY`
- `DEMO_MODE`
- `NEXT_PUBLIC_SUPABASE_URL`
- `NEXT_PUBLIC_SUPABASE_ANON_KEY`
- `NEXT_PUBLIC_DEMO_MODE`

### Installation & Launch

1. **Clone repository**:
   ```bash
   git clone https://github.com/abishekss2007/Veda-X.git
   cd Veda-X
   ```

2. **Backend Setup**:
   ```bash
   python -m venv env
   source env/bin/activate  # On Windows: env\Scripts\activate
   pip install -r requirements.txt
   ```

3. **Run Automated Test Suite**:
   ```bash
   python -m pytest backend/tests -v -o pythonpath=backend
   ```

4. **Start Development Server**:
   ```bash
   python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
   ```
   Open `http://127.0.0.1:8000` in your browser.

---

## 12. Pre-Configured Demo Accounts

> **Demo Mode Only**: In demonstration mode, all accounts use password `Demo@2026` and OTP code `123456`.

| Role | Demo Email | Password | 2FA Verification Code |
|---|---|---|---|
| **Principal Investigator** | `pi@ayurctms.demo` | `Demo@2026` | `123456` |
| **System Administrator** | `admin@ayurctms.demo` | `Demo@2026` | `123456` |
| **Research Coordinator** | `coordinator@ayurctms.demo` | `Demo@2026` | `123456` |
| **Doctor / Investigator** | `doctor@ayurctms.demo` | `Demo@2026` | `123456` |
| **Monitor (CRA)** | `monitor@ayurctms.demo` | `Demo@2026` | `123456` |
| **Ethics Committee** | `ec@ayurctms.demo` | `Demo@2026` | `123456` |
| **Pharmacovigilance Officer** | `pv@ayurctms.demo` | `Demo@2026` | `123456` |
| **Auditor / Regulator** | `auditor@ayurctms.demo` | `Demo@2026` | `123456` |
| **Institution Leadership** | `leader@ayurctms.demo` | `Demo@2026` | `123456` |

---

## 13. CI/CD Pipeline

The automated CI/CD pipeline validates every commit and pull request on the `main` branch:

```mermaid
flowchart LR
    Push["git push / PR (main)"] --> Check["GitHub Actions CI Workflow"]
    
    subgraph Parallel_Jobs["Quality & Security Gates"]
        Check --> Backend["Backend Tests (Python 3.11, Pytest 28 Tests)"]
        Check --> Frontend["Frontend Check (Node 20 Syntax & Asset Validation)"]
        Check --> Security["Security Scan (Gitleaks + pip-audit)"]
    end

    Backend --> Gate{"All Gates Pass?"}
    Frontend --> Gate
    Security --> Gate

    Gate -->|"Yes (on push to main)"| Deploy["Deploy Job"]
    Gate -->|"No"| Fail["Build Fails & Blocks Merge"]

    Deploy -->|"Webhook Post"| Render["Render Production API"]
    Push -->|"Automatic Git Hook"| Vercel["Vercel Frontend CDN"]
```

---

## 14. Cloud Deployment Architecture

- **Frontend (Vercel)**: Deployed automatically from the GitHub `main` branch with `/api/*` rewrite rules routing API calls to Render.
- **Backend (Render)**: FastAPI ASGI application running under Uvicorn with environment secrets managed via the Render Dashboard.
- **Database (Supabase)**: Managed PostgreSQL instance with Row-Level Security, storage buckets for trial documentation, and edge functions.

---

## 15. Product Roadmap

- [x] 9-Role specialized clinical workspaces with custom KPIs
- [x] Hierarchical "Report to Superior" escalation engine with SLAs
- [x] Cryptographic SHA-256 Merkle hash chain audit ledger
- [x] Re-authentication gate on role preview switching
- [ ] *[Planned]* Go-based FHIR R4 interoperability gateway
- [ ] *[Planned]* CDISC ODM / SDTM clinical data export module
- [ ] *[Planned]* Tauri desktop offline client with local encrypted SQLite cache

---

## 16. Limitations & Disclaimer

- **Prototype Demonstration Data**: All clinical studies, participant subject codes, laboratory parameters, and adverse event listings are synthetic datasets generated for demonstration purposes.
- **Non-Certified**: AyurCTMS is an academic and hackathon prototype designed to reflect GCP-ASU and DPDP principles, but has not undergone formal CDSCO or ISO 14155 certification.
- **Zero Real Patient Data**: Real patient PII must never be stored in this demonstration prototype.
