import os
from pathlib import Path
from typing import Optional
from dotenv import load_dotenv
from supabase import create_client, Client

_backend_dir = Path(__file__).resolve().parent.parent.parent
load_dotenv(_backend_dir / ".env")
load_dotenv(_backend_dir.parent / ".env")

def get_supabase_url() -> str:
    return os.getenv("SUPABASE_URL", "")

def get_supabase_secret_key() -> str:
    return os.getenv("SUPABASE_SECRET_KEY", "") or os.getenv("SUPABASE_SERVICE_ROLE_KEY", "")

def get_supabase_publishable_key() -> str:
    return os.getenv("SUPABASE_PUBLISHABLE_KEY", "") or os.getenv("SUPABASE_ANON_KEY", "")

_supabase_client: Optional[Client] = None

def get_supabase_admin_client() -> Optional[Client]:
    """
    Returns authenticated Supabase Client for backend tasks.
    Uses SUPABASE_SECRET_KEY to bypass RLS for administrative jobs.
    Returns None if keys are not configured (falls back to local/mock mode).
    """
    global _supabase_client
    if _supabase_client is not None:
        return _supabase_client

    url = get_supabase_url()
    if not url:
        return None

    # Use secret key on backend; fall back to publishable if secret key is not set
    auth_key = get_supabase_secret_key() or get_supabase_publishable_key()
    if not auth_key:
        return None

    try:
        _supabase_client = create_client(url, auth_key)
        return _supabase_client
    except Exception as exc:
        print(f"[Supabase Init Warning] Could not connect to Supabase: {exc}")
        return None

def new_supabase_auth_client() -> Optional[Client]:
    """
    Returns a throwaway client for user sign-in checks.
    Signing in on the shared admin client would swap its secret key for the
    user's session, making every later backend query subject to RLS.
    """
    url = get_supabase_url()
    auth_key = get_supabase_publishable_key() or get_supabase_secret_key()
    if not url or not auth_key:
        return None
    return create_client(url, auth_key)

def is_supabase_enabled() -> bool:
    url = get_supabase_url()
    auth_key = get_supabase_secret_key() or get_supabase_publishable_key()
    return bool(url and auth_key)

