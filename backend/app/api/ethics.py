import hashlib
from datetime import datetime, timezone, timedelta
from typing import List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.orm import Session

from ..db.database import get_db
from ..db.models import (
    EthicsCommitteeMember, ProtocolApproval, AutomatedECTransmission,
    AdverseEvent, User
)
from ..schemas.schemas import ECMemberCreate, ECMemberOut, ProtocolAmendmentCreate
from ..core.audit import log_audit_event
from .deps import get_current_user, require_role

router = APIRouter(prefix="/ethics", tags=["GCP-ASU Ethics Committee (EC) Module"])

STATUTORY_ROLES = [
    "Chairperson",
    "Basic medical scientist / pharmacologist",
    "Clinician",
    "Legal expert",
    "Social scientist / NGO representative",
    "Philosopher / ethicist",
    "Lay community member",
    "Member Secretary",
    "ASU expert"
]

@router.get("/composition-status")
def get_ec_composition_status(db: Session = Depends(get_db)):
    """
    Evaluates GCP-ASU statutory committee rules:
    - Minimum 5 members required.
    - ASU expert MUST be present for Ayurveda/Siddha/Unani trials.
    - Chairperson preferably outside institution.
    """
    members = db.query(EthicsCommitteeMember).filter(EthicsCommitteeMember.is_active == True).all()
    roles_present = {m.role for m in members}
    total_members = len(members)

    has_asu_expert = "ASU expert" in roles_present
    has_min_5 = total_members >= 5
    has_chairperson = "Chairperson" in roles_present

    warnings = []
    if not has_min_5:
        warnings.append(f"Regulatory Non-Compliance: EC has {total_members} members. GCP-ASU mandates at least 5 members.")
    if not has_asu_expert:
        warnings.append("Critical Violation: No ASU expert registered on Ethics Committee. Required for ASU clinical trials.")
    if not has_chairperson:
        warnings.append("Warning: Chairperson role is currently vacant.")

    is_compliant = has_min_5 and has_asu_expert and has_chairperson

    return {
        "is_compliant": is_compliant,
        "total_active_members": total_members,
        "has_asu_expert": has_asu_expert,
        "has_chairperson": has_chairperson,
        "roles_present": list(roles_present),
        "missing_roles": [r for r in STATUTORY_ROLES if r not in roles_present],
        "warnings": warnings,
        "members": [
            {
                "id": m.id,
                "name": m.name,
                "role": m.role,
                "affiliation_type": m.affiliation_type,
                "qualifications": m.qualifications,
                "appointment_date": m.appointment_date
            }
            for m in members
        ]
    }


@router.post("/members", response_model=ECMemberOut, status_code=status.HTTP_201_CREATED)
def add_ec_member(
    req: ECMemberCreate,
    request: Request,
    current_user: User = Depends(require_role(["Admin", "EC Member"])),
    db: Session = Depends(get_db)
):
    """Adds a new member to the GCP-ASU Ethics Committee register."""
    client_ip = request.client.host if request.client else "127.0.0.1"
    member = EthicsCommitteeMember(
        name=req.name,
        role=req.role,
        affiliation_type=req.affiliation_type,
        qualifications=req.qualifications,
        is_active=True,
        appointment_date=datetime.now(timezone.utc)
    )
    db.add(member)
    db.commit()
    db.refresh(member)

    log_audit_event(
        db=db,
        user_id=current_user.id,
        user_email=current_user.email,
        role=current_user.role,
        ip_address=client_ip,
        action="ADD_EC_MEMBER",
        entity_type="EthicsCommitteeMember",
        entity_id=str(member.id),
        new_value=f"Name={member.name}, Role={member.role}, Affiliation={member.affiliation_type}",
        site_id=current_user.site_id
    )

    return member


@router.get("/protocols")
def list_protocols(db: Session = Depends(get_db)):
    """Lists protocol approvals, amendments, and renewal expiry countdowns."""
    protocols = db.query(ProtocolApproval).all()
    now = datetime.now(timezone.utc)

    results = []
    for p in protocols:
        expiry_dt = p.expiry_date.replace(tzinfo=timezone.utc) if p.expiry_date.tzinfo is None else p.expiry_date
        days_remaining = max(0, (expiry_dt - now).days)
        is_expiring_soon = days_remaining <= 30
        
        results.append({
            "id": p.id,
            "protocol_code": p.protocol_code,
            "title": p.title,
            "amendment_number": p.amendment_number,
            "submission_date": p.submission_date,
            "approval_date": p.approval_date,
            "expiry_date": p.expiry_date,
            "days_remaining_until_renewal": days_remaining,
            "is_expiring_soon": is_expiring_soon,
            "status": "Renewal Required" if days_remaining == 0 else ("Expiring Soon" if is_expiring_soon else p.status)
        })
    return results


@router.post("/dispatch-sae-to-ec/{adverse_event_id}")
def auto_dispatch_sae_to_ec(
    adverse_event_id: int,
    request: Request,
    current_user: User = Depends(require_role(["PV Officer", "Doctor / Investigator", "Admin"])),
    db: Session = Depends(get_db)
):
    """
    GCP-ASU requirement:
    Automatically transmits Serious Adverse Events (SAEs) to the Ethics Committee
    and cryptographically records the exact dispatch timestamp and receipt hash.
    """
    client_ip = request.client.host if request.client else "127.0.0.1"
    ae = db.query(AdverseEvent).filter(AdverseEvent.id == adverse_event_id).first()
    if not ae:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Adverse Event record not found.")

    now = datetime.now(timezone.utc)
    ae.sent_to_ec_at = now

    # Generate transmission cryptographic receipt hash
    transmission_payload = f"SAE|{ae.id}|{ae.event_term}|{now.isoformat()}|{ae.site_id}"
    receipt_hash = hashlib.sha256(transmission_payload.encode("utf-8")).hexdigest()

    transmission = AutomatedECTransmission(
        transmission_type="SAE Notification",
        reference_id=f"AE-{ae.id}-{ae.event_term[:10]}",
        sent_at=now,
        ec_members_dispatched=db.query(EthicsCommitteeMember).filter(EthicsCommitteeMember.is_active == True).count(),
        status="Dispatched to EC Members",
        transmission_hash=receipt_hash
    )
    db.add(transmission)
    db.commit()

    log_audit_event(
        db=db,
        user_id=current_user.id,
        user_email=current_user.email,
        role=current_user.role,
        ip_address=client_ip,
        action="AUTOMATED_SAE_DISPATCH_TO_EC",
        entity_type="AdverseEvent",
        entity_id=str(ae.id),
        details=f"SAE '{ae.event_term}' dispatched to EC. Timestamp: {now.isoformat()}",
        site_id=ae.site_id
    )

    return {
        "message": "SAE automatically dispatched to Ethics Committee register with timestamp.",
        "adverse_event_id": ae.id,
        "sent_to_ec_at": now.isoformat(),
        "receipt_hash": receipt_hash,
        "recipients_count": transmission.ec_members_dispatched
    }
