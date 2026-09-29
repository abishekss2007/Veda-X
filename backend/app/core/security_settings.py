"""
AyurCTMS Enterprise Security Settings
=====================================
Compliant with:
- OWASP Top 10 2021 & OWASP API Security Top 10 2023
- Ministry of AYUSH GCP-ASU Guidelines
- Digital Personal Data Protection (DPDP) Act 2023 + DPDP Rules 2025
- CERT-In Directions No. 20(3)/2022-CERT-In (28 April 2022)
"""

from typing import Dict, List, Set

class SecuritySettings:
    # 1. Cryptography and Password Standards
    PASSWORD_MIN_LENGTH: int = 10
    PASSWORD_HASH_ALGORITHM: str = "bcrypt"
    BCRYPT_ROUNDS: int = 12
    PII_ENCRYPTION_CIPHER: str = "AES-256-GCM"
    HASH_CHAIN_ALGORITHM: str = "SHA-256"
    
    # Common/Leaked password blacklist (OWASP ASVS & NIST SP 800-63B)
    DISALLOWED_PASSWORDS: Set[str] = {
        "password", "password123", "1234567890", "ayurveda123", "admin12345",
        "qwerty1234", "clinical123", "ayurctms2024", "welcome1234", "doctor12345",
        "administrator", "iloveindia", "hospital123", "monkey1234"
    }

    # 2. Account Protection & Lockout
    MAX_LOGIN_ATTEMPTS: int = 5
    LOCKOUT_DURATION_SECONDS: int = 15 * 60  # 15 minutes
    OTP_VALIDITY_SECONDS: int = 5 * 60       # 5 minutes
    PASSWORD_RESET_TOKEN_EXPIRY_SECONDS: int = 15 * 60 # 15 minutes

    # Roles requiring mandatory 2-Factor Authentication (OTP)
    ROLES_MANDATORY_OTP: Set[str] = {
        "Doctor / Investigator", # Principal Investigator (PI)
        "PV Officer",            # Pharmacovigilance Officer
        "Auditor / Regulator",   # Regulatory Auditor
        "Admin"                  # System Administrator
    }

    # 3. Session & Token Policies
    ACCESS_TOKEN_LIFETIME_SECONDS: int = 15 * 60      # 15 minutes
    REFRESH_TOKEN_LIFETIME_SECONDS: int = 8 * 3600    # 8 hours
    SESSION_INACTIVITY_MAX_SECONDS: int = 15 * 60     # 15 minutes
    SESSION_INACTIVITY_WARNING_SECONDS: int = 14 * 60 # 14 minutes (1 min prior)
    COOKIE_HTTP_ONLY: bool = True
    COOKIE_SECURE: bool = True
    COOKIE_SAMESITE: str = "Strict"

    # 4. Mandatory 9 Role-Based Access Control (RBAC) System
    VALID_ROLES: List[str] = [
        "Research Coordinator",
        "Doctor / Investigator",
        "Monitor",
        "EC Member",
        "PV Officer",
        "Admin",
        "Auditor / Regulator",
        "Institution Leadership",
        "Data Protection Officer"
    ]

    # Clinical data viewing authorization (Admin and Monitor are strictly restricted)
    CAN_VIEW_DIRECT_CLINICAL_DATA: Set[str] = {
        "Research Coordinator",
        "Doctor / Investigator",
        "PV Officer",
        "EC Member",
        "Auditor / Regulator"
    }

    # PII Unmasking Permission (Names and Phone Numbers visible ONLY to PI & Coordinator)
    CAN_VIEW_UNMASKED_PII: Set[str] = {
        "Doctor / Investigator",
        "Research Coordinator"
    }

    # Strictly Read-Only Roles
    READ_ONLY_ROLES: Set[str] = {
        "Monitor",
        "Auditor / Regulator",
        "Institution Leadership"
    }

    # 5. Rate Limiting (OWASP API4:2023 Unrestricted Resource Consumption)
    LOGIN_RATE_LIMIT: int = 5    # requests per minute per IP
    GENERAL_RATE_LIMIT: int = 100 # requests per minute per user/IP

    # 6. File Security (OWASP Top 10 A08: Software and Data Integrity Failures)
    MAX_FILE_SIZE_BYTES: int = 10 * 1024 * 1024  # 10 MB
    ALLOWED_MIME_TYPES: Dict[str, bytes] = {
        "application/pdf": b"%PDF",
        "image/jpeg": b"\xff\xd8\xff",
        "image/png": b"\x89PNG\r\n\x1a\n",
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": b"PK\x03\x04",
        "text/csv": b""
    }
    FORBIDDEN_FILE_EXTENSIONS: Set[str] = {
        ".exe", ".bat", ".cmd", ".sh", ".ps1", ".vbs", ".dll", ".so", ".bin", ".scr", ".com"
    }

    # CSV/Excel Formula Injection Characters (OWASP CSV Injection)
    CSV_INJECTION_PREFIXES: tuple = ("=", "+", "-", "@", "\t", "\r")

    # 7. HTTP Security Headers (OWASP Top 10 A05: Security Misconfiguration)
    SECURITY_HEADERS: Dict[str, str] = {
        "Strict-Transport-Security": "max-age=63072000; includeSubDomains; preload",
        "Content-Security-Policy": (
            "default-src 'self'; "
            "img-src 'self' data: blob:; "
            "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; "
            "font-src 'self' https://fonts.gstatic.com; "
            "script-src 'self' 'unsafe-inline'; "
            "connect-src 'self'; "
            "frame-ancestors 'none'; "
            "base-uri 'self'; "
            "form-action 'self';"
        ),
        "X-Frame-Options": "DENY",
        "X-Content-Type-Options": "nosniff",
        "Referrer-Policy": "no-referrer",
        "Permissions-Policy": "camera=(), microphone=(), geolocation=(), payment=(), usb=()",
        "X-XSS-Protection": "1; mode=block",
        "Cache-Control": "no-store, no-cache, must-revalidate, max-age=0"
    }

    # 8. Regulatory Timelines and Deadlines
    CERT_IN_INCIDENT_SLA_HOURS: int = 6
    DPBI_BREACH_SLA_HOURS: int = 72
    DPDP_GRIEVANCE_SLA_DAYS: int = 90
    CERT_IN_LOG_RETENTION_DAYS: int = 180
    DPDP_LOG_RETENTION_DAYS: int = 365
    GCP_ASU_ARCHIVE_RETENTION_YEARS: int = 5

    # 9. CERT-In Annexure I Specified Incident Categories
    CERT_IN_INCIDENT_TYPES: List[str] = [
        "scanning_probing",
        "system_compromise_and_unauthorised_access",
        "website_defacement_and_malicious_code",
        "attacks_on_servers_and_applications",
        "identity_theft_and_spoofing",
        "dos_and_ddos_attacks",
        "data_breach_and_data_leak",
        "attacks_on_critical_infrastructure_and_cloud",
        "unauthorised_access_to_clinical_database",
        "ransomware_or_malicious_payload_attack"
    ]

security_settings = SecuritySettings()
