import hashlib
import json
from datetime import datetime, timezone
from typing import Optional, Dict, Any, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import desc

GENESIS_HASH = "0000000000000000000000000000000000000000000000000000000000000000"

def compute_entry_hash(
    prev_hash: str,
    timestamp_iso: str,
    user_id: Optional[int],
    role: str,
    ip_address: str,
    action: str,
    entity_type: str,
    entity_id: Optional[str],
    previous_value: Optional[str],
    new_value: Optional[str],
    reason: Optional[str]
) -> str:
    """
    Computes a cryptographic SHA-256 digest binding all audit fields to the previous hash.
    Any tampering with any historical row breaks the subsequent hashes in the chain.
    """
    canonical_payload = (
        f"{prev_hash}|"
        f"{timestamp_iso}|"
        f"{user_id or ''}|"
        f"{role}|"
        f"{ip_address}|"
        f"{action}|"
        f"{entity_type}|"
        f"{entity_id or ''}|"
        f"{previous_value or ''}|"
        f"{new_value or ''}|"
        f"{reason or ''}"
    )
    return hashlib.sha256(canonical_payload.encode("utf-8")).hexdigest()


def log_audit_event(
    db: Session,
    user_id: Optional[int],
    user_email: str,
    role: str,
    ip_address: str,
    action: str,
    entity_type: str,
    entity_id: Optional[str] = None,
    previous_value: Optional[str] = None,
    new_value: Optional[str] = None,
    reason: Optional[str] = None,
    details: Optional[str] = None,
    site_id: Optional[str] = None
):
    """
    Appends a new cryptographically chained record to the immutable audit ledger.
    """
    from ..db.models import AuditLogEntry

    effective_reason = reason or details

    # Retrieve the latest entry to get its current_hash and entry index
    last_entry = db.query(AuditLogEntry).order_by(desc(AuditLogEntry.id)).first()
    if last_entry is None:
        prev_hash = GENESIS_HASH
        entry_index = 1
    else:
        prev_hash = last_entry.current_hash
        entry_index = last_entry.entry_index + 1

    now_iso = datetime.now(timezone.utc).isoformat()
    curr_hash = compute_entry_hash(
        prev_hash=prev_hash,
        timestamp_iso=now_iso,
        user_id=user_id,
        role=role,
        ip_address=ip_address,
        action=action,
        entity_type=entity_type,
        entity_id=str(entity_id) if entity_id is not None else None,
        previous_value=previous_value,
        new_value=new_value,
        reason=effective_reason
    )

    entry = AuditLogEntry(
        entry_index=entry_index,
        timestamp=now_iso,
        user_id=user_id,
        user_email=user_email,
        role=role,
        site_id=site_id,
        ip_address=ip_address,
        action=action,
        entity_type=entity_type,
        entity_id=str(entity_id) if entity_id is not None else None,
        previous_value=previous_value,
        new_value=new_value,
        reason=effective_reason,
        prev_hash=prev_hash,
        current_hash=curr_hash
    )
    db.add(entry)
    db.commit()
    db.refresh(entry)
    return entry


def verify_audit_chain(db: Session) -> Dict[str, Any]:
    """
    Examines every single audit log record from index 1 to N,
    re-computing the hash from row fields and comparing against current_hash
    and comparing prev_hash against the previous row's current_hash.
    Pinpoints the EXACT index if tampering has occurred.
    """
    from ..db.models import AuditLogEntry
    entries = db.query(AuditLogEntry).order_by(AuditLogEntry.entry_index.asc()).all()

    if not entries:
        return {
            "valid": True,
            "total_records": 0,
            "broken_at_index": None,
            "message": "Audit chain empty. Genesis state intact."
        }

    expected_prev_hash = GENESIS_HASH

    for idx, row in enumerate(entries):
        # 1. Verify link to previous entry
        if row.prev_hash != expected_prev_hash:
            return {
                "valid": False,
                "total_records": len(entries),
                "broken_at_index": row.entry_index,
                "tampered_row_id": row.id,
                "action": row.action,
                "expected_prev_hash": expected_prev_hash,
                "actual_prev_hash": row.prev_hash,
                "message": f"Cryptographic link broken at Entry #{row.entry_index}. Previous hash mismatch."
            }

        # 2. Re-compute hash of this row's content
        recomputed_hash = compute_entry_hash(
            prev_hash=row.prev_hash,
            timestamp_iso=row.timestamp,
            user_id=row.user_id,
            role=row.role,
            ip_address=row.ip_address,
            action=row.action,
            entity_type=row.entity_type,
            entity_id=row.entity_id,
            previous_value=row.previous_value,
            new_value=row.new_value,
            reason=row.reason
        )

        if recomputed_hash != row.current_hash:
            return {
                "valid": False,
                "total_records": len(entries),
                "broken_at_index": row.entry_index,
                "tampered_row_id": row.id,
                "action": row.action,
                "expected_hash": recomputed_hash,
                "actual_hash": row.current_hash,
                "message": f"Data integrity violation at Entry #{row.entry_index}. Content was altered after signing."
            }

        expected_prev_hash = row.current_hash

    return {
        "valid": True,
        "total_records": len(entries),
        "broken_at_index": None,
        "head_hash": expected_prev_hash,
        "message": f"Chain verified successfully. All {len(entries)} audit entries cryptographically authenticated."
    }
