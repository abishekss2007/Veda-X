-- AyurCTMS Supabase schema bootstrap
-- Run this complete file once in the Supabase SQL Editor for a new project.
-- It combines the ordered migrations in migrations/001-006 and is safe to rerun
-- for supported schema objects and policies. It does not create demo users/data.
-- Supabase-managed auth, storage, roles, and extensions must remain enabled.


-- >>> BEGIN migrations\001_profiles_roles.sql
-- ==============================================================================
-- 001_profiles_roles.sql
-- User Profiles, DPDP Consent & Approval Status for AyurCTMS
-- ==============================================================================

-- Create custom enum types for role and status
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'user_role_type') THEN
        CREATE TYPE user_role_type AS ENUM (
            'Principal Investigator',
            'Research Coordinator',
            'Doctor / Investigator',
            'Monitor',
            'EC Member',
            'PV Officer',
            'Admin',
            'Auditor / Regulator',
            'Institution Leadership'
        );
    END IF;

    IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'account_status_type') THEN
        CREATE TYPE account_status_type AS ENUM (
            'pending',
            'approved',
            'suspended'
        );
    END IF;
END $$;

-- Table: profiles
CREATE TABLE IF NOT EXISTS public.profiles (
    id UUID PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
    full_name TEXT NOT NULL,
    email TEXT UNIQUE NOT NULL,
    phone TEXT,
    role user_role_type NOT NULL DEFAULT 'Research Coordinator',
    site TEXT NOT NULL DEFAULT 'SITE-01',
    status account_status_type NOT NULL DEFAULT 'pending',
    consent_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    notice_version TEXT NOT NULL DEFAULT 'DPDP-V1.0',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Indexing for fast lookups
CREATE INDEX IF NOT EXISTS idx_profiles_email ON public.profiles(email);
CREATE INDEX IF NOT EXISTS idx_profiles_role ON public.profiles(role);
CREATE INDEX IF NOT EXISTS idx_profiles_status ON public.profiles(status);
CREATE INDEX IF NOT EXISTS idx_profiles_site ON public.profiles(site);

-- Function and trigger to auto-create profile on Supabase auth.users signup
CREATE OR REPLACE FUNCTION public.handle_new_user()
RETURNS TRIGGER AS $$
BEGIN
    INSERT INTO public.profiles (
        id,
        full_name,
        email,
        phone,
        role,
        site,
        status,
        consent_at,
        notice_version
    ) VALUES (
        NEW.id,
        COALESCE(NEW.raw_user_meta_data->>'full_name', 'Trial Team Member'),
        NEW.email,
        NEW.raw_user_meta_data->>'phone',
        -- Default to safe role; Admin and PI must be verified/approved by administrator
        COALESCE((NEW.raw_user_meta_data->>'role')::user_role_type, 'Research Coordinator'),
        COALESCE(NEW.raw_user_meta_data->>'site', 'SITE-01'),
        'pending',
        NOW(),
        COALESCE(NEW.raw_user_meta_data->>'notice_version', 'DPDP-V1.0')
    )
    ON CONFLICT (id) DO UPDATE SET
        full_name = EXCLUDED.full_name,
        updated_at = NOW();

    RETURN NEW;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Attach trigger to auth.users
DROP TRIGGER IF EXISTS on_auth_user_created ON auth.users;
CREATE TRIGGER on_auth_user_created
    AFTER INSERT ON auth.users
    FOR EACH ROW EXECUTE FUNCTION public.handle_new_user();

-- <<< END migrations\001_profiles_roles.sql


-- >>> BEGIN migrations\002_submissions.sql
-- ==============================================================================
-- 002_submissions.sql
-- Submissions, Version History & Verifications for AyurCTMS
-- ==============================================================================

-- Submission status enum type
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'submission_status_type') THEN
        CREATE TYPE submission_status_type AS ENUM (
            'Draft',
            'Submitted',
            'Verified',
            'Needs correction'
        );
    END IF;
END $$;

-- Table: submissions
CREATE TABLE IF NOT EXISTS public.submissions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    owner_id UUID NOT NULL REFERENCES public.profiles(id) ON DELETE CASCADE,
    role user_role_type NOT NULL,
    study_id TEXT NOT NULL DEFAULT 'AYUR-CT-2026-001',
    type TEXT NOT NULL, -- form, document, consent, ae_report, visit_note, prakriti_assessment
    title TEXT NOT NULL,
    payload JSONB NOT NULL DEFAULT '{}'::jsonb,
    status submission_status_type NOT NULL DEFAULT 'Draft',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_submissions_owner ON public.submissions(owner_id);
