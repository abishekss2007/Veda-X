import uuid
from typing import Optional, List, Dict, Any
from datetime import datetime, timezone, timedelta
from fastapi import APIRouter, Depends, HTTPException, status, Request
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from ..core.audit import log_audit_event
from ..db.database import get_db
from ..db.models import User
from .deps import get_current_user, require_role

router = APIRouter(prefix="/escalations", tags=["Escalations & Superior Reporting"])

# ==============================================================================
# SYNTHETIC SEED DATA: 15 Sample Escalations across all roles, categories, and urgencies
# ==============================================================================
_synthetic_escalations: List[Dict[str, Any]] = [
    {
        "id": "esc-101",
        "from_user": "usr-doc-01",
        "from_name": "Dr. Arvind Joshi",
        "from_role": "Doctor / Investigator",
        "study_id": "AYUR-CT-2026-001",
        "site_id": "SITE-01",
        "subject_code": "SUB-AIIA-001-042",
        "category": "Safety",
        "urgency": "Critical",
        "summary": "Suspected Severe Pitta-Kopa Reaction (SAE) with hepatic enzyme elevation",
        "details": "Subject developed high fever, severe urticaria and ALT/AST > 3x ULN after 7 days of formulation batch B-9021. Dosing paused immediately.",
        "attachment_url": "lab_reports_sub_042.pdf",
        "status": "Sent",
        "created_at": (datetime.now(timezone.utc) - timedelta(minutes=42)).isoformat(),
        "acknowledged_by": None,
        "acknowledged_at": None,
        "assigned_to": None,
        "resolved_at": None,
        "resolution_notes": None,
        "events": [
            {
                "id": "ev-1",
                "event_type": "created",
                "actor_name": "Dr. Arvind Joshi",
                "actor_role": "Doctor / Investigator",
                "message": "Report created with Critical urgency. Auto-forwarded to PI, Admin, PV Officer, and EC.",
                "created_at": (datetime.now(timezone.utc) - timedelta(minutes=42)).isoformat()
            }
        ]
    },
    {
        "id": "esc-102",
        "from_user": "usr-coord-01",
        "from_name": "Dr. Sunita Patel",
        "from_role": "Research Coordinator",
        "study_id": "AYUR-CT-2026-001",
        "site_id": "SITE-01",
        "subject_code": "SUB-AIIA-001-018",
        "category": "Consent",
        "urgency": "High",
        "summary": "Language re-consent pending following protocol amendment V2.1",
        "details": "Subject is illiterate; witness signature was completed in Hindi orally but updated translated vernacular sheet required per GCP-ASU Part A.",
        "attachment_url": None,
        "status": "Acknowledged",
        "created_at": (datetime.now(timezone.utc) - timedelta(hours=3, minutes=15)).isoformat(),
        "acknowledged_by": "Prof. Sharma (PI)",
        "acknowledged_at": (datetime.now(timezone.utc) - timedelta(hours=2)).isoformat(),
        "assigned_to": "Dr. Sunita Patel",
        "resolved_at": None,
        "resolution_notes": None,
        "events": [
            {
                "id": "ev-2",
                "event_type": "created",
                "actor_name": "Dr. Sunita Patel",
                "actor_role": "Research Coordinator",
                "message": "Report created.",
                "created_at": (datetime.now(timezone.utc) - timedelta(hours=3, minutes=15)).isoformat()
            },
            {
                "id": "ev-3",
                "event_type": "acknowledged",
                "actor_name": "Prof. Sharma",
                "actor_role": "Principal Investigator",
                "message": "Acknowledged. Please administer regional script with impartial witness prior to next dispensing.",
                "created_at": (datetime.now(timezone.utc) - timedelta(hours=2)).isoformat()
            }
        ]
    },
    {
        "id": "esc-103",
        "from_user": "usr-mon-01",
        "from_name": "Vikram Verma",
        "from_role": "Monitor",
        "study_id": "AYUR-CT-2026-001",
        "site_id": "SITE-01",
        "subject_code": "SUB-AIIA-001-009",
        "category": "Protocol deviation",
        "urgency": "High",
        "summary": "Source data discrepancy in Prakriti score card vs CRF entry",
        "details": "Discrepancy noted during SDV visit: Vata sub-score recorded as 52 on physical case sheet but entered as 42 on electronic CRF.",
        "attachment_url": None,
        "status": "In progress",
        "created_at": (datetime.now(timezone.utc) - timedelta(hours=14)).isoformat(),
        "acknowledged_by": "Prof. Sharma (PI)",
        "acknowledged_at": (datetime.now(timezone.utc) - timedelta(hours=12)).isoformat(),
        "assigned_to": "Dr. Arvind Joshi",
        "resolved_at": None,
        "resolution_notes": None,
        "events": [
            {
                "id": "ev-4",
                "event_type": "created",
                "actor_name": "Vikram Verma",
                "actor_role": "Monitor",
                "message": "SDV discrepancy flagged.",
                "created_at": (datetime.now(timezone.utc) - timedelta(hours=14)).isoformat()
            },
            {
                "id": "ev-5",
                "event_type": "assigned",
                "actor_name": "Prof. Sharma",
                "actor_role": "Principal Investigator",
                "message": "Assigned to Dr. Arvind Joshi for source document reconciliation.",
                "created_at": (datetime.now(timezone.utc) - timedelta(hours=12)).isoformat()
            }
        ]
    },
    {
        "id": "esc-104",
        "from_user": "usr-pv-01",
        "from_name": "Dr. Gayatri Devi",
        "from_role": "PV Officer",
        "study_id": "AYUR-CT-2026-001",
        "site_id": "SITE-01",
        "subject_code": None,
        "category": "Safety",
        "urgency": "Critical",
        "summary": "Cluster of mild gastric intolerance (Amlapitta) across 6 subjects in Batch B-9021",
        "details": "Statistical signal detection identified disproportionality score PRR = 3.2 for heartburn symptoms within 30 min of ingestion. Sample sent for chemical batch assay.",
        "attachment_url": "dsmb_safety_signal_01.pdf",
        "status": "Sent",
        "created_at": (datetime.now(timezone.utc) - timedelta(minutes=55)).isoformat(),
        "acknowledged_by": None,
        "acknowledged_at": None,
        "assigned_to": None,
        "resolved_at": None,
        "resolution_notes": None,
        "events": [
            {
                "id": "ev-6",
                "event_type": "created",
                "actor_name": "Dr. Gayatri Devi",
                "actor_role": "PV Officer",
                "message": "Safety signal escalated to PI and Admin. Auto-dispatched copy to EC.",
                "created_at": (datetime.now(timezone.utc) - timedelta(minutes=55)).isoformat()
            }
        ]
    },
    {
        "id": "esc-105",
        "from_user": "usr-ec-01",
        "from_name": "Justice M. K. Narayanan",
        "from_role": "EC Member",
        "study_id": "AYUR-CT-2026-001",
        "site_id": "SITE-01",
        "subject_code": None,
        "category": "Ethics",
        "urgency": "Normal",
        "summary": "Ethics Committee Annual Renewal Approval granted with minor advisory",
        "details": "IEC reviewed protocol progress report. Renewal approved for 12 months. Recommendation to maintain bi-weekly liver function monitoring.",
        "attachment_url": "iec_annual_approval_letter.pdf",
        "status": "Resolved",
        "created_at": (datetime.now(timezone.utc) - timedelta(days=2)).isoformat(),
        "acknowledged_by": "System Administrator",
        "acknowledged_at": (datetime.now(timezone.utc) - timedelta(days=2, hours=-1)).isoformat(),
        "assigned_to": "Prof. Sharma",
        "resolved_at": (datetime.now(timezone.utc) - timedelta(days=1)).isoformat(),
        "resolution_notes": "Advisory noted and included in protocol adherence charter.",
        "events": [
            {
                "id": "ev-7",
                "event_type": "created",
                "actor_name": "Justice M. K. Narayanan",
                "actor_role": "EC Member",
                "message": "Decision communicated.",
                "created_at": (datetime.now(timezone.utc) - timedelta(days=2)).isoformat()
            },
            {
                "id": "ev-8",
                "event_type": "resolved",
                "actor_name": "Prof. Sharma",
                "actor_role": "Principal Investigator",
                "message": "Resolution completed. Protocol compliance confirmed.",
                "created_at": (datetime.now(timezone.utc) - timedelta(days=1)).isoformat()
            }
        ]
    },
    {
        "id": "esc-106",
        "from_user": "usr-aud-01",
        "from_name": "K. R. Sengupta",
        "from_role": "Auditor / Regulator",
        "study_id": "AYUR-CT-2026-002",
        "site_id": "SITE-02",
        "subject_code": None,
        "category": "Data issue",
        "urgency": "High",
        "summary": "Audit observation: NTP sovereign clock synchronization check required for secondary site",
        "details": "SITE-02 server logs show 1.2 second time skew vs time.nic.in. CERT-In Directions require strict sub-second sovereign sync.",
        "attachment_url": None,
        "status": "In progress",
        "created_at": (datetime.now(timezone.utc) - timedelta(hours=18)).isoformat(),
        "acknowledged_by": "System Administrator",
        "acknowledged_at": (datetime.now(timezone.utc) - timedelta(hours=16)).isoformat(),
        "assigned_to": "System Administrator",
        "resolved_at": None,
        "resolution_notes": None,
        "events": [
            {
                "id": "ev-9",
                "event_type": "created",
                "actor_name": "K. R. Sengupta",
                "actor_role": "Auditor / Regulator",
                "message": "Audit finding submitted to Admin and PI.",
                "created_at": (datetime.now(timezone.utc) - timedelta(hours=18)).isoformat()
            }
        ]
    },
    {
        "id": "esc-107",
        "from_user": "usr-lead-01",
        "from_name": "Prof. (Dr.) Tanuja Nesari",
        "from_role": "Institution Leadership",
        "study_id": "AYUR-CT-2026-001",
        "site_id": "SITE-01",
        "subject_code": None,
        "category": "Other",
        "urgency": "Normal",
        "summary": "Instruction: Prepare interim DSMB recruitment summary for Ministry of AYUSH review",
        "details": "Ministry delegation visiting next month. Request aggregated study health metrics, recruitment percentage, and zero-PII portfolio score.",
        "attachment_url": None,
        "status": "Acknowledged",
        "created_at": (datetime.now(timezone.utc) - timedelta(hours=22)).isoformat(),
        "acknowledged_by": "Prof. Sharma (PI)",
        "acknowledged_at": (datetime.now(timezone.utc) - timedelta(hours=20)).isoformat(),
        "assigned_to": "Prof. Sharma",
        "resolved_at": None,
        "resolution_notes": None,
        "events": [
            {
                "id": "ev-10",
                "event_type": "created",
                "actor_name": "Prof. (Dr.) Tanuja Nesari",
                "actor_role": "Institution Leadership",
                "message": "Instruction sent.",
                "created_at": (datetime.now(timezone.utc) - timedelta(hours=22)).isoformat()
            }
        ]
    },
    {
        "id": "esc-108",
        "from_user": "usr-coord-01",
        "from_name": "Dr. Sunita Patel",
        "from_role": "Research Coordinator",
        "study_id": "AYUR-CT-2026-001",
        "site_id": "SITE-01",
        "subject_code": "SUB-AIIA-001-029",
        "category": "Participant",
        "urgency": "Normal",
        "summary": "Subject relocated to adjacent district; tele-consultation visit requested",
        "details": "Subject unable to attend in-person Day 28 visit due to family emergency. Request approval for video assessment of symptom score.",
        "attachment_url": None,
        "status": "Resolved",
        "created_at": (datetime.now(timezone.utc) - timedelta(days=4)).isoformat(),
        "acknowledged_by": "Prof. Sharma (PI)",
        "acknowledged_at": (datetime.now(timezone.utc) - timedelta(days=4, hours=-1)).isoformat(),
        "assigned_to": "Dr. Arvind Joshi",
        "resolved_at": (datetime.now(timezone.utc) - timedelta(days=3)).isoformat(),
        "resolution_notes": "Telephonic GCP-ASU compliant remote review authorized for Visit 4.",
        "events": []
    },
    {
        "id": "esc-109",
        "from_user": "usr-doc-01",
        "from_name": "Dr. Arvind Joshi",
        "from_role": "Doctor / Investigator",
        "study_id": "AYUR-CT-2026-001",
        "site_id": "SITE-01",
        "subject_code": "SUB-AIIA-001-033",
        "category": "Safety",
        "urgency": "High",
        "summary": "Moderate Ushnata (heat sensation) with palpitations following evening dose",
        "details": "Subject experienced flushing and heart rate 104 bpm 45 min after intake. Dose reduced by 50% provisionally pending PI review.",
        "attachment_url": None,
        "status": "Sent",
        "created_at": (datetime.now(timezone.utc) - timedelta(hours=5)).isoformat(),
        "acknowledged_by": None,
        "acknowledged_at": None,
        "assigned_to": None,
        "resolved_at": None,
        "resolution_notes": None,
        "events": []
    },
    {
        "id": "esc-110",
        "from_user": "usr-mon-01",
        "from_name": "Vikram Verma",
        "from_role": "Monitor",
        "study_id": "AYUR-CT-2026-001",
        "site_id": "SITE-01",
        "subject_code": None,
        "category": "Site issue",
        "urgency": "Normal",
        "summary": "Investigational Product pharmacy temperature log calibrated and archived",
        "details": "Quarterly digital thermometer sensor re-calibration completed at Central Pharmacy. Temperatures maintained between 18°C and 24°C.",
        "attachment_url": "calibration_cert_q3.pdf",
        "status": "Resolved",
        "created_at": (datetime.now(timezone.utc) - timedelta(days=5)).isoformat(),
        "acknowledged_by": "System Administrator",
        "acknowledged_at": (datetime.now(timezone.utc) - timedelta(days=5)).isoformat(),
        "assigned_to": None,
        "resolved_at": (datetime.now(timezone.utc) - timedelta(days=5)).isoformat(),
        "resolution_notes": "Calibration certificate filed under Site Master File Section 4.",
        "events": []
    },
    {
        "id": "esc-111",
        "from_user": "usr-coord-01",
        "from_name": "Dr. Sunita Patel",
        "from_role": "Research Coordinator",
        "study_id": "AYUR-CT-2026-002",
        "site_id": "SITE-02",
        "subject_code": "SUB-AIIA-002-014",
        "category": "Consent",
        "urgency": "High",
        "summary": "Subject withdrawal request following family relocation",
        "details": "Subject requested withdrawal from trial AYUR-CT-2026-002 due to interstate migration. End of trial visit scheduled for safety exit assessment.",
        "attachment_url": None,
        "status": "Acknowledged",
        "created_at": (datetime.now(timezone.utc) - timedelta(hours=8)).isoformat(),
        "acknowledged_by": "Prof. Sharma (PI)",
        "acknowledged_at": (datetime.now(timezone.utc) - timedelta(hours=6)).isoformat(),
        "assigned_to": "Dr. Sunita Patel",
        "resolved_at": None,
        "resolution_notes": None,
        "events": []
    },
    {
        "id": "esc-112",
        "from_user": "usr-doc-01",
        "from_name": "Dr. Arvind Joshi",
        "from_role": "Doctor / Investigator",
        "study_id": "AYUR-CT-2026-003",
        "site_id": "SITE-01",
        "subject_code": "SUB-AIIA-003-021",
        "category": "Safety",
        "urgency": "Normal",
        "summary": "Mild tingling sensation (Vata-Kopa) in distal extremities",
        "details": "Subject in Nimba-Haridra cohort reported mild transient numbness. Neurological exam normal. Advised warm water intake.",
        "attachment_url": None,
        "status": "In progress",
        "created_at": (datetime.now(timezone.utc) - timedelta(hours=10)).isoformat(),
        "acknowledged_by": "Dr. Gayatri Devi (PV Officer)",
        "acknowledged_at": (datetime.now(timezone.utc) - timedelta(hours=9)).isoformat(),
        "assigned_to": "Dr. Arvind Joshi",
        "resolved_at": None,
        "resolution_notes": None,
        "events": []
    },
    {
        "id": "esc-113",
        "from_user": "usr-pv-01",
        "from_name": "Dr. Gayatri Devi",
        "from_role": "PV Officer",
        "study_id": "AYUR-CT-2026-004",
        "site_id": "SITE-03",
        "subject_code": "SUB-AIIA-004-008",
        "category": "Safety",
        "urgency": "Critical",
        "summary": "SAE Notification: Acute icterus with bilirubin 4.2 mg/dL requiring hospitalization",
        "details": "Subject admitted with jaundice. Trial medication de-challenged immediately. Suspected idiosyncratic herbal interaction. Expedited 24-hr CDSCO/AYUSH notice prepared.",
        "attachment_url": "sae_hospital_admission_008.pdf",
        "status": "Sent",
        "created_at": (datetime.now(timezone.utc) - timedelta(minutes=25)).isoformat(),
        "acknowledged_by": None,
        "acknowledged_at": None,
        "assigned_to": None,
        "resolved_at": None,
        "resolution_notes": None,
        "events": []
    },
    {
        "id": "esc-114",
        "from_user": "usr-aud-01",
        "from_name": "K. R. Sengupta",
        "from_role": "Auditor / Regulator",
        "study_id": "AYUR-CT-2026-004",
        "site_id": "SITE-03",
        "subject_code": "SUB-AIIA-004-002",
        "category": "Protocol deviation",
        "urgency": "Normal",
        "summary": "Witness signature verification query on informed consent archival copy",
        "details": "Witness relationship to illiterate participant was not specified in the supplementary box. Request written clarification from site coordinator.",
        "attachment_url": None,
        "status": "Acknowledged",
        "created_at": (datetime.now(timezone.utc) - timedelta(days=1, hours=4)).isoformat(),
        "acknowledged_by": "System Administrator",
        "acknowledged_at": (datetime.now(timezone.utc) - timedelta(days=1, hours=2)).isoformat(),
        "assigned_to": "Dr. Sunita Patel",
        "resolved_at": None,
        "resolution_notes": None,
        "events": []
    },
    {
        "id": "esc-115",
        "from_user": "usr-lead-01",
        "from_name": "Prof. (Dr.) Tanuja Nesari",
        "from_role": "Institution Leadership",
        "study_id": "AYUR-CT-2026-005",
        "site_id": "SITE-04",
        "subject_code": None,
        "category": "Site issue",
        "urgency": "Normal",
        "summary": "Authorizing recruitment expansion for Jaipur Site (NIA) in Tamaka Shwasa study",
        "details": "Approval granted to recruit additional 25 participants at NIA Jaipur following fast-track site assessment. Ensure site pharmacy audit is conducted.",
        "attachment_url": "directorate_expansion_memo.pdf",
        "status": "Resolved",
        "created_at": (datetime.now(timezone.utc) - timedelta(days=3)).isoformat(),
        "acknowledged_by": "Prof. Sharma (PI)",
        "acknowledged_at": (datetime.now(timezone.utc) - timedelta(days=3)).isoformat(),
        "assigned_to": "System Administrator",
        "resolved_at": (datetime.now(timezone.utc) - timedelta(days=2)).isoformat(),
        "resolution_notes": "Site capacity expanded on central trial ledger.",
        "events": []
    }
]

