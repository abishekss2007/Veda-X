from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text, Float, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime, timezone, timedelta
from .database import Base

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    full_name = Column(String(255), nullable=False)
    role = Column(String(100), nullable=False)
    site_id = Column(String(50), nullable=False, default="SITE-01")
    is_active = Column(Boolean, default=True)
    
    # Account Lockout & Security
    failed_login_attempts = Column(Integer, default=0)
    locked_until = Column(DateTime, nullable=True)
    password_changed_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    
    # 2FA OTP state
    otp_code = Column(String(10), nullable=True)
    otp_created_at = Column(DateTime, nullable=True)
    otp_stage_token = Column(String(500), nullable=True)

    # Relationships
    monitoring_reports = relationship("MonitoringVisitReport", back_populates="monitor")


class Participant(Base):
    __tablename__ = "participants"

    id = Column(Integer, primary_key=True, index=True)
    subject_code = Column(String(50), unique=True, index=True, nullable=False) # e.g. SUB-AIIA-001-042
    site_id = Column(String(50), nullable=False, index=True)
    age = Column(Integer, nullable=False)
    gender = Column(String(20), nullable=False)
    
    # Vulnerable populations / Minors & Disability (DPDP Section 9)
    is_minor = Column(Boolean, default=False)
    is_disabled = Column(Boolean, default=False)
    legal_guardian_name = Column(String(255), nullable=True)
    legal_guardian_consent_verified = Column(Boolean, default=False)
    tracking_profiling_prohibited = Column(Boolean, default=True)
    
    # Ayurveda Specific Assessment
    prakriti_vata = Column(Integer, default=33) # 0-100 scale
    prakriti_pitta = Column(Integer, default=33)
    prakriti_kapha = Column(Integer, default=34)
    dominant_prakriti = Column(String(50), default="Vata-Pitta")
    ayurvedic_diagnosis = Column(String(255), default="Amavata (Rheumatoid Spectrum)")
    modern_diagnosis = Column(String(255), default="Rheumatoid Arthritis (ICD-11: FA20)")
    
    # Clinical Enrolment Gates (GCP-ASU)
    is_enrolled = Column(Boolean, default=False)
    is_dosed = Column(Boolean, default=False)
    
    # DPDP Data status & GCP-ASU 5-Year Archival Retention
    data_status = Column(String(50), default="active") # active, retained_for_legal_reasons, erased
    retention_until = Column(DateTime, default=lambda: datetime.now(timezone.utc) + timedelta(days=5*365))
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    # Relationships
    pii = relationship("ParticipantPII", back_populates="participant", uselist=False, cascade="all, delete-orphan")
    consents = relationship("InformedConsent", back_populates="participant", cascade="all, delete-orphan")
    dispensing_logs = relationship("DispensingLog", back_populates="participant")
    adverse_events = relationship("AdverseEvent", back_populates="participant")


class ParticipantPII(Base):
    """
    Strictly isolated table for storing Direct Personal Identifiable Information (PII).
    Encrypted at application level with AES-256-GCM.
    Accessible ONLY to Doctor/Investigator and Site Research Coordinator.
    """
    __tablename__ = "participant_pii"

    id = Column(Integer, primary_key=True, index=True)
    participant_id = Column(Integer, ForeignKey("participants.id"), unique=True, nullable=False)
    encrypted_name = Column(Text, nullable=False)
    encrypted_phone = Column(Text, nullable=False)
    masked_phone = Column(String(20), nullable=False) # e.g. 98XXXXXX10
    encrypted_aadhaar_or_id = Column(Text, nullable=True)
    address = Column(Text, nullable=True)
    emergency_contact = Column(String(255), nullable=True)
    consent_to_disclose_identity = Column(Boolean, default=False)
    disclosure_legal_reason = Column(String(255), nullable=True)

    participant = relationship("Participant", back_populates="pii")


class ConsentVersion(Base):
    """
    GCP-ASU Section 1: Template and Version tracking for Ethics Committee approved Informed Consent.
    """
    __tablename__ = "consent_versions"

    id = Column(Integer, primary_key=True, index=True)
    version_number = Column(String(20), unique=True, nullable=False) # e.g. "v1.0", "v2.0"
    protocol_code = Column(String(50), nullable=False, default="AYUR-CT-2026-001")
    protocol_title = Column(String(255), nullable=False)
    ec_approval_date = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    is_current = Column(Boolean, default=True)

    # Mandatory GCP-ASU Informed Consent Sections
    aims = Column(Text, nullable=False)
    methods = Column(Text, nullable=False)
    duration = Column(String(100), nullable=False)
    expected_benefits = Column(Text, nullable=False)
    alternative_treatments = Column(Text, nullable=False)
    foreseeable_risks_discomfort = Column(Text, nullable=False)
    extent_of_confidentiality = Column(Text, nullable=False)
    free_treatment_injury = Column(Text, nullable=False)
    compensation_disability_death = Column(Text, nullable=False)
    research_team_contacts = Column(Text, nullable=False)
    biological_samples_secondary_use = Column(Text, nullable=False)


