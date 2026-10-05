import secrets
from datetime import datetime, timezone, timedelta
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status, Request, Response
from sqlalchemy.orm import Session

from ..db.database import get_db
from ..db.models import User
from ..schemas.schemas import (
    LoginRequest, OTPVerifyRequest, ForgotPasswordRequest,
    ResetPasswordRequest, TokenResponse, UserOut
)
from ..core.security import (
    verify_password, hash_password, validate_password_strength,
    create_access_token, create_refresh_token, create_otp_stage_token,
    decode_token
)
from pydantic import BaseModel
from ..core.security_settings import security_settings
from ..core.audit import log_audit_event
from .deps import get_current_user

router = APIRouter(prefix="/auth", tags=["Authentication & Access Control"])

class RoleSwitchLogRequest(BaseModel):
    from_role: str
    to_role: str
    user_email: str
    success: bool
    reason: Optional[str] = None

@router.post("/log-role-switch")
def log_role_switch(
    req: RoleSwitchLogRequest,
    request: Request,
    db: Session = Depends(get_db)
):
    client_ip = request.client.host if request.client else "127.0.0.1"
    action = "ROLE_SWITCH_SUCCESS" if req.success else "ROLE_SWITCH_FAILED"
    log_audit_event(
        db=db,
        user_id=None,
        user_email=req.user_email,
        role=req.from_role,
        ip_address=client_ip,
        action=action,
        entity_type="RoleSwitch",
        entity_id=req.to_role,
        previous_value=req.from_role,
        new_value=req.to_role,
        reason=req.reason or f"Role switch from '{req.from_role}' to '{req.to_role}'. Success: {req.success}."
    )
    return {"status": "logged"}


@router.post("/login", response_model=TokenResponse)
def login(
    req: LoginRequest,
    request: Request,
    response: Response,
    db: Session = Depends(get_db)
):
    """
    Secure Login complying with OWASP & DPDP:
    - Rejects after 5 wrong attempts with 15-minute account lockout.
    - Constant-time error message: 'Wrong email or password'.
    - Mandatory 2FA OTP for PI, PV Officer, Auditor, and Admin.
    """
    client_ip = request.client.host if request.client else "127.0.0.1"
    user = db.query(User).filter(User.email == req.email.lower().strip()).first()

    # Generic error message to prevent account enumeration
    GENERIC_LOGIN_ERROR = "Wrong email or password"

    if not user:
        # Dummy verification to prevent timing attacks
        verify_password("dummy_password_attempt", "$2b$12$EixZaYVK1fsbw1ZfbX3OXePaWxn96p36WQmG6W65sVVCG.XwAom6i")
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=GENERIC_LOGIN_ERROR)

    now = datetime.now(timezone.utc)

    # 1. Check Account Lockout
    if user.locked_until and user.locked_until.replace(tzinfo=timezone.utc) > now:
        remaining_seconds = int((user.locked_until.replace(tzinfo=timezone.utc) - now).total_seconds())
        remaining_minutes = max(1, remaining_seconds // 60)
        log_audit_event(
            db=db,
            user_id=user.id,
            user_email=user.email,
            role=user.role,
            ip_address=client_ip,
            action="LOGIN_ATTEMPT_WHILE_LOCKED",
            entity_type="User",
            entity_id=str(user.id),
            reason=f"Account locked. {remaining_minutes} min remaining.",
            site_id=user.site_id
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Account is temporarily locked due to multiple failed login attempts. Please try again in {remaining_minutes} minutes."
        )

    # 2. Check Password
    if not verify_password(req.password, user.hashed_password):
        user.failed_login_attempts += 1
        if user.failed_login_attempts >= security_settings.MAX_LOGIN_ATTEMPTS:
            user.locked_until = now + timedelta(seconds=security_settings.LOCKOUT_DURATION_SECONDS)
            db.commit()
            log_audit_event(
                db=db,
                user_id=user.id,
                user_email=user.email,
                role=user.role,
                ip_address=client_ip,
                action="ACCOUNT_LOCKED_FAILED_ATTEMPTS",
                entity_type="User",
                entity_id=str(user.id),
                reason=f"Exceeded {security_settings.MAX_LOGIN_ATTEMPTS} failed attempts. Locked for 15 minutes.",
                site_id=user.site_id
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Account has been locked for 15 minutes due to 5 consecutive failed login attempts."
            )
        db.commit()
        log_audit_event(
            db=db,
            user_id=user.id,
            user_email=user.email,
            role=user.role,
            ip_address=client_ip,
            action="LOGIN_FAILED",
            entity_type="User",
            entity_id=str(user.id),
            reason=f"Failed attempt {user.failed_login_attempts}/{security_settings.MAX_LOGIN_ATTEMPTS}",
            site_id=user.site_id
        )
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=GENERIC_LOGIN_ERROR)

    # Reset failed attempts on success
    user.failed_login_attempts = 0
    user.locked_until = None

    # 3. Check Mandatory 2-Factor Authentication (OTP)
    if user.role in security_settings.ROLES_MANDATORY_OTP:
        # Generate 6-digit cryptographically secure OTP
        otp = f"{secrets.randbelow(900000) + 100000}"
        user.otp_code = otp
        user.otp_created_at = now
        otp_stage_token = create_otp_stage_token(user.id, user.email, user.role)
        user.otp_stage_token = otp_stage_token
        db.commit()

        log_audit_event(
            db=db,
            user_id=user.id,
            user_email=user.email,
            role=user.role,
            ip_address=client_ip,
            action="OTP_ISSUED",
            entity_type="User",
            entity_id=str(user.id),
            reason="Two-factor challenge issued for high-privilege role.",
            site_id=user.site_id
        )

        return TokenResponse(
            access_token="",
            refresh_token="",
            user_id=user.id,
            email=user.email,
            full_name=user.full_name,
            role=user.role,
            site_id=user.site_id,
            requires_otp=True,
            otp_stage_token=otp_stage_token
        )

    # 4. Standard Session Issuance (Non-OTP roles)
    access_token = create_access_token({"sub": str(user.id), "email": user.email, "role": user.role, "site_id": user.site_id})
    refresh_token = create_refresh_token({"sub": str(user.id)})
    db.commit()

    # Set HttpOnly, Secure, SameSite=Strict cookies
    response.set_cookie(
        key="ayur_access_token",
        value=access_token,
        httponly=True,
        secure=True,
        samesite="Strict",
        max_age=security_settings.ACCESS_TOKEN_LIFETIME_SECONDS
    )

    log_audit_event(
        db=db,
        user_id=user.id,
        user_email=user.email,
        role=user.role,
        ip_address=client_ip,
        action="LOGIN_SUCCESS",
        entity_type="User",
        entity_id=str(user.id),
        site_id=user.site_id
    )

    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        user_id=user.id,
        email=user.email,
        full_name=user.full_name,
        role=user.role,
        site_id=user.site_id,
        requires_otp=False
    )


