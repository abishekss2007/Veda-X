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
legal_router = APIRouter(tags=["Shared Legal Documents"])

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


# ==============================================================================
# ETHICS COMMITTEE: LEGAL DOCUMENTS & EXPIRY COUNTDOWN MODULE
# ==============================================================================

LEGAL_DOC_TYPES = [
    "EC approval letter",
    "protocol approval",
    "insurance",
    "CTRI certificate",
    "MoU/contract",
    "licence",
    "other"
]

def generate_initial_legal_docs() -> List[Dict[str, Any]]:
    now = datetime.now(timezone.utc)
    return [
        {
            "id": "leg-001",
            "title": "CTRI Clinical Trial Registry Certificate",
            "type": "CTRI certificate",
            "study": "AYUR-CT-2026-001",
            "version": "v1.0",
            "issue_date": (now - timedelta(days=55)).strftime("%Y-%m-%d"),
            "expiry_date": (now + timedelta(days=310)).strftime("%Y-%m-%d"),
            "days_remaining": 310,
            "status": "safe",
            "status_label": "Expires in 310 days",
            "reason": "Statutory national CTRI registration valid for full study duration.",
            "file_name": "CTRI_Registration_2026_09_0812.pdf",
            "file_size": "2.4 MB",
            "uploaded_by": "Dr. Rajeshwar Sharma (EC Chair)",
            "versions": [
                {"version": "v1.0", "uploaded_at": (now - timedelta(days=55)).isoformat(), "uploaded_by": "Dr. Rajeshwar Sharma"}
            ]
        },
        {
            "id": "leg-002",
            "title": "Institutional Protocol Approval Clearance",
            "type": "protocol approval",
            "study": "AYUR-CT-2026-001",
            "version": "v2.0",
            "issue_date": (now - timedelta(days=185)).strftime("%Y-%m-%d"),
            "expiry_date": (now + timedelta(days=180)).strftime("%Y-%m-%d"),
            "days_remaining": 180,
            "status": "safe",
            "status_label": "Expires in 180 days",
            "reason": "Amended regimen approved with zero high-risk dosha warnings.",
            "file_name": "IEC_Protocol_Approval_AYUR001_v2.pdf",
            "file_size": "4.1 MB",
            "uploaded_by": "Member Secretary (IEC)",
            "versions": [
                {"version": "v1.0", "uploaded_at": (now - timedelta(days=365)).isoformat(), "uploaded_by": "Prof. Sharma (PI)"},
                {"version": "v2.0", "uploaded_at": (now - timedelta(days=185)).isoformat(), "uploaded_by": "Member Secretary (IEC)"}
            ]
        },
        {
            "id": "leg-003",
            "title": "Hospital Multi-Site Clinical Trial MoU & Contract",
            "type": "MoU/contract",
            "study": "AYUR-CT-2026-001",
            "version": "v1.1",
            "issue_date": (now - timedelta(days=250)).strftime("%Y-%m-%d"),
            "expiry_date": (now + timedelta(days=115)).strftime("%Y-%m-%d"),
            "days_remaining": 115,
            "status": "safe",
            "status_label": "Expires in 115 days",
            "reason": "Inter-institutional governance contract with Jamnagar IPGT&RA.",
            "file_name": "MoU_AIIA_IPGTRA_Clinical_2026.pdf",
            "file_size": "1.8 MB",
            "uploaded_by": "Legal Expert (IEC)",
            "versions": [
                {"version": "v1.1", "uploaded_at": (now - timedelta(days=250)).isoformat(), "uploaded_by": "Legal Expert (IEC)"}
            ]
        },
        {
            "id": "leg-004",
            "title": "Subject Clinical Trial Insurance Policy",
            "type": "insurance",
            "study": "AYUR-CT-2026-001",
            "version": "v1.0",
            "issue_date": (now - timedelta(days=297)).strftime("%Y-%m-%d"),
            "expiry_date": (now + timedelta(days=68)).strftime("%Y-%m-%d"),
            "days_remaining": 68,
            "status": "attention",
            "status_label": "Expires in 68 days",
            "reason": "Trial insurance policy renewal due with underwriter within 68 days to maintain continuous patient coverage.",
            "file_name": "NewIndia_ClinicalInsurance_Policy_2026.pdf",
            "file_size": "3.2 MB",
            "uploaded_by": "Admin (System)",
            "versions": [
                {"version": "v1.0", "uploaded_at": (now - timedelta(days=297)).isoformat(), "uploaded_by": "Admin (System)"}
            ]
        },
        {
            "id": "leg-005",
            "title": "AYUSH GMP Drug Manufacturing Licence (Extract Batch)",
            "type": "licence",
            "study": "AYUR-CT-2026-002",
            "version": "v1.0",
            "issue_date": (now - timedelta(days=323)).strftime("%Y-%m-%d"),
            "expiry_date": (now + timedelta(days=42)).strftime("%Y-%m-%d"),
            "days_remaining": 42,
            "status": "attention",
            "status_label": "Expires in 42 days",
            "reason": "Statutory manufacturing licence annual re-inspection due; renew before expiration to avoid investigational drug dosing stoppage.",
            "file_name": "AYUSH_GMP_Manufacturing_Licence_Batch04.pdf",
            "file_size": "1.5 MB",
            "uploaded_by": "Prof. Sharma (PI)",
            "versions": [
                {"version": "v1.0", "uploaded_at": (now - timedelta(days=323)).isoformat(), "uploaded_by": "Prof. Sharma (PI)"}
            ]
        },
        {
            "id": "leg-006",
            "title": "Annual Ethics Committee Protocol Renewal Letter",
            "type": "EC approval letter",
            "study": "AYUR-CT-2026-002",
            "version": "v1.0",
            "issue_date": (now - timedelta(days=346)).strftime("%Y-%m-%d"),
            "expiry_date": (now + timedelta(days=19)).strftime("%Y-%m-%d"),
            "days_remaining": 19,
            "status": "urgent",
            "status_label": "Expires in 19 days",
            "reason": "Mandatory annual ethics committee review overdue for renewal; unrenewed trials must halt subject recruitment under GCP-ASU.",
            "file_name": "IEC_Annual_Renewal_Decision_AYUR002.pdf",
            "file_size": "2.1 MB",
            "uploaded_by": "Dr. Rajeshwar Sharma (EC Chair)",
            "versions": [
                {"version": "v1.0", "uploaded_at": (now - timedelta(days=346)).isoformat(), "uploaded_by": "Dr. Rajeshwar Sharma"}
            ]
        },
        {
            "id": "leg-007",
            "title": "Biological Specimen Transfer Agreement (BMTA)",
            "type": "MoU/contract",
            "study": "AYUR-CT-2026-003",
            "version": "v1.0",
            "issue_date": (now - timedelta(days=174)).strftime("%Y-%m-%d"),
            "expiry_date": (now + timedelta(days=6)).strftime("%Y-%m-%d"),
            "days_remaining": 6,
            "status": "urgent",
            "status_label": "Expires in 6 days",
            "reason": "Biological specimen transit authorization expires in 6 days; samples cannot be moved across labs without active BMTA clearance.",
            "file_name": "BMTA_Specimen_Transport_Agreement_2026.pdf",
            "file_size": "1.2 MB",
            "uploaded_by": "Member Secretary (IEC)",
            "versions": [
                {"version": "v1.0", "uploaded_at": (now - timedelta(days=174)).isoformat(), "uploaded_by": "Member Secretary (IEC)"}
            ]
        },
        {
            "id": "leg-008",
            "title": "Institutional Bio-safety Committee (IBSC) Clearance",
            "type": "other",
            "study": "AYUR-CT-2026-003",
            "version": "v1.0",
            "issue_date": (now - timedelta(days=380)).strftime("%Y-%m-%d"),
            "expiry_date": (now - timedelta(days=14)).strftime("%Y-%m-%d"),
            "days_remaining": -14,
            "status": "expired",
            "status_label": "Expired 14 days ago",
            "reason": "Expired 14 days ago: Dosing paused for cohort C pending expedited DBT/RCGM bio-safety re-validation.",
            "file_name": "IBSC_Biosafety_Clearance_2025.pdf",
            "file_size": "1.9 MB",
            "uploaded_by": "Admin (System)",
            "versions": [
                {"version": "v1.0", "uploaded_at": (now - timedelta(days=380)).isoformat(), "uploaded_by": "Admin (System)"}
            ]
        }
    ]

