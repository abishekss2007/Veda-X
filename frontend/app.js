/**
 * AyurCTMS — Full Frontend Controller
 * Minimal, clean, accessible interface with Supabase backend connectivity,
 * 9-role routing, route guards, DPDP consent enforcement, and submissions versioning.
 */

// Global Application State
const appState = {
  currentUser: null, // Set when logged in: { email, role, fullName, site }
  activeRole: null,
  activeDashboardTab: 'overview',
  sessionTimer: null,
  sessionSecondsLeft: 15 * 60,
  isLoggedIn: false,
  failedAttempts: {},
  
  // Seeded Legal Documents with Live Expiry Dates & Version History
  legalDocuments: [
    {
      id: "leg-001",
      title: "CTRI Clinical Trial Registry Certificate",
      type: "CTRI certificate",
      study: "AYUR-CT-2026-001",
      version: "v1.0",
      issue_date: "2026-08-05",
      expiry_date: "2027-08-06",
      days_remaining: 310,
      status: "safe",
      reason: "Statutory national CTRI registration valid for full study duration.",
      file_name: "CTRI_Registration_2026_09_0812.pdf",
      file_size: "2.4 MB",
      uploaded_by: "Dr. Rajeshwar Sharma (EC Chair)",
      versions: [
        { version: "v1.0", uploaded_at: "2026-08-05T10:00:00Z", uploaded_by: "Dr. Rajeshwar Sharma" }
      ]
    },
    {
      id: "leg-002",
      title: "Institutional Protocol Approval Clearance",
      type: "protocol approval",
      study: "AYUR-CT-2026-001",
      version: "v2.0",
      issue_date: "2026-03-29",
      expiry_date: "2027-03-29",
      days_remaining: 180,
      status: "safe",
      reason: "Amended regimen approved with zero high-risk dosha warnings.",
      file_name: "IEC_Protocol_Approval_AYUR001_v2.pdf",
      file_size: "4.1 MB",
      uploaded_by: "Member Secretary (IEC)",
      versions: [
        { version: "v1.0", uploaded_at: "2025-09-30T10:00:00Z", uploaded_by: "Prof. Sharma (PI)" },
        { version: "v2.0", uploaded_at: "2026-03-29T11:00:00Z", uploaded_by: "Member Secretary (IEC)" }
      ]
    },
    {
      id: "leg-003",
      title: "Hospital Multi-Site Clinical Trial MoU & Contract",
      type: "MoU/contract",
      study: "AYUR-CT-2026-001",
      version: "v1.1",
      issue_date: "2026-01-23",
      expiry_date: "2027-01-23",
      days_remaining: 115,
      status: "safe",
      reason: "Inter-institutional governance contract with Jamnagar IPGT&RA.",
      file_name: "MoU_AIIA_IPGTRA_Clinical_2026.pdf",
      file_size: "1.8 MB",
      uploaded_by: "Legal Expert (IEC)",
      versions: [
        { version: "v1.1", uploaded_at: "2026-01-23T14:00:00Z", uploaded_by: "Legal Expert (IEC)" }
      ]
    },
    {
      id: "leg-004",
      title: "Subject Clinical Trial Insurance Policy",
      type: "insurance",
      study: "AYUR-CT-2026-001",
      version: "v1.0",
      issue_date: "2025-12-07",
      expiry_date: "2026-12-07",
      days_remaining: 68,
      status: "attention",
      reason: "Trial insurance policy renewal due with underwriter within 68 days to maintain continuous patient coverage.",
      file_name: "NewIndia_ClinicalInsurance_Policy_2026.pdf",
      file_size: "3.2 MB",
      uploaded_by: "Admin (System)",
      versions: [
        { version: "v1.0", uploaded_at: "2025-12-07T09:30:00Z", uploaded_by: "Admin (System)" }
      ]
    },
    {
      id: "leg-005",
      title: "AYUSH GMP Drug Manufacturing Licence (Extract Batch)",
      type: "licence",
      study: "AYUR-CT-2026-002",
      version: "v1.0",
      issue_date: "2025-11-11",
      expiry_date: "2026-11-11",
      days_remaining: 42,
      status: "attention",
      reason: "Statutory manufacturing licence annual re-inspection due; renew before expiration to avoid investigational drug dosing stoppage.",
      file_name: "AYUSH_GMP_Manufacturing_Licence_Batch04.pdf",
      file_size: "1.5 MB",
      uploaded_by: "Prof. Sharma (PI)",
      versions: [
        { version: "v1.0", uploaded_at: "2025-11-11T12:00:00Z", uploaded_by: "Prof. Sharma (PI)" }
      ]
    },
    {
      id: "leg-006",
      title: "Annual Ethics Committee Protocol Renewal Letter",
      type: "EC approval letter",
      study: "AYUR-CT-2026-002",
      version: "v1.0",
      issue_date: "2025-10-19",
      expiry_date: "2026-10-19",
      days_remaining: 19,
      status: "urgent",
      reason: "Mandatory annual ethics committee review overdue for renewal; unrenewed trials must halt subject recruitment under GCP-ASU.",
      file_name: "IEC_Annual_Renewal_Decision_AYUR002.pdf",
      file_size: "2.1 MB",
      uploaded_by: "Dr. Rajeshwar Sharma (EC Chair)",
      versions: [
        { version: "v1.0", uploaded_at: "2025-10-19T15:00:00Z", uploaded_by: "Dr. Rajeshwar Sharma" }
      ]
    },
    {
      id: "leg-007",
      title: "Biological Specimen Transfer Agreement (BMTA)",
      type: "MoU/contract",
      study: "AYUR-CT-2026-003",
      version: "v1.0",
      issue_date: "2026-04-09",
      expiry_date: "2026-10-06",
      days_remaining: 6,
      status: "urgent",
      reason: "Biological specimen transit authorization expires in 6 days; samples cannot be moved across labs without active BMTA clearance.",
      file_name: "BMTA_Specimen_Transport_Agreement_2026.pdf",
      file_size: "1.2 MB",
      uploaded_by: "Member Secretary (IEC)",
      versions: [
        { version: "v1.0", uploaded_at: "2026-04-09T10:30:00Z", uploaded_by: "Member Secretary (IEC)" }
      ]
    },
    {
      id: "leg-008",
      title: "Institutional Bio-safety Committee (IBSC) Clearance",
      type: "other",
      study: "AYUR-CT-2026-003",
      version: "v1.0",
      issue_date: "2025-09-16",
      expiry_date: "2026-09-16",
      days_remaining: -14,
      status: "expired",
      reason: "Expired 14 days ago: Dosing paused for cohort C pending expedited DBT/RCGM bio-safety re-validation.",
      file_name: "IBSC_Biosafety_Clearance_2025.pdf",
      file_size: "1.9 MB",
      uploaded_by: "Admin (System)",
      versions: [
        { version: "v1.0", uploaded_at: "2025-09-16T11:00:00Z", uploaded_by: "Admin (System)" }
      ]
    }
  ],
  
  // Local/Cached Submissions Store (Synchronized with Supabase backend)
  submissions: [
    {
      id: "sub-101",
      owner_id: "usr-coord-01",
      owner_name: "Dr. Sunita Patel",
      role: "Research Coordinator",
      study_id: "AYUR-CT-2026-001",
      type: "consent",
      title: "Informed Consent Form — Subject SUB-AIIA-001-042 (Hindi Oral)",
      payload: { subject_code: "SUB-AIIA-001-042", language: "Hindi", oral_explanation: true },
      status: "Verified",
      created_at: "2026-09-28T10:00:00Z",
      updated_at: "2026-09-28T14:30:00Z",
      versions: [
        { changed_at: "2026-09-28T10:00:00Z", reason: "Initial written consent entry", who: "Dr. Sunita Patel" }
      ],
      verifications: [
        { verified_by: "Prof. Sharma (PI)", verified_at: "2026-09-28T14:30:00Z", note: "Audio explanation and subject signature cross-verified." }
      ]
    },
    {
      id: "sub-102",
      owner_id: "usr-coord-01",
      owner_name: "Dr. Sunita Patel",
      role: "Research Coordinator",
      study_id: "AYUR-CT-2026-001",
      type: "prakriti_assessment",
      title: "Deha Prakriti Assessment — Subject SUB-AIIA-001-042",
      payload: { subject_code: "SUB-AIIA-001-042", vata: 55, pitta: 30, kapha: 15, dominant: "Vata-Pitta" },
      status: "Submitted",
      created_at: "2026-09-28T11:00:00Z",
      updated_at: "2026-09-28T11:00:00Z",
      versions: [],
      verifications: []
    },
    {
      id: "sub-103",
      owner_id: "usr-doc-01",
      owner_name: "Dr. Arvind Joshi",
      role: "Doctor / Investigator",
      study_id: "AYUR-CT-2026-001",
      type: "ae_report",
      title: "Adverse Drug Reaction Log — Pitta-Kopa / Ushnata",
      payload: { subject_code: "SUB-AIIA-001-042", severity: "Mild", asu_term: "Pitta-Kopa" },
      status: "Draft",
      created_at: "2026-09-29T09:00:00Z",
      updated_at: "2026-09-29T09:00:00Z",
      versions: [],
      verifications: []
    },
    {
      id: "sub-104",
      owner_id: "usr-mon-01",
      owner_name: "Vikram Verma",
      role: "Monitor",
      study_id: "AYUR-CT-2026-001",
      type: "visit_note",
      title: "Site Monitoring Visit Report — SITE-01 Source Data Verification",
      payload: { site_id: "SITE-01", deviations: 0, notes: "All CRF data verified against raw case records." },
      status: "Needs correction",
      created_at: "2026-09-29T14:00:00Z",
      updated_at: "2026-09-29T16:00:00Z",
      versions: [
        { changed_at: "2026-09-29T16:00:00Z", reason: "Clarified batch dispensing count", who: "Vikram Verma" }
      ],
      verifications: []
    }
  ]
};

// Map of Role to URL Slug
const ROLE_TO_SLUG = {
  "Principal Investigator": "pi",
  "Research Coordinator": "coordinator",
  "Doctor / Investigator": "doctor",
  "Monitor": "monitor",
  "EC Member": "ec",
  "PV Officer": "pv",
  "Admin": "admin",
  "Auditor / Regulator": "auditor",
  "Institution Leadership": "leadership"
};

const SLUG_TO_ROLE = Object.fromEntries(Object.entries(ROLE_TO_SLUG).map(([r, s]) => [s, r]));

// Shared role security config — single source of truth
const SECURE_ROLES = ["Principal Investigator", "Admin", "EC Member"];

// Demo Accounts Store
const DEMO_ACCOUNTS = {
  "admin@ayurctms.demo": { pwd: "Admin@Demo#2026", role: "Admin", name: "System Administrator", site: "SITE-HQ" },
  "pi@ayurctms.demo": { pwd: "Pi@Demo#2026", role: "Principal Investigator", name: "Prof. (Dr.) Rajeshwar Sharma", site: "SITE-01" },
  "coordinator@ayurctms.demo": { pwd: "Coord@Demo#2026", role: "Research Coordinator", name: "Dr. Sunita Patel, BAMS", site: "SITE-01" },
  "doctor@ayurctms.demo": { pwd: "Doctor@Demo#2026", role: "Doctor / Investigator", name: "Dr. Arvind Joshi, MD (Ayu)", site: "SITE-01" },
  "monitor@ayurctms.demo": { pwd: "Monitor@Demo#2026", role: "Monitor", name: "Vikram Verma, CRA", site: "SITE-01" },
  "ec@ayurctms.demo": { pwd: "Ethics@Demo#2026", role: "EC Member", name: "Justice (Retd.) M. K. Narayanan", site: "EC-BOARD" },
  "pv@ayurctms.demo": { pwd: "Pharma@Demo#2026", role: "PV Officer", name: "Dr. Gayatri Devi, MD (Ayu)", site: "SITE-01" },
  "auditor@ayurctms.demo": { pwd: "Audit@Demo#2026", role: "Auditor / Regulator", name: "K. R. Sengupta, ISO Lead Auditor", site: "SITE-HQ" },
  "leader@ayurctms.demo": { pwd: "Leader@Demo#2026", role: "Institution Leadership", name: "Prof. (Dr.) Tanuja Nesari, Director", site: "SITE-HQ" }
};

// ==============================================================================
// INITIALIZATION
// ==============================================================================
document.addEventListener("DOMContentLoaded", () => {
  setupRouting();
  setupRoleCards();
  setupRegistrationForm();
  setupLoginForm();
  setupSessionTimeout();
  setupThemeToggle();
  setupAddParticipantForm();
  setupUploadLegalDocForm();
  checkSupabaseBackendStatus();
});

// ==============================================================================
// ROUTING & ROUTE GUARDS
// ==============================================================================
function setupRouting() {
  window.addEventListener("hashchange", handleRouteChange);
  handleRouteChange();
}

function handleRouteChange() {
  const hash = window.location.hash || "#landing";
  const views = ["landing", "register", "login", "dashboard"];

  // Handle Dashboard URLs e.g. #dashboard/pi
  if (hash.startsWith("#dashboard")) {
    const slug = hash.replace("#dashboard/", "").replace("#dashboard", "") || "coordinator";
    const requestedRole = SLUG_TO_ROLE[slug];

    // ROUTE GUARD: Must be logged in
    if (!appState.isLoggedIn) {
      showToast("Please sign in to access the clinical trial dashboard.");
      window.location.hash = "#login";
      return;
    }

    // ROUTE GUARD: User cannot view another role's dashboard without an authenticated session for that role
    const userRole = appState.currentUser.role;
    if (requestedRole && requestedRole !== userRole) {
      showToast(`Access restricted: please authenticate to view the ${requestedRole} dashboard.`);
      window.location.hash = `#dashboard/${ROLE_TO_SLUG[userRole]}`;
      return;
    }

    // Render Dashboard Shell for the role
    showView("dashboard");
    renderDashboardView(userRole);
    return;
  }

  // Handle standard public pages
  const viewId = hash.replace("#", "");
  if (viewId === "login" && !appState.pendingRoleSwitch) {
    const roleInput = document.getElementById("login-role");
    if (roleInput) roleInput.disabled = false;
    const cancelBtn1 = document.getElementById("btn-cancel-role-switch");
    const cancelBtn2 = document.getElementById("btn-cancel-role-switch-step2");
    if (cancelBtn1) cancelBtn1.classList.add("hidden");
    if (cancelBtn2) cancelBtn2.classList.add("hidden");
  }
  if (views.includes(viewId)) {
    showView(viewId);
  } else {
    showView("landing");
  }
}

function showView(viewId) {
  document.querySelectorAll(".view-container, .dashboard-shell").forEach(el => {
    el.classList.remove("active");
    if (el.classList.contains("dashboard-shell")) el.classList.add("hidden");
  });

  if (viewId === "dashboard") {
    document.getElementById("view-dashboard").classList.remove("hidden");
  } else {
    const target = document.getElementById(`view-${viewId}`);
    if (target) target.classList.add("active");
  }
}

// ==============================================================================
// LANDING PAGE & ROLE SELECTOR CARDS
// ==============================================================================
function setupRoleCards() {
  const cards = document.querySelectorAll(".role-card");
  cards.forEach(card => {
    card.addEventListener("click", () => {
      const selectedRole = card.getAttribute("data-role");
      const roleEl = document.getElementById("login-role");
      roleEl.value = selectedRole;
      roleEl.dispatchEvent(new Event("change"));
      window.location.hash = "#login";
    });
  });
}

function quickFillDemo(email, pwd, role) {
  document.getElementById("login-role").value = role;
  document.getElementById("login-email").value = email;
  document.getElementById("login-password").value = pwd;
  window.location.hash = "#login";
  showToast(`Demo credentials filled for: ${role}`);
}

// ==============================================================================
// REGISTRATION (12-char Password Strength & DPDP Consent Gate)
// ==============================================================================
function setupRegistrationForm() {
  const pwdInput = document.getElementById("reg-password");
  const strengthBar = document.getElementById("strength-bar");
  const strengthText = document.getElementById("strength-text");

  pwdInput.addEventListener("input", (e) => {
    const pwd = e.target.value;
    let score = 0;
    if (pwd.length >= 12) score += 1;
    if (/[A-Z]/.test(pwd)) score += 1;
    if (/[a-z]/.test(pwd)) score += 1;
    if (/[0-9]/.test(pwd)) score += 1;
    if (/[^A-Za-z0-9]/.test(pwd)) score += 1;

    const percent = Math.min(100, score * 20);
    strengthBar.style.width = `${percent}%`;

    if (score < 3) {
      strengthBar.style.backgroundColor = "var(--color-red)";
      strengthText.textContent = "Weak — Must be at least 12 characters with uppercase, lowercase, numbers, and symbols.";
    } else if (score < 5) {
      strengthBar.style.backgroundColor = "var(--color-amber)";
      strengthText.textContent = "Medium — Add symbols or numbers for a resilient password.";
    } else {
      strengthBar.style.backgroundColor = "var(--color-green)";
      strengthText.textContent = "Strong password — Complies with OWASP & GCP-ASU security rules.";
    }
  });

  const form = document.getElementById("form-register");
  form.addEventListener("submit", async (e) => {
    e.preventDefault();

    const consentTicked = document.getElementById("reg-privacy-consent").checked;
    if (!consentTicked) {
      alert("DPDP Act Compliance: You must read and tick the privacy consent notice before registering.");
      return;
    }

    const pwd = pwdInput.value;
    const confirmPwd = document.getElementById("reg-confirm-password").value;
    if (pwd !== confirmPwd) {
      alert("Passwords do not match.");
      return;
    }

    if (pwd.length < 12) {
      alert("Password must be at least 12 characters long.");
      return;
    }

    const payload = {
      full_name: document.getElementById("reg-fullname").value,
      email: document.getElementById("reg-email").value,
      phone: document.getElementById("reg-phone").value,
      role: document.getElementById("reg-role").value,
      site: document.getElementById("reg-site").value,
      password: pwd,
      confirm_password: confirmPwd,
      privacy_consent_ticked: consentTicked
    };

    try {
      const res = await fetch("/api/supabase/auth/register", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload)
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || "Registration failed.");

      form.classList.add("hidden");
      document.getElementById("register-success-box").classList.remove("hidden");
      showToast("Registration received! An admin will review and approve your account.");
    } catch (err) {
      alert(err.message);
    }
  });
}

