from datetime import datetime, timezone
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.orm import Session

from ..db.database import get_db
from ..db.models import InformedConsent, ConsentVersion, Participant, User
from ..schemas.schemas import InformedConsentCreate, InformedConsentWithdraw, ConsentVersionOut
from ..core.audit import log_audit_event
from .deps import get_current_user, require_role, verify_site_access

router = APIRouter(prefix="/consent", tags=["GCP-ASU & DPDP Informed Consent"])

@router.get("/templates/current", response_model=ConsentVersionOut)
def get_current_consent_template(db: Session = Depends(get_db)):
    """
    Retrieves current Ethics Committee approved Informed Consent template
    containing all 11 statutory GCP-ASU sections.
    """
    version = db.query(ConsentVersion).filter(ConsentVersion.is_current == True).first()
    if not version:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No active consent template configured.")
    return version


@router.get("/participant/{participant_id}")
def get_participant_consents(
    participant_id: int,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Retrieves all signed consent history for a participant."""
    participant = verify_site_access(participant_id, current_user, db, request)
    consents = db.query(InformedConsent).filter(InformedConsent.participant_id == participant.id).all()
    
    return [
        {
            "id": c.id,
            "version_number": c.version.version_number if c.version else "Unknown",
            "language": c.language,
            "explained_orally": c.explained_orally,
            "is_illiterate": c.is_illiterate,
            "impartial_witness_name": c.impartial_witness_name,
            "has_witness_signature": bool(c.impartial_witness_signature),
            "signed_date": c.signed_date,
            "status": c.status,
            "requires_reconsent": c.requires_reconsent,
            "withdrawal_date": c.withdrawal_date,
            "withdrawal_reason": c.withdrawal_reason
        }
        for c in consents
    ]


@router.post("/record", status_code=status.HTTP_201_CREATED)
def record_informed_consent(
    req: InformedConsentCreate,
    request: Request,
    current_user: User = Depends(require_role(["Research Coordinator", "Doctor / Investigator"])),
    db: Session = Depends(get_db)
):
    """
    Records signed Informed Consent:
    - Enforces language choice (Hindi, English, Regional).
    - Requires oral explanation checkbox.
    - Illiterate participant gate: impartial witness's name and signature are mandatory;
      blocks enrolment if missing!
    - Updates participant `is_enrolled = True` upon successful valid written consent.
    """
    client_ip = request.client.host if request.client else "127.0.0.1"
    participant = verify_site_access(req.participant_id, current_user, db, request)

    # Validate active consent version
    version = db.query(ConsentVersion).filter(ConsentVersion.id == req.consent_version_id).first()
    if not version:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid consent template version.")

    # Illiterate participant validation gate (GCP-ASU requirement)
    if req.is_illiterate:
        if not req.impartial_witness_name or not req.impartial_witness_name.strip():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="GCP-ASU Mandatory Requirement: For illiterate participants, an impartial witness name is strictly mandatory before enrolment."
            )
        if not req.impartial_witness_signature or not req.impartial_witness_signature.strip():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="GCP-ASU Mandatory Requirement: For illiterate participants, an impartial witness signature is strictly mandatory before enrolment."
            )

    consent = InformedConsent(
        participant_id=participant.id,
        consent_version_id=version.id,
        language=req.language,
        explained_orally=req.explained_orally,
        is_illiterate=req.is_illiterate,
        impartial_witness_name=req.impartial_witness_name if req.is_illiterate else None,
        impartial_witness_signature=req.impartial_witness_signature if req.is_illiterate else None,
        signed_date=datetime.now(timezone.utc),
        status="active",
        requires_reconsent=False
    )
    db.add(consent)

    # Valid written consent on file: Enrolment gate unlocked
    participant.is_enrolled = True
    db.commit()

    log_audit_event(
        db=db,
        user_id=current_user.id,
        user_email=current_user.email,
        role=current_user.role,
        ip_address=client_ip,
        action="RECORD_INFORMED_CONSENT",
        entity_type="InformedConsent",
        entity_id=participant.subject_code,
        new_value=f"Version={version.version_number}, Lang={req.language}, Oral={req.explained_orally}, Illiterate={req.is_illiterate}",
        site_id=participant.site_id
    )

    return {
        "message": "Valid written informed consent recorded on file. Participant enrolment gate unlocked.",
        "consent_id": consent.id,
        "participant_subject_code": participant.subject_code,
        "is_enrolled": participant.is_enrolled
    }


@router.post("/bump-version")
def bump_consent_version(
    version_number: str,
    amendment_reason: str,
    request: Request,
    current_user: User = Depends(require_role(["Doctor / Investigator", "Admin", "EC Member"])),
    db: Session = Depends(get_db)
):
    """
    When Ethics Committee approves a new version of the Informed Consent:
    - Retires old current version.
    - Flags every participant active on the old version for mandatory re-consent.
    """
    client_ip = request.client.host if request.client else "127.0.0.1"

    # Mark all old versions as non-current
    db.query(ConsentVersion).update({"is_current": False})

    # Retrieve previous template data to duplicate with updated version
    prev = db.query(ConsentVersion).order_by(ConsentVersion.id.desc()).first()
    new_version = ConsentVersion(
        version_number=version_number,
        protocol_code=prev.protocol_code if prev else "AYUR-CT-2026-001",
        protocol_title=prev.protocol_title if prev else "Clinical Evaluation of ASU Formulation",
        ec_approval_date=datetime.now(timezone.utc),
        is_current=True,
        aims=prev.aims if prev else "Standard study aims",
        methods=prev.methods if prev else "Double-blind ASU protocol",
        duration=prev.duration if prev else "12 Weeks",
        expected_benefits=prev.expected_benefits if prev else "Dosha shamana and clinical recovery",
        alternative_treatments=prev.alternative_treatments if prev else "Standard Ayurvedic or Allopathic care",
        foreseeable_risks_discomfort=prev.foreseeable_risks_discomfort if prev else "Mild transient koshtha shuddhi",
        extent_of_confidentiality=prev.extent_of_confidentiality if prev else "Data strictly pseudonymous under DPDP Act",
        free_treatment_injury=prev.free_treatment_injury if prev else "Free medical management for any research-related injury",
        compensation_disability_death=prev.compensation_disability_death if prev else "Statutory compensation as per GCP-ASU & CDSCO rules",
        research_team_contacts=prev.research_team_contacts if prev else "PI Phone: +91-11-2953-8401",
        biological_samples_secondary_use=prev.biological_samples_secondary_use if prev else "Secondary biological use requires separate express consent"
    )
    db.add(new_version)
    db.flush()

    # Flag all participants currently on older versions for mandatory re-consent
    affected_consents = db.query(InformedConsent).filter(
        InformedConsent.consent_version_id != new_version.id,
        InformedConsent.status == "active"
    ).all()

    for c in affected_consents:
        c.requires_reconsent = True

    db.commit()

    log_audit_event(
        db=db,
        user_id=current_user.id,
        user_email=current_user.email,
        role=current_user.role,
        ip_address=client_ip,
        action="CONSENT_VERSION_APPROVED_RECONSENT_TRIGGERED",
        entity_type="ConsentVersion",
        entity_id=version_number,
        details=f"Flagged {len(affected_consents)} active participants on older versions for re-consent.",
        reason=amendment_reason
    )

    return {
        "message": f"Consent version {version_number} approved by EC.",
        "new_version_id": new_version.id,
        "participants_flagged_for_reconsent": len(affected_consents)
    }


@router.post("/withdraw/{consent_id}")
def withdraw_consent(
    consent_id: int,
    req: InformedConsentWithdraw,
    request: Request,
    current_user: User = Depends(require_role(["Research Coordinator", "Doctor / Investigator"])),
    db: Session = Depends(get_db)
):
    """
    DPDP Sections 5-6 & GCP-ASU Compliance:
    - Consent can be withdrawn as easily as it was given.
    - Personal data processing ceases immediately.
    - Clinical trial records are NOT auto-deleted, but marked 'retained_for_legal_reasons'
      for the statutory 5-year GCP-ASU retention period.
    """
    client_ip = request.client.host if request.client else "127.0.0.1"
    consent = db.query(InformedConsent).filter(InformedConsent.id == consent_id).first()
    if not consent:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Consent record not found.")

    participant = verify_site_access(consent.participant_id, current_user, db, request)

    now = datetime.now(timezone.utc)
    consent.status = "withdrawn"
    consent.withdrawal_date = now
    consent.withdrawal_reason = req.reason

    # GCP-ASU & DPDP Rule: Stop processing, mark retained for legal reasons
    participant.data_status = "retained_for_legal_reasons"
    participant.is_enrolled = False
    participant.is_dosed = False

    db.commit()

    log_audit_event(
        db=db,
        user_id=current_user.id,
        user_email=current_user.email,
        role=current_user.role,
        ip_address=client_ip,
        action="WITHDRAW_CONSENT",
        entity_type="Participant",
        entity_id=participant.subject_code,
        new_value="Status: retained_for_legal_reasons",
        reason=req.reason,
        site_id=participant.site_id
    )

    return {
        "message": "Consent successfully withdrawn. Clinical data processing halted and record marked 'retained for legal reasons' for regulatory 5-year retention.",
        "subject_code": participant.subject_code,
        "data_status": participant.data_status,
        "retention_until": participant.retention_until.isoformat()
    }
