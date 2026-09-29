from fastapi import Depends, HTTPException, status, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime, timezone

from ..core.config import settings
from ..core.security import decode_token
from ..core.security_settings import security_settings
from ..core.audit import log_audit_event
from ..db.database import get_db
from ..db.models import User, Participant

security_bearer = HTTPBearer(auto_error=False)

def get_current_user(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security_bearer),
    db: Session = Depends(get_db)
) -> User:
    """
    Extracts and authenticates user from JWT bearer token.
    Enforces token type, active status, and rejects intermediate OTP-stage tokens.
    """
    token = None
    if credentials:
        token = credentials.credentials
    else:
        # Check secure HttpOnly cookie fallback
        token = request.cookies.get("ayur_access_token")

    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required. Please provide a valid session token.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    payload = decode_token(token)
    
    # Reject intermediate OTP stage token from accessing protected APIs
    if payload.get("type") == "otp_stage":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Two-step authentication incomplete. Please verify your OTP to proceed.",
        )

    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token payload.")

    user = db.query(User).filter(User.id == int(user_id)).first()
    if not user or not user.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User account is inactive or revoked.")

    return user


def require_role(allowed_roles: List[str]):
    """
    Server-side Role-Based Access Control (RBAC).
    Never trusts frontend to hide actions.
    If unauthorized, logs security event to audit trail and raises 403:
    'Your role (X) cannot do this'
    """
    def role_checker(
        request: Request,
        current_user: User = Depends(get_current_user),
        db: Session = Depends(get_db)
    ) -> User:
        if current_user.role not in allowed_roles:
            client_ip = request.client.host if request.client else "127.0.0.1"
            # Log unauthorized privilege escalation attempt in tamper-proof audit log
            log_audit_event(
                db=db,
                user_id=current_user.id,
                user_email=current_user.email,
                role=current_user.role,
                ip_address=client_ip,
                action="UNAUTHORIZED_ACCESS_ATTEMPT",
                entity_type="API_ROUTE",
                entity_id=request.url.path,
                details=f"Role '{current_user.role}' attempted action requiring: {allowed_roles}",
                site_id=current_user.site_id
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Your role ({current_user.role}) cannot do this."
            )
        return current_user

    return role_checker


def verify_site_access(
    participant_id: int,
    current_user: User,
    db: Session,
    request: Request
) -> Participant:
    """
    Row-Level Security & Tenancy Verification.
    Ensures research coordinators and site staff can ONLY access records belonging to their assigned site.
    Prevents ID-enumeration (BOLA/IDOR) attacks across hospital sites.
    """
    participant = db.query(Participant).filter(Participant.id == participant_id).first()
    if not participant:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Participant record not found.")

    # Research Coordinator site tenancy check
    if current_user.role == "Research Coordinator" and participant.site_id != current_user.site_id:
        client_ip = request.client.host if request.client else "127.0.0.1"
        log_audit_event(
            db=db,
            user_id=current_user.id,
            user_email=current_user.email,
            role=current_user.role,
            ip_address=client_ip,
            action="CROSS_SITE_ACCESS_BLOCKED",
            entity_type="Participant",
            entity_id=str(participant.id),
            details=f"User at {current_user.site_id} attempted access to participant at {participant.site_id}",
            site_id=current_user.site_id
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Cross-site access denied. You are only authorized for {current_user.site_id}."
        )

    return participant