class InformedConsent(Base):
    """
    Participant consent record tracked against specific approved version.
    """
    __tablename__ = "informed_consents"

    id = Column(Integer, primary_key=True, index=True)
    participant_id = Column(Integer, ForeignKey("participants.id"), nullable=False)
    consent_version_id = Column(Integer, ForeignKey("consent_versions.id"), nullable=False)
    language = Column(String(50), nullable=False) # Hindi, English, Regional (Tamil/Bengali/Marathi)
    explained_orally = Column(Boolean, default=False, nullable=False)
    
    # Illiterate participant protections (Mandatory impartial witness)
    is_illiterate = Column(Boolean, default=False)
    impartial_witness_name = Column(String(255), nullable=True)
    impartial_witness_signature = Column(String(255), nullable=True)
    
    # Status and version tracking
    signed_date = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    status = Column(String(50), default="active") # active, superseded, withdrawn
    requires_reconsent = Column(Boolean, default=False)
    withdrawal_date = Column(DateTime, nullable=True)
    withdrawal_reason = Column(Text, nullable=True)

    participant = relationship("Participant", back_populates="consents")
    version = relationship("ConsentVersion")


class EthicsCommitteeMember(Base):
    """
    GCP-ASU EC Roster with statutory role verification.
    """
    __tablename__ = "ethics_committee_members"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    # Required roles: Chairperson, Basic medical scientist / pharmacologist, Clinician, Legal expert,
    # Social scientist / NGO representative, Philosopher / ethicist, Lay community member, Member Secretary, ASU expert
    role = Column(String(100), nullable=False)
    affiliation_type = Column(String(50), default="Outside Institution") # Outside Institution preferred for Chair
    qualifications = Column(String(255), nullable=False)
    is_active = Column(Boolean, default=True)
    appointment_date = Column(DateTime, default=lambda: datetime.now(timezone.utc))


class ProtocolApproval(Base):
    __tablename__ = "protocol_approvals"

    id = Column(Integer, primary_key=True, index=True)
    protocol_code = Column(String(50), unique=True, nullable=False)
    title = Column(String(255), nullable=False)
    amendment_number = Column(String(20), default="A00")
    submission_date = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    approval_date = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    expiry_date = Column(DateTime, default=lambda: datetime.now(timezone.utc) + timedelta(days=365))
    status = Column(String(50), default="Approved") # Approved, Amendment Pending, Renewed, Expired
    sent_to_ec_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))


class AutomatedECTransmission(Base):
    """
    GCP-ASU: Automatic timestamped transmission of SAEs and amendments to EC.
    """
    __tablename__ = "automated_ec_transmissions"

    id = Column(Integer, primary_key=True, index=True)
    transmission_type = Column(String(50), nullable=False) # SAE, Protocol Amendment
    reference_id = Column(String(100), nullable=False)
    sent_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    ec_members_dispatched = Column(Integer, default=9)
    status = Column(String(50), default="Dispatched & Logged")
    transmission_hash = Column(String(64), nullable=False)


class AdverseEvent(Base):
    __tablename__ = "adverse_events"

    id = Column(Integer, primary_key=True, index=True)
    participant_id = Column(Integer, ForeignKey("participants.id"), nullable=False)
    site_id = Column(String(50), nullable=False)
    event_term = Column(String(255), nullable=False)
    ayurvedic_term = Column(String(255), nullable=False) # e.g. Pitta-Kopa / Ushnata / Dahata
    is_serious = Column(Boolean, default=False)
    severity = Column(String(50), default="Moderate")
    outcome = Column(String(50), default="Recovering")
    reported_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    sent_to_ec_at = Column(DateTime, nullable=True)
    sent_to_pv_at = Column(DateTime, nullable=True)
    causality_asu = Column(String(100), default="Probable (Nidana-Dosha correlation)")

    participant = relationship("Participant", back_populates="adverse_events")