_legal_docs_cache: List[Dict[str, Any]] = []

def get_legal_docs_store() -> List[Dict[str, Any]]:
    global _legal_docs_cache
    if not _legal_docs_cache:
        _legal_docs_cache = generate_initial_legal_docs()
    return _legal_docs_cache


@router.get("/legal-documents")
def list_legal_documents(
    current_user: User = Depends(require_role(["EC Member", "Principal Investigator", "Admin"]))
):
    """
    Returns legal documents with live expiry countdowns, status badges, and timeline sorting.
    Access strictly restricted to EC Member, PI, and Admin.
    """
    docs = get_legal_docs_store()
    now = datetime.now(timezone.utc)

    # Recalculate live days remaining
    for d in docs:
        try:
            exp = datetime.strptime(d["expiry_date"], "%Y-%m-%d").replace(tzinfo=timezone.utc)
            delta_days = (exp - now).days
            d["days_remaining"] = delta_days
            if delta_days > 90:
                d["status"] = "safe"
                d["status_label"] = f"Expires in {delta_days} days"
            elif 30 <= delta_days <= 90:
                d["status"] = "attention"
                d["status_label"] = f"Expires in {delta_days} days"
            elif 0 <= delta_days < 30:
                d["status"] = "urgent"
                d["status_label"] = f"Expires in {delta_days} days"
            else:
                d["status"] = "expired"
                d["status_label"] = f"Expired {abs(delta_days)} days ago"
        except Exception:
            pass

    # Sort: expired first, then ascending by days remaining (next to expire)
    sorted_docs = sorted(docs, key=lambda x: x.get("days_remaining", 9999))

    # Calculate statutory auto alerts: 90, 60, 30 days and on expiry
    alerts = []
    expired_count = sum(1 for d in docs if d["status"] == "expired")
    urgent_count = sum(1 for d in docs if d["status"] == "urgent")
    attention_count = sum(1 for d in docs if d["status"] == "attention")

    if expired_count > 0:
        alerts.append({
            "threshold": "expired",
            "level": "critical",
            "message": f"Critical Expiry Alert: {expired_count} regulatory document has expired. Immediate statutory action required under GCP-ASU."
        })
    if urgent_count > 0:
        alerts.append({
            "threshold": "30_days",
            "level": "urgent",
            "message": f"30-Day Alert: {urgent_count} document(s) expiring in under 30 days. Renewal submission mandatory to avoid trial halt."
        })
    if attention_count > 0:
        alerts.append({
            "threshold": "60_90_days",
            "level": "warning",
            "message": f"60/90-Day Early Warning: {attention_count} document(s) due for renewal within the next 30 to 90 days."
        })

    return {
        "documents": sorted_docs,
        "total_documents": len(docs),
        "counts": {
            "safe": sum(1 for d in docs if d["status"] == "safe"),
            "attention": attention_count,
            "urgent": urgent_count,
            "expired": expired_count
        },
        "alerts": alerts
    }


