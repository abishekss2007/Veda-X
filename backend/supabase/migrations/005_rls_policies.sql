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
CREATE POLICY "Users can read own profile"
    ON public.profiles FOR SELECT
    USING (auth.uid() = id);

-- Admin and PI can view all profiles
CREATE POLICY "Admin and PI can view all profiles"
    ON public.profiles FOR SELECT
    USING (public.get_current_user_role() IN ('Admin', 'Principal Investigator'));

-- User can update non-privileged fields of own profile
CREATE POLICY "Users can update own profile"
    ON public.profiles FOR UPDATE
    USING (auth.uid() = id)
    WITH CHECK (auth.uid() = id);

-- ------------------------------------------------------------------------------
-- 2. SUBMISSIONS POLICIES
-- ------------------------------------------------------------------------------
-- Approved users can read their own submissions
CREATE POLICY "Users can read own submissions"
    ON public.submissions FOR SELECT
    USING (
        public.is_current_user_approved() AND 
        (owner_id = auth.uid())
    );

-- Admin and PI can read all submissions across studies
CREATE POLICY "Admin and PI can read all submissions"
    ON public.submissions FOR SELECT
    USING (
        public.is_current_user_approved() AND 
        public.get_current_user_role() IN ('Admin', 'Principal Investigator')
    );

-- Monitor and Auditor: Read-only access across all submissions
CREATE POLICY "Monitor and Auditor can read all submissions"
    ON public.submissions FOR SELECT
    USING (
        public.is_current_user_approved() AND 
        public.get_current_user_role() IN ('Monitor', 'Auditor / Regulator')
    );

-- Institution Leadership: Can view submissions for portfolio KPI analysis
CREATE POLICY "Leadership can view submissions"
    ON public.submissions FOR SELECT
    USING (
        public.is_current_user_approved() AND 
        public.get_current_user_role() = 'Institution Leadership'
    );

-- Approved users can create submissions where owner_id = auth.uid()
CREATE POLICY "Approved users can insert submissions"
    ON public.submissions FOR INSERT
    WITH CHECK (
        public.is_current_user_approved() AND 
        owner_id = auth.uid()
    );

-- Users can update only their own submissions while in 'Draft' or 'Needs correction' status
CREATE POLICY "Users can update own draft submissions"
    ON public.submissions FOR UPDATE
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
CREATE POLICY "Admin and PI can update submission status"
    ON public.submissions FOR UPDATE
    USING (
        public.is_current_user_approved() AND 
        public.get_current_user_role() IN ('Admin', 'Principal Investigator')
    );

-- ------------------------------------------------------------------------------
-- 3. SUBMISSION VERSIONS & VERIFICATIONS POLICIES
-- ------------------------------------------------------------------------------
CREATE POLICY "Approved users can view submission versions"
    ON public.submission_versions FOR SELECT
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

CREATE POLICY "Approved users can insert submission versions"
    ON public.submission_versions FOR INSERT
    WITH CHECK (public.is_current_user_approved());

CREATE POLICY "Approved users can view verifications"
    ON public.verifications FOR SELECT
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

CREATE POLICY "Reviewers can insert verifications"
    ON public.verifications FOR INSERT
    WITH CHECK (
        public.is_current_user_approved() AND 
        public.get_current_user_role() IN ('Admin', 'Principal Investigator', 'Monitor', 'Doctor / Investigator')
    );

-- ------------------------------------------------------------------------------
-- 4. DOCUMENTS & STORAGE POLICIES
-- ------------------------------------------------------------------------------
CREATE POLICY "Users can read own documents"
    ON public.documents FOR SELECT
    USING (
        public.is_current_user_approved() AND 
        (owner_id = auth.uid() OR public.get_current_user_role() IN ('Admin', 'Principal Investigator', 'Monitor', 'Auditor / Regulator'))
    );

CREATE POLICY "Approved users can insert documents"
    ON public.documents FOR INSERT
    WITH CHECK (
        public.is_current_user_approved() AND 
        owner_id = auth.uid()
    );

-- Storage bucket RLS policies for 'trial-documents'
CREATE POLICY "Users can upload trial documents"
    ON storage.objects FOR INSERT
    TO authenticated
    WITH CHECK (
        bucket_id = 'trial-documents' AND 
        public.is_current_user_approved()
    );

CREATE POLICY "Users can read trial documents"
    ON storage.objects FOR SELECT
    TO authenticated
    USING (
        bucket_id = 'trial-documents' AND 
        public.is_current_user_approved()
    );

-- ------------------------------------------------------------------------------
-- 5. AUDIT AND SECURITY LOGS (INSERT-ONLY FOR APPS, NO UPDATE/DELETE)
-- ------------------------------------------------------------------------------
CREATE POLICY "Anyone authenticated can insert audit logs"
    ON public.audit_log FOR INSERT
    TO authenticated
    WITH CHECK (true);

CREATE POLICY "Auditors, Admin, PI can read audit logs"
    ON public.audit_log FOR SELECT
    TO authenticated
    USING (public.get_current_user_role() IN ('Auditor / Regulator', 'Admin', 'Principal Investigator'));

CREATE POLICY "System can insert security logs"
    ON public.security_log FOR INSERT
    TO authenticated, anon
    WITH CHECK (true);

CREATE POLICY "Admin and Auditor can read security logs"
    ON public.security_log FOR SELECT
    TO authenticated
    USING (public.get_current_user_role() IN ('Admin', 'Auditor / Regulator'));