# In-memory notifications store
_notifications: List[Dict[str, Any]] = [
    {
        "id": "notif-1",
        "target_role": "Principal Investigator",
        "ref_id": "esc-101",
        "type": "critical_escalation",
        "title": "CRITICAL: Suspected Severe Pitta-Kopa Reaction (SAE)",
        "message": "Dr. Arvind Joshi reported Critical Safety escalation on SUB-AIIA-001-042.",
        "is_read": False,
        "created_at": (datetime.now(timezone.utc) - timedelta(minutes=42)).isoformat()
    },
    {
        "id": "notif-2",
        "target_role": "Admin",
        "ref_id": "esc-101",
        "type": "critical_escalation",
        "title": "CRITICAL: Suspected Severe Pitta-Kopa Reaction (SAE)",
        "message": "Dr. Arvind Joshi reported Critical Safety escalation on SUB-AIIA-001-042.",
        "is_read": False,
        "created_at": (datetime.now(timezone.utc) - timedelta(minutes=42)).isoformat()
    },
    {
        "id": "notif-3",
        "target_role": "PV Officer",
        "ref_id": "esc-101",
        "type": "critical_escalation",
        "title": "SAFETY SIGNAL: Suspected SAE on SUB-AIIA-001-042",
        "message": "Auto-copied to PV Queue per GCP-ASU pharmacovigilance rules.",
        "is_read": False,
        "created_at": (datetime.now(timezone.utc) - timedelta(minutes=42)).isoformat()
    },
    {
        "id": "notif-4",
        "target_role": "EC Member",
        "ref_id": "esc-101",
        "type": "critical_escalation",
        "title": "SAE EXPEDITED NOTICE: SUB-AIIA-001-042",
        "message": "Expedited 24h SAE notice dispatched to Ethics Committee.",
        "is_read": False,
        "created_at": (datetime.now(timezone.utc) - timedelta(minutes=42)).isoformat()
    }
]

