-- ==============================================================================
-- 004_audit_security_logs.sql
-- Cryptographic SHA-256 Chained Audit Trail & Security Event Logs
-- ==============================================================================

-- Table: audit_log (Tamper-proof cryptographic ledger)
CREATE TABLE IF NOT EXISTS public.audit_log (
    id BIGSERIAL PRIMARY KEY,
    user_id UUID,
    user_email TEXT NOT NULL,
    role TEXT NOT NULL,
    action TEXT NOT NULL,
    entity TEXT NOT NULL,
    old_value JSONB,
    new_value JSONB,
    timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    previous_hash TEXT NOT NULL,
    hash TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_audit_log_timestamp ON public.audit_log(timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_audit_log_user ON public.audit_log(user_email);

-- Table: security_log (Authentication, lockout, and session events)
CREATE TABLE IF NOT EXISTS public.security_log (
    id BIGSERIAL PRIMARY KEY,
    user_email TEXT NOT NULL,
    event TEXT NOT NULL, -- login, failed_login, lockout, logout, session_timeout
    ip_address TEXT NOT NULL DEFAULT '127.0.0.1',
    timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    details TEXT
);

CREATE INDEX IF NOT EXISTS idx_security_log_timestamp ON public.security_log(timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_security_log_email ON public.security_log(user_email);

-- Trigger Function: Prohibit UPDATE and DELETE on audit and security logs
CREATE OR REPLACE FUNCTION public.prohibit_log_tampering()
RETURNS TRIGGER AS $$
BEGIN
    RAISE EXCEPTION 'SECURITY POLICY VIOLATION: Clinical trial logs are strictly immutable (CERT-In 2022 & GCP-ASU Part A.7). UPDATE and DELETE operations are forbidden.';
    RETURN NULL;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_audit_log_immutable ON public.audit_log;
CREATE TRIGGER trg_audit_log_immutable
    BEFORE UPDATE OR DELETE ON public.audit_log
    FOR EACH ROW EXECUTE FUNCTION public.prohibit_log_tampering();

DROP TRIGGER IF EXISTS trg_security_log_immutable ON public.security_log;
CREATE TRIGGER trg_security_log_immutable
    BEFORE UPDATE OR DELETE ON public.security_log
    FOR EACH ROW EXECUTE FUNCTION public.prohibit_log_tampering();
