import csv
import io
from typing import List, Optional
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, status, Request, Response
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from ..db.database import get_db
from ..db.models import Participant, ParticipantPII, InformedConsent, User
from ..schemas.schemas import ParticipantCreate, ParticipantUpdate, ParticipantOut
from ..core.security import encrypt_pii, decrypt_pii, mask_phone_number, mask_name, sanitize_csv_cell
from ..core.security_settings import security_settings
from ..core.audit import log_audit_event
from .deps import get_current_user, require_role, verify_site_access

router = APIRouter(prefix="/participants", tags=["GCP-ASU Participants & RLS"])

@router.get("", response_model=List[ParticipantOut])
def list_participants(
    request: Request,
    site_id: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    List participants enforcing PostgreSQL Row-Level Security logic:
    - Admin sees NO clinical data (403 Forbidden).
    - Research Coordinator sees ONLY their own site.
    - Monitor / Auditor get read-only data with masked PII.
    - Names/Phones are unmasked ONLY for PI (Doctor) and Site Coordinator.
    """
    client_ip = request.client.host if request.client else "127.0.0.1"

    # 1. Admin Block (Prompt 7 Rule 3: 'the Admin sees no clinical data')
    if current_user.role == "Admin":
        log_audit_event(
            db=db,
            user_id=current_user.id,
            user_email=current_user.email,
            role=current_user.role,
            ip_address=client_ip,
            action="UNAUTHORIZED_CLINICAL_ACCESS_BLOCKED",
            entity_type="ClinicalData",
            details="System Admin attempted to query patient clinical records directly.",
            site_id=current_user.site_id
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Your role (Admin) cannot do this. Administrators are restricted from viewing clinical trial subject data."
        )

    query = db.query(Participant)

    # 2. Coordinator Site Tenancy Lock
    if current_user.role == "Research Coordinator":
        query = query.filter(Participant.site_id == current_user.site_id)
    elif site_id:
        query = query.filter(Participant.site_id == site_id)

    participants = query.all()

    # Determine PII unmasking permissions
    can_unmask_pii = current_user.role in security_settings.CAN_VIEW_UNMASKED_PII

    results = []
    for p in participants:
        p_dict = {
            "id": p.id,
            "subject_code": p.subject_code,
            "site_id": p.site_id,
            "age": p.age,
            "gender": p.gender,
            "is_minor": p.is_minor,
            "is_disabled": p.is_disabled,
            "legal_guardian_name": p.legal_guardian_name,
            "legal_guardian_consent_verified": p.legal_guardian_consent_verified,
            "tracking_profiling_prohibited": p.tracking_profiling_prohibited,
            "prakriti_vata": p.prakriti_vata,
            "prakriti_pitta": p.prakriti_pitta,
            "prakriti_kapha": p.prakriti_kapha,
            "dominant_prakriti": p.dominant_prakriti,
            "ayurvedic_diagnosis": p.ayurvedic_diagnosis,
            "modern_diagnosis": p.modern_diagnosis,
            "is_enrolled": p.is_enrolled,
            "is_dosed": p.is_dosed,
            "data_status": p.data_status,
            "retention_until": p.retention_until,
            "created_at": p.created_at
        }

        # Handle separate restricted PII table
        if p.pii:
            if can_unmask_pii:
                # Coordinator sees only their own site unmasked
                if current_user.role == "Research Coordinator" and p.site_id != current_user.site_id:
                    p_dict["full_name"] = mask_name(decrypt_pii(p.pii.encrypted_name))
                    p_dict["phone_number"] = p.pii.masked_phone
                else:
                    p_dict["full_name"] = decrypt_pii(p.pii.encrypted_name)
                    p_dict["phone_number"] = decrypt_pii(p.pii.encrypted_phone)
            else:
                # Monitor, Auditor, EC Member get masked representation
                raw_name = decrypt_pii(p.pii.encrypted_name)
                p_dict["full_name"] = mask_name(raw_name)
                p_dict["phone_number"] = p.pii.masked_phone
        else:
            p_dict["full_name"] = None
            p_dict["phone_number"] = None

        results.append(ParticipantOut(**p_dict))

    # Log personal data access (DPDP requirement)
    log_audit_event(
        db=db,
        user_id=current_user.id,
        user_email=current_user.email,
        role=current_user.role,
        ip_address=client_ip,
        action="VIEW_PARTICIPANTS_LIST",
        entity_type="Participant",
        entity_id=f"count={len(results)}",
        reason=f"PII unmasked: {can_unmask_pii}",
        site_id=current_user.site_id
    )

    return results


@router.get("/{participant_id}", response_model=ParticipantOut)
def get_participant_by_id(
    participant_id: int,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Retrieves single participant with row-level security and cross-site prevention."""
    if current_user.role == "Admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Your role (Admin) cannot do this. Administrators cannot view clinical data."
        )

    # Verify site tenancy
    p = verify_site_access(participant_id, current_user, db, request)
    can_unmask_pii = current_user.role in security_settings.CAN_VIEW_UNMASKED_PII

    p_dict = {
        "id": p.id,
        "subject_code": p.subject_code,
        "site_id": p.site_id,
        "age": p.age,
        "gender": p.gender,
        "is_minor": p.is_minor,
        "is_disabled": p.is_disabled,
        "legal_guardian_name": p.legal_guardian_name,
        "legal_guardian_consent_verified": p.legal_guardian_consent_verified,
        "tracking_profiling_prohibited": p.tracking_profiling_prohibited,
        "prakriti_vata": p.prakriti_vata,
        "prakriti_pitta": p.prakriti_pitta,
        "prakriti_kapha": p.prakriti_kapha,
        "dominant_prakriti": p.dominant_prakriti,
        "ayurvedic_diagnosis": p.ayurvedic_diagnosis,
        "modern_diagnosis": p.modern_diagnosis,
        "is_enrolled": p.is_enrolled,
        "is_dosed": p.is_dosed,
        "data_status": p.data_status,
        "retention_until": p.retention_until,
        "created_at": p.created_at
    }

    if p.pii:
        if can_unmask_pii:
            p_dict["full_name"] = decrypt_pii(p.pii.encrypted_name)
            p_dict["phone_number"] = decrypt_pii(p.pii.encrypted_phone)
        else:
            p_dict["full_name"] = mask_name(decrypt_pii(p.pii.encrypted_name))
            p_dict["phone_number"] = p.pii.masked_phone

    return ParticipantOut(**p_dict)


