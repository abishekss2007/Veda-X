import os
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from .core.config import settings
from .core.security_settings import security_settings
from .core.security import hash_password, encrypt_pii, mask_phone_number
from .core.middleware import SecurityHeadersMiddleware
from .core.audit import log_audit_event
from .db.database import engine, Base, SessionLocal
from .db.models import (
    User, Participant, ParticipantPII, ConsentVersion, InformedConsent,
    EthicsCommitteeMember, ProtocolApproval, InvestigationalProduct,
    CERTInPointOfContact, DPDPNotice, DataProcessorContract, AuditLogEntry
)

# Import API Routers
from .api import (
    auth, participants, consent, ethics, clinical_ayurveda,
    investigational_products, monitoring, dpdp, cert_in,
    compliance, audit, files, supabase_integration, escalations, tasks
)

def seed_synthetic_data(db: Session):
    """
    Populates synthetic demonstration clinical trial data covering:
    - 9 User Roles
    - GCP-ASU Informed Consent template with all statutory sections
    - Ethics Committee roster with mandatory roles including ASU expert
    - Classical Ayurvedic Investigational Product batch
    - DPDP Privacy Notice & CERT-In Point of Contact
    """
    if db.query(User).first():
        return # Data already seeded

    print("[AyurCTMS] Seeding initial regulatory-compliant synthetic data...")

    # 1. Seed 9 User Roles
    seed_users = [
        ("coordinator@ayurctms.in", "AyurCoord#2026", "Dr. Sunita Patel, BAMS", "Research Coordinator", "SITE-01"),
        ("pi.sharma@ayurctms.in", "AyurDoctor#2026", "Prof. (Dr.) Rajeshwar Sharma", "Doctor / Investigator", "SITE-01"),
        ("monitor.verma@ayurctms.in", "AyurMonitor#2026", "Vikram Verma, CRA", "Monitor", "SITE-01"),
        ("ec.chair@ayurctms.in", "AyurEthics#2026", "Justice (Retd.) M. K. Narayanan", "EC Member", "SITE-01"),
        ("pv.officer@ayurctms.in", "AyurSafety#2026", "Dr. Gayatri Devi, MD (Ayu)", "PV Officer", "SITE-01"),
        ("admin@ayurctms.in", "AyurAdmin#2026!", "System Administrator", "Admin", "SITE-HQ"),
        ("auditor@ayurctms.in", "AyurAuditor#2026", "K. R. Sengupta, ISO Lead Auditor", "Auditor / Regulator", "SITE-HQ"),
        ("director@ayurctms.in", "AyurLeader#2026", "Prof. (Dr.) Tanuja Nesari, Director", "Institution Leadership", "SITE-HQ"),
        ("dpo@ayurctms.gov.in", "AyurDPDP#2026", "Dr. Rajeshwar Sharma (DPO)", "Data Protection Officer", "SITE-HQ"),
        # Coordinator for Site 02 to demonstrate cross-site tenancy protection
        ("coord.site2@ayurctms.in", "AyurCoord#2026", "Dr. Ramesh Nair", "Research Coordinator", "SITE-02")
    ]

    for email, pwd, name, role, site in seed_users:
        u = User(
            email=email,
            hashed_password=hash_password(pwd),
            full_name=name,
            role=role,
            site_id=site,
            is_active=True
        )
        db.add(u)
    db.flush()

    # 2. Seed GCP-ASU Informed Consent Template v1.0
    consent_v1 = ConsentVersion(
        version_number="v1.0",
        protocol_code="AYUR-CT-2026-001",
        protocol_title="Efficacy and Safety of Yogaraj Guggulu Modified Formulation in Amavata (Rheumatoid Arthritis)",
        is_current=True,
        aims="To evaluate the therapeutic efficacy and safety of Classical Yogaraj Guggulu with Shunthi Kwatha in reducing inflammation and pain in Amavata.",
        methods="Randomized, double-blind, active-controlled multi-center clinical study following GCP-ASU standards.",
        duration="12 weeks of active intervention followed by a 4-week wash-out observation period.",
        expected_benefits="Relief of Sandhishoola (joint pain), Sandhigraha (morning stiffness), and normalization of ESR/CRP inflammatory markers.",
        alternative_treatments="Standard Disease Modifying Anti-Rheumatic Drugs (DMARDs) or supportive Ayurvedic shamana aushadhis.",
        foreseeable_risks_discomfort="Mild transient gastric heaviness, altered bowel habit (Koshtha Shuddhi), or mild nausea.",
        extent_of_confidentiality="Participants are identified solely by Subject Codes (e.g. SUB-AIIA-001-042). Direct PII is stored separately with AES-256 encryption under DPDP Act 2023.",
        free_treatment_injury="Free comprehensive medical management and hospitalization will be provided for any research-related injury occurring during the trial period.",
        compensation_disability_death="Statutory financial compensation as per Ministry of AYUSH GCP-ASU guidelines and CDSCO regulatory mandates.",
        research_team_contacts="Principal Investigator: Prof. (Dr.) Rajeshwar Sharma | Emergency Mobile: +91-11-2953-8401 | Site-01 Desk",
        biological_samples_secondary_use="Stored serum and blood samples will NOT be utilized for secondary purposes without express, separate written informed consent."
    )
    db.add(consent_v1)
    db.flush()

    # 3. Seed Ethics Committee Register (GCP-ASU Statutory Composition)
    ec_roster = [
        ("Justice (Retd.) M. K. Narayanan", "Chairperson", "Outside Institution", "Former High Court Judge, Legal & Bioethics Specialist"),
        ("Prof. (Dr.) B. K. Mohapatra", "ASU expert", "Outside Institution", "MD, PhD (Ayurveda), Senior Dravyaguna & Rasashastra Scholar"),
        ("Dr. Rohini Sundaram", "Clinician", "Institutional", "MD (Internal Medicine), Clinical Trials Faculty"),
        ("Dr. Sanjay Deshmukh", "Basic medical scientist / pharmacologist", "Outside Institution", "PhD (Medical Pharmacology)"),
        ("Adv. Meenakshi Lekhi-Verma", "Legal expert", "Outside Institution", "Senior Counsel, Supreme Court of India"),
        ("Smt. Aruna Roy-Chowdhury", "Social scientist / NGO representative", "Outside Institution", "President, Arogya Jan Kalyan NGO"),
        ("Prof. Devendra Swamy", "Philosopher / ethicist", "Outside Institution", "MA, PhD (Sanskrit & Indian Ethics)"),
        ("Shri Om Prakash Gupta", "Lay community member", "Outside Institution", "Retired Educationist, Community Representative"),
        ("Dr. Arvind Chandrashekar", "Member Secretary", "Institutional", "MD (Ayu), Member Secretary Ethics Board")
    ]
    for name, role, aff, qual in ec_roster:
        db.add(EthicsCommitteeMember(name=name, role=role, affiliation_type=aff, qualifications=qual, is_active=True))

    # 4. Seed Protocol Approvals
    db.add(ProtocolApproval(
        protocol_code="AYUR-CT-2026-001",
        title="Clinical Trial of Yogaraj Guggulu in Amavata",
        amendment_number="A01",
        status="Approved"
    ))

    # 5. Seed Investigational Product Batch
    ip = InvestigationalProduct(
        study_code="AYUR-CT-2026-001",
        batch_number="YOG-GUG-2026-B01",
        formulation_name="Yogaraj Guggulu Gutika (Standardized Ayurvedic Formulation)",
        dosage_form="vati",
        anupana="Ushnodaka (Luke-warm Water) or Shunthi Kwatha",
        desh="Sadharana Desha (Temperate / Sub-tropical)",
        kala="Pratah-Kala (Morning) & Sayam-Kala (Evening) before meals",
        pathya="Yava, Kulattha, Shigru, Moong dal, warm water, gentle mobilising exercises",
        apathya="Masha, Dadhi (Curd), Viruddha Ahara, cold exposure, daytime sleeping (Diva-swapna)",
        storage_temperature="Store below 25°C in a dry, cool atmosphere",
        storage_humidity="Relative humidity not exceeding 60%",
        special_instructions="Store in amber airtight HDPE containers. Do not freeze.",
        investigator_contact="+91-11-2953-8401",
        institution_name="All India Institute of Ayurveda (AIIA), New Delhi"
    )
    db.add(ip)
    db.flush()

    # 6. Seed Participants
    # Participant 1: Standard Adult Enrolled & Dosed
    p1 = Participant(
        subject_code="SUB-AIIA-001-042",
        site_id="SITE-01",
        age=45,
        gender="Female",
        is_minor=False,
        is_disabled=False,
        legal_guardian_consent_verified=False,
        tracking_profiling_prohibited=True,
        prakriti_vata=55,
        prakriti_pitta=30,
        prakriti_kapha=15,
        dominant_prakriti="Vata-Pitta",
        ayurvedic_diagnosis="Amavata (Madhyama Koshtha)",
        modern_diagnosis="Rheumatoid Arthritis (Seropositive)",
        is_enrolled=True,
        is_dosed=True,
        data_status="active"
    )
    db.add(p1)
    db.flush()
    db.add(ParticipantPII(
        participant_id=p1.id,
        encrypted_name=encrypt_pii("Radhika Sharma"),
        encrypted_phone=encrypt_pii("9876543210"),
        masked_phone=mask_phone_number("9876543210"),
        address="Pocket B, Sarita Vihar, New Delhi"
    ))
    db.add(InformedConsent(
        participant_id=p1.id,
        consent_version_id=consent_v1.id,
        language="Hindi",
        explained_orally=True,
        is_illiterate=False,
        status="active"
    ))

    # Participant 2: Minor (Age 16) with Verified Guardian Consent (DPDP Section 9)
    p2 = Participant(
        subject_code="SUB-AIIA-001-043",
        site_id="SITE-01",
        age=16,
        gender="Male",
        is_minor=True,
        is_disabled=False,
        legal_guardian_name="Smt. Kavita Verma (Mother & Lawful Guardian)",
        legal_guardian_consent_verified=True,
        tracking_profiling_prohibited=True,
        prakriti_vata=40,
        prakriti_pitta=45,
        prakriti_kapha=15,
        dominant_prakriti="Pitta-Vata",
        ayurvedic_diagnosis="Sandhigata Vata (Juvenile onset)",
        modern_diagnosis="Juvenile Idiopathic Arthritis",
        is_enrolled=True,
        is_dosed=False,
        data_status="active"
    )
    db.add(p2)
    db.flush()
    db.add(ParticipantPII(
        participant_id=p2.id,
        encrypted_name=encrypt_pii("Aarav Verma"),
        encrypted_phone=encrypt_pii("9812345678"),
        masked_phone=mask_phone_number("9812345678"),
        address="Lajpat Nagar IV, New Delhi"
    ))
    db.add(InformedConsent(
        participant_id=p2.id,
        consent_version_id=consent_v1.id,
        language="English",
        explained_orally=True,
        is_illiterate=False,
        status="active"
    ))

    # Participant 3: Illiterate Participant with Impartial Witness (GCP-ASU Part A.1)
    p3 = Participant(
        subject_code="SUB-AIIA-001-044",
        site_id="SITE-01",
        age=62,
        gender="Male",
        is_minor=False,
        is_disabled=False,
        tracking_profiling_prohibited=True,
        prakriti_vata=60,
        prakriti_pitta=20,
        prakriti_kapha=20,
        dominant_prakriti="Vata-Kapha",
        ayurvedic_diagnosis="Kaphaja Shotha with Asthigata Vata",
        modern_diagnosis="Osteoarthritis with Chronic Effusion",
        is_enrolled=True,
        is_dosed=False,
        data_status="active"
    )
    db.add(p3)
    db.flush()
    db.add(ParticipantPII(
        participant_id=p3.id,
        encrypted_name=encrypt_pii("Ram Lal Yadav"),
        encrypted_phone=encrypt_pii("9988776655"),
        masked_phone=mask_phone_number("9988776655"),
        address="Badarpur Border, Faridabad"
    ))
    db.add(InformedConsent(
        participant_id=p3.id,
        consent_version_id=consent_v1.id,
        language="Hindi",
        explained_orally=True,
        is_illiterate=True,
        impartial_witness_name="Shri Harishankar Tiwari (Social Worker)",
        impartial_witness_signature="H.S. Tiwari [Verified Thumb Impression Witness]",
        status="active"
    ))

    # Participant 4: Participant from Site-02 (Used for Tenancy & BOLA testing)
    p4 = Participant(
        subject_code="SUB-BHU-002-001",
        site_id="SITE-02",
        age=50,
        gender="Female",
        is_minor=False,
        is_disabled=False,
        tracking_profiling_prohibited=True,
        prakriti_vata=35,
        prakriti_pitta=45,
        prakriti_kapha=20,
        dominant_prakriti="Pitta-Vata",
        ayurvedic_diagnosis="Pitta-Vrita Vata",
        modern_diagnosis="Psoriatic Arthropathy",
        is_enrolled=True,
        is_dosed=False,
        data_status="active"
    )
    db.add(p4)
    db.flush()
    db.add(ParticipantPII(
        participant_id=p4.id,
        encrypted_name=encrypt_pii("Sunita Banerjee"),
        encrypted_phone=encrypt_pii("9711223344"),
        masked_phone=mask_phone_number("9711223344"),
        address="Lanka, Varanasi, Uttar Pradesh"
    ))

    # 7. Seed CERT-In Point of Contact
    db.add(CERTInPointOfContact(
        name="Prof. (Dr.) Anand Kumar",
        designation="Chief Information Security Officer (CISO)",
        organization="All India Institute of Ayurveda, Ministry of AYUSH",
        postal_address="Mathura Road, Gautampuri, Sarita Vihar, New Delhi 110076",
        email="ciso@ayurctms.gov.in",
        phone="+91-11-2953-8402"
    ))

    # 8. Seed DPDP Privacy Notice
    db.add(DPDPNotice(
        version="DPDP-V1.0",
        language="English",
        notice_text="AyurCTMS processes your health measurements solely for evaluating Ayurvedic clinical trial interventions under Ministry of AYUSH GCP-ASU standards.",
        data_categories_collected="Age, gender, pulse, blood markers, Prakriti parameters, encrypted phone number.",
        purposes="Clinical study safety and regulatory efficacy verification.",
        dpo_name=settings.DPO_NAME,
        dpo_email=settings.DPO_EMAIL,
        dpo_phone=settings.DPO_PHONE,
        is_active=True
    ))

    # 9. Seed Data Processor Contracts
    db.add(DataProcessorContract(
        processor_name="AWS Cloud India (Amazon Web Services India Pvt Ltd)",
        service_type="Cloud Infrastructure & Database Hosting (Mumbai Region)",
        dpdp_compliant_agreement=True,
        data_location="Mumbai, Maharashtra, India"
    ))
    db.add(DataProcessorContract(
        processor_name="SRL Diagnostics Central Testing Lab",
        service_type="Central Bio-analytical Laboratory",
        dpdp_compliant_agreement=True,
        data_location="Delhi-NCR, India"
    ))

    db.commit()

    # Genesis Audit Log Entry
    log_audit_event(
        db=db,
        user_id=None,
        user_email="system@ayurctms.gov.in",
        role="System Initialization",
        ip_address="127.0.0.1",
        action="GENESIS_SYSTEM_INITIALIZATION",
        entity_type="Ledger",
        entity_id="GENESIS",
        details="AyurCTMS Enterprise Compliant Ledger initialized with SHA-256 cryptographic chain."
    )

    print("[AyurCTMS] Initial database seeding completed successfully.")


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Initialize DB Schema
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        seed_synthetic_data(db)
    finally:
        db.close()
    yield

