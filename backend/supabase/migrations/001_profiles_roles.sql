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