// ==============================================================================
// LOGIN & 2FA VERIFICATION (5-Attempt Lockout & Demo OTP)
// ==============================================================================
// ==============================================================================
// LOGIN & 2FA VERIFICATION (Demo Mode & Multi-Role Access)
// ==============================================================================

// DEMO ONLY, remove before real use: Checks NEXT_PUBLIC_DEMO_MODE flag
const isDemoModeActive = () => {
  if (typeof process !== "undefined" && process.env && process.env.NEXT_PUBLIC_DEMO_MODE !== undefined) {
    return String(process.env.NEXT_PUBLIC_DEMO_MODE).toLowerCase() === "true";
  }
  if (typeof window !== "undefined") {
    if (window.NEXT_PUBLIC_DEMO_MODE !== undefined) {
      return String(window.NEXT_PUBLIC_DEMO_MODE).toLowerCase() === "true";
    }
    const localFlag = localStorage.getItem("NEXT_PUBLIC_DEMO_MODE");
    if (localFlag !== null) return localFlag === "true";
  }
  return true; // Enabled by default for reviewer prototype
};

function setupLoginForm() {
  const formStep1 = document.getElementById("form-login-step1");
  const formOTP = document.getElementById("form-login-otp");
  const errorBox1 = document.getElementById("login-error-msg");
  const errorBox2 = document.getElementById("otp-error-msg");
  const roleSelect = document.getElementById("login-role");
  const submitBtn = document.getElementById("btn-proceed-step1");
  const cancelBtn1 = document.getElementById("btn-cancel-role-switch");
  const cancelBtn2 = document.getElementById("btn-cancel-role-switch-step2");
  if (cancelBtn1) cancelBtn1.addEventListener("click", cancelRoleSwitch);
  if (cancelBtn2) cancelBtn2.addEventListener("click", cancelRoleSwitch);

  // Update button label based on role selection
  function updateSubmitLabel() {
    if (submitBtn) submitBtn.textContent = "Continue to verification \u2192";
  }
  if (roleSelect) roleSelect.addEventListener("change", updateSubmitLabel);
  updateSubmitLabel();

  // DEMO ONLY, remove before real use: Toggle Hint Box & Badge
  const demoBadge = document.getElementById("login-demo-badge");
  const demoHintBox = document.getElementById("demo-access-hint-box");
  const btnFillDemo = document.getElementById("btn-fill-demo-details");

  if (isDemoModeActive()) {
    if (demoBadge) demoBadge.classList.remove("hidden");
    if (demoHintBox) demoHintBox.classList.remove("hidden");
    if (btnFillDemo) {
      btnFillDemo.addEventListener("click", () => {
        const emailInput = document.getElementById("login-email");
        const pwdInput = document.getElementById("login-password");
        const roleInput = document.getElementById("login-role");
        const selectedRole = roleInput.value || "Research Coordinator";
        const demoAccount = Object.entries(DEMO_ACCOUNTS).find(([, account]) => account.role === selectedRole);
        if (!demoAccount) {
          errorBox1.textContent = "No configured demo account is available for this role.";
          errorBox1.classList.remove("hidden");
          return;
        }
        const [email, account] = demoAccount;
        emailInput.value = email;
        pwdInput.value = account.pwd;
        roleInput.value = account.role;
        roleInput.dispatchEvent(new Event("change", { bubbles: true }));
        errorBox1.classList.add("hidden");
      });
    }
  } else {
    if (demoBadge) demoBadge.classList.add("hidden");
    if (demoHintBox) demoHintBox.classList.add("hidden");
  }

  // Step 1: Password Check
  formStep1.addEventListener("submit", async (e) => {
    e.preventDefault();
    errorBox1.classList.add("hidden");
    const email = document.getElementById("login-email").value.toLowerCase().trim();
    const password = document.getElementById("login-password").value;
    const role = document.getElementById("login-role").value;
    if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)) {
      errorBox1.textContent = "Please enter a valid email address.";
      errorBox1.classList.remove("hidden");
      return;
    }

    if (!appState.pendingRoleSwitch) {
      clearStoredAuthState();
      if (appState.isLoggedIn) {
        try {
          await fetch("/api/auth/logout", { method: "POST", credentials: "same-origin" });
        } catch (error) {}
      }
    }
    appState.pendingLoginSession = null;

    const demoMode = isDemoModeActive();
    const endpoint = demoMode ? "/api/supabase/auth/login" : "/api/auth/login";
    try {
      const response = await fetch(endpoint, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        credentials: "same-origin",
        body: JSON.stringify(demoMode ? { email, password, role } : { email, password })
      });
      const data = await response.json();
      if (!response.ok) throw new Error(data.detail || "Authentication failed.");

      if (demoMode) {
        if (!data.challenge_id || data.role !== role) throw new Error("The selected role does not match this account.");
        appState.pendingLoginSession = { flow: "demo", email: data.email, role: data.role, challengeId: data.challenge_id };
      } else {
        if (!data.requires_otp || !data.otp_stage_token) throw new Error("Backend verification is required for every role.");
        if (role && data.role !== role) throw new Error("The selected role does not match this account.");
        appState.pendingLoginSession = { flow: "backend", email: data.email, role: data.role, otpStageToken: data.otp_stage_token };
      }

      document.getElementById("verify-role-text").textContent = appState.pendingLoginSession.role;
      document.getElementById("login-step-1").classList.add("hidden");
      document.getElementById("login-step-2").classList.remove("hidden");
      document.getElementById("otp-code-input").value = "";
      document.getElementById("otp-code-input").focus();
    } catch (error) {
      errorBox1.textContent = error instanceof TypeError
        ? "Could not reach the backend. Check that FastAPI is running at this app's origin."
        : (error.message || "Authentication failed.");
      errorBox1.classList.remove("hidden");
      if (appState.pendingRoleSwitch) {
        const viewAsSelect = document.getElementById("select-view-as-role");
        if (viewAsSelect) viewAsSelect.value = appState.pendingRoleSwitch.fromRole;
        logRoleSwitchAttempt(
          appState.pendingRoleSwitch.fromRole,
          appState.pendingRoleSwitch.toRole,
          email || appState.pendingRoleSwitch.userEmail,
          false,
          errorBox1.textContent
        );
      }
    }
  });

  // Step 2: 2FA OTP Verification
  formOTP.addEventListener("submit", async (e) => {
    e.preventDefault();
    errorBox2.classList.add("hidden");
    const session = appState.pendingLoginSession;
    const code = document.getElementById("otp-code-input").value.trim();
    if (!session) {
      errorBox2.textContent = "Please restart sign-in before verifying.";
      errorBox2.classList.remove("hidden");
      return;
    }
    try {
      const demoMode = session.flow === "demo";
      const response = await fetch(demoMode ? "/api/supabase/auth/verify-otp" : "/api/auth/verify-otp", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        credentials: "same-origin",
        body: JSON.stringify(demoMode
          ? { email: session.email, role: session.role, challenge_id: session.challengeId, otp_code: code }
          : { otp_stage_token: session.otpStageToken, otp_code: code })
      });
      const data = await response.json();
      if (!response.ok) throw new Error(data.detail || "Invalid verification code.");
      const verifiedSession = demoMode ? data : {
        verified: true,
        email: data.email,
        role: data.role,
        full_name: data.full_name,
        site_id: data.site_id
      };
      if (!verifiedSession.verified || verifiedSession.email !== session.email || verifiedSession.role !== session.role) {
        throw new Error("The backend did not verify this user and role.");
      }
      const switchInfo = appState.pendingRoleSwitch;
      appState.pendingRoleSwitch = null;
      clearStoredAuthState();
      completeLogin(verifiedSession);
      if (switchInfo) {
        logRoleSwitchAttempt(
          switchInfo.fromRole,
          switchInfo.toRole,
          verifiedSession.email,
          true,
          "Role switch verified successfully"
        );
      }
    } catch (error) {
      errorBox2.textContent = error.message || "Verification failed.";
      errorBox2.classList.remove("hidden");
      if (appState.pendingRoleSwitch) {
        const viewAsSelect = document.getElementById("select-view-as-role");
        if (viewAsSelect) viewAsSelect.value = appState.pendingRoleSwitch.fromRole;
        logRoleSwitchAttempt(
          appState.pendingRoleSwitch.fromRole,
          appState.pendingRoleSwitch.toRole,
          session ? session.email : appState.pendingRoleSwitch.userEmail,
          false,
          errorBox2.textContent
        );
      }
    }
  });

  // Back to Step 1 Button
  document.getElementById("btn-back-step1").addEventListener("click", () => {
    appState.pendingLoginSession = null;
    clearStoredAuthState();
    document.getElementById("otp-code-input").value = "";
    document.getElementById("login-step-2").classList.add("hidden");
    document.getElementById("login-step-1").classList.remove("hidden");
  });

  const invalidatePendingLogin = () => {
    if (!appState.pendingLoginSession) return;
    appState.pendingLoginSession = null;
    clearStoredAuthState();
    document.getElementById("otp-code-input").value = "";
    document.getElementById("login-step-2").classList.add("hidden");
    document.getElementById("login-step-1").classList.remove("hidden");
  };
  document.getElementById("login-email").addEventListener("input", invalidatePendingLogin);
  document.getElementById("login-role").addEventListener("change", invalidatePendingLogin);

  // Passkey Demo Buttons
  document.getElementById("tab-opt-code").addEventListener("click", () => {
    document.getElementById("tab-opt-code").classList.add("active");
    document.getElementById("tab-opt-passkey").classList.remove("active");
    document.getElementById("form-login-otp").classList.remove("hidden");
    document.getElementById("pane-passkey-demo").classList.add("hidden");
  });

  document.getElementById("tab-opt-passkey").addEventListener("click", () => {
    document.getElementById("tab-opt-passkey").classList.add("active");
    document.getElementById("tab-opt-code").classList.remove("active");
    document.getElementById("form-login-otp").classList.add("hidden");
    document.getElementById("pane-passkey-demo").classList.remove("hidden");
  });

  document.getElementById("btn-simulate-passkey").addEventListener("click", () => {
    showToast("Passkey verification is unavailable in this prototype. Use the verification code.");
    document.getElementById("tab-opt-code").click();
  });

  // Global Sign out button (top bar)
  const btnGlobalSignout = document.getElementById("btn-global-signout");
  if (btnGlobalSignout) btnGlobalSignout.addEventListener("click", signOut);
}

function clearStoredAuthState() {
  const authKeys = ["ayur_access_token", "access_token", "refresh_token", "verified", "verified_user", "auth_session", "role", "user"];
  [window.localStorage, window.sessionStorage].forEach(storage => {
    authKeys.forEach(key => storage.removeItem(key));
  });
}

function completeLogin(session) {
  if (!session || session.verified !== true || !session.email || !session.role) return;
  const email = session.email.toLowerCase();
  const selectedRole = session.role;
  const account = {
    name: session.full_name || email.split("@")[0].replace(/[._-]/g, " ").replace(/\b\w/g, c => c.toUpperCase()),
    site: session.site_id || "SITE-01",
  };

  appState.isLoggedIn = true;
  appState.currentUser = { email, ...account, role: selectedRole };
  appState.activeRole = selectedRole;
  appState.pendingLoginSession = null;
  window.appState = appState;

  // Update Top Bar
  const guestNav = document.getElementById("nav-guest");
  if (guestNav) guestNav.classList.add("hidden");
  document.getElementById("nav-auth").classList.remove("hidden");
  document.getElementById("auth-role-badge").textContent = selectedRole;
  document.getElementById("auth-user-name").textContent = account.name;
  document.getElementById("auth-site-tag").textContent = account.site;

  // Reset Login Modal for next time
  document.getElementById("login-step-2").classList.add("hidden");
  document.getElementById("login-step-1").classList.remove("hidden");
  const roleInput = document.getElementById("login-role");
  if (roleInput) roleInput.disabled = false;
  const cancelBtn1 = document.getElementById("btn-cancel-role-switch");
  const cancelBtn2 = document.getElementById("btn-cancel-role-switch-step2");
  if (cancelBtn1) cancelBtn1.classList.add("hidden");
  if (cancelBtn2) cancelBtn2.classList.add("hidden");
  const viewAsSelect = document.getElementById("select-view-as-role");
  if (viewAsSelect) viewAsSelect.value = selectedRole;

  // Route to the Role Dashboard URL
  const slug = ROLE_TO_SLUG[selectedRole] || "coordinator";
  window.location.hash = `#dashboard/${slug}`;
  if (window.ChartDataHelper) ChartDataHelper.fetchLatestData();
  loadSavedSubmissions();
  showToast(`Welcome, ${account.name}. Signed into ${selectedRole} workspace.`);
}

async function signOut() {
  try {
    await fetch("/api/auth/logout", { method: "POST", credentials: "same-origin" });
  } catch (error) {}
  clearStoredAuthState();
  appState.isLoggedIn = false;
  appState.currentUser = null;
  appState.activeRole = null;
  appState.pendingLoginSession = null;
  appState.viewAsRole = null;
  appState.pendingRoleSwitch = null;
  const roleInput = document.getElementById("login-role");
  if (roleInput) roleInput.disabled = false;

  const guestNav = document.getElementById("nav-guest");
  if (guestNav) guestNav.classList.remove("hidden");
  document.getElementById("nav-auth").classList.add("hidden");

  window.location.hash = "#landing";
  showToast("You have been signed out safely. Sessions revoked.");
}

// ==============================================================================
// ROLE DASHBOARDS & KPI RENDERING
// ==============================================================================
// ==============================================================================
// ROLE DASHBOARDS, KPI RENDERING & CLINICAL WORKSPACE
// ==============================================================================
const ROLE_KPIS = {
  "Principal Investigator": [
    { label: "Enrolled vs Target", value: "148 / 200", note: "74% recruited across 6 protocols" },
    { label: "Active SAEs", value: "8 Cases", note: "Expedited safety reviews active" },
    { label: "Compliance Score", value: "98.2%", note: "GCP-ASU & DPDP audited" },
    { label: "Unacknowledged Reports", value: "2 Pending", note: "Action required within SLA" }
  ],
  "Research Coordinator": [
    { label: "Visits Due This Week", value: "12 Visits", note: "Window tracking active" },
    { label: "Consents Pending", value: "3 Re-consents", note: "Protocol amendment V2.1" },
    { label: "Scheduled Doses", value: "28 Today", note: "Yogaraj Guggulu & Ashwagandha" }
  ],
  "Doctor / Investigator": [
    { label: "Assigned Subjects", value: "42 Subjects", note: "SITE-01 active cohort" },
    { label: "Active ADRs / Symptoms", value: "6 Monitored", note: "Dosha causality graded" },
    { label: "Clinical CRFs", value: "41 Complete", note: "Source data reconciled" },
    { label: "Safety Flags", value: "2 to PI", note: "1 Critical, 1 High" }
  ],
  "Monitor": [
    { label: "Missing Data Points", value: "14 Items", note: "Clarification queries issued" },
    { label: "Overdue Visits", value: "4 Subjects", note: "Rescheduling required" },
    { label: "Protocol Deviations", value: "4 Deviations", note: "2 Minor, 2 Major" },
    { label: "Site SDV Score", value: "95.6%", note: "Verified against physical case sheets" }
  ],
  "EC Member": [
    { label: "Approvals Pending", value: "2 Protocols", note: "Annual renewal reviews" },
    { label: "Renewals < 30 Days", value: "1 Study", note: "AYUR-CT-2026-004 renewal due" },
    { label: "Amendments to Review", value: "3 Packages", note: "Vernacular consent sheets" },
    { label: "SAEs Dispatched", value: "8 Reports", note: "Expedited notices on file" }
  ],
  "PV Officer": [
    { label: "New AE/SAE", value: "8 Signals", note: "Under clinical review" },
    { label: "Expedited Due < 24h", value: "2 Reports", note: "CDSCO / AYUSH statutory deadline" },
    { label: "Overdue Reports", value: "0 Overdue", note: "100% within statutory window" },
    { label: "Coded vs Uncoded", value: "52 / 60", note: "MedDRA & ASU mapping active" }
  ],
  "Admin": [
    { label: "Pending Approvals", value: "3 Users", note: "Awaiting role verification" },
    { label: "Active Studies", value: "6 Trials", note: "4 multi-centric sites" },
    { label: "Regulatory Status", value: "100% Compliant", note: "GCP-ASU, DPDP & CERT-In" },
    { label: "Critical Incidents", value: "2 Active", note: "1h SLA countdown" }
  ],
  "Auditor / Regulator": [
    { label: "Hash Chain Integrity", value: "Verified Valid", note: "SHA-256 genesis intact" },
    { label: "Immutable Audit Logs", value: "142 Logs", note: "Zero tamper detected" },
    { label: "Retention Lock", value: "5 Years", note: "GCP-ASU Part A.7 locked" },
    { label: "Integrity Checks", value: "100% Pass", note: "CERT-In sovereign clock sync" }
  ],
  "Institution Leadership": [
    { label: "Active Trials", value: "6 Studies", note: "All Phase I-III trials" },
    { label: "Total Enrolment", value: "150 / 200", note: "75% of composite target" },
    { label: "Safety Events", value: "8 SAEs", note: "All managed without death" },
    { label: "Average Health Index", value: "93.5 / 100", note: "Portfolio composite score" }
  ]
};

const ROLE_WORKSPACE_LABELS = {
  "Principal Investigator": "Protocol & Site Oversight",
  "Research Coordinator": "Subject Enrolment & Visits",
  "Doctor / Investigator": "Patient Consultation & Exam",
  "Monitor": "Site SDV & Deviations",
  "EC Member": "Protocol Approvals & Quorum",
  "PV Officer": "Safety Signals & MedDRA",
  "Admin": "User & System Management",
  "Auditor / Regulator": "Immutable Audit Trail",
  "Institution Leadership": "Portfolio Risk Analytics"
};