# ==============================================================================
# SCHEMAS
# ==============================================================================
class EscalationCreateIn(BaseModel):
    from_user: Optional[str] = "usr-current"
    from_name: str
    from_role: str
    study_id: str = "AYUR-CT-2026-001"
    site_id: str = "SITE-01"
    subject_code: Optional[str] = None
    category: str
    urgency: str = "Normal" # Normal, High, Critical
    summary: str = Field(..., max_length=120)
    details: str
    attachment_name: Optional[str] = None
    attachment_url: Optional[str] = None

class EscalationAcknowledgeIn(BaseModel):
    actor_name: str
    actor_role: str
    notes: Optional[str] = None

class EscalationReplyIn(BaseModel):
    actor_name: str
    actor_role: str
    message: str

class EscalationAssignIn(BaseModel):
    actor_name: str
    actor_role: str
    assign_to: str
    notes: Optional[str] = None

class EscalationResolveIn(BaseModel):
    actor_name: str
    actor_role: str
    resolution_notes: str

# ==============================================================================
# ENDPOINTS
# ==============================================================================

@router.get("")
def list_escalations(
    role: Optional[str] = None,
    user_email: Optional[str] = None,
    status: Optional[str] = None,
    urgency: Optional[str] = None,
    category: Optional[str] = None,
    current_user: User = Depends(get_current_user),
):
    """
    Returns escalations filtered by user role and RLS rules:
    - Admin & PI see all escalations
    - PV Officer sees all Safety/AE/SAE escalations + any self-created
    - EC Member sees all Ethics and Critical escalations + any self-created
    - Other roles see only their own submitted reports
    """
    results = []
    for esc in _synthetic_escalations:
        # RLS Filtering
        if current_user.role in ["Admin", "Principal Investigator"]:
            allow = True
        elif current_user.role == "PV Officer":
            allow = (esc["category"] == "Safety" or "AE" in esc["summary"] or "SAE" in esc["summary"] or esc["from_role"] == "PV Officer")
        elif current_user.role == "EC Member":
            allow = (esc["category"] == "Ethics" or esc["urgency"] == "Critical" or esc["from_role"] == "EC Member")
        else:
            allow = (esc["from_role"] == current_user.role or current_user.email.lower() == esc["from_user"].lower())
        
        if not allow:
            continue

        if status and esc["status"].lower() != status.lower():
            continue
        if urgency and esc["urgency"].lower() != urgency.lower():
            continue
        if category and esc["category"].lower() != category.lower():
            continue

        results.append(esc)

    return sorted(results, key=lambda x: x["created_at"], reverse=True)