@router.post("", response_model=ParticipantOut, status_code=status.HTTP_201_CREATED)
def create_participant(
    req: ParticipantCreate,
    request: Request,
    current_user: User = Depends(require_role(["Research Coordinator", "Doctor / Investigator"])),
    db: Session = Depends(get_db)
):
    """
    Creates a new clinical trial participant:
    - Enforces DPDP Section 9: If participant is minor (<18) or disabled, verifiable guardian consent is mandatory.
    - Isolates and encrypts Direct PII into restricted participant_pii table (AES-256).
    - Participant is created in 'not enrolled' status until valid written consent is signed on file.
    """
    client_ip = request.client.host if request.client else "127.0.0.1"

    # DPDP Section 9 Check: Minors and Persons with Disability
    is_underage = req.age < 18
    if (is_underage or req.is_disabled) and (not req.legal_guardian_name or not req.legal_guardian_consent_verified):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="DPDP Section 9 Violation: Verifiable parent/guardian consent is mandatory before enrolling minors (<18) or persons with disability."
        )

    # Check duplicate subject code
    existing = db.query(Participant).filter(Participant.subject_code == req.subject_code).first()
    if existing:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Subject code already registered.")

    # Create participant record with pseudonymous ID
    participant = Participant(
        subject_code=req.subject_code,
        site_id=current_user.site_id if current_user.role == "Research Coordinator" else req.site_id,
        age=req.age,
        gender=req.gender,
        is_minor=is_underage or req.is_minor,
        is_disabled=req.is_disabled,
        legal_guardian_name=req.legal_guardian_name,
        legal_guardian_consent_verified=req.legal_guardian_consent_verified,
        tracking_profiling_prohibited=True,
        prakriti_vata=req.prakriti_vata,
        prakriti_pitta=req.prakriti_pitta,
        prakriti_kapha=req.prakriti_kapha,
        dominant_prakriti=req.dominant_prakriti,
        ayurvedic_diagnosis=req.ayurvedic_diagnosis,
        modern_diagnosis=req.modern_diagnosis,
        is_enrolled=False, # Gate: Must have valid written consent on file
        is_dosed=False,
        data_status="active"
    )
    db.add(participant)
    db.flush()

    # Isolate Direct PII in separate locked table with AES-256 encryption
    pii = ParticipantPII(
        participant_id=participant.id,
        encrypted_name=encrypt_pii(req.full_name),
        encrypted_phone=encrypt_pii(req.phone_number),
        masked_phone=mask_phone_number(req.phone_number),
        address=req.address,
        emergency_contact=req.emergency_contact
    )
    db.add(pii)
    db.commit()
    db.refresh(participant)

    log_audit_event(
        db=db,
        user_id=current_user.id,
        user_email=current_user.email,
        role=current_user.role,
        ip_address=client_ip,
        action="CREATE_PARTICIPANT",
        entity_type="Participant",
        entity_id=participant.subject_code,
        new_value=f"Age={participant.age}, Site={participant.site_id}, Minor={participant.is_minor}",
        site_id=participant.site_id
    )

    return ParticipantOut(
        id=participant.id,
        subject_code=participant.subject_code,
        site_id=participant.site_id,
        age=participant.age,
        gender=participant.gender,
        is_minor=participant.is_minor,
        is_disabled=participant.is_disabled,
        legal_guardian_name=participant.legal_guardian_name,
        legal_guardian_consent_verified=participant.legal_guardian_consent_verified,
        tracking_profiling_prohibited=participant.tracking_profiling_prohibited,
        prakriti_vata=participant.prakriti_vata,
        prakriti_pitta=participant.prakriti_pitta,
        prakriti_kapha=participant.prakriti_kapha,
        dominant_prakriti=participant.dominant_prakriti,
        ayurvedic_diagnosis=participant.ayurvedic_diagnosis,
        modern_diagnosis=participant.modern_diagnosis,
        is_enrolled=participant.is_enrolled,
        is_dosed=participant.is_dosed,
        data_status=participant.data_status,
        retention_until=participant.retention_until,
        created_at=participant.created_at,
        full_name=req.full_name,
        phone_number=req.phone_number
    )