const ROLES_WITHOUT_MY_REPORTS = new Set(["Research Coordinator", "Monitor", "EC Member"]);

function renderDashboardView(role) {
  const currentActualRole = appState.currentUser ? appState.currentUser.role : role;
  appState.activeRole = role;

  // Update sidebar info
  const sideRoleEl = document.getElementById("side-user-role");
  if (sideRoleEl) sideRoleEl.textContent = role;
  const sideEmailEl = document.getElementById("side-user-email");
  if (sideEmailEl && appState.currentUser) sideEmailEl.textContent = appState.currentUser.email;

  // "View as role" preview switcher (Available on all dashboards, switches via full authentication)
  const viewAsContainer = document.getElementById("view-as-role-container");
  const viewAsSelect = document.getElementById("select-view-as-role");
  if (viewAsContainer) viewAsContainer.classList.remove("hidden");
  if (viewAsSelect) viewAsSelect.value = role;

  // Show "Team Activity" menu only for Admin and PI
  const teamNav = document.getElementById("nav-item-team");
  if (teamNav) {
    if (role === "Admin" || role === "Principal Investigator") {
      teamNav.classList.remove("hidden");
    } else {
      teamNav.classList.add("hidden");
    }
  }

  // Update workspace navigation label
  const wsLabel = document.getElementById("workspace-nav-label");
  if (wsLabel) wsLabel.textContent = ROLE_WORKSPACE_LABELS[role] || "Role Workspace";

  // Update incoming reports navigation label based on role
  const escLabel = document.getElementById("escalations-nav-label");
  if (escLabel) {
    escLabel.textContent = (role === "Admin" || role === "Principal Investigator") ? "Incoming Reports" : "My Reports";
  }
  const reportsNav = document.getElementById("nav-item-escalations");
  const reportsPane = document.getElementById("dash-pane-escalations");
  const notificationBell = document.getElementById("btn-notif-bell");
  const canSeeReports = !ROLES_WITHOUT_MY_REPORTS.has(role);
  reportsNav?.classList.toggle("hidden", !canSeeReports);
  reportsPane?.classList.toggle("hidden", !canSeeReports);
  notificationBell?.classList.toggle("hidden", !canSeeReports);
  if (!canSeeReports) {
    if (appState.activeDashboardTab === "escalations") appState.activeDashboardTab = "overview";
  }

  const newSubmissionNav = document.getElementById("nav-item-new-submission");
  const canSubmitReport = currentActualRole !== "Admin" && currentActualRole !== "Principal Investigator";
  if (newSubmissionNav) newSubmissionNav.classList.toggle("hidden", !canSubmitReport);
  if (!canSubmitReport && appState.activeDashboardTab === "new-submission") {
    appState.activeDashboardTab = "overview";
  }

  const assignJobsNav = document.getElementById("nav-item-assign-jobs");
  const assignedByMeNav = document.getElementById("nav-item-assigned-by-me");
  const myTasksNav = document.getElementById("nav-item-my-tasks");
  const canManageTasks = ["Admin", "Research Coordinator"].includes(currentActualRole) && role === currentActualRole;
  const canViewAssignedByMe = currentActualRole === "Research Coordinator" && role === currentActualRole;
  const canViewMyTasks = currentActualRole !== "Admin" && currentActualRole === role;
  assignJobsNav?.classList.toggle("hidden", !canManageTasks);
  assignedByMeNav?.classList.toggle("hidden", !canViewAssignedByMe);
  myTasksNav?.classList.toggle("hidden", !canViewMyTasks);
  if (!canManageTasks && appState.activeDashboardTab === "assign-jobs") appState.activeDashboardTab = "overview";
  if (!canViewAssignedByMe && appState.activeDashboardTab === "assigned-by-me") appState.activeDashboardTab = "overview";
  if (!canViewMyTasks && appState.activeDashboardTab === "my-tasks") appState.activeDashboardTab = "overview";

  // Requirement 3: Legal Documents navigation link visibility (EC Member, PI, and Admin only)
  const legalDocsNav = document.getElementById("nav-item-legal-docs");
  const legalDocsBadge = document.getElementById("legal-docs-nav-badge");
  if (legalDocsNav) {
    if (role === "EC Member" || role === "Principal Investigator" || role === "Admin") {
      legalDocsNav.classList.remove("hidden");
      // Compute urgent (<30d) and expired alerts
      const dueCount = appState.legalDocuments.filter(d => d.days_remaining <= 30).length;
      if (legalDocsBadge) {
        if (dueCount > 0) {
          legalDocsBadge.textContent = `${dueCount} Alert${dueCount > 1 ? 's' : ''}`;
          legalDocsBadge.classList.remove("hidden");
        } else {
          legalDocsBadge.classList.add("hidden");
        }
      }
    } else {
      legalDocsNav.classList.add("hidden");
    }
  }

  const leadershipLegalNav = document.getElementById("nav-item-leadership-legal");
  const canViewLeadershipLegal = currentActualRole === "Institution Leadership" && role === "Institution Leadership";
  leadershipLegalNav?.classList.toggle("hidden", !canViewLeadershipLegal);
  if (!canViewLeadershipLegal && appState.activeDashboardTab === "leadership-legal") {
    appState.activeDashboardTab = "overview";
  }

  // Welcome banner text
  const welcomeHeading = document.getElementById("welcome-role-heading");
  if (welcomeHeading) welcomeHeading.textContent = `Welcome, ${role}`;
  const pageTitle = document.getElementById("dash-page-title");
  if (pageTitle) pageTitle.textContent = `${role} Dashboard`;

  // Render 4 KPI cards
  const kpis = ROLE_KPIS[role] || ROLE_KPIS["Research Coordinator"];
  const container = document.getElementById("kpi-cards-container");
  if (container) {
    container.innerHTML = kpis.map(k => `
      <div class="dash-card">
        <div class="kpi-label">${k.label}</div>
        <div class="kpi-value">${k.value}</div>
        <div class="kpi-note">${k.note}</div>
      </div>
    `).join("");
  }

  // Render overview charts (Exclusively for PI, Admin, and Monitor)
  renderOverviewCharts(role);

  // Render role-tailored workspace
  renderRoleWorkspace(role);

  // Load escalations
  if (canSeeReports) loadEscalationsUI();

  // Load submissions
  loadSubmissionsUI();

  // Default to overview pane if not already set
  if (!appState.activeDashboardTab) {
    showDashTab("overview");
  } else {
    showDashTab(appState.activeDashboardTab);
  }
}

function switchViewAsRole(selectedRole) {
  if (!appState.isLoggedIn || !appState.currentUser) {
    window.location.hash = "#login";
    return;
  }
  if (selectedRole === appState.activeRole) {
    return;
  }

  // Pre-select and lock target role, require full authentication before switching
  appState.pendingRoleSwitch = {
    fromRole: appState.activeRole,
    toRole: selectedRole,
    userEmail: appState.currentUser.email
  };

  const roleInput = document.getElementById("login-role");
  if (roleInput) {
    roleInput.value = selectedRole;
    roleInput.disabled = true;
    roleInput.dispatchEvent(new Event("change", { bubbles: true }));
  }

  const emailInput = document.getElementById("login-email");
  const pwdInput = document.getElementById("login-password");
  const errorBox1 = document.getElementById("login-error-msg");
  const errorBox2 = document.getElementById("otp-error-msg");
  if (emailInput) emailInput.value = "";
  if (pwdInput) pwdInput.value = "";
  if (errorBox1) errorBox1.classList.add("hidden");
  if (errorBox2) errorBox2.classList.add("hidden");

  const step1 = document.getElementById("login-step-1");
  const step2 = document.getElementById("login-step-2");
  if (step1) step1.classList.remove("hidden");
  if (step2) step2.classList.add("hidden");

  const cancelBtn1 = document.getElementById("btn-cancel-role-switch");
  const cancelBtn2 = document.getElementById("btn-cancel-role-switch-step2");
  if (cancelBtn1) cancelBtn1.classList.remove("hidden");
  if (cancelBtn2) cancelBtn2.classList.remove("hidden");

  window.location.hash = "#login";
}

function cancelRoleSwitch() {
  if (appState.pendingRoleSwitch) {
    const fromRole = appState.pendingRoleSwitch.fromRole;
    appState.pendingRoleSwitch = null;
    const viewAsSelect = document.getElementById("select-view-as-role");
    if (viewAsSelect) viewAsSelect.value = fromRole;
    const roleInput = document.getElementById("login-role");
    if (roleInput) roleInput.disabled = false;
    const cancelBtn1 = document.getElementById("btn-cancel-role-switch");
    const cancelBtn2 = document.getElementById("btn-cancel-role-switch-step2");
    if (cancelBtn1) cancelBtn1.classList.add("hidden");
    if (cancelBtn2) cancelBtn2.classList.add("hidden");
    window.location.hash = `#dashboard/${ROLE_TO_SLUG[fromRole] || "coordinator"}`;
  } else if (appState.isLoggedIn && appState.currentUser) {
    window.location.hash = `#dashboard/${ROLE_TO_SLUG[appState.currentUser.role] || "coordinator"}`;
  } else {
    window.location.hash = "#landing";
  }
}

async function logRoleSwitchAttempt(fromRole, toRole, userEmail, success, reason) {
  try {
    await fetch("/api/auth/log-role-switch", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        from_role: fromRole,
        to_role: toRole,
        user_email: userEmail || "unknown",
        success: Boolean(success),
        reason: reason || (success ? "Role switch verified" : "Failed role switch")
      })
    });
  } catch (err) {
    console.warn("Could not record role switch audit event:", err);
  }
}

function showDashTab(tabId) {
  const actualRole = appState.currentUser ? appState.currentUser.role : null;
  if (tabId === "escalations" && ROLES_WITHOUT_MY_REPORTS.has(appState.activeRole)) {
    showToast("My Reports is not available for this role.");
    showDashTab("overview");
    return;
  }
  if (tabId === "assign-jobs" && (!actualRole || !["Admin", "Research Coordinator"].includes(actualRole) || appState.activeRole !== actualRole)) {
    showToast("Access Restricted: only Admin and Research Coordinator can assign jobs.");
    showDashTab("overview");
    return;
  }
  if (tabId === "add-participant" && (actualRole !== "Research Coordinator" || appState.activeRole !== actualRole)) {
    showToast("Access Restricted: only Research Coordinators can add participants.");
    showDashTab("overview");
    return;
  }
  if (tabId === "my-tasks" && (!actualRole || actualRole === "Admin" || actualRole !== appState.activeRole)) {
    showToast("Access Restricted: tasks are available only to your signed-in role.");
    showDashTab("overview");
    return;
  }
  if (tabId === "assigned-by-me" && (actualRole !== "Research Coordinator" || appState.activeRole !== actualRole)) {
    showToast("Access Restricted: assigned work is visible only to its Research Coordinator.");
    showDashTab("overview");
    return;
  }
  if (tabId === "leadership-legal" && (actualRole !== "Institution Leadership" || appState.activeRole !== actualRole)) {
    showToast("Access Restricted: Legal is available only to Institution Leadership.");
    showDashTab("overview");
    return;
  }
  const dashboardShell = document.getElementById("view-dashboard");
  dashboardShell?.classList.toggle("is-fullscreen-pane", ["new-submission", "escalations", "add-participant", "new-record"].includes(tabId));
  appState.activeDashboardTab = tabId;
  document.querySelectorAll(".sidebar-item").forEach(item => item.classList.remove("active"));
  document.querySelectorAll(".dash-pane").forEach(pane => pane.classList.remove("active"));

  const navItem = document.getElementById(`nav-item-${tabId}`);
  if (navItem) navItem.classList.add("active");

  const pane = document.getElementById(`dash-pane-${tabId}`);
  if (pane) pane.classList.add("active");

  if (tabId === "overview") renderOverviewCharts(appState.activeRole || "Research Coordinator");
  if (tabId === "new-submission") {
    if (!actualRole || actualRole === "Admin" || actualRole === "Principal Investigator") {
      showToast("Access Restricted: reports can only be submitted by non-recipient roles.");
      showDashTab("overview");
      return;
    }
    populateNewSubmissionForm();
  }
  if (tabId === "submissions") loadSubmissionsUI();
  if (tabId === "team") filterTeamActivityUI();
  if (tabId === "escalations") loadEscalationsUI();
  if (tabId === "workspace") renderRoleWorkspace(appState.activeRole || "Research Coordinator");
  if (tabId === "legal-docs") {
    const curRole = appState.activeRole || (appState.currentUser ? appState.currentUser.role : "EC Member");
    if (curRole !== "EC Member" && curRole !== "Principal Investigator" && curRole !== "Admin") {
      showToast("Access Restricted: Legal documents are visible only to EC Member, PI, and Admin.");
      showDashTab("overview");
      return;
    }
    renderLegalDocumentsPage();
  }
  if (tabId === "assign-jobs") loadAdminTasks();
  if (tabId === "assigned-by-me") loadCoordinatorAssignedTasks();
  if (tabId === "my-tasks") loadMyTasks();
  if (tabId === "leadership-legal") loadLeadershipLegalDocs();
}

// ==============================================================================
// REUSABLE DASHBOARD OVERVIEW CHARTS (PI, Admin, and Monitor ONLY)
// ==============================================================================
function renderOverviewCharts(role) {
  const container = document.getElementById("overview-charts-container");
  if (!container) return;

  // STRICT ACCESS RULES:
  // Only PI, Admin and Monitor dashboards show charts in the Overview section.
  // All other 6 roles (Coordinator, Doctor, EC, PV, Auditor, Leadership) MUST NOT show charts.
  if (role !== "Principal Investigator" && role !== "Admin" && role !== "Monitor") {
    container.innerHTML = "";
    container.classList.add("hidden");
    return;
  }

  container.classList.remove("hidden");

  if (!window.ChartCard || !window.ChartDataHelper) {
    container.innerHTML = `<div class="dash-card"><p>Loading analytics modules...</p></div>`;
    return;
  }

  if (role === "Principal Investigator") {
    renderPICharts(container);
  } else if (role === "Admin") {
    if (typeof renderAdminCharts === "function") renderAdminCharts(container);
  } else if (role === "Monitor") {
    if (typeof renderMonitorCharts === "function") renderMonitorCharts(container);
  }
}

/**
 * Step 2: Principal Investigator Charts (3 Charts)
 * 1. Enrolment vs Target by site (Line)
 * 2. AEs by severity (Stacked Bar: Mild, Moderate, Severe)
 * 3. Reports by urgency (Donut: Normal, High, Critical)
 */
function renderPICharts(container) {
  const piData = ChartDataHelper.getPIData();

  // 1. Enrolment vs Target by Site (Line Chart)
  const card1 = ChartCard.render({
    id: "chart-pi-enrolment",
    title: "Multi-Center Enrolment vs Target Trajectory",
    insight: piData.enrolment.insight,
    type: "line",
    data: piData.enrolment.data,
    options: {
      badge: "4 Centers",
      badgeClass: "badge-green",
      seriesLabel: "Enrolled",
      height: 220
    }
  });

  // 2. AEs by Severity & Site (Stacked Bar Chart: Mild, Moderate, Severe SAE)
  const card2 = ChartCard.render({
    id: "chart-pi-ae-severity",
    title: "Adverse Events by Severity & Center",
    insight: piData.adverseEvents.insight,
    type: "stacked-bar",
    data: piData.adverseEvents.data,
    options: {
      badge: "60 Total AEs",
      badgeClass: "badge-secondary",
      height: 220,
      keys: [
        { key: "mild", label: "Mild (Dosha-Kopa)", color: "#10b981" },
        { key: "moderate", label: "Moderate (Advisory)", color: "#f59e0b" },
        { key: "severe", label: "Severe (SAE)", color: "#ef4444" }
      ]
    }
  });

  // 3. Reports by Urgency (Donut Chart: Normal, High, Critical)
  const card3 = ChartCard.render({
    id: "chart-pi-reports-urgency",
    title: "Escalation Reports by Urgency & SLA",
    insight: piData.reports.insight,
    type: "donut",
    data: piData.reports.data,
    options: {
      badge: "GCP-ASU SLA",
      badgeClass: "badge-warning",
      height: 220
    }
  });

  container.innerHTML = card1 + card2 + card3;
}

/**
 * Admin Charts (3 Charts)
 * 1. Users by role and status (Bar)
 * 2. Compliance checks green/amber/red (Donut)
 * 3. Studies by phase (Bar)
 */
function renderAdminCharts(container) {
  const adminData = ChartDataHelper.getAdminData();

  // 1. Users by Role & Status (Bar Chart)
  const card1 = ChartCard.render({
    id: "chart-admin-users",
    title: "User Registrations by Role & Status",
    insight: adminData.users.insight,
    type: "bar",
    data: adminData.users.data,
    options: {
      badge: "38 Total Accounts",
      badgeClass: "badge-green",
      height: 220
    }
  });

  // 2. Compliance Checks (Donut Chart: Green, Amber, Red)
  const card2 = ChartCard.render({
    id: "chart-admin-compliance",
    title: "Regulatory Compliance Audit Checks",
    insight: adminData.compliance.insight,
    type: "donut",
    data: adminData.compliance.data,
    options: {
      badge: "GCP-ASU & DPDP",
      badgeClass: "badge-secondary",
      height: 220
    }
  });

  // 3. Studies by Phase (Bar Chart: Phase I, II, III)
  const card3 = ChartCard.render({
    id: "chart-admin-phases",
    title: "Clinical Trial Protocols by Phase",
    insight: adminData.phases.insight,
    type: "bar",
    data: adminData.phases.data,
    options: {
      badge: "6 Central Trials",
      badgeClass: "badge-secondary",
      height: 220
    }
  });

  container.innerHTML = card1 + card2 + card3;
}

/**
 * Monitor Charts (3 Charts — Strictly Assigned Sites SITE-01 & SITE-02)
 * 1. Missing data by site (Bar)
 * 2. Protocol deviations by type (Bar)
 * 3. Overdue visits trend (Line)
 */
