# AyurCTMS Security & Regulatory Compliance Specification

**Platform:** AyurCTMS (Ayurveda Clinical Trial Management System)  
**Standard Compliance:**
- **Ministry of AYUSH GCP-ASU Guidelines** (Good Clinical Practice for ASU Trials)
- **Digital Personal Data Protection (DPDP) Act 2023** & **DPDP Rules 2025**
- **CERT-In Directions No. 20(3)/2022-CERT-In** (28 April 2022)
- **OWASP Top 10:2021** & **OWASP API Security Top 10:2023**

---

## 1. Executive Summary & Plain-Language Architecture

AyurCTMS is engineered to provide military-grade data protection, cryptographic auditability, and regulatory compliance for clinical trials evaluating Ayurveda, Siddha, and Unani (ASU) medicines. Unlike traditional systems that treat compliance as static policy documents, AyurCTMS enforces compliance programmatically at the database, network, API, and UI layers.

Every medical observation, subject interaction, and permission check is governed by strict tenancy boundaries, cryptographic hash-chaining, and automatic regulatory notification countdown timers.

---

## 2. Nine Distinct Role-Based Access Control (RBAC) System

AyurCTMS strictly separates operational duties into nine distinct roles. Access controls are checked on the server for every single API route—never trusting the client interface to hide buttons:

| Role | Permitted Actions | Row-Level Data Visibility | Clinical Data Access |
|---|---|---|---|
| **Research Coordinator** | Create participants, schedule visits, record consent, log doses | **Own Site Only** (e.g., SITE-01) | Full Clinical Access |
| **Doctor / Investigator (PI)** | Clinical examination, Prakriti assessment, AE/SAE management, dispensing approval | Multi-site or Site-specific | Full Clinical + Unmasked PII |
| **Monitor (CRA)** | Verify source documents, file monitoring visit reports, log protocol deviations | Multi-site | **Read-Only** (Masked PII) |
| **Ethics Committee (EC) Member** | Review protocol approvals, amendments, renewals; receive automated SAEs | Trial-wide | Summary & Safety Records |
| **PV Officer (Pharmacovigilance)** | ASU adverse reaction coding, causality evaluation, DSMB reporting | Trial-wide | Safety & Dosha Reaction Data |
| **Admin** | Manage user accounts, sites, CERT-In PoC, security logs | Organization-level | **BLOCKED from Clinical Patient Data** |
| **Auditor / Regulator** | Inspect audit trail, verify cryptographic SHA-256 chain, download compliance reports | Trial-wide | **Strictly Read-Only** |
| **Institution Leadership** | Cross-trial executive health index, recruitment KPIs, risk maps | Enterprise | **De-identified & Aggregated Only** |
| **Data Protection Officer (DPO)** | Oversee DPDP requests, handle grievance register, report 72h breaches to DPBI | Enterprise | Privacy & Compliance Ledger |

---

## 3. Defense-in-Depth Security Controls (OWASP Hardening)

### 3.1 Login, Password & Account Protection
- **Password Hashing:** Passwords are hashed using `bcrypt` with work factor 12 (or Argon2id). Passwords are never stored or transmitted in plain text.
- **Complexity & Blacklist:** Enforces minimum 10 characters and cross-checks inputs against NIST SP 800-63B blacklists of known breached passwords.
- **Account Lockout:** After 5 consecutive failed login attempts, the account is locked for 15 minutes.
- **Two-Step Login (OTP):** Compulsory 2-factor authentication for high-privilege roles (PI, PV Officer, Auditor, Admin). Single-use 6-digit cryptographic OTP expiring in 5 minutes.
- **Forgot Password Link:** Generates single-use, 15-minute expiring cryptographic tokens.
- **Timing & Enumeration Resistance:** Failed login errors return only generic `"Wrong email or password"`.

### 3.2 Sessions and Token Security
- **Access Tokens (JWT):** Expire after 15 minutes, signed using HS256 with secrets stored strictly in environment variables.
- **Refresh Tokens:** Expire after 8 hours and are automatically rotated upon each single use.
- **Cookie Security:** Delivered in `HttpOnly`, `Secure`, `SameSite=Strict` cookies, preventing XSS-based token theft.
- **Inactivity Timeout:** Users are automatically logged out after 15 minutes of inactivity, with a warning modal at 14 minutes.
- **Global Session Revocation:** Changing passwords or logging out immediately terminates all active sessions.

### 3.3 Protection of Patient Identifiable Information (PII)
- **Pseudonymous Identifiers:** Subjects are identified trial-wide only by codes (e.g., `SUB-AIIA-001-042`).
- **Direct PII Table Isolation:** Names, contact phone numbers, and addresses reside in a dedicated, isolated table (`participant_pii`).
- **Field-Level Encryption:** Direct PII fields are encrypted at rest with `AES-256-GCM` using authenticated 12-byte random nonces.
- **Masking:** Phone numbers appear masked (`98XXXXXX10`) and names are redacted on screens and exports for all roles except the PI and Site Coordinator.
- **Data Residency:** All clinical trial data is hosted within sovereign Indian borders (Mumbai, Maharashtra).

### 3.4 Input Validation & Anti-Tampering
- **Pydantic Validation:** All inputs are strictly typed, bounded (age 1-120), and sanitized.
- **Parameterized SQL:** All database interactions utilize SQLAlchemy ORM with bound parameters, neutralizing SQL injection attacks.
- **CSV/Excel Formula Injection:** Bulk exports sanitize cells starting with `=`, `+`, `-`, or `@` to prevent spreadsheet command execution.
- **File Upload Protection:**
  - Enforces a 10 MB maximum size limit.
  - Verifies true binary magic bytes (rejects disguised Windows `.exe` / ELF executables renamed to `.pdf` or `.png`).
  - Renames files to random UUIDs in private storage.
  - Generates 5-minute signed, tokenized download links.

