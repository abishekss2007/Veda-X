-- ==============================================================================
-- 007_fix_handle_new_user.sql
-- Supabase Auth inserts into auth.users with a search_path that excludes
-- "public", so the unqualified user_role_type cast in handle_new_user() failed
-- and every signup returned "Database error creating new user".
-- ==============================================================================

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
        COALESCE((NEW.raw_user_meta_data->>'role')::public.user_role_type, 'Research Coordinator'),
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
$$ LANGUAGE plpgsql SECURITY DEFINER SET search_path = public;