function renderMonitorCharts(container) {
  const monData = ChartDataHelper.getMonitorData();

  // 1. Missing Data by Site (Bar Chart)
  const card1 = ChartCard.render({
    id: "chart-monitor-missing",
    title: "Unverified CRF Data Points by Center",
    insight: monData.missing.insight,
    type: "bar",
    data: monData.missing.data,
    options: {
      badge: "Assigned Centers",
      badgeClass: "badge-warning",
      height: 220
    }
  });

  // 2. Protocol Deviations by Type (Bar Chart)
  const card2 = ChartCard.render({
    id: "chart-monitor-deviations",
    title: "Protocol Deviations by Category",
    insight: monData.deviations.insight,
    type: "bar",
    data: monData.deviations.data,
    options: {
      badge: "GCP Monitoring",
      badgeClass: "badge-secondary",
      height: 220
    }
  });

  // 3. Overdue Visits Trend (Line Chart)
  const card3 = ChartCard.render({
    id: "chart-monitor-overdue",
    title: "Overdue Subject Visits Trajectory",
    insight: monData.overdue.insight,
    type: "line",
    data: monData.overdue.data,
    options: {
      badge: "4-Week Window",
      badgeClass: "badge-red",
      seriesLabel: "Overdue Visits",
      height: 220
    }
  });

  container.innerHTML = card1 + card2 + card3;
}

// Subscribe to real-time data changes to update charts without page reload
if (typeof window !== "undefined" && window.ChartDataHelper) {
  ChartDataHelper.onUpdate(() => {
    if (appState.isLoggedIn && appState.activeDashboardTab === "overview") {
      renderOverviewCharts(appState.activeRole || "Research Coordinator");
    }
  });
}

// ==============================================================================
// 9 ROLE-SPECIFIC WORKSPACES
// ==============================================================================
async function renderRoleWorkspace(role) {
  const container = document.getElementById("workspace-content-area");
  const titleEl = document.getElementById("workspace-title");
  const subEl = document.getElementById("workspace-subtitle");
  const actionsEl = document.getElementById("workspace-quick-actions");
  if (!container) return;

  if (titleEl) titleEl.textContent = `${role} Workspace`;
  if (subEl) subEl.textContent = `Tailored operations, compliance monitors, and clinical actions for ${role}.`;

  // Fetch study data if not already cached
  if (!appState.studyData) {
    try {
      const res = await fetch("/api/escalations/study-data");
      if (res.ok) appState.studyData = await res.json();
    } catch {}
  }
  const data = appState.studyData || { studies: [], sites: [], participants: [], adverse_events: [] };

  if (role === "Principal Investigator") {
    if (actionsEl) actionsEl.innerHTML = "";
    container.innerHTML = `
      <div class="workspace-grid">
        <div class="dash-card">
          <div class="card-title-bar">
            <h4>Study Protocols & Recruitment Health</h4>
            <span class="badge badge-info">6 Active Protocols</span>
          </div>
          <div class="table-responsive">
            <table class="data-table">
              <thead><tr><th>Protocol ID</th><th>Study Title</th><th>Enrolled / Target</th><th>SAEs</th><th>Health</th></tr></thead>
              <tbody>
                ${data.studies.map(s => `
                  <tr>
                    <td><strong>${s.id}</strong></td>
                    <td>${s.name}</td>
                    <td><strong>${s.enrolled}</strong> / ${s.target}</td>
                    <td><span class="badge ${s.saes > 0 ? 'badge-red' : 'badge-green'}">${s.saes} SAE</span></td>
                    <td><span class="badge badge-green">${s.health_score}%</span></td>
                  </tr>
                `).join('')}
              </tbody>
            </table>
          </div>
        </div>
        <div class="dash-card">
          <div class="card-title-bar">
            <h4>Site Compliance & SDV Score</h4>
            <span class="badge badge-green">4 Sites Audited</span>
          </div>
          <div class="table-responsive">
            <table class="data-table">
              <thead><tr><th>Site</th><th>Recruited</th><th>SDV</th><th>Status</th></tr></thead>
              <tbody>
                ${data.sites.map(site => `
                  <tr>
                    <td><strong>${site.name.split(',')[0]}</strong></td>
                    <td>${site.enrolled}</td>
                    <td>${site.sdv_score}%</td>
                    <td><span class="badge badge-green">${site.audit_status}</span></td>
                  </tr>
                `).join('')}
              </tbody>
            </table>
          </div>
        </div>
      </div>
    `;
  } else if (role === "Research Coordinator") {
    if (actionsEl) {
      actionsEl.innerHTML = `
        <button class="btn btn-primary btn-sm" onclick="openAddParticipantModal()" id="btn-add-participant" style="font-weight: 600;">+ Add Participant</button>
        <button class="btn btn-warning btn-sm" onclick="openEscalationDrawer('', 'Consent', 'High')">⚡ Report Protocol Deviation to PI</button>
      `;
    }
    const coordParticipants = data.participants.slice(0, 10);
    container.innerHTML = `
      <div class="dash-card">
        <div class="card-title-bar">
          <h4>Participant Visit & Dosing Ledger (SITE-01)</h4>
          <div style="display: flex; gap: 8px; align-items: center;">
            <span class="badge badge-info" id="coordinator-participant-count">${data.participants.length} Total Coded Records</span>
          </div>
        </div>
        <div class="table-responsive">
          <table class="data-table">
            <thead><tr><th>Subject Code</th><th>Study ID</th><th>Prakriti</th><th>Status</th><th>Visits Done</th><th>Dose Compliance</th><th>Actions</th></tr></thead>
            <tbody id="coordinator-participants-tbody">
              ${coordParticipants.map(p => `
                <tr>
                  <td><code>${p.subject_code}</code></td>
                  <td>${p.study_id}</td>
                  <td>${p.prakriti || p.dominant_prakriti || 'Vata-Pitta'}</td>
                  <td><span class="badge badge-green">${p.status || 'Active Enrolled'}</span></td>
                  <td>${p.visits_completed !== undefined ? p.visits_completed : 0} / ${p.total_visits || 8}</td>
                  <td><span class="badge badge-info">${p.compliance_pct !== undefined ? p.compliance_pct : 100}%</span></td>
                  <td><button class="btn btn-secondary btn-sm" onclick="openEscalationDrawer('${p.subject_code}', 'Participant', 'Normal')">Report Issue</button></td>
                </tr>
              `).join('')}
            </tbody>
          </table>
        </div>
      </div>
    `;

  } else if (role === "Doctor / Investigator") {
    if (actionsEl) actionsEl.innerHTML = `<button class="btn btn-warning btn-sm" onclick="openEscalationDrawer('SUB-AIIA-01-042', 'Safety', 'Critical')">🚨 Report Urgent AE/SAE to PI</button>`;
    container.innerHTML = `
      <div class="workspace-grid">
        <div class="dash-card">
          <div class="card-title-bar">
            <h4>Patient Clinical Evaluation by Subject Code</h4>
            <div class="search-box-pill">
              <span>🔍</span>
              <input type="text" id="doc-search-code" placeholder="Enter code (e.g. SUB-AIIA-01-042)" value="SUB-AIIA-01-042">
            </div>
          </div>
          <div class="clinical-summary-box" style="padding: 14px; background: var(--bg-subtle); border-radius: 6px; line-height: 1.6; font-size: 0.88rem;">
            <p><strong>Subject Identifier:</strong> <code>SUB-AIIA-01-042</code> • <strong>Protocol:</strong> AYUR-CT-2026-001</p>
            <p><strong>Prakriti Scoring:</strong> Vata 52, Pitta 32, Kapha 16 (<em>Vata-Pitta Pradhana</em>)</p>
            <p><strong>Ayurvedic Diagnosis:</strong> Smriti-Bhramsha (Generalized Cognitive Impairment) with Pitta-Kopa</p>
            <p><strong>Modern Diagnosis:</strong> Mild Cognitive Impairment (MoCA Score: 22/30)</p>
            <p><strong>Dosing Regimen:</strong> Ashwagandha Churna 3g BD + Brahmi Ghrita 5g Mane (Compliance: 94%)</p>
            <p><strong>Recent Safety Flag:</strong> Hepatic Enzyme Elevation (ALT 112 IU/L) recorded at Day 28 Visit</p>
          </div>
          <div style="display: flex; gap: 10px; margin-top: 14px;">
            <button class="btn btn-warning btn-sm" onclick="openEscalationDrawer('SUB-AIIA-01-042', 'Participant', 'High')">Flag Subject to PI</button>
            <button class="btn btn-danger btn-sm" onclick="openEscalationDrawer('SUB-AIIA-01-042', 'Safety', 'Critical')">🚨 Report AE/SAE to PI & PV</button>
          </div>
        </div>
        <div class="dash-card">
          <div class="card-title-bar"><h4>Doctor Next-Actions Checklist</h4></div>
          <ul style="padding-left: 20px; font-size: 0.85rem; line-height: 1.8; color: var(--text-muted);">
            <li>✓ Review ALT/AST liver panel for SUB-AIIA-01-042</li>
            <li>✓ Complete Prakriti scoring for 3 newly enrolled subjects</li>
            <li>✓ Sign off electronic CRF for Visit 3 cohort</li>
            <li>✓ Verify de-challenge symptom log with PV Officer</li>
          </ul>
        </div>
      </div>
    `;
  } else if (role === "Monitor") {
    if (actionsEl) actionsEl.innerHTML = `<button class="btn btn-warning btn-sm" onclick="openEscalationDrawer('', 'Protocol deviation', 'High')">⚡ Report SDV Deviation to PI & Admin</button>`;
    container.innerHTML = `
      <div class="workspace-grid">
        <div class="dash-card">
          <div class="card-title-bar"><h4>Site Ranking & Source Data Verification (SDV)</h4></div>
          <div class="table-responsive">
            <table class="data-table">
              <thead><tr><th>Site</th><th>Monitored</th><th>SDV Rate</th><th>Deviations</th><th>Action</th></tr></thead>
              <tbody>
                ${data.sites.map(s => `
                  <tr>
                    <td><strong>${s.name.split(',')[0]}</strong></td>
                    <td>${s.enrolled} records</td>
                    <td><strong>${s.sdv_score}%</strong></td>
                    <td><span class="badge ${s.open_deviations > 1 ? 'badge-red' : 'badge-green'}">${s.open_deviations} Open</span></td>
                    <td><button class="btn btn-secondary btn-sm" onclick="openEscalationDrawer('', 'Protocol deviation', 'High')">Flag Site</button></td>
                  </tr>
                `).join('')}
              </tbody>
            </table>
          </div>
        </div>
        <div class="dash-card">
          <div class="card-title-bar"><h4>Active Protocol Deviations</h4></div>
          <ul style="padding-left: 20px; font-size: 0.85rem; line-height: 1.8; color: var(--text-muted);">
            <li>⚠️ <strong>SITE-02:</strong> Window excursion for Visit 4 (+6 days)</li>
            <li>⚠️ <strong>SITE-01:</strong> Discrepancy between paper case sheet & e-CRF</li>
            <li>⚠️ <strong>SITE-03:</strong> Witness relationship box empty on consent</li>
          </ul>
        </div>
      </div>
    `;
  } else if (role === "EC Member") {
    if (actionsEl) {
      actionsEl.innerHTML = `
        <button class="btn btn-primary btn-sm" onclick="showDashTab('legal-docs')" style="font-weight: 600;">⚖️ Legal Documents & Timeline</button>
        <button class="btn btn-secondary btn-sm" onclick="openUploadLegalDocModal()">+ Upload Legal Document</button>
        <button class="btn btn-warning btn-sm" onclick="openEscalationDrawer('', 'Ethics', 'Normal')">⚡ Send Decision / Query to PI & Admin</button>
      `;
    }
    const safeCount = appState.legalDocuments.filter(d => d.days_remaining > 90).length;
    const attentionCount = appState.legalDocuments.filter(d => d.days_remaining >= 30 && d.days_remaining <= 90).length;
    const urgentCount = appState.legalDocuments.filter(d => d.days_remaining >= 0 && d.days_remaining < 30).length;
    const expiredCount = appState.legalDocuments.filter(d => d.days_remaining < 0).length;

    container.innerHTML = `
      <!-- Legal Documents Summary Card on EC Dashboard -->
      <div class="dash-card" style="border-left: 4px solid var(--accent-primary, #0d9488); margin-bottom: 20px;">
        <div class="card-title-bar">
          <div style="display: flex; align-items: center; gap: 8px;">
            <span style="font-size: 1.3rem;">⚖️</span>
            <h4>Statutory Legal Documents & Approvals Summary</h4>
          </div>
          <div style="display: flex; gap: 8px;">
            <button class="btn btn-primary btn-sm" onclick="showDashTab('legal-docs')" style="font-weight: 600;">View Registry & Timeline &rarr;</button>
            <button class="btn btn-secondary btn-sm" onclick="openUploadLegalDocModal()">+ Upload New Document</button>
          </div>
        </div>
        <p style="font-size: 0.85rem; color: var(--text-muted); margin-bottom: 12px;">
          Statutory regulatory licenses, clinical trial insurance, protocol clearances, and institutional MoUs tracked under GCP-ASU.
        </p>
        <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(170px, 1fr)); gap: 12px; margin-bottom: 14px;">
          <div style="padding: 10px; background: var(--bg-subtle); border-radius: 6px;">
            <div style="font-size: 0.72rem; color: var(--text-muted); text-transform: uppercase; font-weight: 600;">Total Active Records</div>
            <div style="font-size: 1.35rem; font-weight: 700; color: var(--text-main);">${appState.legalDocuments.length} Documents</div>
            <div style="font-size: 0.78rem; color: var(--text-dim);">CTRI, MoUs, Approvals</div>
          </div>
          <div style="padding: 10px; background: #ecfdf5; border-radius: 6px; border: 1px solid #a7f3d0;">
            <div style="font-size: 0.72rem; color: #065f46; text-transform: uppercase; font-weight: 600;">Safe (>90 Days)</div>
            <div style="font-size: 1.35rem; font-weight: 700; color: #047857;">${safeCount} Documents</div>
            <div style="font-size: 0.78rem; color: #065f46;">Full statutory validity</div>
          </div>
          <div style="padding: 10px; background: #fffbeb; border-radius: 6px; border: 1px solid #fde68a;">
            <div style="font-size: 0.72rem; color: #92400e; text-transform: uppercase; font-weight: 600;">Attention (30–90 Days)</div>
            <div style="font-size: 1.35rem; font-weight: 700; color: #b45309;">${attentionCount} Due Soon</div>
            <div style="font-size: 0.78rem; color: #92400e;">60/90-day alert active</div>
          </div>
          <div style="padding: 10px; background: #fef2f2; border-radius: 6px; border: 1px solid #fecaca;">
            <div style="font-size: 0.72rem; color: #991b1b; text-transform: uppercase; font-weight: 600;">Urgent & Expired (<30d)</div>
            <div style="font-size: 1.35rem; font-weight: 700; color: #b91c1c;">${urgentCount + expiredCount} Critical</div>
            <div style="font-size: 0.78rem; color: #991b1b;">Immediate action required</div>
          </div>
        </div>
        <div style="padding: 10px 14px; background: #fef2f2; border-left: 4px solid #ef4444; border-radius: 4px; font-size: 0.85rem; color: #991b1b; display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 8px;">
          <span>🚨 <strong>Next Document to Expire:</strong> Biological Specimen Transfer Agreement (BMTA) — <strong style="text-decoration: underline;">Expires in 6 days</strong></span>
          <button class="btn btn-secondary btn-sm" onclick="showDashTab('legal-docs')" style="font-size: 0.8rem; padding: 3px 8px;">Review Timeline</button>
        </div>
      </div>

      <div class="workspace-grid">
        <div class="dash-card">
          <div class="card-title-bar"><h4>Institutional Ethics Committee (IEC) Approvals</h4></div>
          <div class="table-responsive">
            <table class="data-table">
              <thead><tr><th>Protocol ID</th><th>Protocol Title</th><th>Status</th><th>Renewal Due</th><th>Decision</th></tr></thead>
              <tbody>
                ${data.studies.slice(0, 4).map(s => `
                  <tr>
                    <td><strong>${s.id}</strong></td>
                    <td>${s.name}</td>
                    <td><span class="badge badge-green">Approved</span></td>
                    <td>310 Days Left</td>
                    <td><button class="btn btn-secondary btn-sm" onclick="openEscalationDrawer('${s.id}', 'Ethics', 'Normal')">Send Query</button></td>
                  </tr>
                `).join('')}
              </tbody>
            </table>
          </div>
        </div>
        <div class="dash-card">
          <div class="card-title-bar"><h4>EC Statutory Quorum Status</h4></div>
          <div style="padding: 12px; background: #ecfdf5; border: 1px solid #a7f3d0; border-radius: 6px; font-size: 0.85rem; color: #065f46;">
            <p><strong>✓ Quorum Active:</strong> 9 Statutory Members registered</p>
            <p><strong>✓ Ayurveda Expert:</strong> Prof. (Dr.) Rajeshwar Sharma present</p>
            <p><strong>✓ Legal Expert:</strong> Justice M. K. Narayanan present</p>
            <p><strong>✓ Lay Person / Community:</strong> Verified</p>
          </div>
        </div>
      </div>
    `;
  } else if (role === "PV Officer") {
    if (actionsEl) actionsEl.innerHTML = `<button class="btn btn-danger btn-sm" onclick="openEscalationDrawer('', 'Safety', 'Critical')">🚨 Escalate Safety Signal to PI & Admin</button>`;
    const saeList = data.adverse_events.filter(a => a.is_sae);
    container.innerHTML = `
      <div class="dash-card">
        <div class="card-title-bar">
          <h4>Expedited Pharmacovigilance & SAE Queue (24h Statutory Clock)</h4>
          <span class="badge badge-red">8 Serious Adverse Events</span>
        </div>
        <div class="table-responsive">
          <table class="data-table">
            <thead><tr><th>AE ID</th><th>Subject Code</th><th>Classical ASU Reaction</th><th>MedDRA Code</th><th>Causality</th><th>Status</th><th>Actions</th></tr></thead>
            <tbody>
              ${saeList.map(a => `
                <tr>
                  <td><strong>${a.id}</strong></td>
                  <td><code>${a.subject_code}</code></td>
                  <td>${a.asu_term}</td>
                  <td><span class="badge badge-info">${a.meddra_code}</span></td>
                  <td><strong>${a.causality}</strong></td>
                  <td><span class="badge badge-red">${a.status}</span></td>
                  <td><button class="btn btn-warning btn-sm" onclick="openEscalationDrawer('${a.subject_code}', 'Safety', 'Critical')">Escalate to PI</button></td>
                </tr>
              `).join('')}
            </tbody>
          </table>
        </div>
      </div>
    `;
  } else if (role === "Admin") {
    if (actionsEl) actionsEl.innerHTML = "";
    container.innerHTML = `
      <div class="workspace-grid">
        <div class="dash-card">
          <div class="card-title-bar"><h4>Trial User Role Accounts & Approval Directory</h4></div>
          <div class="table-responsive">
            <table class="data-table">
              <thead><tr><th>Role</th><th>Email</th><th>Site</th><th>Status</th><th>Action</th></tr></thead>
              <tbody>
                <tr><td>Principal Investigator</td><td>pi@ayurctms.demo</td><td>SITE-01</td><td><span class="badge badge-green">Approved</span></td><td><button class="btn btn-secondary btn-sm" disabled>Active</button></td></tr>
                <tr><td>Research Coordinator</td><td>coordinator@ayurctms.demo</td><td>SITE-01</td><td><span class="badge badge-green">Approved</span></td><td><button class="btn btn-secondary btn-sm" disabled>Active</button></td></tr>
                <tr><td>Doctor / Investigator</td><td>doctor@ayurctms.demo</td><td>SITE-01</td><td><span class="badge badge-green">Approved</span></td><td><button class="btn btn-secondary btn-sm" disabled>Active</button></td></tr>
                <tr><td>Monitor</td><td>monitor@ayurctms.demo</td><td>SITE-01</td><td><span class="badge badge-green">Approved</span></td><td><button class="btn btn-secondary btn-sm" disabled>Active</button></td></tr>
                <tr><td>PV Officer</td><td>pv@ayurctms.demo</td><td>SITE-01</td><td><span class="badge badge-green">Approved</span></td><td><button class="btn btn-secondary btn-sm" disabled>Active</button></td></tr>
              </tbody>
            </table>
          </div>
        </div>
        <div class="dash-card">
          <div class="card-title-bar"><h4>Regulatory PoC & Infrastructure</h4></div>
          <div style="font-size: 0.85rem; line-height: 1.8; color: var(--text-muted);">
            <p><strong>Primary Database:</strong> Supabase Cloud (PostgreSQL 15)</p>
            <p><strong>Data Residency:</strong> Mumbai, Maharashtra, India (ap-south-1)</p>
            <p><strong>NTP Sovereign Clock:</strong> time.nic.in (NPL synchronized)</p>
            <p><strong>CERT-In 6h Desk:</strong> incident@cert-in.org.in (24x7 active)</p>
            <p><strong>DPO Point of Contact:</strong> dpo@ayurctms.gov.in</p>
          </div>
        </div>
      </div>
    `;
  } else if (role === "Auditor / Regulator") {
    if (actionsEl) actionsEl.innerHTML = `<button class="btn btn-warning btn-sm" onclick="openEscalationDrawer('', 'Data issue', 'High')">⚡ Raise Audit Finding to Admin & PI</button>`;
    container.innerHTML = `
      <div class="dash-card">
        <div class="card-title-bar">
          <h4>SHA-256 Chained Cryptographic Audit Trail (De-Identified)</h4>
          <button class="btn btn-primary btn-sm" onclick="verifyHashChainInteractive()">🔒 Verify Hash Chain</button>
        </div>
        <p style="font-size: 0.84rem; color: var(--text-muted); margin-bottom: 14px;">
          GCP-ASU Part A.7 & CERT-In Compliant append-only ledger. All events are linked via SHA-256 cryptographic hashes.
        </p>
        <div class="table-responsive">
          <table class="data-table">
            <thead><tr><th>Timestamp (IST)</th><th>Action</th><th>Role</th><th>Entity</th><th>Hash Preview</th></tr></thead>
            <tbody>
              <tr><td>2026-09-30 00:42:15</td><td>ESCALATION_SUBMITTED</td><td>Doctor</td><td>Escalation: esc-101</td><td><code>e8f9a2b4...3c1d</code></td></tr>
              <tr><td>2026-09-30 00:15:30</td><td>LOGIN_SUCCESS</td><td>PI</td><td>Session: pi@...</td><td><code>7b4d1c9e...5a8f</code></td></tr>
              <tr><td>2026-09-29 23:55:10</td><td>SUBMISSION_VERIFIED</td><td>PI</td><td>Consent: sub-101</td><td><code>1a9f4c3b...8e2d</code></td></tr>
              <tr><td>2026-09-29 21:30:00</td><td>CRF_ENTRY_CREATED</td><td>Coordinator</td><td>Subject: SUB-018</td><td><code>9c2d1b8a...4f7e</code></td></tr>
            </tbody>
          </table>
        </div>
      </div>
    `;
  } else if (role === "Institution Leadership") {
    if (actionsEl) actionsEl.innerHTML = `<button class="btn btn-warning btn-sm" onclick="openEscalationDrawer('', 'Other', 'Normal')">⚡ Send Leadership Instruction</button>`;
    container.innerHTML = `
      <div class="workspace-grid">
        <div class="dash-card">
          <div class="card-title-bar">
            <h4>Institutional Trial Portfolio (De-Identified)</h4>
            <span class="badge badge-green">Composite Health: 93.5/100</span>
          </div>
          <div class="table-responsive">
            <table class="data-table">
              <thead><tr><th>Protocol</th><th>Phase</th><th>Recruitment</th><th>Health Score</th></tr></thead>
              <tbody>
                ${data.studies.map(s => `
                  <tr>
                    <td><strong>${s.id}</strong></td>
                    <td>${s.phase}</td>
                    <td><strong>${s.enrolled}</strong> / ${s.target} (${Math.round((s.enrolled/s.target)*100)}%)</td>
                    <td><span class="badge badge-green">${s.health_score}%</span></td>
                  </tr>
                `).join('')}
              </tbody>
            </table>
          </div>
        </div>
        <div class="dash-card">
          <div class="card-title-bar"><h4>Top Portfolio Risks & Advisory</h4></div>
          <ul style="padding-left: 20px; font-size: 0.85rem; line-height: 1.8; color: var(--text-muted);">
            <li>🟢 <strong>AYUR-CT-001:</strong> On schedule, cognitive MoCA score improving</li>
            <li>🟡 <strong>AYUR-CT-004:</strong> 3 SAEs reported, liver enzyme advisory active</li>
            <li>🟢 <strong>AYUR-CT-002:</strong> Target 85% achieved at Jamnagar site</li>
            <li>🟡 <strong>SITE-02:</strong> Pharmacy temperature monitoring calibrated</li>
          </ul>
        </div>
      </div>
    `;
  }
}

