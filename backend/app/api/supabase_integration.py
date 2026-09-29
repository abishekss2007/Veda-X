from typing import Optional, List, Dict, Any
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, status, Request
from pydantic import BaseModel, EmailStr, Field

from ..core.supabase_client import get_supabase_admin_client, is_supabase_enabled, get_supabase_url
from ..core.audit import log_audit_event
from ..db.database import get_db
from sqlalchemy.orm import Session

router = APIRouter(prefix="/supabase", tags=["Supabase Integration & Submissions"])

# In-Memory Fallback Submissions Store for Mock Mode
_mock_submissions = [
    {
        "id": "sub-101",
        "owner_id": "usr-coord-01",
        "owner_name": "Dr. Sunita Patel",
        "role": "Research Coordinator",
        "study_id": "AYUR-CT-2026-001",
        "type": "consent",
        "title": "Informed Consent Form — Subject SUB-AIIA-001-042 (Hindi Oral)",
        "payload": {"subject_code": "SUB-AIIA-001-042", "language": "Hindi", "oral_explanation": True},
        "status": "Verified",
        "created_at": "2026-09-28T10:00:00Z",
        "updated_at": "2026-09-28T14:30:00Z",
        "versions": [{"changed_at": "2026-09-28T10:00:00Z", "reason": "Initial submission"}],
        "verifications": [{"verified_by": "Prof. Sharma (PI)", "verified_at": "2026-09-28T14:30:00Z", "note": "Verified oral explanation on file."}]
    },
    {
        "id": "sub-102",
        "owner_id": "usr-coord-01",
        "owner_name": "Dr. Sunita Patel",
        "role": "Research Coordinator",
        "study_id": "AYUR-CT-2026-001",
        "type": "prakriti_assessment",
        "title": "Deha Prakriti Assessment — Subject SUB-AIIA-001-042",
        "payload": {"subject_code": "SUB-AIIA-001-042", "vata": 55, "pitta": 30, "kapha": 15, "dominant": "Vata-Pitta"},
        "status": "Submitted",
        "created_at": "2026-09-28T11:00:00Z",
        "updated_at": "2026-09-28T11:00:00Z",
        "versions": [],
        "verifications": []
    },
    {
        "id": "sub-103",
        "owner_id": "usr-doc-01",
        "owner_name": "Dr. Arvind Joshi",
        "role": "Doctor / Investigator",
        "study_id": "AYUR-CT-2026-001",
        "type": "ae_report",
        "title": "Adverse Drug Reaction Log — Pitta-Kopa / Ushnata",
        "payload": {"subject_code": "SUB-AIIA-001-042", "severity": "Mild", "asu_term": "Pitta-Kopa"},
        "status": "Draft",
        "created_at": "2026-09-29T09:00:00Z",
        "updated_at": "2026-09-29T09:00:00Z",
        "versions": [],
        "verifications": []
    }
]

class RegisterIn(BaseModel):
    full_name: str = Field(..., min_length=2)
    email: EmailStr
    phone: str = Field(..., min_length=10)
    role: str
    site: str = "SITE-01"
    password: str = Field(..., min_length=12)
    confirm_password: str
    privacy_consent_ticked: bool

class LoginIn(BaseModel):
    role: str
    email: EmailStr
    password: str

class VerifyOTPIn(BaseModel):
    email: EmailStr
    role: str
    otp_code: str = Field(..., min_length=6, max_length=6)

class SubmissionCreateIn(BaseModel):
    owner_id: str
    role: str
    study_id: str = "AYUR-CT-2026-001"
    type: str # form, document, consent, ae_report, visit_note, prakriti_assessment
    title: str
    payload: Dict[str, Any]
    status: str = "Draft"

class SubmissionUpdateIn(BaseModel):
    title: Optional[str] = None
    payload: Dict[str, Any]
    status: Optional[str] = None
    reason: str = Field(..., min_length=3)
    changed_by: str

class SubmissionVerifyIn(BaseModel):
    verified_by: str
    verifier_role: str
    verifier_email: str
    note: str = Field(..., min_length=3)

@router.get("/status")
def get_supabase_status():
    """Returns whether Supabase connection is active or in Mock mode."""
    client = get_supabase_admin_client()
    return {
        "is_configured": is_supabase_enabled(),
        "is_connected": client is not None,
        "supabase_url": get_supabase_url() if get_supabase_url() else "Not configured",
        "mode": "Supabase Production/Staging" if is_supabase_enabled() else "Mock / Offline Simulation Mode",
        "notice": "All data persistent in Supabase" if is_supabase_enabled() else "Not connected to database. Running in local mock mode."
    }