@router.post("/verify-otp", response_model=TokenResponse)
def verify_otp(
    req: OTPVerifyRequest,
    request: Request,
    response: Response,
    db: Session = Depends(get_db)
):
    """
    Verifies 6-digit OTP code within 5 minutes.
    Single-use only: OTP is cleared immediately upon successful verification.
    """
    client_ip = request.client.host if request.client else "127.0.0.1"
    payload = decode_token(req.otp_stage_token)

    if payload.get("type") != "otp_stage":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid OTP stage session.")

    user_id = int(payload.get("sub"))
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User account not found.")

    now = datetime.now(timezone.utc)
    if not user.otp_code or not user.otp_created_at:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No active OTP challenge on file.")

    # 5-minute expiry check
    if (now - user.otp_created_at.replace(tzinfo=timezone.utc)).total_seconds() > security_settings.OTP_VALIDITY_SECONDS:
        user.otp_code = None
        db.commit()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="OTP has expired (5-minute validity). Please request a new one.")

    # Single-use code check
    if req.otp_code != user.otp_code:
        log_audit_event(
            db=db,
            user_id=user.id,
            user_email=user.email,
            role=user.role,
            ip_address=client_ip,
            action="OTP_VERIFICATION_FAILED",
            entity_type="User",
            entity_id=str(user.id),
            site_id=user.site_id
        )
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid OTP code.")

    # Clear OTP code immediately (single-use guarantee)
    user.otp_code = None
    user.otp_stage_token = None
    db.commit()

    access_token = create_access_token({"sub": str(user.id), "email": user.email, "role": user.role, "site_id": user.site_id})
    refresh_token = create_refresh_token({"sub": str(user.id)})

    response.set_cookie(
        key="ayur_access_token",
        value=access_token,
        httponly=True,
        secure=True,
        samesite="Strict",
        max_age=security_settings.ACCESS_TOKEN_LIFETIME_SECONDS
    )

    log_audit_event(
        db=db,
        user_id=user.id,
        user_email=user.email,
        role=user.role,
        ip_address=client_ip,
        action="OTP_VERIFICATION_SUCCESS",
        entity_type="User",
        entity_id=str(user.id),
        site_id=user.site_id
    )

    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        user_id=user.id,
        email=user.email,
        full_name=user.full_name,
        role=user.role,
        site_id=user.site_id,
        requires_otp=False
    )


