from datetime import datetime, timezone, timedelta
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.orm import Session

from ..db.database import get_db
from ..db.models import (
    DPDPNotice, DPDPDataRequest, DPDPGrievance, DataBreachIncident,
    DataProcessorContract, Participant, User
)
from ..schemas.schemas import (
    DPDPDataRequestCreate, DPDPGrievanceCreate, DataBreachCreate
)
from ..core.config import settings
from ..core.audit import log_audit_event
from .deps import get_current_user, require_role

router = APIRouter(prefix="/dpdp", tags=["DPDP Act 2023 & DPDP Rules 2025"])

@router.get("/dpo-contact")
def get_dpo_contact():
    """
    DPDP Section 8(9) & Rule 3:
    Provides DPO contact details displayed on every screen footer and consent notice.
    """
    return {
        "name": settings.DPO_NAME,
        "designation": settings.DPO_DESIGNATION,
        "email": settings.DPO_EMAIL,
        "phone": settings.DPO_PHONE,
        "address": settings.DPO_ADDRESS,
        "jurisdiction": "Data Protection Board of India (DPBI)"
    }


@router.get("/notice/current")
def get_current_dpdp_notice(db: Session = Depends(get_db)):
    """
    DPDP Sections 5-6, Rule 3:
    Standalone, plain-language privacy notice without pre-ticked boxes.
    """
    notice = db.query(DPDPNotice).filter(DPDPNotice.is_active == True).first()
    if not notice:
        return {
            "version": "DPDP-V1.0",
            "effective_date": datetime.now(timezone.utc),
            "plain_language_summary": "We collect health and dosha clinical trial measurements strictly for Ayurvedic drug safety research.",
            "data_categories_collected": "Age, gender, pulse, Prakriti scores, adverse drug observations, contact details.",
            "purposes": "Clinical efficacy evaluation, drug safety reporting under Ministry of AYUSH GCP-ASU.",
            "dpo": get_dpo_contact()
        }
    return notice