class InvestigationalProduct(Base):
    """
    GCP-ASU Investigational Product Tracking & Ayurveda specific protocol fields.
    """
    __tablename__ = "investigational_products"

    id = Column(Integer, primary_key=True, index=True)
    study_code = Column(String(50), nullable=False, default="AYUR-CT-2026-001")
    batch_number = Column(String(50), unique=True, nullable=False)
    formulation_name = Column(String(255), nullable=False) # e.g. Yogaraj Guggulu Modified Release
    dosage_form = Column(String(50), nullable=False) # vati, churna, kashaya, taila, asava/arishta
    
    # Ayurveda Specific Fields
    anupana = Column(String(100), nullable=False, default="Ushnodaka (Warm Water)")
    desh = Column(String(100), nullable=False, default="Sadharana Desha")
    kala = Column(String(100), nullable=False, default="Pratah-Kala (Morning) Rasayana-Kala")
    pathya = Column(Text, nullable=False, default="Laghu Ahara, Moong Dal, Luke-warm water, gentle yoga")
    apathya = Column(Text, nullable=False, default="Viruddha Ahara, cold drinks, daytime sleep (Diva-swapna), curds at night")
    
    # Storage & Handling
    storage_temperature = Column(String(100), default="Store below 25°C in a dry place")
    storage_humidity = Column(String(100), default="Relative humidity < 60%")
    special_instructions = Column(Text, default="Protect from direct sunlight and moisture. Seal airtight.")
    expiry_date = Column(DateTime, default=lambda: datetime.now(timezone.utc) + timedelta(days=2*365))
    investigator_contact = Column(String(255), default="+91-11-2953-8401 (PI Clinical Emergency)")
    institution_name = Column(String(255), default="All India Institute of Ayurveda (AIIA), New Delhi")

    dispensing_logs = relationship("DispensingLog", back_populates="product")


class DispensingLog(Base):
    __tablename__ = "dispensing_logs"

    id = Column(Integer, primary_key=True, index=True)
    ip_id = Column(Integer, ForeignKey("investigational_products.id"), nullable=False)
    participant_id = Column(Integer, ForeignKey("participants.id"), nullable=False)
    dispensed_by_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    quantity = Column(Float, nullable=False)
    unit = Column(String(20), default="Vati (Tablets)")
    dispensed_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    returned_quantity = Column(Float, default=0.0)
    notes = Column(Text, nullable=True)

    product = relationship("InvestigationalProduct", back_populates="dispensing_logs")
    participant = relationship("Participant", back_populates="dispensing_logs")


class MonitoringVisitReport(Base):
    """
    Monitor role data and visit report.
    """
    __tablename__ = "monitoring_visit_reports"

    id = Column(Integer, primary_key=True, index=True)
    monitor_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    site_id = Column(String(50), nullable=False)
    visit_date = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    missing_data_count = Column(Integer, default=0)
    overdue_visits_count = Column(Integer, default=0)
    protocol_deviations_noted = Column(Integer, default=0)
    findings = Column(Text, nullable=False)
    action_items = Column(Text, nullable=False)
    status = Column(String(50), default="Submitted")
    retention_until = Column(DateTime, default=lambda: datetime.now(timezone.utc) + timedelta(days=5*365))

    monitor = relationship("User", back_populates="monitoring_reports")


class DPDPNotice(Base):
    """
    DPDP Act 2023 Sections 5-6, Rule 3: Privacy Notice
    """
    __tablename__ = "dpdp_notices"

    id = Column(Integer, primary_key=True, index=True)
    version = Column(String(20), unique=True, nullable=False) # e.g. "DPDP-V1.0"
    language = Column(String(50), nullable=False, default="English")
    notice_text = Column(Text, nullable=False)
    data_categories_collected = Column(Text, nullable=False)
    purposes = Column(Text, nullable=False)
    dpo_name = Column(String(255), nullable=False)
    dpo_email = Column(String(255), nullable=False)
    dpo_phone = Column(String(50), nullable=False)
    is_active = Column(Boolean, default=True)
    effective_date = Column(DateTime, default=lambda: datetime.now(timezone.utc))


class DPDPDataRequest(Base):
    """
    DPDP Data Principal Rights (Access, Correction, Update, Erasure).
    Max 90-day response deadline.
    """
    __tablename__ = "dpdp_data_requests"

    id = Column(Integer, primary_key=True, index=True)
    request_type = Column(String(50), nullable=False) # access, correction, update, erasure
    subject_code = Column(String(50), nullable=False)
    details = Column(Text, nullable=False)
    status = Column(String(50), default="Received") # Received, In Review, Fulfilled, Retained for Legal Reasons
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    deadline_at = Column(DateTime, default=lambda: datetime.now(timezone.utc) + timedelta(days=90))
    resolution_notes = Column(Text, nullable=True)
    resolved_at = Column(DateTime, nullable=True)


