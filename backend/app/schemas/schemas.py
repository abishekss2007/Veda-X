from pydantic import BaseModel, EmailStr, Field, field_validator, ConfigDict
from typing import Optional, List
from datetime import datetime

# ================= AUTHENTICATION SCHEMAS =================
class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=1, max_length=128)

class OTPVerifyRequest(BaseModel):
    otp_stage_token: str
    otp_code: str = Field(..., min_length=6, max_length=6, pattern=r"^\d{6}$")

class ForgotPasswordRequest(BaseModel):
    email: EmailStr

class ResetPasswordRequest(BaseModel):
    token: str
    new_password: str = Field(..., min_length=10, max_length=128)

class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in_seconds: int = 900
    user_id: int
    email: str
    full_name: str
    role: str
    site_id: str
    requires_otp: bool = False
    otp_stage_token: Optional[str] = None

class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    email: EmailStr
    full_name: str
    role: str
    site_id: str
    is_active: bool

# ================= GCP-ASU PARTICIPANT SCHEMAS =================
class ParticipantCreate(BaseModel):
    subject_code: str = Field(..., min_length=3, max_length=50, pattern=r"^[A-Z0-9\-]+$")
    site_id: str = Field(default="SITE-01", max_length=50)
    age: int = Field(..., ge=1, le=120)
    gender: str = Field(..., pattern=r"^(Male|Female|Other)$")
    
    # Vulnerable populations / Minor
    is_minor: bool = False
    is_disabled: bool = False
    legal_guardian_name: Optional[str] = None
    legal_guardian_consent_verified: bool = False

    # Direct PII (Stored in separate restricted encrypted table)
    full_name: str = Field(..., min_length=2, max_length=255)
    phone_number: str = Field(..., min_length=10, max_length=20)
    address: Optional[str] = None
    emergency_contact: Optional[str] = None

    # Ayurveda Clinical Fields
    prakriti_vata: int = Field(default=33, ge=0, le=100)
    prakriti_pitta: int = Field(default=33, ge=0, le=100)
    prakriti_kapha: int = Field(default=34, ge=0, le=100)
    dominant_prakriti: str = "Vata-Pitta"
    ayurvedic_diagnosis: str = "Amavata (Rheumatoid Spectrum)"
    modern_diagnosis: str = "Rheumatoid Arthritis (ICD-11: FA20)"

    @field_validator("age")
    @classmethod
    def validate_minor_guardian(cls, v, info):
        # Checked in endpoint logic as well
        return v

class ParticipantUpdate(BaseModel):
    age: Optional[int] = Field(None, ge=1, le=120)
    prakriti_vata: Optional[int] = Field(None, ge=0, le=100)
    prakriti_pitta: Optional[int] = Field(None, ge=0, le=100)
    prakriti_kapha: Optional[int] = Field(None, ge=0, le=100)
    dominant_prakriti: Optional[str] = None
    ayurvedic_diagnosis: Optional[str] = None
    modern_diagnosis: Optional[str] = None
    reason_for_change: str = Field(..., min_length=5, max_length=500)

class ParticipantOut(BaseModel):
    id: int
    subject_code: str
    site_id: str
    age: int
    gender: str
    is_minor: bool
    is_disabled: bool
    legal_guardian_name: Optional[str] = None
    legal_guardian_consent_verified: bool
    tracking_profiling_prohibited: bool
    
    # Ayurveda Diagnosis
    prakriti_vata: int
    prakriti_pitta: int
    prakriti_kapha: int
    dominant_prakriti: str
    ayurvedic_diagnosis: str
    modern_diagnosis: str
    
    is_enrolled: bool
    is_dosed: bool
    data_status: str
    retention_until: datetime
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
    full_name: Optional[str] = None
    phone_number: Optional[str] = None # Masked if unauthorized

# ================= GCP-ASU INFORMED CONSENT SCHEMAS =================
class InformedConsentCreate(BaseModel):
    participant_id: int
    consent_version_id: int
    language: str = Field(..., pattern=r"^(Hindi|English|Tamil|Bengali|Marathi|Telugu|Kannada|Sanskrit)$")
    explained_orally: bool
    is_illiterate: bool = False
    impartial_witness_name: Optional[str] = None
    impartial_witness_signature: Optional[str] = None

class InformedConsentWithdraw(BaseModel):
    reason: str = Field(..., min_length=5, max_length=500)

class ConsentVersionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    version_number: str
    protocol_code: str
    protocol_title: str
    ec_approval_date: datetime
    is_current: bool
    aims: str
    methods: str
    duration: str
    expected_benefits: str
    alternative_treatments: str
    foreseeable_risks_discomfort: str
    extent_of_confidentiality: str
    free_treatment_injury: str
    compensation_disability_death: str
    research_team_contacts: str
    biological_samples_secondary_use: str