@router.get("/data-requests")
def list_data_requests(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Lists Data Principal rights requests (Access, Correction, Update, Erasure).
    Calculates remaining days toward the statutory 90-day response deadline.
    """
    requests = db.query(DPDPDataRequest).order_by(DPDPDataRequest.created_at.desc()).all()
    now = datetime.now(timezone.utc)

    results = []
    for r in requests:
        deadline_dt = r.deadline_at.replace(tzinfo=timezone.utc) if r.deadline_at.tzinfo is None else r.deadline_at
        days_remaining = max(0, (deadline_dt - now).days)
        results.append({
            "id": r.id,
            "subject_code": r.subject_code,
            "request_type": r.request_type,
            "details": r.details,
            "status": r.status,
            "created_at": r.created_at,
            "deadline_at": r.deadline_at,
            "days_remaining": days_remaining,
            "is_overdue": days_remaining == 0 and r.status not in ["Fulfilled", "Resolved", "Retained for Legal Reasons"],
            "resolution_notes": r.resolution_notes,
            "resolved_at": r.resolved_at
        })
    return results


@router.post("/data-requests", status_code=status.HTTP_201_CREATED)
def submit_data_request(
    req: DPDPDataRequestCreate,
    request: Request,
    db: Session = Depends(get_db)
):
    """
    Submits a DPDP Data Principal Right Request:
    Starts the 90-day response countdown clock.
    """
    client_ip = request.client.host if request.client else "127.0.0.1"
    now = datetime.now(timezone.utc)
    
    # Check if participant exists
    p = db.query(Participant).filter(Participant.subject_code == req.subject_code).first()
    if not p:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Subject code not found.")

    dr = DPDPDataRequest(
        request_type=req.request_type,
        subject_code=req.subject_code,
        details=req.details,
        status="Received",
        created_at=now,
        deadline_at=now + timedelta(days=settings.DPDP_DATA_REQUEST_MAX_RESPONSE_DAYS)
    )
    db.add(dr)
    db.commit()
    db.refresh(dr)

    log_audit_event(
        db=db,
        user_id=None,
        user_email="data.principal@ayurctms.in",
        role="Data Principal",
        ip_address=client_ip,
        action="DATA_PRINCIPAL_REQUEST_FILED",
        entity_type="DPDPDataRequest",
        entity_id=str(dr.id),
        details=f"Type={dr.request_type}, Subject={dr.subject_code}, 90-Day Deadline={dr.deadline_at.isoformat()}"
    )

    return {
        "message": f"Data Principal {req.request_type.capitalize()} request registered. Response deadline: 90 days.",
        "request_id": dr.id,
        "deadline_at": dr.deadline_at.isoformat(),
        "days_allocated": 90
    }


@router.post("/data-requests/{request_id}/resolve")
def resolve_data_request(
    request_id: int,
    resolution_status: str,
    notes: str,
    request: Request,
    current_user: User = Depends(require_role(["Doctor / Investigator", "Admin", "Data Protection Officer"])),
    db: Session = Depends(get_db)
):
    """Resolves or fulfills a Data Principal request."""
    client_ip = request.client.host if request.client else "127.0.0.1"
    dr = db.query(DPDPDataRequest).filter(DPDPDataRequest.id == request_id).first()
    if not dr:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Data request not found.")

    dr.status = resolution_status
    dr.resolution_notes = notes
    dr.resolved_at = datetime.now(timezone.utc)
    db.commit()

    log_audit_event(
        db=db,
        user_id=current_user.id,
        user_email=current_user.email,
        role=current_user.role,
        ip_address=client_ip,
        action="RESOLVE_DATA_PRINCIPAL_REQUEST",
        entity_type="DPDPDataRequest",
        entity_id=str(dr.id),
        details=f"Status={dr.status}, Notes={notes}"
    )

    return {"message": "Data Principal request updated.", "request_id": dr.id, "status": dr.status}


@router.get("/grievances")
def list_grievances(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Lists DPDP grievance complaints with 90-day countdown."""
    grievances = db.query(DPDPGrievance).order_by(DPDPGrievance.filed_at.desc()).all()
    now = datetime.now(timezone.utc)

    return [
        {
            "id": g.id,
            "complainant_name": g.complainant_name,
            "issue_description": g.issue_description,
            "status": g.status,
            "filed_at": g.filed_at,
            "days_remaining": max(0, ((g.deadline_at.replace(tzinfo=timezone.utc) if g.deadline_at.tzinfo is None else g.deadline_at) - now).days),
            "resolution_notes": g.resolution_notes,
            "resolved_at": g.resolved_at
        }
        for g in grievances
    ]


@router.post("/grievances", status_code=status.HTTP_201_CREATED)
def file_grievance(
    req: DPDPGrievanceCreate,
    request: Request,
    db: Session = Depends(get_db)
):
    """Files a DPDP Grievance for Redressal by the DPO."""
    client_ip = request.client.host if request.client else "127.0.0.1"
    now = datetime.now(timezone.utc)

    g = DPDPGrievance(
        complainant_name=req.complainant_name,
        complainant_contact=req.complainant_contact,
        issue_description=req.issue_description,
        status="Open",
        filed_at=now,
        deadline_at=now + timedelta(days=settings.DPDP_GRIEVANCE_MAX_RESPONSE_DAYS)
    )
    db.add(g)
    db.commit()
    db.refresh(g)

    log_audit_event(
        db=db,
        user_id=None,
        user_email="grievance.portal@ayurctms.in",
        role="Complainant",
        ip_address=client_ip,
        action="GRIEVANCE_FILED",
        entity_type="DPDPGrievance",
        entity_id=str(g.id),
        details=f"Complainant={g.complainant_name}, 90-Day SLA Active"
    )

    return {
        "message": "Grievance successfully filed. Assigned to Data Protection Officer with 90-day statutory resolution timeline.",
        "grievance_id": g.id,
        "deadline_at": g.deadline_at.isoformat()
    }


@router.post("/report-breach", status_code=status.HTTP_201_CREATED)
def report_personal_data_breach(
    req: DataBreachCreate,
    request: Request,
    current_user: User = Depends(require_role(["Admin", "Data Protection Officer", "Doctor / Investigator"])),
    db: Session = Depends(get_db)
):
    """
    DPDP Section 8(6) & Rule 7:
    Breach notification workflow with live 72-hour countdown timer
    to notify the Data Protection Board of India (DPBI) and affected individuals.
    """
    client_ip = request.client.host if request.client else "127.0.0.1"
    now = datetime.now(timezone.utc)
    deadline_72h = now + timedelta(hours=settings.DPBI_BREACH_NOTIFICATION_HOURS)

    breach = DataBreachIncident(
        incident_ref=req.incident_ref,
        discovery_timestamp=now,
        incident_nature=req.incident_nature,
        data_affected=req.data_affected,
        number_affected=req.number_affected,
        countdown_deadline_dpbi=deadline_72h,
        remediation_summary=req.remediation_summary,
        status="Investigating - 72h Countdown Active"
    )
    db.add(breach)
    db.commit()
    db.refresh(breach)

    log_audit_event(
        db=db,
        user_id=current_user.id,
        user_email=current_user.email,
        role=current_user.role,
        ip_address=client_ip,
        action="REPORT_DATA_BREACH",
        entity_type="DataBreachIncident",
        entity_id=breach.incident_ref,
        details=f"Affected={breach.number_affected}, Nature={breach.incident_nature[:50]}, 72h Deadline={deadline_72h.isoformat()}",
        site_id=current_user.site_id
    )

    template_message = (
        f"Notice of Personal Data Security Incident ({req.incident_ref}): "
        f"AyurCTMS has detected potential unauthorized access affecting {req.data_affected}. "
        "Appropriate containment measures are active under the supervision of the DPO. "
        f"Contact {settings.DPO_EMAIL} for immediate inquiries."
    )

    return {
        "message": "Personal data breach registered. 72-Hour DPBI countdown timer initiated.",
        "incident_ref": breach.incident_ref,
        "discovery_timestamp": now.isoformat(),
        "countdown_deadline_dpbi": deadline_72h.isoformat(),
        "hours_allocated": 72,
        "template_notification_to_affected_individuals": template_message
    }


@router.get("/breaches")
def list_breaches(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Lists breaches with live 72-hour countdown calculation."""
    breaches = db.query(DataBreachIncident).order_by(DataBreachIncident.discovery_timestamp.desc()).all()
    now = datetime.now(timezone.utc)

    results = []
    for b in breaches:
        deadline_dt = b.countdown_deadline_dpbi.replace(tzinfo=timezone.utc) if b.countdown_deadline_dpbi.tzinfo is None else b.countdown_deadline_dpbi
        seconds_remaining = max(0, int((deadline_dt - now).total_seconds()))
        hours_remaining = seconds_remaining / 3600.0

        results.append({
            "id": b.id,
            "incident_ref": b.incident_ref,
            "discovery_timestamp": b.discovery_timestamp,
            "incident_nature": b.incident_nature,
            "data_affected": b.data_affected,
            "number_affected": b.number_affected,
            "countdown_deadline_dpbi": b.countdown_deadline_dpbi,
            "seconds_remaining": seconds_remaining,
            "hours_remaining": round(hours_remaining, 2),
            "is_within_72h": seconds_remaining > 0,
            "dpbi_reported_at": b.dpbi_reported_at,
            "status": b.status
        })
    return results


@router.get("/data-processors")
def list_data_processors(db: Session = Depends(get_db)):
    """DPDP Section 8(5): Data processor register with signed contracts."""
    processors = db.query(DataProcessorContract).all()
    return [
        {
            "id": p.id,
            "processor_name": p.processor_name,
            "service_type": p.service_type,
            "contract_signed_date": p.contract_signed_date,
            "dpdp_compliant_agreement": p.dpdp_compliant_agreement,
            "data_location": p.data_location,
            "last_audit_date": p.last_audit_date
        }
        for p in processors
    ]
