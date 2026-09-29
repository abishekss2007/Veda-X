-- ==============================================================================
-- 006_escalations.sql
-- "Report to Superior" Escalation System, Realtime Events & RLS Policies
-- ==============================================================================

-- 1. Create Escalations Table
CREATE TABLE IF NOT EXISTS public.escalations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    from_user UUID REFERENCES public.profiles(id),
    from_name TEXT NOT NULL,
    from_role user_role NOT NULL,
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
CREATE POLICY "Users can view own escalations"
    ON public.escalations FOR SELECT
    USING (auth.uid() = from_user);

-- Approved users can create escalations
CREATE POLICY "Approved users can create escalations"
    ON public.escalations FOR INSERT
    WITH CHECK (public.is_current_user_approved());

-- Admin and PI can view all escalations in their studies
CREATE POLICY "Admin and PI can view all escalations"
    ON public.escalations FOR SELECT
    USING (public.get_current_user_role() IN ('Admin', 'Principal Investigator'));

-- Admin and PI can update escalations (acknowledge, assign, resolve)
CREATE POLICY "Admin and PI can update escalations"
    ON public.escalations FOR UPDATE
    USING (public.get_current_user_role() IN ('Admin', 'Principal Investigator'))
    WITH CHECK (public.get_current_user_role() IN ('Admin', 'Principal Investigator'));

-- PV Officer can view Safety and AE/SAE escalations
CREATE POLICY "PV Officer can view safety escalations"
    ON public.escalations FOR SELECT
    USING (
        public.get_current_user_role() = 'PV Officer' 
        AND (category = 'Safety' OR summary ILIKE '%AE%' OR summary ILIKE '%SAE%')
    );

-- EC Member can view Ethics and SAE escalations
CREATE POLICY "EC Member can view ethics and sae escalations"
    ON public.escalations FOR SELECT
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
CREATE POLICY "Users can view events for accessible escalations"
    ON public.escalation_events FOR SELECT
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

CREATE POLICY "Authorized users can post replies and events"
    ON public.escalation_events FOR INSERT
    WITH CHECK (public.is_current_user_approved());

-- 7. Add to Supabase Realtime publication
DO $$
BEGIN
    IF EXISTS (
        SELECT 1 FROM pg_publication WHERE pubname = 'supabase_realtime'
    ) THEN
        ALTER PUBLICATION supabase_realtime ADD TABLE public.escalations;
        ALTER PUBLICATION supabase_realtime ADD TABLE public.escalation_events;
        ALTER PUBLICATION supabase_realtime ADD TABLE public.notifications;
    END IF;
END $$;
