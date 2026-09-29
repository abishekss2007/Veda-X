import os
from pathlib import Path
from typing import List
from pydantic import BaseModel
from dotenv import load_dotenv

# Automatically load backend/.env and root .env
_backend_dir = Path(__file__).resolve().parent.parent.parent
load_dotenv(_backend_dir / ".env")
load_dotenv(_backend_dir.parent / ".env")

class Settings(BaseModel):
    PROJECT_NAME: str = "AyurCTMS"
    VERSION: str = "2.4.0-Enterprise-Compliant"
    ENVIRONMENT: str = os.getenv("ENVIRONMENT", "production")
    
    # Secrets & Cryptography
    SECRET_KEY: str = os.getenv("SECRET_KEY", "vedax-secret-encryption-master-key-32ch-min!")
    JWT_SECRET: str = os.getenv("JWT_SECRET", "vedax-jwt-signing-secure-token-production-key-2026!")
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 15
    REFRESH_TOKEN_EXPIRE_HOURS: int = 8
    
    # Database
    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///./ayur_ctms.db")
    
    # Security Policies
    ACCOUNT_LOCKOUT_ATTEMPTS: int = 5
    ACCOUNT_LOCKOUT_MINUTES: int = 15
    OTP_EXPIRE_MINUTES: int = 5
    SESSION_INACTIVITY_TIMEOUT_MINUTES: int = 15
    SESSION_WARNING_BEFORE_MINUTES: int = 1
    
    # Rate Limits (Requests per minute)
    RATE_LIMIT_LOGIN_PER_MINUTE: int = 5
    RATE_LIMIT_API_PER_MINUTE: int = 100
    
    # Upload limits
    MAX_UPLOAD_SIZE_BYTES: int = 10 * 1024 * 1024  # 10 MB
    ALLOWED_UPLOAD_EXTENSIONS: List[str] = [".pdf", ".jpg", ".jpeg", ".png", ".xlsx", ".csv"]
    
    # Regulatory Compliance Settings
    # 1. GCP-ASU (Ministry of AYUSH)
    GCP_ASU_RECORD_RETENTION_YEARS: int = 5
    MINIMUM_EC_MEMBERS: int = 5
    
    # 2. DPDP Act 2023 & Rules 2025 (India)
    DPDP_ACCESS_LOG_RETENTION_DAYS: int = 365
    DPDP_GRIEVANCE_MAX_RESPONSE_DAYS: int = 90
    DPDP_DATA_REQUEST_MAX_RESPONSE_DAYS: int = 90
    DPBI_BREACH_NOTIFICATION_HOURS: int = 72
    DPO_NAME: str = "Dr. Rajeshwar Sharma, M.D. (Ayu), CIPP/A"
    DPO_DESIGNATION: str = "Designated Data Protection Officer"
    DPO_EMAIL: str = "dpo@ayurctms.gov.in"
    DPO_PHONE: str = "+91-11-2953-8400"
    DPO_ADDRESS: str = "All India Institute of Ayurveda (AIIA), Mathura Road, Gautampuri, Sarita Vihar, New Delhi 110076"
    
    # 3. CERT-In Directions 2022
    CERT_IN_REPORTING_DEADLINE_HOURS: int = 6
    CERT_IN_LOG_RETENTION_DAYS: int = 180
    CERT_IN_OFFICIAL_EMAIL: str = "incident@cert-in.org.in"
    CERT_IN_OFFICIAL_PHONE: str = "1800-11-4949"
    CERT_IN_OFFICIAL_PORTAL: str = "https://www.cert-in.org.in"
    
    # NTP Clocks (NIC / NPL)
    NTP_SERVERS: List[str] = ["time.nic.in", "time.nplindia.org", "samay1.nic.in"]
    PRIMARY_DATA_RESIDENCY: str = "Mumbai, Maharashtra, India (ap-south-1)"

settings = Settings()
