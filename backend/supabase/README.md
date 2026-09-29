# AyurCTMS — Supabase Backend & Database Architecture

This module implements a decoupled **Supabase Backend** for AyurCTMS, incorporating the **GCP-ASU Guidelines**, the **DPDP Act 2023 with DPDP Rules 2025**, and **CERT-In Directions 2022**.

---

## 1. Directory Structure

```text
/backend/supabase/
  README.md              Setup steps, key configuration & architecture
  .env.example           Environment variables (placeholders only)
  client.ts              Browser client (publishable key) & server client (secret key)
  migrations/
    001_profiles_roles.sql       Profiles, DPDP consent tracking & auto-provision trigger
    002_submissions.sql          Submissions, version history & regulatory verifications
    003_documents.sql            Trial documents & Supabase storage bucket config
    004_audit_security_logs.sql  SHA-256 chained audit trail & security log
    005_rls_policies.sql         Row-Level Security (RLS) enforcement across all tables
  seed/
    seed_demo_users.ts   Creates the 9 statutory demo accounts
    seed_demo_data.sql   Synthetic submissions, versions & verifications
  services/
    auth.service.ts         Register, login, OTP challenge, role approval
    submissions.service.ts  Create, list, update, and formal verification sign-off
    documents.service.ts    Storage uploads & 5-minute signed download links
    audit.service.ts        Cryptographic SHA-256 chain logger & verifier
```

---

## 2. Environment Variables & Security Rules

### Required Variables:
1. `SUPABASE_URL`: Your Supabase Project URL (`https://xyzcompany.supabase.co`).
2. `SUPABASE_PUBLISHABLE_KEY`: Publishable key (formerly anon key). Safe for browser / frontend code when RLS is enabled.
3. `SUPABASE_SECRET_KEY`: Service role secret key. **BACKEND ONLY — NEVER expose to browser JavaScript or commit to Git.**

### Security Rules (Strictly Enforced):
- `SUPABASE_PUBLISHABLE_KEY` is loaded on client/browser code.
- `SUPABASE_SECRET_KEY` is **BACKEND ONLY**. `client.ts` will throw a runtime exception if `getServerClient()` is invoked in a browser environment.
- Never prefix the secret key with `NEXT_PUBLIC_` or `VITE_`.
- `.env` is ignored in Git via [.gitignore](../../.gitignore).

---

## 3. How to Run Migrations in Supabase

1. Open your [Supabase Project Dashboard](https://supabase.com/dashboard).
2. Go to the **SQL Editor** tab on the left navigation bar.
3. Run the migrations in order:
   - Run `migrations/001_profiles_roles.sql`
   - Run `migrations/002_submissions.sql`
   - Run `migrations/003_documents.sql`
   - Run `migrations/004_audit_security_logs.sql`
   - Run `migrations/005_rls_policies.sql`
4. Run `seed/seed_demo_data.sql` to populate synthetic trial records.

---

## 4. Statutory Demo Accounts (Change Before Real Use)

| Role | Email | Password | Access Scope |
|---|---|---|---|
| **Admin** | `admin@ayurctms.demo` | `Admin@Demo#2026` | System Administration, Profile Approval (Clinical Blocked) |
| **Principal Investigator** | `pi@ayurctms.demo` | `Pi@Demo#2026` | Full Clinical Access, Study-wide Submissions, Verifications |
| **Research Coordinator** | `coordinator@ayurctms.demo` | `Coord@Demo#2026` | Site-01 Enrolment, Consent, Dosing, CRF Entry |
| **Doctor / Investigator** | `doctor@ayurctms.demo` | `Doctor@Demo#2026` | Clinical Examination, Prakriti, ADR Logging |
| **Monitor (CRA)** | `monitor@ayurctms.demo` | `Monitor@Demo#2026` | Read-Only Source Access, Monitoring Visit Reports |
| **EC Member** | `ec@ayurctms.demo` | `Ethics@Demo#2026` | Ethics Review, Automated SAE Receipts |
| **PV Officer** | `pv@ayurctms.demo` | `Pharma@Demo#2026` | ASU Adverse Reaction Coding & Causality Grading |
| **Auditor / Regulator** | `auditor@ayurctms.demo` | `Audit@Demo#2026` | Read-Only SHA-256 Hash Chain Inspector |
| **Institution Leadership** | `leader@ayurctms.demo` | `Leader@Demo#2026` | Portfolio KPIs, Health Scores (De-identified Only) |

---

## 5. Security & Row-Level Security (RLS) Matrix

- **Owner Isolation:** Non-admin/PI users can only read and write submissions where `owner_id = auth.uid()`.
- **Admin/PI Study View:** Admin and PI can view all submissions across studies and execute status updates.
- **Read-Only Roles:** Monitors and Auditors have strictly read-only access.
- **Append-Only Immutability:** `audit_log` and `security_log` have database triggers prohibiting `UPDATE`, `DELETE`, and `TRUNCATE`.
- **Approval Gate:** Only users with `status = 'approved'` can query clinical data.