# ================= GCP-ASU ETHICS COMMITTEE SCHEMAS =================
class ECMemberCreate(BaseModel):
    name: str = Field(..., min_length=2, max_length=255)
    role: str = Field(..., pattern=r"^(Chairperson|Basic medical scientist / pharmacologist|Clinician|Legal expert|Social scientist / NGO representative|Philosopher / ethicist|Lay community member|Member Secretary|ASU expert)$")
    affiliation_type: str = Field(default="Outside Institution")
    qualifications: str = Field(..., min_length=2, max_length=255)

class ECMemberOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    name: str
    role: str
    affiliation_type: str
    qualifications: str
    is_active: bool
    appointment_date: datetime

class ProtocolAmendmentCreate(BaseModel):
    protocol_code: str
    title: str
    amendment_number: str
    description: str

# ================= GCP-ASU INVESTIGATIONAL PRODUCT & DISPENSING =================
class InvestigationalProductCreate(BaseModel):
    study_code: str
    batch_number: str
    formulation_name: str
    dosage_form: str = Field(..., pattern=r"^(vati|churna|kashaya|taila|asava/arishta|avaleha|bhasma)$")
    anupana: str
    desh: str
    kala: str
    pathya: str
    apathya: str
    storage_temperature: str
    storage_humidity: str
    special_instructions: str
    expiry_date: datetime
    investigator_contact: str
    institution_name: str

class DispenseRequest(BaseModel):
    ip_id: int
    participant_id: int
    quantity: float = Field(..., gt=0)
    unit: str = "Vati (Tablets)"
    notes: Optional[str] = None

class LabelPreviewOut(BaseModel):
    trial_legend: str = "For Clinical Studies only"
    study_code: str
    batch_number: str
    formulation_name: str
    dosage_form: str
    participant_subject_code: str
    institution_name: str
    investigator_contact: str
    storage_instructions: str
    anupana: str
    kala: str
    dispensed_date: str

# ================= MONITORING & ADVERSE EVENTS =================
class MonitoringVisitReportCreate(BaseModel):
    site_id: str
    missing_data_count: int = Field(default=0, ge=0)
    overdue_visits_count: int = Field(default=0, ge=0)
    protocol_deviations_noted: int = Field(default=0, ge=0)
    findings: str = Field(..., min_length=10)
    action_items: str = Field(..., min_length=10)

class AdverseEventCreate(BaseModel):
    participant_id: int
    site_id: str
    event_term: str
    ayurvedic_term: str
    is_serious: bool = False
    severity: str = "Moderate"
    outcome: str = "Recovering"
    causality_asu: str = "Probable (Nidana-Dosha correlation)"

# ================= DPDP ACT 2023 SCHEMAS =================
class DPDPDataRequestCreate(BaseModel):
    subject_code: str
    request_type: str = Field(..., pattern=r"^(access|correction|update|erasure)$")
    details: str = Field(..., min_length=5, max_length=1000)

class DPDPGrievanceCreate(BaseModel):
    complainant_name: str
    complainant_contact: str
    issue_description: str = Field(..., min_length=10, max_length=2000)

class DataBreachCreate(BaseModel):
    incident_ref: str
    incident_nature: str
    data_affected: str
    number_affected: int = Field(..., ge=0)
    remediation_summary: Optional[str] = None

# ================= CERT-In DIRECTIONS SCHEMAS =================
class CERTInIncidentCreate(BaseModel):
    incident_ref: str
    incident_type: str = Field(..., min_length=3)
    severity: str = Field(default="High", pattern=r"^(Critical|High|Medium|Low)$")
    description: str = Field(..., min_length=10)

class CERTInPoCUpdate(BaseModel):
    name: str = Field(..., min_length=2)
    designation: str = Field(..., min_length=2)
    organization: str = Field(..., min_length=2)
    postal_address: str = Field(..., min_length=5)
    email: EmailStr
    phone: str = Field(..., min_length=10, max_length=20)

# ================= AUDIT CHAIN SCHEMAS =================
class AuditLogOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    entry_index: int
    timestamp: str
    user_email: str
    role: str
    site_id: Optional[str] = None
    ip_address: str
    action: str
    entity_type: str
    entity_id: Optional[str] = None
    previous_value: Optional[str] = None
    new_value: Optional[str] = None
    reason: Optional[str] = None
    prev_hash: str
    current_hash: str

class ChainVerificationOut(BaseModel):
    valid: bool
    total_records: int
    broken_at_index: Optional[int] = None
    tampered_row_id: Optional[int] = None
    action: Optional[str] = None
    head_hash: Optional[str] = None
    message: str