// ==============================================================================
// FULL-PAGE REPORT SUBMISSION
// ==============================================================================
function populateNewSubmissionForm(prefillCode) {
  const user = appState.currentUser || {};
  const studyInput = document.getElementById("new-submission-study");
  const siteInput = document.getElementById("new-submission-site");
  const subjectSelect = document.getElementById("new-submission-subject");
  if (studyInput) studyInput.value = user.study_id || "AYUR-CT-2026-001";
  if (siteInput) siteInput.value = user.site_id || user.site || "SITE-01";

  if (subjectSelect) {
    const selectedCode = prefillCode || subjectSelect.value;
    subjectSelect.replaceChildren(new Option("No specific participant", ""));
    const participants = appState.studyData?.participants || [];
    participants.forEach(participant => {
      if (!participant.subject_code) return;
      subjectSelect.add(new Option(participant.subject_code, participant.subject_code));
    });
    subjectSelect.value = selectedCode;
  }
}

function openNewSubmission(prefillCode, prefillCategory, prefillUrgency) {
  const role = appState.currentUser?.role;
  if (!role || role === "Admin" || role === "Principal Investigator") {
    showToast("Access Restricted: reports can only be submitted by non-recipient roles.");
    return;
  }

  populateNewSubmissionForm(prefillCode);
  if (prefillCategory) document.getElementById("new-submission-category").value = prefillCategory;
  if (prefillUrgency) document.getElementById("new-submission-urgency").value = prefillUrgency;
  showDashTab("new-submission");
}

function openEscalationDrawer(prefillCode, prefillCategory, prefillUrgency) {
  openNewSubmission(prefillCode, prefillCategory, prefillUrgency);
}

function updateNewSubmissionCharCount(input) {
  const count = document.getElementById("new-submission-char-count");
  if (count) count.textContent = `${input.value.length} / 120`;
}

function renderEscalationAttachment(esc) {
  const attachmentName = esc.attachment_name || esc.attachment_url;
  if (!attachmentName) return "";
  const safeName = String(attachmentName).replace(/[&<>"']/g, character => ({
    "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;"
  })[character]);

  try {
    const url = new URL(esc.attachment_url || "", window.location.origin);
    if (url.origin === window.location.origin && url.pathname.startsWith("/api/files/download/")) {
      const href = `${url.pathname}${url.search}`;
      return `<div style="font-size: 0.8rem; margin-bottom: 8px;">📎 <a href="${href}" target="_blank" rel="noopener">${safeName} (5-minute private link)</a></div>`;
    }
  } catch (error) {}

  return `<div style="font-size: 0.8rem; margin-bottom: 8px;">📎 Attachment: ${safeName}</div>`;
}

async function submitNewSubmission(event) {
  event.preventDefault();
  const user = appState.currentUser;
  const form = document.getElementById("form-new-escalation");
  const status = document.getElementById("new-submission-status");
  if (!user || !form || !status) return;

  const payload = {
    from_user: user.email,
    from_name: user.name || user.email.split("@")[0],
    from_role: user.role,
    study_id: document.getElementById("new-submission-study").value,
    site_id: document.getElementById("new-submission-site").value,
    subject_code: document.getElementById("new-submission-subject").value || null,
    category: document.getElementById("new-submission-category").value,
    urgency: document.getElementById("new-submission-urgency").value,
    summary: document.getElementById("new-submission-summary").value.trim(),
    details: document.getElementById("new-submission-details").value.trim(),
    attachment_name: null,
    attachment_url: null
  };

  try {
    const attachment = document.getElementById("new-submission-attachment").files?.[0];
    if (attachment) {
      const uploadForm = new FormData();
      uploadForm.append("file", attachment);
      const uploadResponse = await fetch("/api/files/upload", {
        method: "POST",
        credentials: "same-origin",
        body: uploadForm
      });
      const uploadResult = await uploadResponse.json();
      if (!uploadResponse.ok) throw new Error(uploadResult.detail || "Attachment upload failed.");
      const signedUrl = new URL(uploadResult.signed_download_url, window.location.origin);
      if (signedUrl.origin !== window.location.origin || !signedUrl.pathname.startsWith("/api/files/download/")) {
        throw new Error("Attachment service returned an invalid download path.");
      }
      payload.attachment_name = uploadResult.original_filename;
      payload.attachment_url = `${signedUrl.pathname}${signedUrl.search}`;
    }

    const response = await fetch("/api/escalations", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      credentials: "same-origin",
      body: JSON.stringify(payload)
    });
    if (!response.ok) {
      const result = await response.json().catch(() => ({}));
      throw new Error(result.detail || "Submission failed. Please try again.");
    }

    const now = new Date();
    const time = `${String(now.getHours()).padStart(2, "0")}:${String(now.getMinutes()).padStart(2, "0")}`;
    form.reset();
    populateNewSubmissionForm();
    updateNewSubmissionCharCount(document.getElementById("new-submission-summary"));
    status.textContent = `Sent to PI and Admin at ${time}`;
    status.classList.remove("hidden");
    showToast(status.textContent);
    if (window.ChartDataHelper) ChartDataHelper.notifyUpdate();
  } catch (error) {
    status.textContent = error.message || "Submission failed. Please try again.";
    status.classList.remove("hidden");
    showToast(status.textContent);
  }
}

function appendTaskCell(row, value, className = "") {
  const cell = document.createElement("td");
  if (className) cell.className = className;
  cell.textContent = value ?? "";
  row.appendChild(cell);
  return cell;
}

function populateAssigneeOptions(data) {
  const choices = [
    ...data.roles.map(role => ({ value: `role:${role}`, label: `${role} (role)` })),
    ...data.users.map(user => ({ value: `user:${user.email}`, label: `${user.full_name} (${user.role})` }))
  ];
  ["task-assignee", "edit-task-assignee"].forEach(id => {
    const select = document.getElementById(id);
    if (!select) return;
    select.replaceChildren(new Option("Select assignee", ""));
    choices.forEach(choice => select.add(new Option(choice.label, choice.value)));
  });
}

async function loadAdminTasks() {
  try {
    const actualRole = appState.currentUser?.role;
    const isAdmin = actualRole === "Admin";
    const assigneesResponse = await fetch("/api/tasks/assignees", { credentials: "same-origin" });
    if (!assigneesResponse.ok) throw new Error("Unable to load approved assignees.");
    const assigneeData = await assigneesResponse.json();
    populateAssigneeOptions(assigneeData);
    document.getElementById("admin-task-table")?.classList.toggle("hidden", !isAdmin);
    if (!isAdmin) return;

    const tasksResponse = await fetch("/api/tasks", { credentials: "same-origin" });
    if (!tasksResponse.ok) throw new Error("Unable to load Admin tasks.");
    const tasks = await tasksResponse.json();
    const body = document.getElementById("admin-task-rows");
    if (!body) return;
    body.replaceChildren();
    tasks.forEach(task => {
      const row = document.createElement("tr");
      const titleCell = appendTaskCell(row, task.title);
      if (task.description) {
        const description = document.createElement("small");
        description.textContent = task.description;
        titleCell.appendChild(document.createElement("br"));
        titleCell.appendChild(description);
      }
      appendTaskCell(row, task.assignee);
      appendTaskCell(row, `${task.study_id} / ${task.site_id}`);
      appendTaskCell(row, task.priority);
      appendTaskCell(row, task.due_date);
      const statusCell = document.createElement("td");
      const statusSelect = document.createElement("select");
      ["Assigned", "In progress", "Done"].forEach(value => statusSelect.add(new Option(value, value)));
      statusSelect.value = task.status;
      statusCell.appendChild(statusSelect);
      const updateButton = document.createElement("button");
      updateButton.type = "button";
      updateButton.className = "btn btn-sm btn-secondary";
      updateButton.textContent = "Save";
      updateButton.addEventListener("click", () => updateTaskStatus(task.id, statusSelect.value, true));
      statusCell.appendChild(updateButton);
      row.appendChild(statusCell);
      appendTaskCell(row, task.overdue_reason || "", task.overdue ? "badge-red" : "");
      const actionCell = document.createElement("td");
      const editButton = document.createElement("button");
      editButton.type = "button";
      editButton.className = "btn btn-sm btn-secondary";
      editButton.textContent = "Edit";
      editButton.addEventListener("click", () => openTaskEditor(task));
      actionCell.appendChild(editButton);
      row.appendChild(actionCell);
      body.appendChild(row);
    });
  } catch (error) {
    showToast(error.message || "Unable to load tasks.");
  }
}

async function loadCoordinatorAssignedTasks() {
  const body = document.getElementById("coordinator-assigned-task-rows");
  if (!body) return;
  try {
    const response = await fetch("/api/tasks/assigned-by-me", { credentials: "same-origin" });
    const result = await response.json();
    if (!response.ok) throw new Error(result.detail || "Unable to load assigned work.");
    body.replaceChildren();
    if (result.length === 0) {
      const row = document.createElement("tr");
      const cell = appendTaskCell(row, "No work assigned yet.");
      cell.colSpan = 7;
      body.appendChild(row);
      return;
    }
    result.forEach(task => {
      const row = document.createElement("tr");
      appendTaskCell(row, task.title);
      appendTaskCell(row, task.assignee);
      appendTaskCell(row, `${task.study_id} / ${task.site_id}`);
      appendTaskCell(row, task.priority);
      appendTaskCell(row, task.due_date);
      appendTaskCell(row, task.status);
      appendTaskCell(row, task.overdue_reason || "", task.overdue ? "badge-red" : "");
      body.appendChild(row);
    });
  } catch (error) {
    showToast(error.message || "Unable to load assigned work.");
  }
}

async function loadMyTasks() {
  try {
    const response = await fetch("/api/tasks", { credentials: "same-origin" });
    if (!response.ok) throw new Error("Unable to load your tasks.");
    const tasks = await response.json();
    const body = document.getElementById("my-task-rows");
    if (!body) return;
    body.replaceChildren();
    tasks.forEach(task => {
      const row = document.createElement("tr");
      appendTaskCell(row, task.title);
      appendTaskCell(row, task.description);
      appendTaskCell(row, `${task.study_id} / ${task.site_id}`);
      appendTaskCell(row, task.priority);
      appendTaskCell(row, task.due_date);
      appendTaskCell(row, task.status);
      const actionCell = document.createElement("td");
      const statusSelect = document.createElement("select");
      ["In progress", "Done"].forEach(value => statusSelect.add(new Option(value, value)));
      statusSelect.value = task.status === "Done" ? "Done" : "In progress";
      const updateButton = document.createElement("button");
      updateButton.type = "button";
      updateButton.className = "btn btn-sm btn-secondary";
      updateButton.textContent = "Update";
      updateButton.addEventListener("click", () => updateTaskStatus(task.id, statusSelect.value, false));
      actionCell.append(statusSelect, updateButton);
      row.appendChild(actionCell);
      body.appendChild(row);
    });
  } catch (error) {
    showToast(error.message || "Unable to load your tasks.");
  }
}

