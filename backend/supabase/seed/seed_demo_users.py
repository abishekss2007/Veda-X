"""
AyurCTMS Demo User Seeder (Python)
Creates the 9 demo accounts in Supabase Auth and approves their profiles, so
records saved from a demo session have a real profiles.id to be owned by.
STRICTLY FOR DEMONSTRATION & LOCAL DEVELOPMENT ONLY.

Run from the repository root:  python backend/supabase/seed/seed_demo_users.py
"""
import secrets
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from app.core.supabase_client import get_supabase_admin_client, get_supabase_secret_key

DEMO_USERS = [
    ("Admin", "admin@ayurctms.demo", "System Administrator", "SITE-HQ"),
    ("Principal Investigator", "pi@ayurctms.demo", "Prof. (Dr.) Rajeshwar Sharma", "SITE-01"),
    ("Research Coordinator", "coordinator@ayurctms.demo", "Dr. Sunita Patel, BAMS", "SITE-01"),
    ("Doctor / Investigator", "doctor@ayurctms.demo", "Dr. Arvind Joshi, MD (Ayu)", "SITE-01"),
    ("Monitor", "monitor@ayurctms.demo", "Vikram Verma, CRA", "SITE-01"),
    ("EC Member", "ec@ayurctms.demo", "Justice (Retd.) M. K. Narayanan", "EC-BOARD"),
    ("PV Officer", "pv@ayurctms.demo", "Dr. Gayatri Devi, MD (Ayu)", "SITE-01"),
    ("Auditor / Regulator", "auditor@ayurctms.demo", "K. R. Sengupta, ISO Lead Auditor", "SITE-HQ"),
    ("Institution Leadership", "leader@ayurctms.demo", "Prof. (Dr.) Tanuja Nesari, Director", "SITE-HQ"),
]


def seed_demo_users() -> int:
    client = get_supabase_admin_client()
    if client is None or not get_supabase_secret_key():
        print("[Seed Error] SUPABASE_URL and SUPABASE_SECRET_KEY must be set in backend/.env")
        return 1

    failures = 0
    for role, email, full_name, site in DEMO_USERS:
        profile = {"status": "approved", "role": role, "site": site, "full_name": full_name}
        try:
            existing = client.from_("profiles").select("id").eq("email", email).limit(1).execute()
            if existing.data:
                user_id = existing.data[0]["id"]
            else:
                # Demo sign-in is checked by the backend, not Supabase Auth, so the
                # Supabase password is random and never needs to be known.
                created = client.auth.admin.create_user({
                    "email": email,
                    "password": secrets.token_urlsafe(32),
                    "email_confirm": True,
                    "user_metadata": {
                        "full_name": full_name,
                        "role": role,
                        "site": site,
                        "notice_version": "DPDP-V1.0",
                    },
                })
                user_id = created.user.id
            client.from_("profiles").update(profile).eq("id", user_id).execute()
            print(f"[Seed Success] {role} ({email}) ready.")
        except Exception as exc:
            failures += 1
            print(f"[Seed Error] {email}: {exc}")

    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(seed_demo_users())
