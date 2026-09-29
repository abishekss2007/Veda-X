import os
import uuid
from datetime import datetime, timezone, timedelta
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Request
from sqlalchemy.orm import Session

from ..db.database import get_db
from ..db.models import User
from ..core.security_settings import security_settings
from ..core.security import create_access_token, decode_token
from ..core.audit import log_audit_event
from .deps import get_current_user

router = APIRouter(prefix="/files", tags=["Secure File Storage & Uploads"])

UPLOAD_STORAGE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "storage_bucket"))
os.makedirs(UPLOAD_STORAGE_DIR, exist_ok=True)

def inspect_magic_bytes(header: bytes) -> Optional[str]:
    """
    Inspects true binary file signatures (magic bytes) to prevent disguised executable uploads (OWASP Top 10 A08).
    """
    if header.startswith(b"%PDF"):
        return "application/pdf"
    if header.startswith(b"\xff\xd8\xff"):
        return "image/jpeg"
    if header.startswith(b"\x89PNG\r\n\x1a\n"):
        return "image/png"
    if header.startswith(b"PK\x03\x04"):
        return "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    # Reject Windows Portable Executable (PE) / DOS binaries (MZ header)
    if header.startswith(b"MZ"):
        return "application/x-dosexec"
    # Reject Linux ELF binaries
    if header.startswith(b"\x7fELF"):
        return "application/x-executable"
    return None


@router.post("/upload")
async def upload_file(
    request: Request,
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Secure File Upload Endpoint:
    - Enforces 10 MB maximum size limit.
    - Inspects binary magic bytes, rejecting disguised executables (.exe, .dll, ELF).
    - Renames files to non-guessable random UUIDs.
    - Returns a time-limited 5-minute signed access token link.
    """
    client_ip = request.client.host if request.client else "127.0.0.1"

    # 1. Check extension blacklist
    filename_lower = file.filename.lower()
    for ext in security_settings.FORBIDDEN_FILE_EXTENSIONS:
        if filename_lower.endswith(ext):
            log_audit_event(
                db=db,
                user_id=current_user.id,
                user_email=current_user.email,
                role=current_user.role,
                ip_address=client_ip,
                action="MALICIOUS_FILE_UPLOAD_BLOCKED",
                entity_type="File",
                entity_id=file.filename,
                details=f"Forbidden file extension: {ext}",
                site_id=current_user.site_id
            )
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Security Policy Violation: Executable file uploads are strictly forbidden ({ext})."
            )

    # 2. Read first 512 bytes for Magic Byte Inspection
    header = await file.read(512)
    detected_mime = inspect_magic_bytes(header)

    # Check for executable disguised as image or document (e.g. evil.exe renamed to report.pdf)
    if detected_mime in ["application/x-dosexec", "application/x-executable"]:
        log_audit_event(
            db=db,
            user_id=current_user.id,
            user_email=current_user.email,
            role=current_user.role,
            ip_address=client_ip,
            action="DISGUISED_EXECUTABLE_BLOCKED",
            entity_type="File",
            entity_id=file.filename,
            details=f"Disguised binary header detected: {header[:4].hex()}",
            site_id=current_user.site_id
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Security Policy Violation: Executable binary file signature detected. Upload rejected."
        )

    # 3. Read full content and check size limit (10MB)
    rest_of_file = await file.read()
    total_content = header + rest_of_file
    if len(total_content) > security_settings.MAX_FILE_SIZE_BYTES:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail="File size exceeds maximum permitted limit of 10 MB."
        )

    # 4. Generate random UUID filename
    file_uuid = str(uuid.uuid4())
    _, ext = os.path.splitext(file.filename)
    safe_storage_name = f"{file_uuid}{ext.lower()}"
    target_path = os.path.join(UPLOAD_STORAGE_DIR, safe_storage_name)

    with open(target_path, "wb") as f:
        f.write(total_content)

    # 5. Generate 5-minute signed token for private download
    signed_token = create_access_token(
        {"sub": str(current_user.id), "file_uuid": safe_storage_name, "type": "signed_file_link"},
        expires_delta=timedelta(minutes=5)
    )

    log_audit_event(
        db=db,
        user_id=current_user.id,
        user_email=current_user.email,
        role=current_user.role,
        ip_address=client_ip,
        action="SECURE_FILE_UPLOAD",
        entity_type="File",
        entity_id=safe_storage_name,
        details=f"Original={file.filename}, Size={len(total_content)} bytes",
        site_id=current_user.site_id
    )

    return {
        "message": "File verified and stored in private vault with 5-minute signed access token.",
        "file_uuid": file_uuid,
        "original_filename": file.filename,
        "safe_storage_name": safe_storage_name,
        "size_bytes": len(total_content),
        "signed_download_url": f"/api/files/download/{safe_storage_name}?token={signed_token}",
        "expires_in_minutes": 5
    }


@router.get("/download/{filename}")
def download_file(filename: str, token: str, request: Request, db: Session = Depends(get_db)):
    """Downloads a file via a 5-minute signed link."""
    payload = decode_token(token)
    if payload.get("type") != "signed_file_link" or payload.get("file_uuid") != filename:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Invalid or expired download signature.")

    file_path = os.path.join(UPLOAD_STORAGE_DIR, filename)
    if not os.path.exists(file_path):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="File not found in private storage.")

    from fastapi.responses import FileResponse
    return FileResponse(file_path)