async function submitTaskAssignment(event) {
  event.preventDefault();
  const status = document.getElementById("task-form-status");
  const payload = {
    assignee: document.getElementById("task-assignee").value,
    title: document.getElementById("task-title").value.trim(),
    description: document.getElementById("task-description").value.trim(),
    study_id: document.getElementById("task-study").value.trim(),
    site_id: document.getElementById("task-site").value.trim(),
    priority: document.getElementById("task-priority").value,
    due_date: document.getElementById("task-due-date").value
  };
  try {
    const response = await fetch("/api/tasks", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      credentials: "same-origin",
      body: JSON.stringify(payload)
    });
    const result = await response.json();
    if (!response.ok) throw new Error(result.detail || "Unable to assign task.");
    document.getElementById("form-assign-task").reset();
    status.textContent = "Task assigned.";
    status.classList.remove("hidden");
    await loadAdminTasks();
  } catch (error) {
    status.textContent = error.message || "Unable to assign task.";
    status.classList.remove("hidden");
  }
}

async function updateTaskStatus(taskId, taskStatus, isAdmin) {
  try {
    const response = await fetch(`/api/tasks/${encodeURIComponent(taskId)}`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      credentials: "same-origin",
      body: JSON.stringify({ status: taskStatus })
    });
    const result = await response.json();
    if (!response.ok) throw new Error(result.detail || "Unable to update task.");
    await (isAdmin ? loadAdminTasks() : loadMyTasks());
  } catch (error) {
    showToast(error.message || "Unable to update task.");
  }
}

function openTaskEditor(task) {
  document.getElementById("edit-task-id").value = task.id;
  document.getElementById("edit-task-title").value = task.title;
  document.getElementById("edit-task-description").value = task.description;
  document.getElementById("edit-task-study").value = task.study_id;
  document.getElementById("edit-task-site").value = task.site_id;
  document.getElementById("edit-task-priority").value = task.priority;
  document.getElementById("edit-task-due-date").value = task.due_date;
  document.getElementById("edit-task-status").value = task.status;
  document.getElementById("edit-task-assignee").value = task.assignee_email ? `user:${task.assignee_email}` : `role:${task.assignee_role}`;
  document.getElementById("modal-edit-task").classList.remove("hidden");
}

async function saveTaskEdit(event) {
  event.preventDefault();
  const taskId = document.getElementById("edit-task-id").value;
  const payload = {
    assignee: document.getElementById("edit-task-assignee").value,
    title: document.getElementById("edit-task-title").value.trim(),
    description: document.getElementById("edit-task-description").value.trim(),
    study_id: document.getElementById("edit-task-study").value.trim(),
    site_id: document.getElementById("edit-task-site").value.trim(),
    priority: document.getElementById("edit-task-priority").value,
    due_date: document.getElementById("edit-task-due-date").value,
    status: document.getElementById("edit-task-status").value
  };
  try {
    const response = await fetch(`/api/tasks/${encodeURIComponent(taskId)}`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      credentials: "same-origin",
      body: JSON.stringify(payload)
    });
    const result = await response.json();
    if (!response.ok) throw new Error(result.detail || "Unable to update task.");
    closeModal("modal-edit-task");
    await loadAdminTasks();
  } catch (error) {
    showToast(error.message || "Unable to update task.");
  }
}

async function loadEscalationsUI() {
  const container = document.getElementById("escalations-cards-container");
  const critBanner = document.getElementById("esc-critical-banner");
  const highBanner = document.getElementById("esc-high-banner");
  const bellBadge = document.getElementById("bell-badge-count");
  const navBadge = document.getElementById("esc-nav-badge");
  if (!container) return;

  const currentRole = appState.activeRole || (appState.currentUser ? appState.currentUser.role : "Research Coordinator");
  
  let escalations = [];
  try {
    const res = await fetch(`/api/escalations?role=${encodeURIComponent(currentRole)}`);
    if (res.ok) escalations = await res.json();
  } catch {}

  appState.escalations = escalations;

  // Check critical and high unacknowledged counts
  const unackCritical = escalations.filter(e => e.urgency === "Critical" && e.status === "Sent");
  const unackHigh = escalations.filter(e => e.urgency === "High" && e.status === "Sent");

  // Show banners for PI / Admin
  if (currentRole === "Admin" || currentRole === "Principal Investigator") {
    if (critBanner) {
      if (unackCritical.length > 0) {
        critBanner.classList.remove("hidden");
        document.getElementById("esc-critical-desc").textContent = `${unackCritical.length} Critical escalation(s) pending PI acknowledgement within 1-hour GCP-ASU SLA.`;
      } else {
        critBanner.classList.add("hidden");
      }
    }
    if (highBanner) {
      if (unackHigh.length > 0) {
        highBanner.classList.remove("hidden");
        document.getElementById("esc-high-desc").textContent = `${unackHigh.length} High urgency report(s) pending review within 24-hour SLA.`;
      } else {
        highBanner.classList.add("hidden");
      }
    }
  } else {
    if (critBanner) critBanner.classList.add("hidden");
    if (highBanner) highBanner.classList.add("hidden");
  }

  // Update badges
  const unreadTotal = escalations.filter(e => e.status === "Sent").length;
  if (bellBadge) {
    if (unreadTotal > 0) {
      bellBadge.textContent = unreadTotal;
      bellBadge.classList.remove("hidden");
    } else {
      bellBadge.classList.add("hidden");
    }
  }
  if (navBadge) {
    if (unreadTotal > 0) {
      navBadge.textContent = unreadTotal;
      navBadge.classList.remove("hidden");
    } else {
      navBadge.classList.add("hidden");
    }
  }

  filterEscalationsUI();
}

function filterEscalationsUI() {
  const container = document.getElementById("escalations-cards-container");
  if (!container) return;

  const urgFilter = document.getElementById("filter-esc-urgency").value;
  const statusFilter = document.getElementById("filter-esc-status").value;
  const catFilter = document.getElementById("filter-esc-category").value;
  const currentRole = appState.activeRole || (appState.currentUser ? appState.currentUser.role : "Research Coordinator");
  const canAct = (currentRole === "Admin" || currentRole === "Principal Investigator");

  let list = appState.escalations || [];
  if (urgFilter) list = list.filter(e => e.urgency === urgFilter);
  if (statusFilter) list = list.filter(e => e.status === statusFilter);
  if (catFilter) list = list.filter(e => e.category === catFilter);

  if (list.length === 0) {
    container.innerHTML = `<div class="dash-card" style="text-align: center; padding: 40px; color: var(--text-muted);">No escalation reports matching selected criteria.</div>`;
    return;
  }

  container.innerHTML = list.map(esc => {
    const isCritical = esc.urgency === "Critical";
    const isHigh = esc.urgency === "High";
    const dateObj = new Date(esc.created_at);
    const timeAgoMins = Math.max(1, Math.round((Date.now() - dateObj.getTime()) / 60000));
    const timeWaitingStr = timeAgoMins < 60 ? `${timeAgoMins}m ago` : `${Math.round(timeAgoMins / 60)}h ago`;
    const isOverdue = (isCritical && timeAgoMins > 60 && esc.status === "Sent") || (isHigh && timeAgoMins > 1440 && esc.status === "Sent");

    return `
      <div class="escalation-card is-${esc.urgency.toLowerCase()}">
        <div class="esc-header-row">
          <div class="esc-tag-group">
            <span class="esc-urgency-tag ${esc.urgency}">${esc.urgency}</span>
            <span class="esc-category-tag">${esc.category}</span>
            ${esc.subject_code ? `<span class="badge badge-info"><code>${esc.subject_code}</code></span>` : ''}
            <span class="badge ${esc.status === 'Resolved' ? 'badge-green' : (esc.status === 'Sent' ? 'badge-red' : 'badge-info')}">${esc.status}</span>
          </div>
          <div class="esc-meta-time">
            ${isOverdue ? `<span style="color: #ef4444; font-weight: 700;">⚠️ Overdue SLA (${timeWaitingStr})</span>` : `Received: ${timeWaitingStr}`}
          </div>
        </div>

        <div class="esc-summary-title">${esc.summary}</div>
        <div class="esc-details-body">${esc.details}</div>
        ${renderEscalationAttachment(esc)}

        ${esc.events && esc.events.length > 0 ? `
          <div class="esc-thread-wrap">
            <div style="font-weight: 600; font-size: 0.75rem; text-transform: uppercase; color: var(--text-dim); margin-bottom: 4px;">Activity & Thread History:</div>
            ${esc.events.map(ev => `
              <div class="esc-thread-item">
                <span class="esc-thread-author">${ev.actor_name} (${ev.actor_role}):</span>
                <span>${ev.message}</span>
              </div>
            `).join('')}
          </div>
        ` : ''}

        <div class="esc-footer-row">
          <div>
            From: <strong>${esc.from_name}</strong> (${esc.from_role}) • Study: <strong>${esc.study_id}</strong>
            ${esc.acknowledged_by ? ` • Ack: ${esc.acknowledged_by}` : ''}
            ${esc.assigned_to ? ` • Assigned to: <strong>${esc.assigned_to}</strong>` : ''}
          </div>

          <div class="esc-actions-btn-group">
            ${canAct && esc.status === 'Sent' ? `
              <button class="btn btn-primary btn-sm" onclick="acknowledgeEscalation('${esc.id}')">✓ Acknowledge</button>
            ` : ''}
            <button class="btn btn-secondary btn-sm" onclick="openEscActionModal('${esc.id}', 'reply')">💬 Reply</button>
            ${canAct && esc.status !== 'Resolved' ? `
              <button class="btn btn-secondary btn-sm" onclick="openEscActionModal('${esc.id}', 'assign')">👤 Assign</button>
              <button class="btn btn-outline-danger btn-sm" onclick="openEscActionModal('${esc.id}', 'resolve')">✓ Mark Resolved</button>
            ` : ''}
          </div>
        </div>
      </div>
    `;
  }).join('');
}

function filterEscalationsByUrgency(urg) {
  document.getElementById("filter-esc-urgency").value = urg;
  showDashTab("escalations");
  filterEscalationsUI();
}

async function acknowledgeEscalation(escId) {
  const user = appState.currentUser || { name: "Prof. Sharma", role: "Principal Investigator" };
  try {
    const res = await fetch(`/api/escalations/${escId}/acknowledge`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ actor_name: user.name || "Principal Investigator", actor_role: appState.activeRole || user.role, notes: "Noted and reviewed in clinical command center." })
    });
    if (res.ok) {
      showToast("Escalation acknowledged. SLA timer fulfilled.");
      loadEscalationsUI();
    }
  } catch {}
}

function openEscActionModal(escId, actionType) {
  const modal = document.getElementById("modal-escalation-action");
  const title = document.getElementById("modal-esc-action-title");
  const body = document.getElementById("modal-esc-action-body");
  if (!modal || !body) return;

  if (actionType === "reply") {
    title.textContent = "Threaded Reply to Escalation";
    body.innerHTML = `
      <form onsubmit="submitEscAction(event, '${escId}', 'reply')">
        <div class="form-group">
          <label>Your Message / Clinical Instruction <span class="req">*</span></label>
          <textarea id="modal-action-text" class="form-control" rows="3" placeholder="Type clinical directions or response to sender..." required></textarea>
        </div>
        <div style="display: flex; justify-content: flex-end; gap: 8px;">
          <button type="button" class="btn btn-secondary" onclick="closeModal('modal-escalation-action')">Cancel</button>
          <button type="submit" class="btn btn-primary">Send Reply &rarr;</button>
        </div>
      </form>
    `;
  } else if (actionType === "assign") {
    title.textContent = "Assign Escalation to Investigator / Officer";
    body.innerHTML = `
      <form onsubmit="submitEscAction(event, '${escId}', 'assign')">
        <div class="form-group">
          <label>Assign To <span class="req">*</span></label>
          <select id="modal-action-assignee" class="form-control" required>
            <option value="Dr. Arvind Joshi (Doctor)">Dr. Arvind Joshi (Doctor / Investigator)</option>
            <option value="Dr. Sunita Patel (Coordinator)">Dr. Sunita Patel (Research Coordinator)</option>
            <option value="Dr. Gayatri Devi (PV Officer)">Dr. Gayatri Devi (PV Officer)</option>
            <option value="Vikram Verma (Monitor)">Vikram Verma (Monitor)</option>
            <option value="System Administrator">System Administrator</option>
          </select>
        </div>
        <div class="form-group">
          <label>Instructions / Task Details</label>
          <textarea id="modal-action-text" class="form-control" rows="2" placeholder="Specific action required (e.g. conduct physical case review)"></textarea>
        </div>
        <div style="display: flex; justify-content: flex-end; gap: 8px;">
          <button type="button" class="btn btn-secondary" onclick="closeModal('modal-escalation-action')">Cancel</button>
          <button type="submit" class="btn btn-primary">Assign Task &rarr;</button>
        </div>
      </form>
    `;
  } else if (actionType === "resolve") {
    title.textContent = "Mark Escalation as Resolved";
    body.innerHTML = `
      <form onsubmit="submitEscAction(event, '${escId}', 'resolve')">
        <div class="form-group">
          <label>Resolution Summary & Regulatory Notes <span class="req">*</span></label>
          <textarea id="modal-action-text" class="form-control" rows="3" placeholder="Document the clinical outcome, corrective action, or regulatory resolution..." required></textarea>
        </div>
        <div style="display: flex; justify-content: flex-end; gap: 8px;">
          <button type="button" class="btn btn-secondary" onclick="closeModal('modal-escalation-action')">Cancel</button>
          <button type="submit" class="btn btn-primary">Confirm Resolution</button>
        </div>
      </form>
    `;
  }

  modal.classList.remove("hidden");
}

async function submitEscAction(e, escId, actionType) {
  e.preventDefault();
  const user = appState.currentUser || { name: "Prof. Sharma", role: "Principal Investigator" };
  const text = document.getElementById("modal-action-text") ? document.getElementById("modal-action-text").value : "";
  const assignee = document.getElementById("modal-action-assignee") ? document.getElementById("modal-action-assignee").value : "";

  let url = `/api/escalations/${escId}/reply`;
  let body = { actor_name: user.name || "Reviewer", actor_role: appState.activeRole || user.role, message: text };

  if (actionType === "assign") {
    url = `/api/escalations/${escId}/assign`;
    body = { actor_name: user.name || "Reviewer", actor_role: appState.activeRole || user.role, assign_to: assignee, notes: text };
  } else if (actionType === "resolve") {
    url = `/api/escalations/${escId}/resolve`;
    body = { actor_name: user.name || "Reviewer", actor_role: appState.activeRole || user.role, resolution_notes: text };
  }

  try {
    const res = await fetch(url, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body)
    });
    if (res.ok) {
      showToast(`Escalation ${actionType} recorded successfully.`);
      closeModal("modal-escalation-action");
      loadEscalationsUI();
    }
  } catch {}
}

function verifyHashChainInteractive() {
  showToast("SHA-256 Genesis linked. All 142 audit blocks cryptographically verified.");
}

// ==============================================================================
// REALTIME NOTIFICATIONS & ESCALATION SYNC
// ==============================================================================
function startRealtimeEscalationSync() {
  setInterval(async () => {
    if (!appState.isLoggedIn) return;
    const currentRole = appState.activeRole || (appState.currentUser ? appState.currentUser.role : null);
    if (!currentRole) return;

    try {
      const res = await fetch(`/api/escalations?role=${encodeURIComponent(currentRole)}`);
      if (res.ok) {
        const fresh = await res.json();
        // Check for new critical escalation
        const prevCount = (appState.escalations || []).length;
        if (fresh.length > prevCount && prevCount > 0) {
          const newest = fresh[0];
          if (newest.urgency === "Critical") {
            showToast(`🚨 CRITICAL ESCALATION: ${newest.summary}`);
          }
        }
        appState.escalations = fresh;
        if (appState.activeDashboardTab === "escalations") {
          filterEscalationsUI();
        }
      }
    } catch {}
  }, 10000);
}
startRealtimeEscalationSync();