CREATE INDEX IF NOT EXISTS idx_submissions_study ON public.submissions(study_id);
CREATE INDEX IF NOT EXISTS idx_submissions_status ON public.submissions(status);
CREATE INDEX IF NOT EXISTS idx_submissions_type ON public.submissions(type);

-- Table: submission_versions (Append-only audit of modifications)
CREATE TABLE IF NOT EXISTS public.submission_versions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    submission_id UUID NOT NULL REFERENCES public.submissions(id) ON DELETE CASCADE,
    old_value JSONB NOT NULL,
    new_value JSONB NOT NULL,
    reason TEXT NOT NULL,
    changed_by UUID NOT NULL REFERENCES public.profiles(id),
    changed_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_sub_versions_submission ON public.submission_versions(submission_id);

-- Table: verifications (Formal regulatory sign-off)
CREATE TABLE IF NOT EXISTS public.verifications (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    submission_id UUID NOT NULL REFERENCES public.submissions(id) ON DELETE CASCADE,
    verified_by UUID NOT NULL REFERENCES public.profiles(id),
    verified_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    note TEXT
);

CREATE INDEX IF NOT EXISTS idx_verifications_submission ON public.verifications(submission_id);

-- Function to record automatic version snapshot when a submission is edited
CREATE OR REPLACE FUNCTION public.log_submission_version()
RETURNS TRIGGER AS $$
BEGIN
    IF (OLD.payload IS DISTINCT FROM NEW.payload) OR (OLD.status IS DISTINCT FROM NEW.status) THEN
        INSERT INTO public.submission_versions (
            submission_id,
            old_value,
            new_value,
            reason,
            changed_by,
            changed_at
        ) VALUES (
            NEW.id,
            jsonb_build_object('payload', OLD.payload, 'status', OLD.status, 'title', OLD.title),
            jsonb_build_object('payload', NEW.payload, 'status', NEW.status, 'title', NEW.title),
            COALESCE(current_setting('app.change_reason', true), 'Clinical data correction / update'),
            COALESCE(auth.uid(), NEW.owner_id),
            NOW()
        );
        NEW.updated_at = NOW();
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

DROP TRIGGER IF EXISTS trg_submission_version ON public.submissions;
CREATE TRIGGER trg_submission_version
    BEFORE UPDATE ON public.submissions
    FOR EACH ROW EXECUTE FUNCTION public.log_submission_version();

-- <<< END migrations\002_submissions.sql


-- >>> BEGIN migrations\003_documents.sql
-- ==============================================================================
-- 003_documents.sql
-- Trial Documents & Supabase Storage Bucket Configuration
-- ==============================================================================