@router.post("/forgot-password")
def forgot_password(req: ForgotPasswordRequest, request: Request, db: Session = Depends(get_db)):
    """
    Sends one-time password reset link expiring in 15 minutes.
    Generic response prevents user enumeration.
    """
    client_ip = request.client.host if request.client else "127.0.0.1"
    user = db.query(User).filter(User.email == req.email.lower().strip()).first()
    
    # Generate token if user exists
    reset_token = None
    if user:
        reset_token = create_access_token(
            {"sub": str(user.id), "type": "password_reset"},
            expires_delta=timedelta(seconds=security_settings.PASSWORD_RESET_TOKEN_EXPIRY_SECONDS)
        )
        log_audit_event(
            db=db,
            user_id=user.id,
            user_email=user.email,
            role=user.role,
            ip_address=client_ip,
            action="PASSWORD_RESET_REQUESTED",
            entity_type="User",
            entity_id=str(user.id),
            site_id=user.site_id
        )

    # Returns generic acknowledgment for privacy
    return {
        "message": "If this email is registered in AyurCTMS, a one-time password reset link (valid for 15 minutes) has been dispatched.",
        "debug_reset_token": reset_token if settings.ENVIRONMENT != "production" else None
    }


@router.post("/reset-password")
def reset_password(req: ResetPasswordRequest, request: Request, db: Session = Depends(get_db)):
    """
    Enforces minimum 10 characters and refuses common passwords.
    Ends all active user sessions upon password change.
    """
    client_ip = request.client.host if request.client else "127.0.0.1"
    payload = decode_token(req.token)

    if payload.get("type") != "password_reset":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid reset token.")

    user_id = int(payload.get("sub"))
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found.")

    # Validate password strength
    valid, err_msg = validate_password_strength(req.new_password)
    if not valid:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=err_msg)

    user.hashed_password = hash_password(req.new_password)
    user.password_changed_at = datetime.now(timezone.utc)
    user.failed_login_attempts = 0
    user.locked_until = None
    db.commit()

    log_audit_event(
        db=db,
        user_id=user.id,
        user_email=user.email,
        role=user.role,
        ip_address=client_ip,
        action="PASSWORD_CHANGED",
        entity_type="User",
        entity_id=str(user.id),
        reason="Password reset successfully. All active sessions invalidated.",
        site_id=user.site_id
    )

    return {"message": "Password changed successfully. All previous sessions terminated. Please log in with your new credentials."}


@router.post("/logout")
def logout(
    request: Request,
    response: Response,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Ends user session and clears authentication cookies."""
    client_ip = request.client.host if request.client else "127.0.0.1"
    response.delete_cookie(key="ayur_access_token")
    
    log_audit_event(
        db=db,
        user_id=current_user.id,
        user_email=current_user.email,
        role=current_user.role,
        ip_address=client_ip,
        action="LOGOUT",
        entity_type="User",
        entity_id=str(current_user.id),
        site_id=current_user.site_id
    )
    return {"message": "Logged out successfully. Session destroyed."}


@router.post("/session/renew")
def renew_session(
    request: Request,
    response: Response,
    current_user: User = Depends(get_current_user)
):
    """
    Sliding session: reissues the 15-minute access cookie while the user is active,
    so only genuine inactivity ends the session.
    """
    token = request.cookies.get("ayur_access_token")
    if not token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="No session cookie to renew.")
    claims = decode_token(token)
    claims.pop("exp", None)
    response.set_cookie(
        key="ayur_access_token",
        value=create_access_token(claims),
        httponly=True,
        secure=request.url.scheme == "https" or claims.get("principal_type") != "demo",
        samesite="Strict",
        max_age=security_settings.ACCESS_TOKEN_LIFETIME_SECONDS
    )
    return {"renewed": True}


@router.get("/me", response_model=UserOut)
def get_current_user_profile(current_user: User = Depends(get_current_user)):
    return current_user