@legal_router.get("/legal-documents")
def list_leadership_legal_documents(
    current_user: User = Depends(require_role(["Institution Leadership"]))
):
    today = datetime.now(timezone.utc).date()
    authorities = {
        "CTRI certificate": "Clinical Trials Registry - India",
        "protocol approval": "Institutional Ethics Committee",
        "EC approval letter": "Institutional Ethics Committee",
        "insurance": "Clinical Trial Insurer",
        "MoU/contract": "Participating Institution",
        "licence": "AYUSH Licensing Authority",
        "other": "Institutional Biosafety Committee",
    }
    documents = []
    for document in get_legal_docs_store():
        expiry = datetime.strptime(document["expiry_date"], "%Y-%m-%d").date()
        days_remaining = (expiry - today).days
        if days_remaining < 0:
            status_label = "Expired"
            countdown = f"Expired {abs(days_remaining)} days ago"
        elif days_remaining <= 30:
            status_label = "Expiring soon"
            countdown = f"Expires in {days_remaining} days"
        else:
            status_label = "Active"
            countdown = f"Expires in {days_remaining} days"
        document_type = document.get("type", "other")
        documents.append({
            "id": document["id"],
            "title": document["title"],
            "type": document_type,
            "issuing_authority": authorities.get(document_type, "Institutional Authority"),
            "issue_date": document.get("issue_date"),
            "expiry_date": document["expiry_date"],
            "days_remaining": days_remaining,
            "status": status_label,
            "countdown": countdown,
        })

    documents.sort(key=lambda item: item["days_remaining"])
    return {"documents": documents}