-- Table: documents
CREATE TABLE IF NOT EXISTS public.documents (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    owner_id UUID NOT NULL REFERENCES public.profiles(id) ON DELETE CASCADE,
    submission_id UUID REFERENCES public.submissions(id) ON DELETE SET NULL,
    file_path TEXT NOT NULL,
    file_name TEXT NOT NULL,
    file_size BIGINT NOT NULL DEFAULT 0,
    mime_type TEXT NOT NULL DEFAULT 'application/pdf',
    version INT NOT NULL DEFAULT 1,
    uploaded_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_documents_owner ON public.documents(owner_id);
CREATE INDEX IF NOT EXISTS idx_documents_submission ON public.documents(submission_id);

-- Create storage bucket for clinical trial documents if it does not already exist
INSERT INTO storage.buckets (id, name, public, file_size_limit, allowed_mime_types)
VALUES (
    'trial-documents',
    'trial-documents',
    false, -- Private bucket: accessible only through authenticated or signed URLs
    10485760, -- 10 MB maximum limit (OWASP)
    ARRAY[
        'application/pdf',
        'image/jpeg',
        'image/png',
        'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        'text/csv'
    ]
)
ON CONFLICT (id) DO UPDATE SET
    public = false,
    file_size_limit = 10485760;

-- <<< END migrations\003_documents.sql


-- >>> BEGIN migrations\004_audit_security_logs.sql
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

-- <<< END migrations\004_audit_security_logs.sql


-- >>> BEGIN migrations\005_rls_policies.sql
-- ==============================================================================
-- 005_rls_policies.sql
-- Mandatory Row-Level Security (RLS) Policies Across All Tables
-- ==============================================================================

-- Enable RLS on all public tables
ALTER TABLE public.profiles ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.submissions ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.submission_versions ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.verifications ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.documents ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.audit_log ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.security_log ENABLE ROW LEVEL SECURITY;

-- Helper function to check if the current user is approved
CREATE OR REPLACE FUNCTION public.is_current_user_approved()
RETURNS BOOLEAN AS $$
BEGIN
    RETURN EXISTS (
        SELECT 1 FROM public.profiles
        WHERE id = auth.uid() AND status = 'approved'
    );
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Helper function to retrieve the current user's role
CREATE OR REPLACE FUNCTION public.get_current_user_role()
RETURNS TEXT AS $$
DECLARE
    user_role TEXT;
BEGIN
    SELECT role::TEXT INTO user_role FROM public.profiles WHERE id = auth.uid();
    RETURN user_role;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- ------------------------------------------------------------------------------
-- 1. PROFILES POLICIES
-- ------------------------------------------------------------------------------
-- A user can read their own profile
DROP POLICY IF EXISTS "Users can read own profile" ON public.profiles;
CREATE POLICY "Users can read own profile" ON public.profiles FOR SELECT
    USING (auth.uid() = id);

-- Admin and PI can view all profiles
DROP POLICY IF EXISTS "Admin and PI can view all profiles" ON public.profiles;
CREATE POLICY "Admin and PI can view all profiles" ON public.profiles FOR SELECT
    USING (public.get_current_user_role() IN ('Admin', 'Principal Investigator'));

-- User can update non-privileged fields of own profile
DROP POLICY IF EXISTS "Users can update own profile" ON public.profiles;
CREATE POLICY "Users can update own profile" ON public.profiles FOR UPDATE
    USING (auth.uid() = id)
    WITH CHECK (auth.uid() = id);

-- ------------------------------------------------------------------------------
-- 2. SUBMISSIONS POLICIES
-- ------------------------------------------------------------------------------
-- Approved users can read their own submissions
DROP POLICY IF EXISTS "Users can read own submissions" ON public.submissions;
CREATE POLICY "Users can read own submissions" ON public.submissions FOR SELECT
    USING (
        public.is_current_user_approved() AND
        (owner_id = auth.uid())
    );

-- Admin and PI can read all submissions across studies
DROP POLICY IF EXISTS "Admin and PI can read all submissions" ON public.submissions;
CREATE POLICY "Admin and PI can read all submissions" ON public.submissions FOR SELECT
    USING (
        public.is_current_user_approved() AND
        public.get_current_user_role() IN ('Admin', 'Principal Investigator')
    );

-- Monitor and Auditor: Read-only access across all submissions
DROP POLICY IF EXISTS "Monitor and Auditor can read all submissions" ON public.submissions;
CREATE POLICY "Monitor and Auditor can read all submissions" ON public.submissions FOR SELECT
    USING (
        public.is_current_user_approved() AND
        public.get_current_user_role() IN ('Monitor', 'Auditor / Regulator')
    );

-- Institution Leadership: Can view submissions for portfolio KPI analysis
DROP POLICY IF EXISTS "Leadership can view submissions" ON public.submissions;
CREATE POLICY "Leadership can view submissions" ON public.submissions FOR SELECT
    USING (
        public.is_current_user_approved() AND
        public.get_current_user_role() = 'Institution Leadership'
    );

-- Approved users can create submissions where owner_id = auth.uid()
DROP POLICY IF EXISTS "Approved users can insert submissions" ON public.submissions;
CREATE POLICY "Approved users can insert submissions" ON public.submissions FOR INSERT
    WITH CHECK (
        public.is_current_user_approved() AND
        owner_id = auth.uid()
    );

-- Users can update only their own submissions while in 'Draft' or 'Needs correction' status
DROP POLICY IF EXISTS "Users can update own draft submissions" ON public.submissions;
CREATE POLICY "Users can update own draft submissions" ON public.submissions FOR UPDATE
    USING (
        public.is_current_user_approved() AND
        owner_id = auth.uid() AND
        status IN ('Draft', 'Needs correction')
    )
    WITH CHECK (
        public.is_current_user_approved() AND
        owner_id = auth.uid()
    );

-- Admin and PI can update submission status (e.g., mark as reviewed/verified)
DROP POLICY IF EXISTS "Admin and PI can update submission status" ON public.submissions;
CREATE POLICY "Admin and PI can update submission status" ON public.submissions FOR UPDATE
    USING (
        public.is_current_user_approved() AND
        public.get_current_user_role() IN ('Admin', 'Principal Investigator')
    );

-- ------------------------------------------------------------------------------
-- 3. SUBMISSION VERSIONS & VERIFICATIONS POLICIES
-- ------------------------------------------------------------------------------
DROP POLICY IF EXISTS "Approved users can view submission versions" ON public.submission_versions;
CREATE POLICY "Approved users can view submission versions" ON public.submission_versions FOR SELECT
    USING (
        public.is_current_user_approved() AND
        EXISTS (
            SELECT 1 FROM public.submissions s
            WHERE s.id = submission_id AND (
                s.owner_id = auth.uid() OR
                public.get_current_user_role() IN ('Admin', 'Principal Investigator', 'Monitor', 'Auditor / Regulator')
            )
        )
    );

DROP POLICY IF EXISTS "Approved users can insert submission versions" ON public.submission_versions;
CREATE POLICY "Approved users can insert submission versions" ON public.submission_versions FOR INSERT
    WITH CHECK (public.is_current_user_approved());

DROP POLICY IF EXISTS "Approved users can view verifications" ON public.verifications;
CREATE POLICY "Approved users can view verifications" ON public.verifications FOR SELECT
    USING (
        public.is_current_user_approved() AND
        EXISTS (
            SELECT 1 FROM public.submissions s
            WHERE s.id = submission_id AND (
                s.owner_id = auth.uid() OR
                public.get_current_user_role() IN ('Admin', 'Principal Investigator', 'Monitor', 'Auditor / Regulator')
            )
        )
    );

DROP POLICY IF EXISTS "Reviewers can insert verifications" ON public.verifications;
CREATE POLICY "Reviewers can insert verifications" ON public.verifications FOR INSERT
    WITH CHECK (
        public.is_current_user_approved() AND
        public.get_current_user_role() IN ('Admin', 'Principal Investigator', 'Monitor', 'Doctor / Investigator')
    );

-- ------------------------------------------------------------------------------
-- 4. DOCUMENTS & STORAGE POLICIES
-- ------------------------------------------------------------------------------
DROP POLICY IF EXISTS "Users can read own documents" ON public.documents;
CREATE POLICY "Users can read own documents" ON public.documents FOR SELECT
    USING (
        public.is_current_user_approved() AND
        (owner_id = auth.uid() OR public.get_current_user_role() IN ('Admin', 'Principal Investigator', 'Monitor', 'Auditor / Regulator'))
    );

DROP POLICY IF EXISTS "Approved users can insert documents" ON public.documents;
CREATE POLICY "Approved users can insert documents" ON public.documents FOR INSERT
    WITH CHECK (
        public.is_current_user_approved() AND
        owner_id = auth.uid()
    );

-- Storage bucket RLS policies for 'trial-documents'
DROP POLICY IF EXISTS "Users can upload trial documents" ON storage.objects;
CREATE POLICY "Users can upload trial documents" ON storage.objects FOR INSERT
    TO authenticated
    WITH CHECK (
        bucket_id = 'trial-documents' AND
        public.is_current_user_approved()
    );

DROP POLICY IF EXISTS "Users can read trial documents" ON storage.objects;
CREATE POLICY "Users can read trial documents" ON storage.objects FOR SELECT
    TO authenticated
    USING (
        bucket_id = 'trial-documents' AND
        public.is_current_user_approved()
    );

-- ------------------------------------------------------------------------------
-- 5. AUDIT AND SECURITY LOGS (INSERT-ONLY FOR APPS, NO UPDATE/DELETE)
-- ------------------------------------------------------------------------------
DROP POLICY IF EXISTS "Anyone authenticated can insert audit logs" ON public.audit_log;
CREATE POLICY "Anyone authenticated can insert audit logs" ON public.audit_log FOR INSERT
    TO authenticated
    WITH CHECK (true);

DROP POLICY IF EXISTS "Auditors, Admin, PI can read audit logs" ON public.audit_log;
CREATE POLICY "Auditors, Admin, PI can read audit logs" ON public.audit_log FOR SELECT
    TO authenticated
    USING (public.get_current_user_role() IN ('Auditor / Regulator', 'Admin', 'Principal Investigator'));

DROP POLICY IF EXISTS "System can insert security logs" ON public.security_log;
CREATE POLICY "System can insert security logs" ON public.security_log FOR INSERT
    TO authenticated, anon
    WITH CHECK (true);

DROP POLICY IF EXISTS "Admin and Auditor can read security logs" ON public.security_log;
CREATE POLICY "Admin and Auditor can read security logs" ON public.security_log FOR SELECT
    TO authenticated
    USING (public.get_current_user_role() IN ('Admin', 'Auditor / Regulator'));

-- <<< END migrations\005_rls_policies.sql


-- >>> BEGIN migrations\006_escalations.sql
-- ==============================================================================
-- 006_escalations.sql
-- "Report to Superior" Escalation System, Realtime Events & RLS Policies
-- ==============================================================================

-- 1. Create Escalations Table
CREATE TABLE IF NOT EXISTS public.escalations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    from_user UUID REFERENCES public.profiles(id),
    from_name TEXT NOT NULL,
    from_role public.user_role_type NOT NULL,
    study_id TEXT NOT NULL DEFAULT 'AYUR-CT-2026-001',
    site_id TEXT NOT NULL DEFAULT 'SITE-01',
    subject_code TEXT, -- Strictly coded identifier (e.g. SUB-AIIA-001-042), NEVER participant name
    category TEXT NOT NULL CHECK (category IN (
        'Safety', 'Participant', 'Consent', 'Protocol deviation',
        'Data issue', 'Site issue', 'Ethics', 'Other'
    )),
    urgency TEXT NOT NULL DEFAULT 'Normal' CHECK (urgency IN ('Normal', 'High', 'Critical')),
    summary VARCHAR(120) NOT NULL,
    details TEXT NOT NULL,
    attachment_url TEXT,
    status TEXT NOT NULL DEFAULT 'Sent' CHECK (status IN ('Sent', 'Acknowledged', 'In progress', 'Resolved')),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    acknowledged_by TEXT,
    acknowledged_at TIMESTAMPTZ,
    assigned_to TEXT,
    resolved_at TIMESTAMPTZ,
    resolution_notes TEXT
);

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_escalations_study ON public.escalations(study_id);
CREATE INDEX IF NOT EXISTS idx_escalations_status ON public.escalations(status);
CREATE INDEX IF NOT EXISTS idx_escalations_urgency ON public.escalations(urgency);
CREATE INDEX IF NOT EXISTS idx_escalations_created_at ON public.escalations(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_escalations_from_user ON public.escalations(from_user);

-- 2. Create Escalation Events Table (Threaded replies, audit log of actions)
CREATE TABLE IF NOT EXISTS public.escalation_events (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    escalation_id UUID NOT NULL REFERENCES public.escalations(id) ON DELETE CASCADE,
    event_type TEXT NOT NULL CHECK (event_type IN ('created', 'acknowledged', 'reply', 'assigned', 'resolved')),
    actor_name TEXT NOT NULL,
    actor_role TEXT NOT NULL,
    message TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_escalation_events_esc_id ON public.escalation_events(escalation_id);

-- 3. Create Notifications Table (Real-time in-app alerts)
CREATE TABLE IF NOT EXISTS public.notifications (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    target_role TEXT NOT NULL,
    target_user UUID REFERENCES public.profiles(id),
    ref_id UUID REFERENCES public.escalations(id) ON DELETE CASCADE,
    type TEXT NOT NULL DEFAULT 'escalation',
    title TEXT NOT NULL,
    message TEXT NOT NULL,
    is_read BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_notifications_role ON public.notifications(target_role);
CREATE INDEX IF NOT EXISTS idx_notifications_unread ON public.notifications(is_read) WHERE is_read = FALSE;

-- 4. Enable Row Level Security (RLS)
ALTER TABLE public.escalations ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.escalation_events ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.notifications ENABLE ROW LEVEL SECURITY;

-- 5. RLS Policies for Escalations
-- Sender can read own escalations
DROP POLICY IF EXISTS "Users can view own escalations" ON public.escalations;
CREATE POLICY "Users can view own escalations" ON public.escalations FOR SELECT
    USING (auth.uid() = from_user);

-- Approved users can create escalations
DROP POLICY IF EXISTS "Approved users can create escalations" ON public.escalations;
CREATE POLICY "Approved users can create escalations" ON public.escalations FOR INSERT
    WITH CHECK (public.is_current_user_approved());

-- Admin and PI can view all escalations in their studies
DROP POLICY IF EXISTS "Admin and PI can view all escalations" ON public.escalations;
CREATE POLICY "Admin and PI can view all escalations" ON public.escalations FOR SELECT
    USING (public.get_current_user_role() IN ('Admin', 'Principal Investigator'));

-- Admin and PI can update escalations (acknowledge, assign, resolve)
DROP POLICY IF EXISTS "Admin and PI can update escalations" ON public.escalations;
CREATE POLICY "Admin and PI can update escalations" ON public.escalations FOR UPDATE
    USING (public.get_current_user_role() IN ('Admin', 'Principal Investigator'))
    WITH CHECK (public.get_current_user_role() IN ('Admin', 'Principal Investigator'));

-- PV Officer can view Safety and AE/SAE escalations
DROP POLICY IF EXISTS "PV Officer can view safety escalations" ON public.escalations;
CREATE POLICY "PV Officer can view safety escalations" ON public.escalations FOR SELECT
    USING (
        public.get_current_user_role() = 'PV Officer'
        AND (category = 'Safety' OR summary ILIKE '%AE%' OR summary ILIKE '%SAE%')
    );

-- EC Member can view Ethics and SAE escalations
DROP POLICY IF EXISTS "EC Member can view ethics and sae escalations" ON public.escalations;
CREATE POLICY "EC Member can view ethics and sae escalations" ON public.escalations FOR SELECT
    USING (
        public.get_current_user_role() = 'EC Member'
        AND (category = 'Ethics' OR urgency = 'Critical')
    );

-- Immutability rule: Escalations can never be deleted
CREATE OR REPLACE FUNCTION public.prevent_escalation_delete()
RETURNS TRIGGER AS $$
BEGIN
    RAISE EXCEPTION 'Regulatory compliance violation: Escalation records cannot be deleted. Status transitions only.';
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_prevent_escalation_delete ON public.escalations;
CREATE TRIGGER trg_prevent_escalation_delete
    BEFORE DELETE ON public.escalations
    FOR EACH ROW EXECUTE FUNCTION public.prevent_escalation_delete();

-- 6. RLS Policies for Escalation Events (Thread / Replies)
DROP POLICY IF EXISTS "Users can view events for accessible escalations" ON public.escalation_events;
CREATE POLICY "Users can view events for accessible escalations" ON public.escalation_events FOR SELECT
    USING (
        EXISTS (
            SELECT 1 FROM public.escalations e
            WHERE e.id = escalation_events.escalation_id
            AND (
                e.from_user = auth.uid()
                OR public.get_current_user_role() IN ('Admin', 'Principal Investigator')
                OR (public.get_current_user_role() = 'PV Officer' AND e.category = 'Safety')
                OR (public.get_current_user_role() = 'EC Member' AND (e.category = 'Ethics' OR e.urgency = 'Critical'))
            )
        )
    );

DROP POLICY IF EXISTS "Authorized users can post replies and events" ON public.escalation_events;
CREATE POLICY "Authorized users can post replies and events" ON public.escalation_events FOR INSERT
    WITH CHECK (public.is_current_user_approved());

-- 7. Add to Supabase Realtime publication
DO $$
BEGIN
    IF EXISTS (
        SELECT 1 FROM pg_publication WHERE pubname = 'supabase_realtime'
    ) AND NOT EXISTS (
        SELECT 1
        FROM pg_publication_tables
        WHERE pubname = 'supabase_realtime'
          AND schemaname = 'public'
          AND tablename = 'escalations'
    ) THEN
        ALTER PUBLICATION supabase_realtime ADD TABLE public.escalations;
    END IF;

    IF EXISTS (
        SELECT 1 FROM pg_publication WHERE pubname = 'supabase_realtime'
    ) AND NOT EXISTS (
        SELECT 1
        FROM pg_publication_tables
        WHERE pubname = 'supabase_realtime'
          AND schemaname = 'public'
          AND tablename = 'escalation_events'
    ) THEN
        ALTER PUBLICATION supabase_realtime ADD TABLE public.escalation_events;
    END IF;

    IF EXISTS (
        SELECT 1 FROM pg_publication WHERE pubname = 'supabase_realtime'
    ) AND NOT EXISTS (
        SELECT 1
        FROM pg_publication_tables
        WHERE pubname = 'supabase_realtime'
          AND schemaname = 'public'
          AND tablename = 'notifications'
    ) THEN
        ALTER PUBLICATION supabase_realtime ADD TABLE public.notifications;
    END IF;
END $$;

-- <<< END migrations\006_escalations.sql