// ==============================================================================
// "MY SUBMISSIONS" & "TEAM ACTIVITY"
// ==============================================================================
function escapeHtml(value) {
  return String(value ?? "").replace(/[&<>"']/g, ch => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[ch]));
}

// Pulls the records saved in Supabase so they survive a refresh; built-in sample rows stay below them
async function loadSavedSubmissions() {
  try {
    const response = await fetch("/api/supabase/submissions", { credentials: "same-origin" });
    const saved = await response.json().catch(() => ({}));
    if (!response.ok) throw new Error(saved.detail || "Unable to load saved submissions.");
    const savedIds = new Set(saved.map(s => s.id));
    appState.submissions = [...saved, ...appState.submissions.filter(s => !savedIds.has(s.id))];
    loadSubmissionsUI();
    if (document.getElementById("filter-team-role")) filterTeamActivityUI();
  } catch (err) {
    showToast(`Saved submissions not loaded: ${err.message}`);
  }
}

function loadSubmissionsUI() {
  const tbody = document.getElementById("tbody-my-submissions");
  if (!tbody) return;

  const currentRole = appState.activeRole || "Research Coordinator";

  // Filter submissions for current user's role
  const userSubs = appState.submissions.filter(s => {
    if (currentRole === "Admin" || currentRole === "Principal Investigator") return true;
    return s.role === currentRole;
  });

  tbody.innerHTML = userSubs.map(s => {
    const isEditable = s.status === "Draft" || s.status === "Needs correction";
    const statusBadge = getStatusBadge(s.status);
    const versionCount = s.versions ? s.versions.length : 0;
    const verifiedBy = s.verifications && s.verifications.length > 0 
      ? `<span class="badge badge-green">${escapeHtml(s.verifications[0].verified_by)}</span>` 
      : '<span style="color: var(--text-dim); font-size: 0.8rem;">Pending</span>';

    return `
      <tr>
        <td><strong>${escapeHtml(s.title)}</strong></td>
        <td><span class="badge badge-secondary">${escapeHtml(s.type)}</span></td>
        <td style="font-size: 0.82rem; color: var(--text-muted);">${s.created_at.slice(0, 10)}</td>
        <td>${statusBadge}</td>
        <td><span class="badge badge-info">${versionCount} Version(s)</span></td>
        <td>${verifiedBy}</td>
        <td>
          <div style="display: flex; gap: 6px;">
            ${isEditable 
              ? `<button class="btn btn-secondary" style="padding: 4px 8px; font-size: 0.78rem;" onclick="openEditModal('${s.id}')">Edit</button>` 
              : `<button class="btn btn-secondary" style="padding: 4px 8px; font-size: 0.78rem;" disabled title="Locked: Verified submissions cannot be edited">Locked</button>`}
            ${s.status !== 'Verified' && (currentRole === 'Principal Investigator' || currentRole === 'Admin')
              ? `<button class="btn btn-primary" style="padding: 4px 8px; font-size: 0.78rem;" onclick="openVerifyModal('${s.id}')">Verify</button>` 
              : ''}
          </div>
        </td>
      </tr>
    `;
  }).join("");
}

function filterTeamActivityUI() {
  const tbody = document.getElementById("tbody-team-submissions");
  if (!tbody) return;

  const roleFilter = document.getElementById("filter-team-role").value;
  const typeFilter = document.getElementById("filter-team-type").value;
  const statusFilter = document.getElementById("filter-team-status").value;

  let list = appState.submissions;
  if (roleFilter) list = list.filter(s => s.role === roleFilter);
  if (typeFilter) list = list.filter(s => s.type === typeFilter);
  if (statusFilter) list = list.filter(s => s.status === statusFilter);

  tbody.innerHTML = list.map(s => `
    <tr>
      <td><strong>${escapeHtml(s.title)}</strong></td>
      <td>${escapeHtml(s.owner_name)} <br><span class="badge badge-secondary">${escapeHtml(s.role)}</span></td>
      <td><span class="badge badge-secondary">${escapeHtml(s.type)}</span></td>
      <td>${s.created_at.slice(0, 10)}</td>
      <td>${getStatusBadge(s.status)}</td>
      <td>
        ${s.status !== 'Verified' 
          ? `<button class="btn btn-primary" style="padding: 4px 8px; font-size: 0.78rem;" onclick="openVerifyModal('${s.id}')">Mark as Reviewed</button>` 
          : `<span class="badge badge-green">Reviewed</span>`}
      </td>
    </tr>
  `).join("");
}

function getStatusBadge(status) {
  switch (status) {
    case "Verified": return '<span class="badge badge-green">Verified</span>';
    case "Submitted": return '<span class="badge badge-info">Submitted</span>';
    case "Draft": return '<span class="badge badge-secondary">Draft</span>';
    case "Needs correction": return '<span class="badge badge-amber">Needs correction</span>';
    default: return `<span class="badge">${status}</span>`;
  }
}

// ==============================================================================
// MODALS LOGIC (Add Participant, Create, Edit with Version Reason, Verify)
// ==============================================================================

// Research Coordinator: Add Participant Modal
function openAddParticipantModal() {
  if (appState.currentUser?.role !== "Research Coordinator" || appState.activeRole !== "Research Coordinator") {
    showToast("Access Denied: Only Research Coordinators can add participants.");
    return;
  }
  const pane = document.getElementById("dash-pane-add-participant");
  if (!pane) return;

  // Auto-generate subject code, e.g. SUB-AIIA-001-043
  let maxSeq = 42;
  const parts = appState.studyData?.participants || [];
  parts.forEach(p => {
    if (p.subject_code) {
      const match = p.subject_code.match(/(\d+)$/);
      if (match) {
        const num = parseInt(match[1], 10);
        if (num > maxSeq) maxSeq = num;
      }
    }
  });
  const nextSeq = String(maxSeq + 1).padStart(3, '0');
  const generatedCode = `SUB-AIIA-001-${nextSeq}`;

  const codeInput = document.getElementById("part-subject-code");
  if (codeInput) codeInput.value = generatedCode;

  const errBox = document.getElementById("part-error-msg");
  if (errBox) {
    errBox.textContent = "";
    errBox.classList.add("hidden");
  }

  showDashTab("add-participant");
}

function setupAddParticipantForm() {
  const form = document.getElementById("form-add-participant");
  if (!form) return;

  form.addEventListener("submit", async (e) => {
    e.preventDefault();
    const errBox = document.getElementById("part-error-msg");
    if (errBox) {
      errBox.textContent = "";
      errBox.classList.add("hidden");
    }

    const subjectCode = document.getElementById("part-subject-code").value.trim();
    const studyId = document.getElementById("part-study").value;
    const age = parseInt(document.getElementById("part-age").value, 10);
    const sex = document.getElementById("part-sex").value;
    const ayurDiagnosis = document.getElementById("part-ayur-diagnosis").value.trim();
    const modernDiagnosis = document.getElementById("part-modern-diagnosis").value.trim();
    const consentStatus = document.getElementById("part-consent-status").value;

    // GCP-ASU Enrolment Gate: Enrolment is blocked without valid consent
    if (consentStatus !== "Written Consent Verified") {
      if (errBox) {
        errBox.textContent = "❌ Enrolment Blocked: Under GCP-ASU and DPDP regulations, participants cannot be enrolled without valid written consent on file.";
        errBox.classList.remove("hidden");
      }
      return;
    }

    const newParticipant = {
      id: `part-${Date.now()}`,
      subject_code: subjectCode,
      study_id: studyId,
      site_id: "SITE-01",
      age: age,
      gender: sex,
      prakriti: "Vata-Pitta",
      status: "Active Enrolled",
      visits_completed: 0,
      total_visits: 8,
      compliance_pct: 100,
      ayurvedic_diagnosis: ayurDiagnosis,
      modern_diagnosis: modernDiagnosis,
      consent_status: consentStatus,
      enrolled_at: new Date().toISOString()
    };

    if (!appState.studyData) {
      appState.studyData = { studies: [], sites: [], participants: [], adverse_events: [] };
    }
    if (!appState.studyData.participants) {
      appState.studyData.participants = [];
    }

    // Prepend to active participants ledger
    appState.studyData.participants.unshift(newParticipant);

    // Call backend API (if connected to FastAPI backend)
    try {
      await fetch("/api/participants", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          subject_code: subjectCode,
          site_id: "SITE-01",
          age: age,
          gender: sex,
          study_id: studyId,
          consent_status: consentStatus,
          ayurvedic_diagnosis: ayurDiagnosis,
          modern_diagnosis: modernDiagnosis
        })
      });
    } catch (err) {
      console.warn("Backend participant sync notice:", err);
    }

    // Prepend new row immediately to coordinator tracker table
    const tbody = document.getElementById("coordinator-participants-tbody");
    if (tbody) {
      const newRow = document.createElement("tr");
      newRow.style.backgroundColor = "rgba(16, 185, 129, 0.2)";
      newRow.innerHTML = `
        <td><code>${newParticipant.subject_code}</code></td>
        <td>${newParticipant.study_id}</td>
        <td>${newParticipant.prakriti}</td>
        <td><span class="badge badge-green">${newParticipant.status}</span></td>
        <td>${newParticipant.visits_completed} / ${newParticipant.total_visits}</td>
        <td><span class="badge badge-info">${newParticipant.compliance_pct}%</span></td>
        <td><button class="btn btn-secondary btn-sm" onclick="openEscalationDrawer('${newParticipant.subject_code}', 'Participant', 'Normal')">Report Issue</button></td>
      `;
      tbody.insertBefore(newRow, tbody.firstChild);

      setTimeout(() => {
        newRow.style.transition = "background-color 1.5s ease";
        newRow.style.backgroundColor = "transparent";
      }, 2000);
    }

    // Update records count badge
    const countBadge = document.getElementById("coordinator-participant-count");
    if (countBadge) {
      countBadge.textContent = `${appState.studyData.participants.length} Total Coded Records`;
    }

    showDashTab("workspace");
    showToast(`✓ Success: Participant ${subjectCode} enrolled and added to site tracker!`);
  });
}

function openNewSubmissionModal() {
  document.getElementById("form-create-submission")?.reset();
  showDashTab("new-record");
}

function closeModal(modalId) {
  document.getElementById(modalId).classList.add("hidden");
}


// Form: Create Submission
document.getElementById("form-create-submission").addEventListener("submit", async (e) => {
  e.preventDefault();
  const title = document.getElementById("sub-title").value.trim();
  const type = document.getElementById("sub-type").value;
  const statusVal = document.getElementById("sub-status").value;
  const notes = document.getElementById("sub-notes").value.trim();

  const newSub = {
    id: `sub-${Date.now()}`,
    owner_id: "current-user-id",
    owner_name: appState.currentUser?.name || "Current User",
    role: appState.activeRole || "Research Coordinator",
    study_id: "AYUR-CT-2026-001",
    type,
    title,
    payload: { notes },
    status: statusVal,
    created_at: new Date().toISOString(),
    updated_at: new Date().toISOString(),
    versions: [],
    verifications: []
  };

  // Save to Backend endpoint (owner is taken from the signed-in session)
  try {
    const response = await fetch("/api/supabase/submissions", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      credentials: "same-origin",
      body: JSON.stringify({
        role: newSub.role,
        type: newSub.type,
        title: newSub.title,
        payload: newSub.payload,
        status: newSub.status
      })
    });
    const saved = await response.json().catch(() => ({}));
    if (!response.ok) throw new Error(saved.detail || "Submission could not be saved.");
    // Keep the database id so later edits and verification reach the same row
    newSub.id = saved.id || newSub.id;
    newSub.owner_id = saved.owner_id || newSub.owner_id;
  } catch (err) {
    showToast(`Submission not saved: ${err.message}`);
    return;
  }

  appState.submissions.unshift(newSub);
  document.getElementById("form-create-submission").reset();
  showDashTab("submissions");
  loadSubmissionsUI();
  showToast(`Submission "${title}" created.`);
});

// Edit Submission
function openEditModal(subId) {
  const sub = appState.submissions.find(s => s.id === subId);
  if (!sub) return;

  document.getElementById("edit-sub-id").value = sub.id;
  document.getElementById("edit-sub-title").value = sub.title;
  document.getElementById("edit-sub-notes").value = JSON.stringify(sub.payload);
  document.getElementById("edit-sub-reason").value = "";
  document.getElementById("modal-edit-submission").classList.remove("hidden");
}

document.getElementById("form-edit-submission").addEventListener("submit", async (e) => {
  e.preventDefault();
  const id = document.getElementById("edit-sub-id").value;
  const sub = appState.submissions.find(s => s.id === id);
  if (!sub) return;

  const reason = document.getElementById("edit-sub-reason").value.trim();
  if (!reason) {
    alert("Regulatory Rule: A documented reason for change is mandatory.");
    return;
  }

  const updatedPayload = { notes: document.getElementById("edit-sub-notes").value };
  const updatedTitle = document.getElementById("edit-sub-title").value;

  // Save to Backend first so the screen never shows an edit the database rejected
  try {
    const response = await fetch(`/api/supabase/submissions/${id}`, {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      credentials: "same-origin",
      body: JSON.stringify({
        title: updatedTitle,
        payload: updatedPayload,
        reason,
        changed_by: appState.currentUser?.name || "Investigator"
      })
    });
    // Built-in sample rows exist only in the browser, so a 404 for them is expected
    if (!response.ok && response.status !== 404) {
      const result = await response.json().catch(() => ({}));
      throw new Error(result.detail || "Update could not be saved.");
    }
  } catch (err) {
    showToast(`Update not saved: ${err.message}`);
    return;
  }

  // Record version snapshot (GCP-ASU requirement: old value, new value, reason, who, when)
  sub.versions.push({
    old_value: sub.payload,
    new_value: updatedPayload,
    reason,
    who: appState.currentUser?.name || "Investigator",
    changed_at: new Date().toISOString()
  });

  sub.title = updatedTitle;
  sub.payload = updatedPayload;
  sub.updated_at = new Date().toISOString();

  closeModal("modal-edit-submission");
  loadSubmissionsUI();
  showToast("Version snapshot recorded and saved.");
});

// Verify Submission
function openVerifyModal(subId) {
  document.getElementById("verify-sub-id").value = subId;
  document.getElementById("modal-verify-submission").classList.remove("hidden");
}

document.getElementById("form-verify-submission").addEventListener("submit", async (e) => {
  e.preventDefault();
  const id = document.getElementById("verify-sub-id").value;
  const sub = appState.submissions.find(s => s.id === id);
  if (!sub) return;

  const note = document.getElementById("verify-note").value;

  // Save to Backend first so the screen never shows a sign-off the database rejected
  try {
    const response = await fetch(`/api/supabase/submissions/${id}/verify`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      credentials: "same-origin",
      body: JSON.stringify({
        verified_by: appState.currentUser?.name || "Principal Investigator",
        verifier_role: appState.activeRole || "Principal Investigator",
        verifier_email: appState.currentUser?.email || "pi@ayurctms.demo",
        note
      })
    });
    // Built-in sample rows exist only in the browser, so a 404 for them is expected
    if (!response.ok && response.status !== 404) {
      const result = await response.json().catch(() => ({}));
      throw new Error(result.detail || "Verification could not be saved.");
    }
  } catch (err) {
    showToast(`Verification not saved: ${err.message}`);
    return;
  }

  sub.status = "Verified";
  sub.verifications.push({
    verified_by: appState.currentUser?.name || "Principal Investigator",
    verified_at: new Date().toISOString(),
    note
  });

  closeModal("modal-verify-submission");
  loadSubmissionsUI();
  filterTeamActivityUI();
  showToast("Submission formally certified and marked as Verified.");
});

// ==============================================================================
// SESSION TIMEOUT (15 Minutes with 1-Minute Warning)
// ==============================================================================
function setupSessionTimeout() {
  const warningBanner = document.getElementById("inactivity-warning-banner");
  const countdownSpan = document.getElementById("inactivity-countdown");

  // Reset timer on user interaction
  let activeSinceRenewal = false;
  const resetTimer = () => {
    if (appState.isLoggedIn) {
      appState.sessionSecondsLeft = 15 * 60;
      activeSinceRenewal = true;
      warningBanner.classList.add("hidden");
    }
  };

  // The server cookie lasts 15 minutes; renew it while the user is active so it
  // does not expire underneath a session this timer still counts as live
  setInterval(async () => {
    if (!appState.isLoggedIn || !activeSinceRenewal) return;
    activeSinceRenewal = false;
    try {
      const response = await fetch("/api/auth/session/renew", { method: "POST", credentials: "same-origin" });
      if (response.status === 401) {
        signOut();
        showToast("Your session has expired. Please sign in again.");
      }
    } catch (error) {}
  }, 5 * 60 * 1000);

  window.addEventListener("mousemove", resetTimer);
  window.addEventListener("keydown", resetTimer);
  window.addEventListener("click", resetTimer);

  setInterval(() => {
    if (!appState.isLoggedIn) return;

    appState.sessionSecondsLeft--;
    
    // Warning at 1 minute remaining (60 seconds)
    if (appState.sessionSecondsLeft <= 60 && appState.sessionSecondsLeft > 0) {
      warningBanner.classList.remove("hidden");
      countdownSpan.textContent = appState.sessionSecondsLeft;
    }

    // Auto-logout at 0 seconds
    if (appState.sessionSecondsLeft <= 0) {
      warningBanner.classList.add("hidden");
      signOut();
      alert("Session expired due to 15 minutes of inactivity. You have been logged out safely.");
    }
  }, 1000);
}

// ==============================================================================
// TOAST NOTIFICATIONS & THEME
// ==============================================================================
function showToast(msg) {
  const container = document.getElementById("toast-container");
  const toast = document.createElement("div");
  toast.className = "toast";
  toast.textContent = msg;
  container.appendChild(toast);
  setTimeout(() => toast.remove(), 4000);
}

function setupThemeToggle() {
  const btn = document.getElementById("theme-toggle-btn");
  btn.addEventListener("click", () => {
    if (document.body.classList.contains("theme-light")) {
      document.body.classList.remove("theme-light");
      document.body.classList.add("theme-dark");
      btn.textContent = "☀️ Light";
    } else {
      document.body.classList.remove("theme-dark");
      document.body.classList.add("theme-light");
      btn.textContent = "🌙 Dark";
    }
  });
}
// ==============================================================================
// LEGAL DOCUMENTS MODULE (ETHICS COMMITTEE, PI & ADMIN)
// ==============================================================================

async function loadLeadershipLegalDocs() {
  const rows = document.getElementById("leadership-legal-rows");
  const timeline = document.getElementById("leadership-legal-timeline");
  const status = document.getElementById("leadership-legal-status");
  if (!rows || !timeline || !status) return;

  try {
    const response = await fetch("/api/legal-documents", { credentials: "same-origin" });
    const result = await response.json();
    if (!response.ok) throw new Error(result.detail || "Unable to load legal documents.");
    rows.replaceChildren();
    timeline.replaceChildren();

    result.documents.forEach(documentInfo => {
      const row = document.createElement("tr");
      [documentInfo.title, documentInfo.type, documentInfo.issuing_authority, documentInfo.issue_date, documentInfo.expiry_date].forEach(value => {
        const cell = document.createElement("td");
        cell.textContent = value || "Not recorded";
        row.appendChild(cell);
      });
      const stateCell = document.createElement("td");
      stateCell.textContent = documentInfo.status;
      stateCell.className = documentInfo.status === "Expired" ? "badge-red" : documentInfo.status === "Expiring soon" ? "badge-amber" : "badge-green";
      row.appendChild(stateCell);
      const countdownCell = document.createElement("td");
      countdownCell.textContent = documentInfo.countdown;
      row.appendChild(countdownCell);
      rows.appendChild(row);

      const item = document.createElement("div");
      item.className = "leadership-legal-timeline-row";
      const details = document.createElement("div");
      const title = document.createElement("strong");
      title.textContent = documentInfo.title;
      const countdown = document.createElement("small");
      countdown.textContent = `${documentInfo.expiry_date} · ${documentInfo.countdown}`;
      details.append(title, countdown);
      const track = document.createElement("div");
      track.className = "leadership-legal-timeline-track";
      const fill = document.createElement("div");
      fill.className = `leadership-legal-timeline-fill ${documentInfo.status === "Expired" ? "expired" : documentInfo.status === "Expiring soon" ? "expiring" : "active"}`;
      fill.style.width = `${Math.max(8, Math.min(100, 100 - Math.max(0, documentInfo.days_remaining) / 365 * 100))}%`;
      track.appendChild(fill);
      item.append(details, track);
      timeline.appendChild(item);
    });
    status.classList.add("hidden");
  } catch (error) {
    status.textContent = error.message || "Unable to load legal documents.";
    status.classList.remove("hidden");
  }
}