class DPDPGrievance(Base):
    __tablename__ = "dpdp_grievances"

    id = Column(Integer, primary_key=True, index=True)
    complainant_name = Column(String(255), nullable=False)
    complainant_contact = Column(String(255), nullable=False)
    issue_description = Column(Text, nullable=False)
    status = Column(String(50), default="Open") # Open, Under Investigation, Resolved
    filed_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    deadline_at = Column(DateTime, default=lambda: datetime.now(timezone.utc) + timedelta(days=90))
    resolution_notes = Column(Text, nullable=True)
    resolved_at = Column(DateTime, nullable=True)


class DataBreachIncident(Base):
    """
    DPDP Section 8(6), Rule 7: Breach Response with 72-hour countdown to DPBI.
    """
    __tablename__ = "data_breach_incidents"

    id = Column(Integer, primary_key=True, index=True)
    incident_ref = Column(String(50), unique=True, nullable=False)
    discovery_timestamp = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    incident_nature = Column(Text, nullable=False)
    data_affected = Column(Text, nullable=False)
    number_affected = Column(Integer, default=0)
    countdown_deadline_dpbi = Column(DateTime, nullable=False) # 72 hours from discovery
    dpbi_reported_at = Column(DateTime, nullable=True)
    principals_notified_at = Column(DateTime, nullable=True)
    remediation_summary = Column(Text, nullable=True)
    status = Column(String(50), default="Investigating")


class CERTInIncident(Base):
    """
    CERT-In Directions 2022: Security Incidents with mandatory 6-hour reporting countdown.
    """
    __tablename__ = "cert_in_incidents"

    id = Column(Integer, primary_key=True, index=True)
    incident_ref = Column(String(50), unique=True, nullable=False)
    discovery_timestamp = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    incident_type = Column(String(100), nullable=False) # From CERT-In Annexure I
    severity = Column(String(20), default="High")
    description = Column(Text, nullable=False)
    countdown_deadline_6h = Column(DateTime, nullable=False) # 6 hours from discovery
    reported_to_cert_in_at = Column(DateTime, nullable=True)
    official_email = Column(String(100), default="incident@cert-in.org.in")
    official_phone = Column(String(50), default="1800-11-4949")
    remediation_status = Column(String(50), default="Open - Countdown Active")


class CERTInPointOfContact(Base):
    """
    CERT-In Designated Point of Contact settings.
    """
    __tablename__ = "cert_in_point_of_contact"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    designation = Column(String(255), nullable=False)
    organization = Column(String(255), nullable=False)
    postal_address = Column(Text, nullable=False)
    email = Column(String(255), nullable=False)
    phone = Column(String(50), nullable=False)
    last_updated = Column(DateTime, default=lambda: datetime.now(timezone.utc))


class AuditLogEntry(Base):
    """
    Tamper-Proof Cryptographically Chained Audit Ledger.
    """
    __tablename__ = "audit_log"

    id = Column(Integer, primary_key=True, index=True)
    entry_index = Column(Integer, unique=True, index=True, nullable=False)
    timestamp = Column(String(100), nullable=False)
    user_id = Column(Integer, nullable=True)
    user_email = Column(String(255), nullable=False)
    role = Column(String(100), nullable=False)
    site_id = Column(String(50), nullable=True)
    ip_address = Column(String(50), nullable=False)
    action = Column(String(100), nullable=False)
    entity_type = Column(String(100), nullable=False)
    entity_id = Column(String(100), nullable=True)
    previous_value = Column(Text, nullable=True)
    new_value = Column(Text, nullable=True)
    reason = Column(Text, nullable=True)
    
    # Cryptographic SHA-256 Hash Chain
    prev_hash = Column(String(64), nullable=False)
    current_hash = Column(String(64), nullable=False)


class DataProcessorContract(Base):
    """
    DPDP Section 8: Written contracts with cloud hosts and data processors.
    """
    __tablename__ = "data_processor_contracts"

    id = Column(Integer, primary_key=True, index=True)
    processor_name = Column(String(255), nullable=False)
    service_type = Column(String(100), nullable=False) # e.g. Cloud Host (AWS Mumbai), Central Lab
    contract_signed_date = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    dpdp_compliant_agreement = Column(Boolean, default=True)
    data_location = Column(String(100), default="Mumbai, India")
    last_audit_date = Column(DateTime, default=lambda: datetime.now(timezone.utc))