@router.post("", status_code=status.HTTP_201_CREATED)
def create_escalation(
    req: EscalationCreateIn,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Creates an escalation report.
    - If Doctor reports AE/SAE, auto-dispatches to PV Officer queue.
    - If Critical or SAE, auto-forwards to EC Member with timestamp.
    - Emits notifications for PI and Admin dashboards.
    """
    now_str = datetime.now(timezone.utc).isoformat()
    esc_id = f"esc-{len(_synthetic_escalations) + 101}"

    if current_user.role in ["Principal Investigator", "Admin"]:
        raise HTTPException(status_code=403, detail="Principal Investigator and Admin are recipients and cannot create escalations.")

    new_esc = {
        "id": esc_id,
        "from_user": current_user.email,
        "from_name": current_user.full_name,
        "from_role": current_user.role,
        "study_id": req.study_id,
        "site_id": current_user.site_id,
        "subject_code": req.subject_code,
        "category": req.category,
        "urgency": req.urgency,
        "summary": req.summary,
        "details": req.details,
        "attachment_name": req.attachment_name,
        "attachment_url": req.attachment_url or req.attachment_name,
        "status": "Sent",
        "created_at": now_str,
        "acknowledged_by": None,
        "acknowledged_at": None,
        "assigned_to": None,
        "resolved_at": None,
        "resolution_notes": None,
        "events": [
            {
                "id": str(uuid.uuid4()),
                "event_type": "created",
                "actor_name": current_user.full_name,
                "actor_role": current_user.role,
                "message": f"Escalation created ({req.urgency} urgency).",
                "created_at": now_str
            }
        ]
    }
    _synthetic_escalations.insert(0, new_esc)

    # 1. Notify PI and Admin
    for target in ["Principal Investigator", "Admin"]:
        _notifications.insert(0, {
            "id": f"notif-{len(_notifications) + 1}",
            "target_role": target,
            "ref_id": esc_id,
            "type": f"{req.urgency.lower()}_escalation",
            "title": f"[{req.urgency.upper()}] {req.category}: {req.summary}",
            "message": f"Reported by {current_user.full_name} ({current_user.role}) on {req.study_id}.",
            "is_read": False,
            "created_at": now_str
        })

    # 2. Rule: Doctor's AE/SAE report is auto-copied to PV Officer queue
    is_safety_event = (req.category == "Safety" or "ae" in req.summary.lower() or "sae" in req.summary.lower())
    if is_safety_event and current_user.role in ["Doctor / Investigator", "Research Coordinator"]:
        _notifications.insert(0, {
            "id": f"notif-{len(_notifications) + 1}",
            "target_role": "PV Officer",
            "ref_id": esc_id,
            "type": "pv_signal",
            "title": f"SAFETY QUEUE: {req.summary}",
            "message": f"Auto-copied from {current_user.role} to Pharmacovigilance review queue.",
            "is_read": False,
            "created_at": now_str
        })
        new_esc["events"].append({
            "id": str(uuid.uuid4()),
            "event_type": "reply",
            "actor_name": "AyurCTMS Safety Router",
            "actor_role": "System",
            "message": "Auto-copied to PV Officer review queue per GCP-ASU standard operating procedure.",
            "created_at": now_str
        })

    # 3. Rule: Confirmed or Critical SAE is auto-sent to EC with sent timestamp
    if req.urgency == "Critical" or "sae" in req.summary.lower():
        _notifications.insert(0, {
            "id": f"notif-{len(_notifications) + 1}",
            "target_role": "EC Member",
            "ref_id": esc_id,
            "type": "ec_expedited",
            "title": f"ETHICS ALERT: Critical Safety Event on {req.study_id}",
            "message": f"Expedited regulatory notice automatically forwarded to Ethics Committee.",
            "is_read": False,
            "created_at": now_str
        })
        new_esc["events"].append({
            "id": str(uuid.uuid4()),
            "event_type": "reply",
            "actor_name": "AyurCTMS Regulatory Router",
            "actor_role": "System",
            "message": f"Expedited notice auto-dispatched to Ethics Committee at {now_str}.",
            "created_at": now_str
        })

    # 4. Audit Log
    log_audit_event(
        db=db,
        user_id=None,
        user_email=current_user.email,
        role=current_user.role,
        ip_address=request.client.host if request.client else "127.0.0.1",
        action="ESCALATION_SUBMITTED",
        entity_type="Escalation",
        entity_id=esc_id,
        details=f"Urgency: {req.urgency}, Category: {req.category}, Summary: '{req.summary[:60]}...'"
    )

    return new_esc

@router.post("/{esc_id}/acknowledge")
def acknowledge_escalation(esc_id: str, req: EscalationAcknowledgeIn, request: Request, current_user: User = Depends(require_role(["Admin", "Principal Investigator"])), db: Session = Depends(get_db)):
    req.actor_name = current_user.full_name
    req.actor_role = current_user.role
    for esc in _synthetic_escalations:
        if esc["id"] == esc_id:
            now_str = datetime.now(timezone.utc).isoformat()
            esc["status"] = "Acknowledged"
            esc["acknowledged_by"] = f"{req.actor_name} ({req.actor_role})"
            esc["acknowledged_at"] = now_str
            msg = f"Acknowledged by {req.actor_name} ({req.actor_role})."
            if req.notes:
                msg += f" Note: {req.notes}"
            esc["events"].append({
                "id": str(uuid.uuid4()),
                "event_type": "acknowledged",
                "actor_name": req.actor_name,
                "actor_role": req.actor_role,
                "message": msg,
                "created_at": now_str
            })
            log_audit_event(
                db=db,
                user_id=None,
                user_email=req.actor_name,
                role=req.actor_role,
                ip_address=request.client.host if request.client else "127.0.0.1",
                action="ESCALATION_ACKNOWLEDGED",
                entity_type="Escalation",
                entity_id=esc_id,
                details=f"Escalation acknowledged by {req.actor_name}."
            )
            return esc
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Escalation not found.")

@router.post("/{esc_id}/reply")
def reply_escalation(esc_id: str, req: EscalationReplyIn, request: Request, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    req.actor_name = current_user.full_name
    req.actor_role = current_user.role
    for esc in _synthetic_escalations:
        if esc["id"] == esc_id:
            now_str = datetime.now(timezone.utc).isoformat()
            esc["events"].append({
                "id": str(uuid.uuid4()),
                "event_type": "reply",
                "actor_name": req.actor_name,
                "actor_role": req.actor_role,
                "message": req.message,
                "created_at": now_str
            })
            log_audit_event(
                db=db,
                user_id=None,
                user_email=req.actor_name,
                role=req.actor_role,
                ip_address=request.client.host if request.client else "127.0.0.1",
                action="ESCALATION_REPLIED",
                entity_type="Escalation",
                entity_id=esc_id,
                details=f"Reply posted by {req.actor_name} ({req.actor_role}): {req.message[:50]}"
            )
            return esc
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Escalation not found.")

@router.post("/{esc_id}/assign")
def assign_escalation(esc_id: str, req: EscalationAssignIn, request: Request, current_user: User = Depends(require_role(["Admin", "Principal Investigator"])), db: Session = Depends(get_db)):
    req.actor_name = current_user.full_name
    req.actor_role = current_user.role
    for esc in _synthetic_escalations:
        if esc["id"] == esc_id:
            now_str = datetime.now(timezone.utc).isoformat()
            esc["assigned_to"] = req.assign_to
            esc["status"] = "In progress"
            msg = f"Assigned to {req.assign_to} by {req.actor_name} ({req.actor_role})."
            if req.notes:
                msg += f" Instructions: {req.notes}"
            esc["events"].append({
                "id": str(uuid.uuid4()),
                "event_type": "assigned",
                "actor_name": req.actor_name,
                "actor_role": req.actor_role,
                "message": msg,
                "created_at": now_str
            })
            log_audit_event(
                db=db,
                user_id=None,
                user_email=req.actor_name,
                role=req.actor_role,
                ip_address=request.client.host if request.client else "127.0.0.1",
                action="ESCALATION_ASSIGNED",
                entity_type="Escalation",
                entity_id=esc_id,
                details=f"Assigned to {req.assign_to}."
            )
            return esc
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Escalation not found.")

@router.post("/{esc_id}/resolve")
def resolve_escalation(esc_id: str, req: EscalationResolveIn, request: Request, current_user: User = Depends(require_role(["Admin", "Principal Investigator"])), db: Session = Depends(get_db)):
    req.actor_name = current_user.full_name
    req.actor_role = current_user.role
    for esc in _synthetic_escalations:
        if esc["id"] == esc_id:
            now_str = datetime.now(timezone.utc).isoformat()
            esc["status"] = "Resolved"
            esc["resolved_at"] = now_str
            esc["resolution_notes"] = req.resolution_notes
            esc["events"].append({
                "id": str(uuid.uuid4()),
                "event_type": "resolved",
                "actor_name": req.actor_name,
                "actor_role": req.actor_role,
                "message": f"Marked as Resolved by {req.actor_name} ({req.actor_role}). Resolution: {req.resolution_notes}",
                "created_at": now_str
            })
            log_audit_event(
                db=db,
                user_id=None,
                user_email=req.actor_name,
                role=req.actor_role,
                ip_address=request.client.host if request.client else "127.0.0.1",
                action="ESCALATION_RESOLVED",
                entity_type="Escalation",
                entity_id=esc_id,
                details=f"Resolved by {req.actor_name}. Notes: {req.resolution_notes[:60]}"
            )
            return esc
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Escalation not found.")

@router.get("/notifications")
def get_notifications(role: Optional[str] = None, current_user: User = Depends(get_current_user)):
    """Returns unread and recent notifications for the specified role."""
    role = current_user.role
    return [
        n for n in _notifications
        if n["target_role"].lower() == role.lower() or (role in ["Admin", "Principal Investigator"] and n["type"].startswith("critical"))
    ]

@router.post("/notifications/{notif_id}/read")
def mark_notification_read(notif_id: str, current_user: User = Depends(get_current_user)):
    for n in _notifications:
        if n["id"] == notif_id and (n["target_role"] == current_user.role or current_user.role in ["Admin", "Principal Investigator"]):
            n["is_read"] = True
            return {"success": True}
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Notification not found.")

# ==============================================================================
# COMPREHENSIVE CLINICAL TRIAL DATASET (6 Studies, 4 Sites, 150 Subject Codes, 60 AEs)
# ==============================================================================

@router.get("/study-data")
def get_study_data(current_user: User = Depends(get_current_user)):
    """Returns rich synthetic clinical datasets powering the 9 role dashboards."""
    studies = [
        {"id": "AYUR-CT-2026-001", "name": "Ashwagandha & Brahmi in Mild Cognitive Impairment", "phase": "Phase II", "target": 50, "enrolled": 42, "saes": 2, "health_score": 96, "sites": 2, "status": "Active", "lead_pi": "Prof. (Dr.) Rajeshwar Sharma"},
        {"id": "AYUR-CT-2026-002", "name": "Yogaraj Guggulu & Dashamula in Amavata (RA)", "phase": "Phase III", "target": 40, "enrolled": 34, "saes": 1, "health_score": 92, "sites": 2, "status": "Active", "lead_pi": "Dr. Sunita Patel"},
        {"id": "AYUR-CT-2026-003", "name": "Nimba & Haridra Extract in Vicharchika (Eczema)", "phase": "Phase II", "target": 30, "enrolled": 26, "saes": 0, "health_score": 95, "sites": 1, "status": "Active", "lead_pi": "Dr. Arvind Joshi"},
        {"id": "AYUR-CT-2026-004", "name": "Guduchi & Shilajit in Madhumeha (Type 2 DM)", "phase": "Phase II", "target": 35, "enrolled": 28, "saes": 3, "health_score": 88, "sites": 2, "status": "Active", "lead_pi": "Prof. (Dr.) Rajeshwar Sharma"},
        {"id": "AYUR-CT-2026-005", "name": "Vasavaleha in Tamaka Shwasa (Bronchial Asthma)", "phase": "Phase I/II", "target": 25, "enrolled": 12, "saes": 1, "health_score": 91, "sites": 1, "status": "Recruiting", "lead_pi": "Dr. Gayatri Devi"},
        {"id": "AYUR-CT-2026-006", "name": "Arjuna & Pushkarmoola in Hridroga (Cardiac Risk)", "phase": "Phase I", "target": 20, "enrolled": 8, "saes": 1, "health_score": 94, "sites": 1, "status": "Recruiting", "lead_pi": "Prof. (Dr.) Rajeshwar Sharma"}
    ]

    sites = [
        {"id": "SITE-01", "name": "All India Institute of Ayurveda (AIIA)", "city": "New Delhi", "enrolled": 68, "target": 75, "sdv_score": 98.4, "open_deviations": 1, "audit_status": "Clean", "coordinator": "Dr. Sunita Patel"},
        {"id": "SITE-02", "name": "IPGT&RA, Gujarat Ayurved University", "city": "Jamnagar", "enrolled": 44, "target": 50, "sdv_score": 95.1, "open_deviations": 2, "audit_status": "Observation Pending", "coordinator": "Dr. Ramesh Nair"},
        {"id": "SITE-03", "name": "Faculty of Ayurveda, IMS-BHU", "city": "Varanasi", "enrolled": 26, "target": 35, "sdv_score": 92.8, "open_deviations": 1, "audit_status": "Clean", "coordinator": "Dr. V. K. Mishra"},
        {"id": "SITE-04", "name": "National Institute of Ayurveda (NIA)", "city": "Jaipur", "enrolled": 12, "target": 25, "sdv_score": 96.0, "open_deviations": 0, "audit_status": "Clean", "coordinator": "Dr. Anita Sharma"}
    ]

    # Generate 150 subject codes across 4 sites
    prakritis = ["Vata-Pitta", "Pitta-Kapha", "Vata-Kapha", "Tridoshaja", "Pitta-Vata"]
    statuses = ["Active", "Active", "Active", "Completed", "Screening", "Withdrawn"]
    participants = []
    
    site_counts = [("SITE-01", 68), ("SITE-02", 44), ("SITE-03", 26), ("SITE-04", 12)]
    idx = 1
    for s_id, count in site_counts:
        study_assigned = "AYUR-CT-2026-001" if s_id == "SITE-01" else ("AYUR-CT-2026-002" if s_id == "SITE-02" else ("AYUR-CT-2026-004" if s_id == "SITE-03" else "AYUR-CT-2026-005"))
        for i in range(1, count + 1):
            sub_code = f"SUB-AIIA-{s_id[-2:]}-{str(i).zfill(3)}"
            participants.append({
                "subject_code": sub_code,
                "study_id": study_assigned,
                "site_id": s_id,
                "prakriti": prakritis[i % len(prakritis)],
                "status": statuses[i % len(statuses)],
                "enrolled_day": 10 + (i % 60),
                "compliance_pct": 88 + (i % 12),
                "visits_completed": (i % 6) + 1,
                "total_visits": 6,
                "adr_count": 1 if (i % 7 == 0) else (2 if (i % 23 == 0) else 0)
            })
            idx += 1

    # 60 Adverse Events (8 SAEs)
    ae_terms = [
        ("Pitta-Kopa (Ushnata / Acid Reflux)", "Mild", "10013946", "Probable", False),
        ("Vata-Kopa (Vibandha / Constipation)", "Mild", "10010774", "Possible", False),
        ("Amlapitta (Gastric Pyrosis)", "Moderate", "10017888", "Probable", False),
        ("Twak-Kandu (Pruritus / Itching)", "Mild", "10037087", "Unlikely", False),
        ("Shiro-Ruka (Cephalea / Headache)", "Mild", "10019211", "Possible", False),
        ("Gourava (Body Heaviness)", "Mild", "10048687", "Probable", False),
        ("Hepatic Enzyme Elevation (ALT/AST > 3x)", "Severe", "10001551", "Probable", True), # SAE 1
        ("Acute Icterus / Bilirubin > 4.0 mg/dL", "Severe", "10023126", "Definite", True), # SAE 2
        ("Severe Bronchospasm requiring ER", "Severe", "10006482", "Unlikely", True), # SAE 3
        ("Syncope following morning dose", "Severe", "10042772", "Possible", True), # SAE 4
        ("Anaphylactoid Skin Eruption", "Severe", "10002198", "Probable", True), # SAE 5
        ("Severe Dehydration secondary to Atisara", "Severe", "10012174", "Possible", True), # SAE 6
        ("Uncontrolled Tachycardia (HR > 130)", "Severe", "10043071", "Probable", True), # SAE 7
        ("Angioedema / Facial Swelling", "Severe", "10002424", "Definite", True) # SAE 8
    ]

    adverse_events = []
    # Add 8 SAEs explicitly
    sae_subjects = ["SUB-AIIA-01-042", "SUB-AIIA-03-008", "SUB-AIIA-04-002", "SUB-AIIA-02-019", "SUB-AIIA-01-011", "SUB-AIIA-03-014", "SUB-AIIA-02-031", "SUB-AIIA-01-055"]
    for j in range(8):
        term, sev, meddra, causal, is_sae = ae_terms[6 + j]
        adverse_events.append({
            "id": f"AE-{str(j + 1).zfill(3)}",
            "subject_code": sae_subjects[j],
            "study_id": "AYUR-CT-2026-001" if j % 2 == 0 else "AYUR-CT-2026-004",
            "asu_term": term,
            "severity": sev,
            "meddra_code": meddra,
            "causality": causal,
            "is_sae": True,
            "reported_date": (datetime.now(timezone.utc) - timedelta(days=j * 3 + 1)).strftime("%Y-%m-%d"),
            "status": "Under Investigation" if j < 3 else "Resolved"
        })

    # Add 52 Non-Serious AEs to reach 60 total
    for k in range(52):
        term, sev, meddra, causal, _ = ae_terms[k % 6]
        sub = participants[(k * 2) % len(participants)]["subject_code"]
        adverse_events.append({
            "id": f"AE-{str(k + 9).zfill(3)}",
            "subject_code": sub,
            "study_id": "AYUR-CT-2026-001" if k % 3 == 0 else ("AYUR-CT-2026-002" if k % 3 == 1 else "AYUR-CT-2026-003"),
            "asu_term": term,
            "severity": sev,
            "meddra_code": meddra,
            "causality": causal,
            "is_sae": False,
            "reported_date": (datetime.now(timezone.utc) - timedelta(days=k + 2)).strftime("%Y-%m-%d"),
            "status": "Monitored / Controlled" if k % 2 == 0 else "Resolved"
        })

    return {
        "studies": studies,
        "sites": sites,
        "total_participants": len(participants),
        "participants": participants,
        "total_aes": len(adverse_events),
        "total_saes": 8,
        "adverse_events": adverse_events
    }

