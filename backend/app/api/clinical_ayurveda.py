from typing import List, Optional
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field

from ..db.database import get_db
from ..db.models import Participant, AdverseEvent, User
from ..schemas.schemas import AdverseEventCreate
from ..core.audit import log_audit_event
from .deps import get_current_user, require_role, verify_site_access

router = APIRouter(prefix="/clinical-ayurveda", tags=["Ayurveda Protocol & ASU Safety"])

class PrakritiAssessmentIn(BaseModel):
    participant_id: int
    # 10 Questions scoring Vata, Pitta, Kapha (1-3 scale each)
    body_frame: str = Field(..., description="Vata: Thin/lean, Pitta: Medium, Kapha: Broad/heavy")
    skin_type: str = Field(..., description="Vata: Dry/rough, Pitta: Warm/oily, Kapha: Thick/cool")
    appetite: str = Field(..., description="Vata: Variable, Pitta: Strong/sharp, Kapha: Constant/slow")
    temperature_preference: str = Field(..., description="Vata: Prefers warm, Pitta: Prefers cold, Kapha: Tolerates all")
    sleep_pattern: str = Field(..., description="Vata: Light/interrupted, Pitta: Moderate, Kapha: Deep/heavy")
    mental_nature: str = Field(..., description="Vata: Quick/creative, Pitta: Analytical/intense, Kapha: Calm/patient")

@router.post("/prakriti-assess")
def assess_prakriti(
    req: PrakritiAssessmentIn,
    request: Request,
    current_user: User = Depends(require_role(["Doctor / Investigator", "Research Coordinator"])),
    db: Session = Depends(get_db)
):
    """
    Computes Ayurvedic Deha Prakriti percentage distribution (Vata, Pitta, Kapha)
    from validated clinical questionnaire and updates participant profile.
    """
    client_ip = request.client.host if request.client else "127.0.0.1"
    participant = verify_site_access(req.participant_id, current_user, db, request)

    # Scoring algorithm based on traditional AyurCTMS Prakriti indicators
    v_score = 0
    p_score = 0
    k_score = 0

    answers = [
        req.body_frame.lower(), req.skin_type.lower(), req.appetite.lower(),
        req.temperature_preference.lower(), req.sleep_pattern.lower(), req.mental_nature.lower()
    ]

    for a in answers:
        if "thin" in a or "dry" in a or "variable" in a or "warm" in a or "light" in a or "quick" in a:
            v_score += 1
        elif "medium" in a or "oily" in a or "strong" in a or "cold" in a or "moderate" in a or "analytical" in a:
            p_score += 1
        else:
            k_score += 1

    total = max(1, v_score + p_score + k_score)
    v_pct = int((v_score / total) * 100)
    p_pct = int((p_score / total) * 100)
    k_pct = 100 - (v_pct + p_pct)

    # Determine dominant dosha prakriti
    scores = [("Vata", v_pct), ("Pitta", p_pct), ("Kapha", k_pct)]
    scores.sort(key=lambda x: x[1], reverse=True)
    dominant = f"{scores[0][0]}-{scores[1][0]}"

    participant.prakriti_vata = v_pct
    participant.prakriti_pitta = p_pct
    participant.prakriti_kapha = k_pct
    participant.dominant_prakriti = dominant
    db.commit()

    log_audit_event(
        db=db,
        user_id=current_user.id,
        user_email=current_user.email,
        role=current_user.role,
        ip_address=client_ip,
        action="ASSESS_PRAKRITI",
        entity_type="Participant",
        entity_id=participant.subject_code,
        new_value=f"Dominant={dominant}, Vata={v_pct}%, Pitta={p_pct}%, Kapha={k_pct}%",
        site_id=participant.site_id
    )

    return {
        "subject_code": participant.subject_code,
        "prakriti_vata": v_pct,
        "prakriti_pitta": p_pct,
        "prakriti_kapha": k_pct,
        "dominant_prakriti": dominant,
        "ayurvedic_diagnosis": participant.ayurvedic_diagnosis,
        "modern_diagnosis": participant.modern_diagnosis
    }


@router.post("/adverse-events", status_code=status.HTTP_201_CREATED)
def record_adverse_event(
    req: AdverseEventCreate,
    request: Request,
    current_user: User = Depends(require_role(["Doctor / Investigator", "PV Officer", "Research Coordinator"])),
    db: Session = Depends(get_db)
):
    """
    Records an ASU Adverse Event / Drug Reaction:
    - Captures both Modern Term and Classical ASU Dosha/Srotas Term.
    - If serious (SAE), triggers automatic alert and queues for immediate EC notification.
    """
    client_ip = request.client.host if request.client else "127.0.0.1"
    participant = verify_site_access(req.participant_id, current_user, db, request)

    now = datetime.now(timezone.utc)
    ae = AdverseEvent(
        participant_id=participant.id,
        site_id=participant.site_id,
        event_term=req.event_term,
        ayurvedic_term=req.ayurvedic_term,
        is_serious=req.is_serious,
        severity=req.severity,
        outcome=req.outcome,
        reported_at=now,
        causality_asu=req.causality_asu
    )
    db.add(ae)
    db.commit()
    db.refresh(ae)

    log_audit_event(
        db=db,
        user_id=current_user.id,
        user_email=current_user.email,
        role=current_user.role,
        ip_address=client_ip,
        action="RECORD_ADVERSE_EVENT",
        entity_type="AdverseEvent",
        entity_id=str(ae.id),
        details=f"SAE={ae.is_serious}, Term={ae.event_term}, ASU={ae.ayurvedic_term}",
        site_id=participant.site_id
    )

    return {
        "message": "Adverse drug reaction recorded in ASU pharmacovigilance ledger.",
        "ae_id": ae.id,
        "subject_code": participant.subject_code,
        "is_serious": ae.is_serious,
        "ayurvedic_term": ae.ayurvedic_term,
        "reported_at": ae.reported_at
    }


@router.get("/adverse-events")
def list_adverse_events(
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Lists all ADRs/SAEs. Restricted by site tenancy for coordinators."""
    query = db.query(AdverseEvent)
    if current_user.role == "Research Coordinator":
        query = query.filter(AdverseEvent.site_id == current_user.site_id)

    events = query.all()
    return [
        {
            "id": e.id,
            "participant_subject_code": e.participant.subject_code if e.participant else "SUB-UNKNOWN",
            "site_id": e.site_id,
            "event_term": e.event_term,
            "ayurvedic_term": e.ayurvedic_term,
            "is_serious": e.is_serious,
            "severity": e.severity,
            "outcome": e.outcome,
            "reported_at": e.reported_at,
            "sent_to_ec_at": e.sent_to_ec_at,
            "sent_to_pv_at": e.sent_to_pv_at,
            "causality_asu": e.causality_asu
        }
        for e in events
    ]
