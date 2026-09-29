-- ==============================================================================
-- seed_demo_data.sql
-- Synthetic Clinical Trial Submissions & Audit Entries for AyurCTMS Demo
-- ==============================================================================

-- Insert synthetic submissions if profiles exist
DO $$
DECLARE
    coord_id UUID;
    pi_id UUID;
    doc_id UUID;
    monitor_id UUID;
    sub1_id UUID := gen_random_uuid();
    sub2_id UUID := gen_random_uuid();
    sub3_id UUID := gen_random_uuid();
BEGIN
    SELECT id INTO coord_id FROM public.profiles WHERE email = 'coordinator@ayurctms.demo' LIMIT 1;
    SELECT id INTO pi_id FROM public.profiles WHERE email = 'pi@ayurctms.demo' LIMIT 1;
    SELECT id INTO doc_id FROM public.profiles WHERE email = 'doctor@ayurctms.demo' LIMIT 1;
    SELECT id INTO monitor_id FROM public.profiles WHERE email = 'monitor@ayurctms.demo' LIMIT 1;

    -- If seed users exist, attach demo records
    IF coord_id IS NOT NULL THEN
        -- 1. Informed Consent Submission
        INSERT INTO public.submissions (
            id, owner_id, role, study_id, type, title, payload, status, created_at, updated_at
        ) VALUES (
            sub1_id,
            coord_id,
            'Research Coordinator',
            'AYUR-CT-2026-001',
            'consent',
            'Subject Consent — SUB-AIIA-001-042 (Hindi Oral Explanation)',
            jsonb_build_object(
                'subject_code', 'SUB-AIIA-001-042',
                'language', 'Hindi',
                'explained_orally', true,
                'witness_required', false,
                'version', 'v1.0'
            ),
            'Verified',
            NOW() - INTERVAL '3 days',
            NOW() - INTERVAL '2 days'
        ) ON CONFLICT (id) DO NOTHING;

        -- 2. Prakriti Clinical Assessment
        INSERT INTO public.submissions (
            id, owner_id, role, study_id, type, title, payload, status, created_at, updated_at
        ) VALUES (
            sub2_id,
            COALESCE(doc_id, coord_id),
            'Doctor / Investigator',
            'AYUR-CT-2026-001',
            'prakriti_assessment',
            'Deha Prakriti Evaluation — SUB-AIIA-001-042 (Vata-Pitta)',
            jsonb_build_object(
                'subject_code', 'SUB-AIIA-001-042',
                'vata_pct', 55,
                'pitta_pct', 30,
                'kapha_pct', 15,
                'dominant', 'Vata-Pitta',
                'ayurvedic_diagnosis', 'Amavata (Madhyama Koshtha)'
            ),
            'Submitted',
            NOW() - INTERVAL '2 days',
            NOW() - INTERVAL '1 day'
        ) ON CONFLICT (id) DO NOTHING;

        -- 3. Monitoring Visit Note
        INSERT INTO public.submissions (
            id, owner_id, role, study_id, type, title, payload, status, created_at, updated_at
        ) VALUES (
            sub3_id,
            COALESCE(monitor_id, coord_id),
            'Monitor',
            'AYUR-CT-2026-001',
            'visit_note',
            'Site Monitoring Visit Report — SITE-01 Protocol Adherence',
            jsonb_build_object(
                'site_id', 'SITE-01',
                'source_data_verified', true,
                'deviations_count', 0,
                'findings', 'All CRF entries cross-verified with source hospital case sheets.'
            ),
            'Draft',
            NOW() - INTERVAL '1 day',
            NOW()
        ) ON CONFLICT (id) DO NOTHING;

        -- Add formal verification record
        IF pi_id IS NOT NULL THEN
            INSERT INTO public.verifications (
                submission_id, verified_by, verified_at, note
            ) VALUES (
                sub1_id,
                pi_id,
                NOW() - INTERVAL '2 days',
                'Informed consent signed in compliance with GCP-ASU Part A.1.'
            ) ON CONFLICT DO NOTHING;
        END IF;

    END IF;

    -- Add Genesis Audit Log
    INSERT INTO public.audit_log (
        user_email, role, action, entity, old_value, new_value, previous_hash, hash
    ) VALUES (
        'system@ayurctms.demo',
        'System Initialization',
        'GENESIS_AUDIT_LEDGER',
        'Ledger',
        '{}'::jsonb,
        jsonb_build_object('status', 'Initialized', 'rulebook', 'GCP-ASU • DPDP 2025 • CERT-In'),
        '0000000000000000000000000000000000000000000000000000000000000000',
        'e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855'
    ) ON CONFLICT DO NOTHING;

    -- Add Initial Security Log
    INSERT INTO public.security_log (
        user_email, event, ip_address, details
    ) VALUES (
        'system@ayurctms.demo',
        'system_start',
        '127.0.0.1',
        'AyurCTMS Supabase security audit subsystem initialized in compliance mode.'
    ) ON CONFLICT DO NOTHING;

END $$;