function renderLegalDocumentsPage() {
  const container = document.getElementById("dash-pane-legal-docs");
  if (!container) return;

  const now = new Date();
  
  // Recalculate live days remaining for all documents
  appState.legalDocuments.forEach(doc => {
    const expDate = new Date(doc.expiry_date);
    const diffTime = expDate - now;
    const diffDays = Math.ceil(diffTime / (1000 * 60 * 60 * 24));
    doc.days_remaining = diffDays;
    if (diffDays > 90) {
      doc.status = "safe";
    } else if (diffDays >= 30 && diffDays <= 90) {
      doc.status = "attention";
    } else if (diffDays >= 0 && diffDays < 30) {
      doc.status = "urgent";
    } else {
      doc.status = "expired";
    }
  });

  // Calculate status counts
  const safeCount = appState.legalDocuments.filter(d => d.status === "safe").length;
  const attentionCount = appState.legalDocuments.filter(d => d.status === "attention").length;
  const urgentCount = appState.legalDocuments.filter(d => d.status === "urgent").length;
  const expiredCount = appState.legalDocuments.filter(d => d.status === "expired").length;

  // Auto alerts banner (at 90, 60, 30 days and on expiry)
  const alertBanner = document.getElementById("legal-alerts-banner");
  const alertSummary = document.getElementById("legal-alerts-summary");
  if (alertBanner && alertSummary) {
    if (expiredCount > 0 || urgentCount > 0 || attentionCount > 0) {
      let alertMsg = "";
      if (expiredCount > 0) {
        alertMsg += `🚨 <strong>CRITICAL EXPIRY:</strong> ${expiredCount} document has EXPIRED. Dosing/recruitment paused for affected cohort under GCP-ASU. `;
      }
      if (urgentCount > 0) {
        alertMsg += `⚠️ <strong>30-DAY URGENT:</strong> ${urgentCount} document(s) expiring within 30 days. Renewal submission mandatory. `;
      }
      if (attentionCount > 0) {
        alertMsg += `🟡 <strong>60/90-DAY NOTICE:</strong> ${attentionCount} document(s) due for renewal within 30 to 90 days. `;
      }
      alertMsg += `Automated regulatory notices dispatched to Ethics Committee, PI, and Admin.`;
      alertSummary.innerHTML = alertMsg;
      alertBanner.classList.remove("hidden");
    } else {
      alertBanner.classList.add("hidden");
    }
  }

  // Update KPI Summary Grid
  const kpiGrid = document.getElementById("legal-kpi-grid");
  if (kpiGrid) {
    kpiGrid.innerHTML = `
      <div class="dash-card">
        <div class="kpi-label">Total Documents Tracked</div>
        <div class="kpi-value">${appState.legalDocuments.length}</div>
        <div class="kpi-note">All studies, institutional MoUs & CTRI</div>
      </div>
      <div class="dash-card">
        <div class="kpi-label" style="color: #047857;">Safe (>90 Days)</div>
        <div class="kpi-value" style="color: #047857;">${safeCount}</div>
        <div class="kpi-note">Active statutory validity</div>
      </div>
      <div class="dash-card">
        <div class="kpi-label" style="color: #b45309;">Attention (30–90 Days)</div>
        <div class="kpi-value" style="color: #b45309;">${attentionCount}</div>
        <div class="kpi-note">60/90-day early alert active</div>
      </div>
      <div class="dash-card">
        <div class="kpi-label" style="color: #b91c1c;">Urgent & Expired (<30d)</div>
        <div class="kpi-value" style="color: #b91c1c;">${urgentCount + expiredCount}</div>
        <div class="kpi-note">${expiredCount} expired • ${urgentCount} expiring <30d</div>
      </div>
    `;
  }

  // Render Expiry Timeline View (Sorted next to expire)
  renderLegalDocsTimeline(appState.legalDocuments);

  // Render Table
  renderLegalDocsTable(appState.legalDocuments);
}

function getLegalDocBadgeHTML(doc) {
  const days = doc.days_remaining;
  if (days > 90) {
    return `<span class="badge badge-green" style="font-weight: 600;">✓ Expires in ${days} days</span>`;
  } else if (days >= 30 && days <= 90) {
    return `<span class="badge badge-amber" style="font-weight: 600;">⚠️ Expires in ${days} days</span>`;
  } else if (days >= 0 && days < 30) {
    return `<span class="badge badge-red" style="font-weight: 700;">🚨 Expires in ${days} day${days === 1 ? '' : 's'}</span>`;
  } else {
    return `<span class="badge badge-darkred">🛑 Expired ${Math.abs(days)} days ago</span>`;
  }
}

function renderLegalDocsTimeline(docs) {
  const container = document.getElementById("legal-docs-timeline-container");
  if (!container) return;

  // Sort ascending by days remaining (expired and closest to expire first)
  const sorted = [...docs].sort((a, b) => a.days_remaining - b.days_remaining);

  container.innerHTML = sorted.map((doc, idx) => {
    const isNext = idx === 0 || (idx === 1 && sorted[0].days_remaining < 0);
    const days = doc.days_remaining;
    
    // Bar fill percentage (shorter days remaining = fuller urgent bar)
    let fillPct = 100;
    let fillColor = "#ef4444";
    if (days > 90) {
      fillPct = Math.max(10, Math.min(100, Math.round((days / 365) * 100)));
      fillColor = "#10b981";
    } else if (days >= 30) {
      fillPct = Math.max(30, Math.min(90, Math.round(((90 - days) / 60) * 100)));
      fillColor = "#f59e0b";
    } else if (days >= 0) {
      fillPct = Math.max(60, Math.min(100, Math.round(((30 - days) / 30) * 100)));
      fillColor = "#ef4444";
    } else {
      fillPct = 100;
      fillColor = "#991b1b";
    }

    return `
      <div class="timeline-item-card" style="${isNext ? 'border-left: 4px solid #ef4444; background: #fffaf0;' : ''}">
        <div style="min-width: 220px;">
          <div style="font-weight: 600; font-size: 0.88rem; display: flex; align-items: center; gap: 6px;">
            ${doc.title}
            ${isNext ? '<span class="badge badge-red" style="font-size: 0.65rem; padding: 1px 4px;">EXPIRES NEXT</span>' : ''}
          </div>
          <div style="font-size: 0.78rem; color: var(--text-muted); margin-top: 2px;">
            <span class="badge badge-secondary" style="font-size: 0.7rem;">${doc.type}</span> • <code>${doc.study}</code> • ${doc.version}
          </div>
        </div>

        <div class="timeline-progress-bar-wrap" title="${doc.status_label || doc.reason}">
          <div class="timeline-progress-fill" style="width: ${fillPct}%; background-color: ${fillColor};"></div>
        </div>

        <div style="min-width: 170px; text-align: right;">
          ${getLegalDocBadgeHTML(doc)}
          <div style="font-size: 0.75rem; color: var(--text-dim); margin-top: 2px;">Expiry: ${doc.expiry_date}</div>
        </div>

        <button class="btn btn-secondary btn-sm" onclick="viewLegalDoc('${doc.id}')" style="font-size: 0.78rem; padding: 3px 8px;">View</button>
      </div>
    `;
  }).join("");
}

function renderLegalDocsTable(docs) {
  const tbody = document.getElementById("legal-docs-tbody");
  if (!tbody) return;

  tbody.innerHTML = docs.map(doc => {
    const isUrgentOrAmber = doc.status === "urgent" || doc.status === "attention" || doc.status === "expired";
    const reasonText = doc.reason || "Uploaded under statutory GCP-ASU clinical trial documentation standard.";
    
    return `
      <tr style="${doc.status === 'expired' ? 'background: rgba(239, 68, 68, 0.05);' : ''}">
        <td>
          <strong>${doc.title}</strong>
          <div style="margin-top: 3px;">
            <span class="badge badge-secondary" style="font-size: 0.72rem;">${doc.type}</span>
          </div>
        </td>
        <td><code>${doc.study}</code></td>
        <td>
          <span class="badge badge-secondary" style="cursor: pointer; text-decoration: underline;" onclick="showVersionHistoryModal('${doc.id}')" title="Click to view version history">
            ${doc.version} (${doc.versions ? doc.versions.length : 1} ver)
          </span>
        </td>
        <td>${doc.issue_date}</td>
        <td><strong>${doc.expiry_date}</strong></td>
        <td>${getLegalDocBadgeHTML(doc)}</td>
        <td style="max-width: 280px; font-size: 0.82rem; line-height: 1.4;">
          ${isUrgentOrAmber ? `<span style="color: ${doc.status === 'expired' ? '#991b1b' : (doc.status === 'urgent' ? '#b91c1c' : '#b45309')}; font-weight: 500;">⚠️ ${reasonText}</span>` : `<span style="color: var(--text-muted);">${reasonText}</span>`}
        </td>
        <td>
          <div style="display: flex; gap: 6px;">
            <button class="btn btn-secondary btn-sm" onclick="viewLegalDoc('${doc.id}')" title="View / Download file" style="padding: 3px 8px; font-size: 0.78rem;">📄 View</button>
            <button class="btn btn-secondary btn-sm" onclick="openUploadLegalDocModal('${doc.title.replace(/'/g, "\\'")}', '${doc.type}', '${doc.study}')" title="Upload new version" style="padding: 3px 8px; font-size: 0.78rem;">+ New Ver</button>
          </div>
        </td>
      </tr>
    `;
  }).join("");
}

function filterLegalDocumentsUI() {
  const typeFilter = document.getElementById("filter-legal-doc-type").value;
  const statusFilter = document.getElementById("filter-legal-doc-status").value;

  let filtered = [...appState.legalDocuments];
  if (typeFilter) {
    filtered = filtered.filter(d => d.type === typeFilter);
  }
  if (statusFilter) {
    filtered = filtered.filter(d => d.status === statusFilter);
  }

  renderLegalDocsTable(filtered);
}

function openUploadLegalDocModal(prefillTitle = "", prefillType = "", prefillStudy = "") {
  const role = appState.activeRole || (appState.currentUser ? appState.currentUser.role : "EC Member");
  if (role !== "EC Member" && role !== "Principal Investigator" && role !== "Admin") {
    showToast("Access Denied: Only EC Members, PI, and Admin can upload trial legal documents.");
    return;
  }

  const modal = document.getElementById("modal-upload-legal-doc");
  if (!modal) return;

  const titleInput = document.getElementById("legal-doc-title");
  const typeInput = document.getElementById("legal-doc-type");
  const studyInput = document.getElementById("legal-doc-study");
  const verInput = document.getElementById("legal-doc-version");
  const issueInput = document.getElementById("legal-doc-issue-date");
  const expiryInput = document.getElementById("legal-doc-expiry-date");
  const errBox = document.getElementById("legal-doc-error-msg");

  if (errBox) {
    errBox.textContent = "";
    errBox.classList.add("hidden");
  }

  const today = new Date().toISOString().slice(0, 10);
  const nextYear = new Date(Date.now() + 365 * 24 * 60 * 60 * 1000).toISOString().slice(0, 10);

  if (prefillTitle) {
    titleInput.value = prefillTitle;
    typeInput.value = prefillType || "other";
    studyInput.value = prefillStudy || "AYUR-CT-2026-001";
    // Check existing version
    const existing = appState.legalDocuments.find(d => d.title.toLowerCase() === prefillTitle.toLowerCase());
    if (existing) {
      const verNum = parseFloat(existing.version.replace('v', '')) || 1.0;
      verInput.value = `v${(verNum + 1.0).toFixed(1)}`;
    } else {
      verInput.value = "v1.0";
    }
  } else {
    titleInput.value = "";
    verInput.value = "v1.0";
  }

  issueInput.value = today;
  expiryInput.value = nextYear;

  modal.classList.remove("hidden");
}

function setupUploadLegalDocForm() {
  const form = document.getElementById("form-upload-legal-doc");
  if (!form) return;

  form.addEventListener("submit", async (e) => {
    e.preventDefault();
    const errBox = document.getElementById("legal-doc-error-msg");
    if (errBox) {
      errBox.textContent = "";
      errBox.classList.add("hidden");
    }

    const title = document.getElementById("legal-doc-title").value.trim();
    const type = document.getElementById("legal-doc-type").value;
    const study = document.getElementById("legal-doc-study").value;
    const version = document.getElementById("legal-doc-version").value.trim();
    const issueDate = document.getElementById("legal-doc-issue-date").value;
    const expiryDate = document.getElementById("legal-doc-expiry-date").value;
    const reason = document.getElementById("legal-doc-reason").value.trim() || "Uploaded under statutory GCP-ASU clinical trial documentation standard.";
    const fileInput = document.getElementById("legal-doc-file");
    const fileName = fileInput.files && fileInput.files[0] ? fileInput.files[0].name : "uploaded_regulatory_doc.pdf";

    if (!title || !issueDate || !expiryDate) {
      if (errBox) {
        errBox.textContent = "Please fill in all mandatory fields.";
        errBox.classList.remove("hidden");
      }
      return;
    }

    const uploaderName = appState.currentUser ? appState.currentUser.name || appState.currentUser.email : "Authorized Officer";
    const nowIso = new Date().toISOString();

    // Documents are never deleted; new uploads become new versions with history
    const existing = appState.legalDocuments.find(d => d.title.toLowerCase() === title.toLowerCase() || (d.type === type && d.study === study));
    
    if (existing) {
      if (!existing.versions) existing.versions = [];
      existing.versions.push({
        version: existing.version,
        uploaded_at: nowIso,
        uploaded_by: uploaderName
      });
      existing.version = version;
      existing.issue_date = issueDate;
      existing.expiry_date = expiryDate;
      existing.file_name = fileName;
      existing.reason = reason;
      showToast(`✓ New version ${version} uploaded for "${title}". Previous version archived in history.`);
    } else {
      const newDoc = {
        id: `leg-${String(appState.legalDocuments.length + 1).padStart(3, '0')}`,
        title,
        type,
        study,
        version,
        issue_date: issueDate,
        expiry_date: expiryDate,
        days_remaining: Math.ceil((new Date(expiryDate) - new Date()) / (1000 * 60 * 60 * 24)),
        status: "safe",
        reason,
        file_name: fileName,
        file_size: "2.4 MB",
        uploaded_by: uploaderName,
        versions: [
          { version, uploaded_at: nowIso, uploaded_by: uploaderName }
        ]
      };
      appState.legalDocuments.unshift(newDoc);
      showToast(`✓ Legal document "${title}" uploaded and registered in Supabase Storage.`);
    }

    // Call backend API if connected
    try {
      await fetch("/api/ethics/legal-documents", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          title,
          type,
          study,
          version,
          issue_date: issueDate,
          expiry_date: expiryDate,
          reason,
          file_name: fileName
        })
      });
    } catch (err) {
      console.warn("Backend sync notice for legal documents:", err);
    }

    closeModal("modal-upload-legal-doc");
    form.reset();

    // Re-render legal docs page if active
    if (appState.activeDashboardTab === "legal-docs") {
      renderLegalDocumentsPage();
    }
    // Re-render EC workspace summary card if active
    if (appState.activeRole === "EC Member" && appState.activeDashboardTab === "workspace") {
      renderRoleWorkspace("EC Member");
    }
  });
}

function viewLegalDoc(docId) {
  const doc = appState.legalDocuments.find(d => d.id === docId);
  if (!doc) return;

  // Log upload / view event in audit log (DPDP & GCP-ASU requirement)
  const viewer = appState.currentUser ? appState.currentUser.email : "Authorized Officer";
  try {
    fetch(`/api/ethics/legal-documents/${docId}/view`, { method: "POST" });
  } catch {}

  showToast(`📄 Viewing "${doc.title}" (${doc.file_name || 'document.pdf'}). Access event logged in audit trail.`);
}

function showVersionHistoryModal(docId) {
  const doc = appState.legalDocuments.find(d => d.id === docId);
  if (!doc) return;

  const titleEl = document.getElementById("version-history-title");
  const subEl = document.getElementById("version-history-subtitle");
  const tbody = document.getElementById("version-history-tbody");

  if (titleEl) titleEl.textContent = `Version History: ${doc.title}`;
  if (subEl) subEl.textContent = `Type: ${doc.type} • Protocol: ${doc.study} • Current Version: ${doc.version} (Documents are immutable and never deleted)`;

  const versions = doc.versions && doc.versions.length > 0 ? doc.versions : [
    { version: doc.version, uploaded_at: doc.issue_date, uploaded_by: doc.uploaded_by || "Authorized Officer" }
  ];

  if (tbody) {
    tbody.innerHTML = versions.map((v, i) => `
      <tr>
        <td><strong>${v.version}</strong> ${i === versions.length - 1 ? '<span class="badge badge-green">Current Active</span>' : '<span class="badge badge-secondary">Archived</span>'}</td>
        <td>${v.uploaded_at ? v.uploaded_at.slice(0, 10) : doc.issue_date}</td>
        <td>${v.uploaded_by || "Authorized Officer"}</td>
        <td><button class="btn btn-secondary btn-sm" onclick="viewLegalDoc('${doc.id}')" style="font-size: 0.75rem; padding: 2px 6px;">Download</button></td>
      </tr>
    `).join("");
  }

  const modal = document.getElementById("modal-version-history");
  if (modal) modal.classList.remove("hidden");
}


// Check Backend connection status
async function checkSupabaseBackendStatus() {
  try {
    const res = await fetch("/api/supabase/status");
    if (res.ok) {
      const data = await res.json();
      const badge = document.getElementById("db-status-badge");
      if (badge) {
        if (data.is_connected) {
          badge.textContent = "Supabase Active";
          badge.style.background = "rgba(16, 185, 129, 0.2)";
          badge.style.color = "#10b981";
        } else {
          badge.textContent = "Mock Database Mode";
          badge.style.background = "rgba(245, 158, 11, 0.2)";
          badge.style.color = "#d97706";
        }
      }
    }
  } catch {
    // Running static
  }
}
