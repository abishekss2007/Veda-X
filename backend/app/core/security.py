import os
import re
import time
import base64
import bcrypt
import jwt
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Tuple
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from fastapi import HTTPException, status, Request
from .config import settings
from .security_settings import security_settings

# AES-GCM 256-bit Key derivation
_RAW_KEY = settings.SECRET_KEY.encode()
if len(_RAW_KEY) < 32:
    _AES_KEY = _RAW_KEY.ljust(32, b"#")[:32]
else:
    _AES_KEY = _RAW_KEY[:32]
_aesgcm = AESGCM(_AES_KEY)


def hash_password(password: str) -> str:
    """Hashes a password securely using bcrypt."""
    salt = bcrypt.gensalt(rounds=security_settings.BCRYPT_ROUNDS)
    return bcrypt.hashpw(password.encode("utf-8"), salt).decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verifies a plain password against the stored bcrypt hash."""
    try:
        return bcrypt.checkpw(plain_password.encode("utf-8"), hashed_password.encode("utf-8"))
    except Exception:
        return False


def validate_password_strength(password: str) -> Tuple[bool, str]:
    """
    Enforces minimum 10 characters and checks against known/common passwords.
    """
    if len(password) < security_settings.PASSWORD_MIN_LENGTH:
        return False, f"Password must be at least {security_settings.PASSWORD_MIN_LENGTH} characters long."
    
    if password.lower() in security_settings.DISALLOWED_PASSWORDS:
        return False, "This password is too common or known to be compromised. Please choose a more complex phrase."
    
    # Must have at least 1 digit or special char for robust clinical security
    if not re.search(r"[0-9!@#$%^&*(),.?\":{}|<>]", password):
        return False, "Password must include at least one number or special character."
    
    return True, "Valid"


def encrypt_pii(plaintext: str) -> str:
    """Encrypts sensitive patient data using AES-256-GCM with a random 12-byte IV."""
    if not plaintext:
        return ""
    nonce = os.urandom(12)
    ciphertext = _aesgcm.encrypt(nonce, plaintext.encode("utf-8"), None)
    # Store as base64: nonce (12 bytes) + ciphertext + tag
    return base64.b64encode(nonce + ciphertext).decode("utf-8")


def decrypt_pii(ciphertext_b64: str) -> str:
    """Decrypts AES-256-GCM ciphertext."""
    if not ciphertext_b64:
        return ""
    try:
        raw = base64.b64decode(ciphertext_b64.encode("utf-8"))
        nonce = raw[:12]
        payload = raw[12:]
        return _aesgcm.decrypt(nonce, payload, None).decode("utf-8")
    except Exception:
        return "[Decryption Error: Corrupted Key or Payload]"


def mask_phone_number(phone: str) -> str:
    """Masks phone number in 98XXXXXX10 format."""
    digits = re.sub(r"\D", "", phone)
    if len(digits) >= 10:
        return f"{digits[:2]}{'X' * (len(digits) - 4)}{digits[-2:]}"
    elif len(digits) >= 4:
        return f"{digits[0]}{'X' * (len(digits) - 2)}{digits[-1]}"
    return "XXXXXX"


def mask_name(name: str) -> str:
    """Masks name for non-clinical authorized roles."""
    parts = name.strip().split()
    if not parts:
        return "P***"
    return " ".join([f"{p[0]}{'*' * (len(p) - 1)}" if len(p) > 1 else p for p in parts])


def sanitize_csv_cell(value: str) -> str:
    """Prevents CSV / Excel formula injection (OWASP)."""
    if isinstance(value, str) and value.startswith(security_settings.CSV_INJECTION_PREFIXES):
        return "'" + value  # Prepend single quote to neutralize formula execution
    return value


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (expires_delta or timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire, "type": "access"})
    return jwt.encode(to_encode, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)


def create_refresh_token(data: dict) -> str:
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(hours=settings.REFRESH_TOKEN_EXPIRE_HOURS)
    to_encode.update({"exp": expire, "type": "refresh"})
    return jwt.encode(to_encode, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)


def create_otp_stage_token(user_id: int, email: str, role: str) -> str:
    """Temporary token issued prior to 2FA OTP verification. Cannot access main APIs."""
    expire = datetime.now(timezone.utc) + timedelta(minutes=settings.OTP_EXPIRE_MINUTES)
    to_encode = {"sub": str(user_id), "email": email, "role": role, "type": "otp_stage", "exp": expire}
    return jwt.encode(to_encode, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)


def decode_token(token: str) -> dict:
    """Decodes and validates JWT token integrity and expiration."""
    try:
        payload = jwt.decode(token, settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM])
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Session token has expired. Please log in again.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except jwt.InvalidTokenError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication token signature or algorithm.",
            headers={"WWW-Authenticate": "Bearer"},
        )


# In-Memory Rate Limiting Engine (OWASP API4:2023)
_rate_limit_store: Dict[str, list] = {}

def check_rate_limit(key: str, max_requests: int, window_seconds: int = 60) -> bool:
    """
    Sliding window rate-limiter. Returns True if request is allowed, False if exceeded.
    """
    now = time.time()
    timestamps = _rate_limit_store.get(key, [])
    # Filter out entries older than window
    valid_timestamps = [t for t in timestamps if now - t < window_seconds]
    if len(valid_timestamps) >= max_requests:
        _rate_limit_store[key] = valid_timestamps
        return False
    valid_timestamps.append(now)
    _rate_limit_store[key] = valid_timestamps
    return True