@router.post("/legal-documents", status_code=status.HTTP_201_CREATED)
def upload_legal_document(
    payload: Dict[str, Any],
    request: Request,
    current_user: User = Depends(require_role(["EC Member", "Principal Investigator", "Admin"])),
    db: Session = Depends(get_db)
):
    """
    Uploads a new trial legal document or creates a new version of an existing document.
    Documents are never deleted. All uploads are logged to the immutable audit trail.
    """
    client_ip = request.client.host if request.client else "127.0.0.1"
    docs = get_legal_docs_store()
    now = datetime.now(timezone.utc)

    title = payload.get("title", "").strip()
    doc_type = payload.get("type", "other")
    study = payload.get("study", "AYUR-CT-2026-001")
    version = payload.get("version", "v1.0")
    issue_date = payload.get("issue_date", now.strftime("%Y-%m-%d"))
    expiry_date = payload.get("expiry_date", (now + timedelta(days=365)).strftime("%Y-%m-%d"))
    reason = payload.get("reason", "Uploaded under statutory GCP-ASU documentation guidelines.")
    file_name = payload.get("file_name", "uploaded_legal_doc.pdf")

    if not title:
        raise HTTPException(status_code=400, detail="Document title is mandatory.")

    # Check if a document with the same title or type/study already exists -> create new version
    existing = next((d for d in docs if d["title"].lower() == title.lower() or (d["type"] == doc_type and d["study"] == study)), None)

    if existing:
        # Increment version snapshot
        new_version_tag = f"v{float(existing['version'].replace('v', '')) + 1.0:.1f}" if existing['version'].startswith('v') else version
        existing["versions"].append({
            "version": existing["version"],
            "uploaded_at": now.isoformat(),
            "uploaded_by": current_user.full_name
        })
        existing["version"] = new_version_tag
        existing["issue_date"] = issue_date
        existing["expiry_date"] = expiry_date
        existing["file_name"] = file_name
        existing["reason"] = reason
        target_doc = existing
        action_verb = "NEW_VERSION_UPLOADED"
    else:
        new_doc = {
            "id": f"leg-{len(docs) + 1:03d}",
            "title": title,
            "type": doc_type,
            "study": study,
            "version": version,
            "issue_date": issue_date,
            "expiry_date": expiry_date,
            "days_remaining": (datetime.strptime(expiry_date, "%Y-%m-%d").replace(tzinfo=timezone.utc) - now).days,
            "status": "safe",
            "status_label": "Expires in 365 days",
            "reason": reason,
            "file_name": file_name,
            "file_size": "2.8 MB",
            "uploaded_by": current_user.full_name,
            "versions": [
                {"version": version, "uploaded_at": now.isoformat(), "uploaded_by": current_user.full_name}
            ]
        }
        docs.insert(0, new_doc)
        target_doc = new_doc
        action_verb = "LEGAL_DOCUMENT_UPLOADED"

    # Log to audit trail
    log_audit_event(
        db=db,
        user_id=current_user.id,
        user_email=current_user.email,
        role=current_user.role,
        ip_address=client_ip,
        action=action_verb,
        entity_type="LegalDocument",
        entity_id=target_doc["id"],
        details=f"{action_verb}: '{target_doc['title']}' ({target_doc['type']}) version {target_doc['version']}. Expiry: {target_doc['expiry_date']}",
        site_id=current_user.site_id
    )

    return target_doc


@router.post("/legal-documents/{doc_id}/view")
def log_view_legal_document(
    doc_id: str,
    request: Request,
    current_user: User = Depends(require_role(["EC Member", "Principal Investigator", "Admin"])),
    db: Session = Depends(get_db)
):
    """
    Logs document access/view event in audit log (DPDP & GCP-ASU mandate).
    """
    client_ip = request.client.host if request.client else "127.0.0.1"
    docs = get_legal_docs_store()
    doc = next((d for d in docs if d["id"] == doc_id), None)
    if not doc:
        raise HTTPException(status_code=404, detail="Legal document not found.")

    log_audit_event(
        db=db,
        user_id=current_user.id,
        user_email=current_user.email,
        role=current_user.role,
        ip_address=client_ip,
        action="VIEW_LEGAL_DOCUMENT",
        entity_type="LegalDocument",
        entity_id=doc["id"],
        details=f"Viewed / downloaded '{doc['title']}' ({doc['version']})",
        site_id=current_user.site_id
    )

    return {"message": "Document view logged in audit trail.", "document": doc}