### 3.5 API Protection & Security Headers
- **Rate Limiting:** 5 requests/minute for authentication endpoints; 100 requests/minute for general API endpoints.
- **HTTP Security Headers:**
  - `Strict-Transport-Security: max-age=63072000; includeSubDomains; preload`
  - `Content-Security-Policy: default-src 'self'; ... frame-ancestors 'none';`
  - `X-Frame-Options: DENY` (anti-clickjacking)
  - `X-Content-Type-Options: nosniff` (anti-MIME sniffing)
  - `Referrer-Policy: no-referrer`
  - `Permissions-Policy: camera=(), microphone=(), geolocation=()`

### 3.6 Tamper-Proof SHA-256 Audit Trail
- Every login, clinical data view, update, export, and privilege check is written to `audit_log`.
- **Cryptographic Hash Chaining:**
  $$\text{Hash}_i = \text{SHA256}(\text{Hash}_{i-1} \parallel \text{Timestamp} \parallel \text{User} \parallel \text{Role} \parallel \text{IP} \parallel \text{Action} \parallel \text{Details})$$
- **Database Immutability Trigger:** A PostgreSQL trigger forbids `UPDATE`, `DELETE`, and `TRUNCATE` operations on `audit_log`.
- **Verify Chain Tool:** Recomputes the entire blockchain-style ledger to pinpoint the exact record if any tampering occurs.

---

## 4. Regulatory Compliance Mapping

### 4.1 Ministry of AYUSH: GCP-ASU Guidelines
1. **Informed Consent Gate:**
   - Pre-configured template with 11 statutory sections (aims, foreseeable risks, free injury treatment, compensation for death/disability, biological sample use).
   - Multi-language storage (Hindi, English, Regional) with "Explained orally" confirmation.
   - Illiterate participant protection: Impartial witness name and signature are mandatory; enrolment is blocked without them.
   - Version tracking: EC-approved amendments flag all previous participants with `requires_reconsent = True`.
   - Dosing Gate: No participant can be dosed without valid written consent on file.
2. **Ethics Committee Module:**
   - 9 statutory member roles register with automatic warnings if fewer than 5 members or if the ASU expert is missing.
   - Automated timestamped dispatch of Serious Adverse Events (SAEs) and amendments to EC members.
3. **Ayurveda-Specific Clinical Fields:**
   - Deha Prakriti questionnaire auto-calculating Vata, Pitta, and Kapha dominance.
   - Anupana (vehicle), Desh (habitat), Kala (season/time), and Pathya/Apathya (dietary/lifestyle regimens).
   - ASU Adverse Drug Reaction (ADR) coding with Dosha/Srotas causality grading.
4. **Investigational Product Tracking:**
   - Batch tracking, storage temperature/humidity controls, and participant dispensing log.
   - Blinded label generator displaying `"For Clinical Studies only"`, study code, investigator contact, and participant subject code (NEVER patient name).
5. **5-Year Archival Retention:**
   - All trial records are preserved for at least 5 years post-study completion; auto-deletion is permanently disabled.

### 4.2 DPDP Act 2023 & DPDP Rules 2025
1. **Notice & Consent:** Standalone plain-language privacy notice without pre-ticked boxes.
2. **Minors & Vulnerable Persons (Section 9):** Requires verifiable guardian consent before enrolling anyone under 18; tracking and profiling of minors is prohibited.
3. **DPO Details:** DPO coordinates displayed in every screen footer and consent notice.
4. **Data Principal Rights Portal:** Workflow for Access, Correction, Update, and Erasure requests with a 90-day countdown timer.
5. **Consent Withdrawal:** Processing halts immediately; records are marked `"retained for legal reasons"` for GCP-ASU regulatory preservation.
6. **72-Hour Breach Notification (Rule 7):** Live countdown timer to report personal data breaches to the Data Protection Board of India (DPBI) and dispatch immediate template notifications to affected data principals.

### 4.3 CERT-In Directions 2022
1. **6-Hour Incident Reporting:** Live countdown timer from incident discovery, supporting all Annexure I incident categories with a pre-filled official report generator targeting `incident@cert-in.org.in` and Phone `1800-11-4949`.
2. **Point of Contact (PoC):** Dedicated admin configuration for the designated 24x7 CERT-In liaison.
3. **NTP Server Clock Synchronization:** Clocks synchronized with National Informatics Centre (`time.nic.in`) and CSIR-NPL (`time.nplindia.org`).
4. **Rolling 180-Day Log Retention:** All system and security logs preserved domestically for 180 days and exportable on demand.

---

## 5. Vulnerability Disclosure & Incident Reporting Policy

If you discover a security vulnerability or discrepancy in AyurCTMS:
1. **Do not disclose publicly.**
2. Send an encrypted email to the Designated Security Officer:
   - **Email:** `ciso@ayurctms.gov.in` and `dpo@ayurctms.gov.in`
   - **Emergency Line:** `+91-11-2953-8402` / `1800-11-4949`
3. Include the endpoint, reproduction steps, and potential regulatory impact.
4. The security response team acknowledges reports within 2 hours and issues remediation updates in compliance with CERT-In 6-hour guidelines.