@router.put("/{participant_id}", response_model=ParticipantOut)
def update_participant(
    participant_id: int,
    req: ParticipantUpdate,
    request: Request,
    current_user: User = Depends(require_role(["Research Coordinator", "Doctor / Investigator"])),
    db: Session = Depends(get_db)
):
    """
    Validated data entry modification:
    - Enforces documented reason for change.
    - Records old value, new value, reason, who and when into cryptographic audit trail.
    """
    client_ip = request.client.host if request.client else "127.0.0.1"
    participant = verify_site_access(participant_id, current_user, db, request)

    # Capture previous state for audit trail
    old_state = f"Age={participant.age}, Vata={participant.prakriti_vata}, Pitta={participant.prakriti_pitta}, Kapha={participant.prakriti_kapha}, AyuDiag={participant.ayurvedic_diagnosis}"

    if req.age is not None:
        participant.age = req.age
        if req.age < 18:
            participant.is_minor = True
    if req.prakriti_vata is not None:
        participant.prakriti_vata = req.prakriti_vata
    if req.prakriti_pitta is not None:
        participant.prakriti_pitta = req.prakriti_pitta
    if req.prakriti_kapha is not None:
        participant.prakriti_kapha = req.prakriti_kapha
    if req.dominant_prakriti is not None:
        participant.dominant_prakriti = req.dominant_prakriti
    if req.ayurvedic_diagnosis is not None:
        participant.ayurvedic_diagnosis = req.ayurvedic_diagnosis
    if req.modern_diagnosis is not None:
        participant.modern_diagnosis = req.modern_diagnosis

    new_state = f"Age={participant.age}, Vata={participant.prakriti_vata}, Pitta={participant.prakriti_pitta}, Kapha={participant.prakriti_kapha}, AyuDiag={participant.ayurvedic_diagnosis}"

    db.commit()
    db.refresh(participant)

    # Tamper-proof audit logging of data correction
    log_audit_event(
        db=db,
        user_id=current_user.id,
        user_email=current_user.email,
        role=current_user.role,
        ip_address=client_ip,
        action="UPDATE_PARTICIPANT_DATA",
        entity_type="Participant",
        entity_id=participant.subject_code,
        previous_value=old_state,
        new_value=new_state,
        reason=req.reason_for_change,
        site_id=participant.site_id
    )

    return get_participant_by_id(participant_id, request, current_user, db)


@router.get("/export/csv")
def export_participants_csv(
    request: Request,
    current_user: User = Depends(require_role(["Doctor / Investigator", "Research Coordinator", "PV Officer", "Auditor / Regulator"])),
    db: Session = Depends(get_db)
):
    """
    Exports clinical data:
    - Strictly pseudonymous (Subject Code only, NEVER names or unmasked contact details).
    - Protects against CSV formula injection (OWASP CSV Injection).
    - Cryptographically logs export action.
    """
    client_ip = request.client.host if request.client else "127.0.0.1"
    query = db.query(Participant)
    if current_user.role == "Research Coordinator":
        query = query.filter(Participant.site_id == current_user.site_id)

    participants = query.all()

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "SubjectCode", "SiteID", "Age", "Gender", "IsMinor", "DominantPrakriti",
        "Vata", "Pitta", "Kapha", "AyurvedicDiagnosis", "ModernDiagnosis",
        "Enrolled", "Dosed", "DataStatus", "RetentionUntil"
    ])

    for p in participants:
        writer.writerow([
            sanitize_csv_cell(p.subject_code),
            sanitize_csv_cell(p.site_id),
            p.age,
            p.gender,
            p.is_minor,
            sanitize_csv_cell(p.dominant_prakriti),
            p.prakriti_vata,
            p.prakriti_pitta,
            p.prakriti_kapha,
            sanitize_csv_cell(p.ayurvedic_diagnosis),
            sanitize_csv_cell(p.modern_diagnosis),
            p.is_enrolled,
            p.is_dosed,
            sanitize_csv_cell(p.data_status),
            p.retention_until.isoformat() if p.retention_until else ""
        ])

    log_audit_event(
        db=db,
        user_id=current_user.id,
        user_email=current_user.email,
        role=current_user.role,
        ip_address=client_ip,
        action="BULK_EXPORT_CSV",
        entity_type="Participant",
        entity_id=f"count={len(participants)}",
        reason="Clinical trial export requested with pseudonymous identifiers.",
        site_id=current_user.site_id
    )

    output.seek(0)
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename=ayurctms_export_{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}.csv"}
    )
