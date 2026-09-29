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