app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description="Regulatory-Compliant Ayurveda Clinical Trial Management System (GCP-ASU, DPDP Act 2023, CERT-In Directions 2022, OWASP Hardened)",
    lifespan=lifespan,
    docs_url="/docs" if settings.ENVIRONMENT != "production" else None,
    redoc_url=None
)

# Attach Security Headers & Rate Limiting Middleware
app.add_middleware(SecurityHeadersMiddleware)

# Strict CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:5173", "http://127.0.0.1:3000", "http://127.0.0.1:5173", "http://localhost:8000"],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
    expose_headers=["X-Session-Timeout-Minutes", "X-Data-Residency"]
)

# Register API Subsystems
app.include_router(auth.router, prefix="/api")
app.include_router(participants.router, prefix="/api")
app.include_router(consent.router, prefix="/api")
app.include_router(ethics.router, prefix="/api")
app.include_router(ethics.legal_router, prefix="/api")
app.include_router(clinical_ayurveda.router, prefix="/api")
app.include_router(investigational_products.router, prefix="/api")
app.include_router(monitoring.router, prefix="/api")
app.include_router(dpdp.router, prefix="/api")
app.include_router(cert_in.router, prefix="/api")
app.include_router(compliance.router, prefix="/api")
app.include_router(audit.router, prefix="/api")
app.include_router(files.router, prefix="/api")
app.include_router(supabase_integration.router, prefix="/api")
app.include_router(escalations.router, prefix="/api")
app.include_router(tasks.router, prefix="/api")

@app.get("/api/health")
def health_check():
    return {
        "status": "healthy",
        "service": settings.PROJECT_NAME,
        "version": settings.VERSION,
        "compliance": {
            "GCP-ASU": "Compliant (Ministry of AYUSH)",
            "DPDP_Act_2023": "Compliant (DPDP Rules 2025)",
            "CERT-In": "Compliant (Directions 28 April 2022)",
            "OWASP": "Top 10 2021 & API Security Top 10 2023 Hardened"
        },
        "residency": settings.PRIMARY_DATA_RESIDENCY
    }

frontend_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "frontend"))
if os.path.exists(frontend_path):
    app.mount("/", StaticFiles(directory=frontend_path, html=True), name="frontend")