@router.post("/auth/register")
def register_user(req: RegisterIn, request: Request, db: Session = Depends(get_db)):
    if not req.privacy_consent_ticked:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="DPDP Act Compliance: You must read and tick the privacy consent notice before registering."
        )
    if req.password != req.confirm_password:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Passwords do not match.")

    # Prohibit self-assignment of Admin or PI
    safe_role = req.role
    if req.role in ["Admin", "Principal Investigator"]:
        safe_role = "Research Coordinator"

    client = get_supabase_admin_client()
    if client:
        try:
            res = client.auth.admin.create_user({
                "email": req.email,
                "password": req.password,
                "email_confirm": False, # Requires admin approval
                "user_metadata": {
                    "full_name": req.full_name,
                    "phone": req.phone,
                    "role": safe_role,
                    "site": req.site,
                    "status": "pending",
                    "notice_version": "DPDP-V1.0"
                }
            })
        except Exception as exc:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))

    log_audit_event(
        db=db,
        user_id=None,
        user_email=req.email,
        role=safe_role,
        ip_address=request.client.host if request.client else "127.0.0.1",
        action="REGISTRATION_SUBMITTED",
        entity_type="Profile",
        entity_id=req.email,
        details=f"Registration submitted for role '{safe_role}'. Status: pending approval."
    )

    return {"message": "Registration received. An admin will approve your account."}

_login_failures: Dict[str, Dict[str, Any]] = {}

@router.post("/auth/login")
def login_user(req: LoginIn, request: Request, db: Session = Depends(get_db)):
    email_lower = req.email.lower().strip()
    now = datetime.now(timezone.utc)
    client_ip = request.client.host if request.client else "127.0.0.1"

    # 1. Check Account Lockout (OWASP & Regulatory requirement)
    fail_data = _login_failures.get(email_lower)
    if fail_data and fail_data.get("locked_until"):
        if fail_data["locked_until"] > now:
            remaining_seconds = int((fail_data["locked_until"] - now).total_seconds())
            remaining_minutes = max(1, remaining_seconds // 60)
            log_audit_event(
                db=db,
                user_id=None,
                user_email=email_lower,
                role=req.role,
                ip_address=client_ip,
                action="LOGIN_ATTEMPT_WHILE_LOCKED",
                entity_type="Account",
                entity_id=email_lower,
                details=f"Account locked. {remaining_minutes} min remaining."
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Account is temporarily locked due to multiple failed login attempts. Please try again in {remaining_minutes} minutes."
            )
        else:
            # Lockout expired
            _login_failures.pop(email_lower, None)

    # Demo accounts pre-configured
    demo_passwords = {
        "admin@ayurctms.demo": ("Admin@Demo#2026", "Admin"),
        "pi@ayurctms.demo": ("Pi@Demo#2026", "Principal Investigator"),
        "coordinator@ayurctms.demo": ("Coord@Demo#2026", "Research Coordinator"),
        "doctor@ayurctms.demo": ("Doctor@Demo#2026", "Doctor / Investigator"),
        "monitor@ayurctms.demo": ("Monitor@Demo#2026", "Monitor"),
        "ec@ayurctms.demo": ("Ethics@Demo#2026", "EC Member"),
        "pv@ayurctms.demo": ("Pharma@Demo#2026", "PV Officer"),
        "auditor@ayurctms.demo": ("Audit@Demo#2026", "Auditor / Regulator"),
        "leader@ayurctms.demo": ("Leader@Demo#2026", "Institution Leadership")
    }

    authenticated = False
    if email_lower in demo_passwords:
        expected_pwd, expected_role = demo_passwords[email_lower]
        if req.password != expected_pwd:
            # Record failure
            f = _login_failures.setdefault(email_lower, {"attempts": 0, "locked_until": None})
            f["attempts"] += 1
            if f["attempts"] >= 5:
                from datetime import timedelta
                f["locked_until"] = now + timedelta(minutes=15)
            log_audit_event(
                db=db,
                user_id=None,
                user_email=email_lower,
                role=req.role,
                ip_address=client_ip,
                action="LOGIN_FAILED_CREDENTIALS",
                entity_type="Account",
                entity_id=email_lower,
                details=f"Wrong password. Attempt {f['attempts']} of 5."
            )
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Wrong email or password")
        
        if req.role != expected_role:
            log_audit_event(
                db=db,
                user_id=None,
                user_email=email_lower,
                role=req.role,
                ip_address=client_ip,
                action="LOGIN_ROLE_MISMATCH",
                entity_type="Account",
                entity_id=email_lower,
                details=f"Selected role '{req.role}' does not match assigned role '{expected_role}'."
            )
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="This account is not approved for that role.")
        authenticated = True
    else:
        # Check standard Supabase Auth
        client = get_supabase_admin_client()
        if client:
            try:
                auth_res = client.auth.sign_in_with_password({"email": req.email, "password": req.password})
                authenticated = True
            except Exception:
                f = _login_failures.setdefault(email_lower, {"attempts": 0, "locked_until": None})
                f["attempts"] += 1
                if f["attempts"] >= 5:
                    from datetime import timedelta
                    f["locked_until"] = now + timedelta(minutes=15)
                raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Wrong email or password")
        else:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Wrong email or password")

    # Reset failure counter on valid password & role
    _login_failures.pop(email_lower, None)

    return {
        "step": "VERIFICATION_REQUIRED",
        "email": req.email,
        "role": req.role,
        "demo_mode": True,
        "demo_code": "123456",
        "expires_in_minutes": 5
    }

