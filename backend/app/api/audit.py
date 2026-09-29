import csv
import io
from datetime import datetime, timezone
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from ..db.database import get_db
from ..db.models import AuditLogEntry, User
from ..schemas.schemas import AuditLogOut, ChainVerificationOut
from ..core.audit import verify_audit_chain, log_audit_event
from ..core.security import sanitize_csv_cell
from .deps import get_current_user, require_role

router = APIRouter(prefix="/audit", tags=["Tamper-Proof Audit Trail"])

@router.get("/logs", response_model=List[AuditLogOut])
def get_audit_logs(
    limit: int = 100,
    offset: int = 0,
    action: Optional[str] = None,
    current_user: User = Depends(require_role(["Auditor / Regulator", "Admin", "Doctor / Investigator"])),
    db: Session = Depends(get_db)
):
    """
    Retrieves the tamper-proof cryptographic audit trail entries.
    Includes previous SHA-256 hash and current SHA-256 hash for verification.
    """
    query = db.query(AuditLogEntry).order_by(AuditLogEntry.entry_index.desc())
    if action:
        query = query.filter(AuditLogEntry.action == action)
    return query.offset(offset).limit(limit).all()


@router.get("/verify-chain", response_model=ChainVerificationOut)
def run_audit_chain_verification(
    request: Request,
    current_user: User = Depends(require_role(["Auditor / Regulator", "Admin", "Doctor / Investigator"])),
    db: Session = Depends(get_db)
):
    """
    Cryptographic Audit Trail Verification Engine:
    Recalculates every SHA-256 hash link from Genesis (Entry #1) to the latest entry.
    If any row was modified, inserted, or deleted in the database,
    it pinpoints the EXACT row index, tampered row ID, and failure reason.
    """
    client_ip = request.client.host if request.client else "127.0.0.1"
    result = verify_audit_chain(db)

    # Log the verification attempt itself
    log_audit_event(
        db=db,
        user_id=current_user.id,
        user_email=current_user.email,
        role=current_user.role,
        ip_address=client_ip,
        action="VERIFY_AUDIT_CHAIN",
        entity_type="AuditLedger",
        entity_id=f"records={result.get('total_records')}",
        details=f"Verification result: {'PASSED' if result.get('valid') else 'FAILED'}. Broken at: {result.get('broken_at_index')}",
        site_id=current_user.site_id
    )

    return ChainVerificationOut(**result)


@router.post("/tamper-simulate-test")
def simulate_tampering_for_test(
    entry_index: int,
    tampered_value: str,
    request: Request,
    current_user: User = Depends(require_role(["Admin"])),
    db: Session = Depends(get_db)
):
    """
    Test helper endpoint for Automated Security Tests:
    Directly alters a row without updating its SHA-256 cryptographic signature,
    proving that 'Verify Chain' reliably flags the exact tampered entry.
    """
    entry = db.query(AuditLogEntry).filter(AuditLogEntry.entry_index == entry_index).first()
    if not entry:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Entry index not found.")

    entry.action = tampered_value # Alter content
    db.commit()

    return {"message": f"Entry #{entry_index} deliberately altered for tamper-detection verification.", "entry_index": entry_index}


@router.get("/export")
def export_audit_logs_csv(
    request: Request,
    current_user: User = Depends(require_role(["Auditor / Regulator", "Admin"])),
    db: Session = Depends(get_db)
):
    """
    Exports cryptographic audit ledger complying with CERT-In 180-day log export mandate.
    """
    client_ip = request.client.host if request.client else "127.0.0.1"
    entries = db.query(AuditLogEntry).order_by(AuditLogEntry.entry_index.asc()).all()

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "EntryIndex", "TimestampUTC", "UserEmail", "Role", "SiteID",
        "IPAddress", "Action", "EntityType", "EntityID", "PrevHash", "CurrentHash"
    ])

    for e in entries:
        writer.writerow([
            e.entry_index,
            e.timestamp,
            sanitize_csv_cell(e.user_email),
            sanitize_csv_cell(e.role),
            sanitize_csv_cell(e.site_id or ""),
            sanitize_csv_cell(e.ip_address),
            sanitize_csv_cell(e.action),
            sanitize_csv_cell(e.entity_type),
            sanitize_csv_cell(e.entity_id or ""),
            e.prev_hash,
            e.current_hash
        ])

    log_audit_event(
        db=db,
        user_id=current_user.id,
        user_email=current_user.email,
        role=current_user.role,
        ip_address=client_ip,
        action="EXPORT_AUDIT_LOGS_CSV",
        entity_type="AuditLog",
        entity_id=f"count={len(entries)}",
        reason="CERT-In / Regulatory audit ledger export.",
        site_id=current_user.site_id
    )

    output.seek(0)
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename=ayurctms_audit_ledger_{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}.csv"}
    )
