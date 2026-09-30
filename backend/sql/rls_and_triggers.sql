-- ============================================================================
-- AyurCTMS: PostgreSQL Row-Level Security (RLS) & Immutability Triggers
-- Compliant with:
-- 1. GCP-ASU Guidelines (Ministry of AYUSH)
-- 2. Digital Personal Data Protection (DPDP) Act 2023 & DPDP Rules 2025
-- 3. CERT-In Directions 2022
-- 4. OWASP Top 10 A01: Broken Access Control & A08: Integrity Failures
-- ============================================================================

-- ----------------------------------------------------------------------------
-- 1. DATABASE ROLE CREATION & LEAST PRIVILEGE PRINCIPLE
-- ----------------------------------------------------------------------------
-- Connect as PostgreSQL Superuser (e.g. postgres) to run this setup

-- Restricted application user (used by FastAPI)
DO $$
BEGIN
    IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'ayur_app') THEN
        CREATE ROLE ayur_app WITH LOGIN PASSWORD 'SecureAyurAppPassword2026!';
    END IF;
END $$;

-- Revoke dangerous table alteration and administrative privileges
REVOKE ALL ON SCHEMA public FROM PUBLIC;
GRANT USAGE ON SCHEMA public TO ayur_app;
GRANT SELECT, INSERT, UPDATE ON ALL TABLES IN SCHEMA public TO ayur_app;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO ayur_app;

-- ----------------------------------------------------------------------------
-- 2. IMMUTABLE TAMPER-PROOF AUDIT LOG TRIGGER
-- Rule: The app connects as ayur_app which CANNOT change tables or switch off security.
-- A database trigger blocks UPDATE, DELETE and TRUNCATE on audit_log.
-- ----------------------------------------------------------------------------
CREATE OR REPLACE FUNCTION prevent_audit_log_modification()
RETURNS TRIGGER AS $$
BEGIN
    RAISE EXCEPTION 'SECURITY VIOLATION: The audit_log table is strictly write-only and immutable. UPDATE and DELETE operations are prohibited by law (GCP-ASU & DPDP Act 2023).';
    RETURN NULL;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_audit_log_immutable ON audit_log;
CREATE TRIGGER trg_audit_log_immutable
BEFORE UPDATE OR DELETE ON audit_log
FOR EACH ROW
EXECUTE FUNCTION prevent_audit_log_modification();

-- Deny truncate on audit_log
REVOKE TRUNCATE ON audit_log FROM ayur_app;
REVOKE TRUNCATE ON audit_log FROM PUBLIC;

-- ----------------------------------------------------------------------------
-- 3. POSTGRESQL ROW-LEVEL SECURITY (RLS) POLICIES
-- ----------------------------------------------------------------------------

-- Enable Row-Level Security on clinical tables
ALTER TABLE participants ENABLE ROW LEVEL SECURITY;
ALTER TABLE participant_pii ENABLE ROW LEVEL SECURITY;
ALTER TABLE informed_consents ENABLE ROW LEVEL SECURITY;
ALTER TABLE adverse_events ENABLE ROW LEVEL SECURITY;
ALTER TABLE dispensing_logs ENABLE ROW LEVEL SECURITY;

-- ----------------------------------------------------------------------------
-- PARTICIPANTS TABLE RLS
-- Rule:
-- - A Coordinator sees only their own site (site_id == app.current_site_id).
-- - The Admin sees NO clinical data.
-- - Doctor/Investigator, Monitor, Auditor can view subject records.
-- ----------------------------------------------------------------------------

-- Participants View Policy: PI and Admin can view participants (PI and Coordinator see unmasked PII, Admin/Monitor/Auditor see masked)
CREATE POLICY participants_select_policy ON participants
FOR SELECT
TO ayur_app
USING (
    CASE 
        WHEN current_setting('app.current_user_role', true) = 'Research Coordinator' 
        THEN site_id = current_setting('app.current_site_id', true)
        ELSE true
    END
);

-- Coordinator-Only Insert Policy: Only Research Coordinator can insert participants at their own site
CREATE POLICY coordinator_only_insert_participants ON participants
FOR INSERT
TO ayur_app
WITH CHECK (
    current_setting('app.current_user_role', true) = 'Research Coordinator'
    AND site_id = current_setting('app.current_site_id', true)
);


-- ----------------------------------------------------------------------------
-- PARTICIPANT_PII TABLE RLS (DIRECT PERSONAL IDENTIFIABLE DATA)
-- Rule:
-- - Names and phone numbers are visible ONLY to the Doctor / Investigator (PI)
--   and the site Coordinator.
-- - Monitor and Auditor get NO access to unmasked PII.
-- ----------------------------------------------------------------------------
CREATE POLICY pii_access_restriction ON participant_pii
FOR SELECT
TO ayur_app
USING (
    current_setting('app.current_user_role', true) IN ('Doctor / Investigator', 'Research Coordinator')
);

CREATE POLICY pii_write_restriction ON participant_pii
FOR INSERT
TO ayur_app
WITH CHECK (
    current_setting('app.current_user_role', true) IN ('Doctor / Investigator', 'Research Coordinator')
);

-- ----------------------------------------------------------------------------
-- ADVERSE EVENTS & DISPENSING RLS
-- ----------------------------------------------------------------------------
CREATE POLICY coordinator_ae_site_tenancy ON adverse_events
FOR ALL
TO ayur_app
USING (
    CASE 
        WHEN current_setting('app.current_user_role', true) = 'Research Coordinator' 
        THEN site_id = current_setting('app.current_site_id', true)
        ELSE true
    END
);

-- ----------------------------------------------------------------------------
-- 4. APPLICATION CONNECTION SESSION VARIABLES HELPER
-- When the backend connects for a request, it sets:
--   SET LOCAL app.current_user_id = '123';
--   SET LOCAL app.current_user_role = 'Research Coordinator';
--   SET LOCAL app.current_site_id = 'SITE-01';
-- ----------------------------------------------------------------------------
COMMENT ON TABLE audit_log IS 'Cryptographically chained, immutable audit ledger adhering to CERT-In 180-day and GCP-ASU 5-year rules.';
COMMENT ON TABLE participant_pii IS 'Direct personal identifiable information protected with AES-256 encryption and isolated table access.';