@router.post("/auth/verify-otp")
def verify_otp_endpoint(req: VerifyOTPIn, request: Request, db: Session = Depends(get_db)):
    if req.otp_code != "123456":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid verification code.")

    role_slug_map = {
        "Principal Investigator": "/dashboard/pi",
        "Research Coordinator": "/dashboard/coordinator",
        "Doctor / Investigator": "/dashboard/doctor",
        "Monitor": "/dashboard/monitor",
        "EC Member": "/dashboard/ec",
        "PV Officer": "/dashboard/pv",
        "Admin": "/dashboard/admin",
        "Auditor / Regulator": "/dashboard/auditor",
        "Institution Leadership": "/dashboard/leadership"
    }

    log_audit_event(
        db=db,
        user_id=None,
        user_email=req.email,
        role=req.role,
        ip_address=request.client.host if request.client else "127.0.0.1",
        action="LOGIN_SUCCESS",
        entity_type="Session",
        entity_id=req.email,
        details="2FA OTP verified. Session created."
    )

    return {
        "success": True,
        "email": req.email,
        "role": req.role,
        "dashboard_route": role_slug_map.get(req.role, "/dashboard/coordinator")
    }

@router.get("/submissions")
def get_submissions(owner_id: Optional[str] = None, role: Optional[str] = None):
    client = get_supabase_admin_client()
    if client:
        try:
            q = client.from_("submissions").select("*, submission_versions(*), verifications(*)")
            if owner_id and role not in ["Admin", "Principal Investigator"]:
                q = q.eq("owner_id", owner_id)
            res = q.order("created_at", desc=True).execute()
            if res.data:
                return res.data
        except Exception:
            pass
    
    # Respect Row Level Security in fallback mock mode
    if owner_id and role not in ["Admin", "Principal Investigator"]:
        return [s for s in _mock_submissions if s.get("owner_id") == owner_id]
    return _mock_submissions

@router.post("/submissions", status_code=status.HTTP_201_CREATED)
def create_submission(req: SubmissionCreateIn):
    client = get_supabase_admin_client()
    if client:
        try:
            res = client.from_("submissions").insert({
                "owner_id": req.owner_id,
                "role": req.role,
                "study_id": req.study_id,
                "type": req.type,
                "title": req.title,
                "payload": req.payload,
                "status": req.status
            }).execute()
            if res.data:
                return res.data[0]
        except Exception as exc:
            print(f"[Supabase Notice] Remote insert fell back to local store: {exc}")

    new_entry = {
        "id": f"sub-{len(_mock_submissions) + 101}",
        "owner_id": req.owner_id,
        "owner_name": "Current User",
        "role": req.role,
        "study_id": req.study_id,
        "type": req.type,
        "title": req.title,
        "payload": req.payload,
        "status": req.status,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "versions": [],
        "verifications": []
    }
    _mock_submissions.insert(0, new_entry)
    return new_entry

@router.put("/submissions/{sub_id}")
def update_submission(sub_id: str, req: SubmissionUpdateIn):
    for s in _mock_submissions:
        if s["id"] == sub_id:
            if s["status"] not in ["Draft", "Needs correction"]:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Cannot edit submission in '{s['status']}' status.")
            s["versions"].append({
                "old_value": s["payload"],
                "new_value": req.payload,
                "reason": req.reason,
                "changed_at": datetime.now(timezone.utc).isoformat()
            })
            if req.title:
                s["title"] = req.title
            s["payload"] = req.payload
            if req.status:
                s["status"] = req.status
            s["updated_at"] = datetime.now(timezone.utc).isoformat()
            return s
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Submission not found.")

@router.post("/submissions/{sub_id}/verify")
def verify_submission(sub_id: str, req: SubmissionVerifyIn):
    for s in _mock_submissions:
        if s["id"] == sub_id:
            s["status"] = "Verified"
            s["verifications"].append({
                "verified_by": f"{req.verified_by} ({req.verifier_role})",
                "verified_at": datetime.now(timezone.utc).isoformat(),
                "note": req.note
            })
            return s
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Submission not found.")
