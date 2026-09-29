from datetime import datetime, timezone
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.orm import Session

from ..db.database import get_db
from ..db.models import InvestigationalProduct, DispensingLog, Participant, InformedConsent, User
from ..schemas.schemas import (
    InvestigationalProductCreate, DispenseRequest, LabelPreviewOut
)
from ..core.audit import log_audit_event
from .deps import get_current_user, require_role, verify_site_access

router = APIRouter(prefix="/investigational-products", tags=["GCP-ASU Investigational Product Tracking"])

@router.get("", response_model=List[dict])
def list_products(db: Session = Depends(get_db)):
    """Lists registered investigational ASU drug batches with Ayurvedic parameters."""
    products = db.query(InvestigationalProduct).all()
    return [
        {
            "id": p.id,
            "study_code": p.study_code,
            "batch_number": p.batch_number,
            "formulation_name": p.formulation_name,
            "dosage_form": p.dosage_form,
            "anupana": p.anupana,
            "desh": p.desh,
            "kala": p.kala,
            "pathya": p.pathya,
            "apathya": p.apathya,
            "storage_temperature": p.storage_temperature,
            "storage_humidity": p.storage_humidity,
            "special_instructions": p.special_instructions,
            "expiry_date": p.expiry_date,
            "institution_name": p.institution_name,
            "investigator_contact": p.investigator_contact
        }
        for p in products
    ]


@router.post("", status_code=status.HTTP_201_CREATED)
def create_product(
    req: InvestigationalProductCreate,
    request: Request,
    current_user: User = Depends(require_role(["Doctor / Investigator", "Admin"])),
    db: Session = Depends(get_db)
):
    """Registers a new investigational ASU drug formulation and batch."""
    client_ip = request.client.host if request.client else "127.0.0.1"

    existing = db.query(InvestigationalProduct).filter(InvestigationalProduct.batch_number == req.batch_number).first()
    if existing:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Batch number already registered.")

    product = InvestigationalProduct(
        study_code=req.study_code,
        batch_number=req.batch_number,
        formulation_name=req.formulation_name,
        dosage_form=req.dosage_form,
        anupana=req.anupana,
        desh=req.desh,
        kala=req.kala,
        pathya=req.pathya,
        apathya=req.apathya,
        storage_temperature=req.storage_temperature,
        storage_humidity=req.storage_humidity,
        special_instructions=req.special_instructions,
        expiry_date=req.expiry_date,
        investigator_contact=req.investigator_contact,
        institution_name=req.institution_name
    )
    db.add(product)
    db.commit()
    db.refresh(product)

    log_audit_event(
        db=db,
        user_id=current_user.id,
        user_email=current_user.email,
        role=current_user.role,
        ip_address=client_ip,
        action="REGISTER_INVESTIGATIONAL_PRODUCT",
        entity_type="InvestigationalProduct",
        entity_id=product.batch_number,
        new_value=f"Formulation={product.formulation_name}, Dosage={product.dosage_form}",
        site_id=current_user.site_id
    )

    return {"message": "Investigational Product batch registered successfully.", "id": product.id}


@router.post("/dispense")
def dispense_product(
    req: DispenseRequest,
    request: Request,
    current_user: User = Depends(require_role(["Doctor / Investigator", "Research Coordinator"])),
    db: Session = Depends(get_db)
):
    """
    Dispensing Log Gate (GCP-ASU Mandatory):
    - NO participant can be dosed without valid written consent on file!
    - Checks that participant is enrolled and has active, non-withdrawn consent.
    - Sets participant `is_dosed = True`.
    """
    client_ip = request.client.host if request.client else "127.0.0.1"
    participant = verify_site_access(req.participant_id, current_user, db, request)

    # 1. Enforce GCP-ASU Enrolment & Consent Gate
    active_consent = db.query(InformedConsent).filter(
        InformedConsent.participant_id == participant.id,
        InformedConsent.status == "active",
        InformedConsent.requires_reconsent == False
    ).first()

    if not participant.is_enrolled or not active_consent:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="GCP-ASU Regulatory Gate Violation: No participant can be enrolled or dosed without valid written consent on file."
        )

    product = db.query(InvestigationalProduct).filter(InvestigationalProduct.id == req.ip_id).first()
    if not product:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Investigational product batch not found.")

    dispense = DispensingLog(
        ip_id=product.id,
        participant_id=participant.id,
        dispensed_by_id=current_user.id,
        quantity=req.quantity,
        unit=req.unit,
        dispensed_at=datetime.now(timezone.utc),
        notes=req.notes
    )
    db.add(dispense)
    
    # Mark dosed
    participant.is_dosed = True
    db.commit()

    log_audit_event(
        db=db,
        user_id=current_user.id,
        user_email=current_user.email,
        role=current_user.role,
        ip_address=client_ip,
        action="DISPENSE_INVESTIGATIONAL_PRODUCT",
        entity_type="DispensingLog",
        entity_id=str(dispense.id),
        new_value=f"Product={product.formulation_name}, Batch={product.batch_number}, Qty={req.quantity} {req.unit}",
        site_id=participant.site_id
    )

    return {
        "message": "Investigational product dispensed and logged.",
        "dispense_id": dispense.id,
        "subject_code": participant.subject_code,
        "quantity": req.quantity,
        "is_dosed": participant.is_dosed
    }


@router.get("/label-preview/{product_id}/{participant_id}", response_model=LabelPreviewOut)
def generate_label_preview(
    product_id: int,
    participant_id: int,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    GCP-ASU Label Preview Generator:
    - Mandatory text: 'For Clinical Studies only'
    - Study code
    - Investigator contact
    - Institution name
    - Participant ID (e.g. SUB-AIIA-001-042)
    - STRICTLY NEVER contains the participant's name!
    """
    participant = verify_site_access(participant_id, current_user, db, request)
    product = db.query(InvestigationalProduct).filter(InvestigationalProduct.id == product_id).first()
    if not product:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Investigational product not found.")

    return LabelPreviewOut(
        trial_legend="For Clinical Studies only",
        study_code=product.study_code,
        batch_number=product.batch_number,
        formulation_name=product.formulation_name,
        dosage_form=product.dosage_form.capitalize(),
        participant_subject_code=participant.subject_code, # NEVER patient name
        institution_name=product.institution_name,
        investigator_contact=product.investigator_contact,
        storage_instructions=f"{product.storage_temperature}. {product.storage_humidity}",
        anupana=product.anupana,
        kala=product.kala,
        dispensed_date=datetime.now(timezone.utc).strftime("%d-%b-%Y")
    )
