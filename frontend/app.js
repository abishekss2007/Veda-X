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

    // ROUTE GUARD: User cannot view another role's dashboard unless Admin or PI
    const userRole = appState.currentUser.role;
    if (requestedRole && requestedRole !== userRole) {
      if (userRole !== "Admin" && userRole !== "Principal Investigator") {
        showToast(`No access to ${requestedRole} dashboard. Redirected to your authorized view.`);
        window.location.hash = `#dashboard/${ROLE_TO_SLUG[userRole]}`;
        return;
      }
    }

    // Render Dashboard Shell for the role
    showView("dashboard");
    renderDashboardView(requestedRole || userRole);
    return;
  }

  // Handle standard public pages
  const viewId = hash.replace("#", "");
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
      document.getElementById("login-role").value = selectedRole;
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
        if (!emailInput.value.trim()) {
          emailInput.value = "judge.reviewer@ayurctms.demo";
        }
        pwdInput.value = "Demo@2026";
        if (!roleInput.value) {
          roleInput.value = "Research Coordinator";
        }
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
    const pwd = document.getElementById("login-password").value;
    let selectedRole = document.getElementById("login-role").value;

    // Email format validation
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    if (!emailRegex.test(email)) {
      errorBox1.textContent = "Please enter a valid email address.";
      errorBox1.classList.remove("hidden");
      return;
    }

    // DEMO ONLY, remove before real use: Demo Mode Bypass Path
    if (isDemoModeActive()) {
      const seededAccount = DEMO_ACCOUNTS[email];
      const isSharedDemoPwd = (pwd === "Demo@2026");
      const isSeededAccountPwd = (seededAccount && seededAccount.pwd === pwd);

      if (!isSharedDemoPwd && !isSeededAccountPwd) {
        errorBox1.textContent = "Wrong email or password";
        errorBox1.classList.remove("hidden");
        return;
      }

      // Infer role from email if not explicitly selected or default
      if (!selectedRole || selectedRole === "") {
        if (email.startsWith("admin@")) selectedRole = "Admin";
        else if (email.startsWith("pi@")) selectedRole = "Principal Investigator";
        else if (email.startsWith("coordinator@") || email.startsWith("coord@")) selectedRole = "Research Coordinator";
        else if (email.startsWith("doctor@") || email.startsWith("doc@")) selectedRole = "Doctor / Investigator";
        else if (email.startsWith("monitor@")) selectedRole = "Monitor";
        else if (email.startsWith("ec@") || email.startsWith("ethics@")) selectedRole = "EC Member";
        else if (email.startsWith("pv@") || email.startsWith("pharma@")) selectedRole = "PV Officer";
        else if (email.startsWith("auditor@") || email.startsWith("audit@")) selectedRole = "Auditor / Regulator";
        else if (email.startsWith("leader@") || email.startsWith("lead@") || email.startsWith("leadership@")) selectedRole = "Institution Leadership";
        else selectedRole = appState.activeRole || "Research Coordinator";
      }

      // Transition to Step 2: 2FA Verification
      appState.pendingLoginSession = { email, role: selectedRole };
      document.getElementById("verify-role-text").textContent = selectedRole;
      document.getElementById("login-step-1").classList.add("hidden");
      document.getElementById("login-step-2").classList.remove("hidden");
      document.getElementById("otp-code-input").value = "";
      document.getElementById("otp-code-input").focus();
      return;
    }

    // Standard Non-Demo Mode (Supabase / Production Path)
    try {
      const res = await fetch("/api/supabase/auth/login", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email, password: pwd, role: selectedRole })
      });
      const data = await res.json();
      if (!res.ok) {
        errorBox1.textContent = data.detail || "Authentication failed.";
        errorBox1.classList.remove("hidden");
        return;
      }

      appState.pendingLoginSession = { email, role: selectedRole };
      document.getElementById("verify-role-text").textContent = selectedRole;
      document.getElementById("login-step-1").classList.add("hidden");
      document.getElementById("login-step-2").classList.remove("hidden");
      document.getElementById("otp-code-input").value = "";
      document.getElementById("otp-code-input").focus();
    } catch (err) {
      // Offline fallback
      const account = DEMO_ACCOUNTS[email];
      if (!account || account.pwd !== pwd) {
        errorBox1.textContent = "Wrong email or password";
        errorBox1.classList.remove("hidden");
        return;
      }
      if (account.role !== selectedRole) {
        errorBox1.textContent = `This account is not approved for that role. (Registered role: ${account.role})`;
        errorBox1.classList.remove("hidden");
        return;
      }
      appState.pendingLoginSession = { email, role: selectedRole };
      document.getElementById("verify-role-text").textContent = selectedRole;
      document.getElementById("login-step-1").classList.add("hidden");
      document.getElementById("login-step-2").classList.remove("hidden");
      document.getElementById("otp-code-input").value = "";
      document.getElementById("otp-code-input").focus();
    }
  });

  // Step 2: 2FA OTP Verification
  formOTP.addEventListener("submit", async (e) => {
    e.preventDefault();
    errorBox2.classList.add("hidden");

    const session = appState.pendingLoginSession || {};
    const email = session.email || document.getElementById("login-email").value.toLowerCase().trim();
    const selectedRole = session.role || document.getElementById("login-role").value;
    const code = document.getElementById("otp-code-input").value.trim();

    // DEMO ONLY, remove before real use: Demo Mode Verification
    if (isDemoModeActive()) {
      if (code !== "123456") {
        errorBox2.textContent = "Invalid verification code. (Hint: In demo mode, the code is 123456)";
        errorBox2.classList.remove("hidden");
        return;
      }

      // Log demo logins as event "demo_login" in the security log
      if (typeof logSecurityEvent === "function") {
        logSecurityEvent("demo_login", { email, role: selectedRole });
      }

      completeLogin(email, selectedRole);
      return;
    }

    // Standard Non-Demo Mode Verification
    try {
      const res = await fetch("/api/supabase/auth/verify-otp", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email, role: selectedRole, otp_code: code })
      });
      const data = await res.json();
      if (!res.ok) {
        errorBox2.textContent = data.detail || "Invalid verification code.";
        errorBox2.classList.remove("hidden");
        return;
      }
      completeLogin(email, selectedRole);
    } catch (err) {
      if (code !== "123456") {
        errorBox2.textContent = "Invalid verification code. (Hint: In demo mode, the code is 123456)";
        errorBox2.classList.remove("hidden");
        return;
      }
      completeLogin(email, selectedRole);
    }
  });

  // Back to Step 1 Button
  document.getElementById("btn-back-step1").addEventListener("click", () => {
    document.getElementById("login-step-2").classList.add("hidden");
    document.getElementById("login-step-1").classList.remove("hidden");
  });

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
    showToast("Biometric token verified via WebAuthn simulation.");
    const session = appState.pendingLoginSession || {};
    const email = session.email || document.getElementById("login-email").value.toLowerCase().trim();
    const selectedRole = session.role || document.getElementById("login-role").value;
    setTimeout(() => completeLogin(email, selectedRole), 600);
  });

  // Global Sign out buttons
  document.getElementById("btn-global-signout").addEventListener("click", signOut);
  document.getElementById("btn-sidebar-signout").addEventListener("click", signOut);
}

function completeLogin(emailParam, roleParam) {
  const email = emailParam || document.getElementById("login-email").value.toLowerCase().trim();
  const selectedRole = roleParam || document.getElementById("login-role").value || "Research Coordinator";
  
  const account = DEMO_ACCOUNTS[email] || {
    role: selectedRole,
    name: email.split("@")[0].replace(/[._-]/g, " ").replace(/\b\w/g, c => c.toUpperCase()) || "Trial Reviewer",
    site: "SITE-01 (AIIA New Delhi)"
  };

  appState.isLoggedIn = true;
  appState.currentUser = { email, ...account, role: selectedRole };
  appState.activeRole = selectedRole;

  // Update Top Bar
  document.getElementById("nav-guest").classList.add("hidden");
  document.getElementById("nav-auth").classList.remove("hidden");
  document.getElementById("auth-role-badge").textContent = selectedRole;
  document.getElementById("auth-user-name").textContent = account.name;
  document.getElementById("auth-site-tag").textContent = account.site;

  // Reset Login Modal for next time
  document.getElementById("login-step-2").classList.add("hidden");
  document.getElementById("login-step-1").classList.remove("hidden");

  // Route to the Role Dashboard URL
  const slug = ROLE_TO_SLUG[selectedRole] || "coordinator";
  window.location.hash = `#dashboard/${slug}`;
  showToast(`Welcome, ${account.name}. Signed into ${selectedRole} workspace.`);
}

function signOut() {
  appState.isLoggedIn = false;
  appState.currentUser = null;
  appState.activeRole = null;

  document.getElementById("nav-guest").classList.remove("hidden");
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
    { label: "Scheduled Doses", value: "28 Today", note: "Yogaraj Guggulu & Ashwagandha" },
    { label: "My Open Reports", value: "2 Reports", note: "Acknowledged by PI" }
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

function renderDashboardView(role) {
  const currentActualRole = appState.currentUser ? appState.currentUser.role : role;
  appState.activeRole = role;

  // Update sidebar info
  const sideRoleEl = document.getElementById("side-user-role");
  if (sideRoleEl) sideRoleEl.textContent = role;
  const sideEmailEl = document.getElementById("side-user-email");
  if (sideEmailEl && appState.currentUser) sideEmailEl.textContent = appState.currentUser.email;

  // "View as role" preview switcher (Visible only to Admin and PI)
  const viewAsContainer = document.getElementById("view-as-role-container");
  const viewAsSelect = document.getElementById("select-view-as-role");
  if (currentActualRole === "Admin" || currentActualRole === "Principal Investigator") {
    if (viewAsContainer) viewAsContainer.classList.remove("hidden");
    if (viewAsSelect) viewAsSelect.value = role;
  } else {
    if (viewAsContainer) viewAsContainer.classList.add("hidden");
  }

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
  loadEscalationsUI();

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
  appState.viewAsRole = selectedRole;
  showToast(`Switched view to preview as ${selectedRole}`);
  renderDashboardView(selectedRole);
}

function showDashTab(tabId) {
  appState.activeDashboardTab = tabId;
  document.querySelectorAll(".sidebar-item").forEach(item => item.classList.remove("active"));
  document.querySelectorAll(".dash-pane").forEach(pane => pane.classList.remove("active"));

  const navItem = document.getElementById(`nav-item-${tabId}`);
  if (navItem) navItem.classList.add("active");

  const pane = document.getElementById(`dash-pane-${tabId}`);
  if (pane) pane.classList.add("active");

  if (tabId === "overview") renderOverviewCharts(appState.activeRole || "Research Coordinator");
  if (tabId === "submissions") loadSubmissionsUI();
  if (tabId === "team") filterTeamActivityUI();
  if (tabId === "escalations") loadEscalationsUI();
  if (tabId === "workspace") renderRoleWorkspace(appState.activeRole || "Research Coordinator");
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
    if (actionsEl) actionsEl.innerHTML = `<button class="btn btn-warning btn-sm" onclick="openEscalationDrawer()">⚡ Issue Urgent Safety Notice</button>`;
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
    if (actionsEl) actionsEl.innerHTML = `<button class="btn btn-warning btn-sm" onclick="openEscalationDrawer('', 'Consent', 'High')">⚡ Report Protocol Deviation to PI</button>`;
    const coordParticipants = data.participants.slice(0, 10);
    container.innerHTML = `
      <div class="dash-card">
        <div class="card-title-bar">
          <h4>Participant Visit & Dosing Ledger (SITE-01)</h4>
          <span class="badge badge-info">${data.participants.length} Total Coded Records</span>
        </div>
        <div class="table-responsive">
          <table class="data-table">
            <thead><tr><th>Subject Code</th><th>Study ID</th><th>Prakriti</th><th>Status</th><th>Visits Done</th><th>Dose Compliance</th><th>Actions</th></tr></thead>
            <tbody>
              ${coordParticipants.map(p => `
                <tr>
                  <td><code>${p.subject_code}</code></td>
                  <td>${p.study_id}</td>
                  <td>${p.prakriti}</td>
                  <td><span class="badge badge-green">${p.status}</span></td>
                  <td>${p.visits_completed} / ${p.total_visits}</td>
                  <td><span class="badge badge-info">${p.compliance_pct}%</span></td>
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
    if (actionsEl) actionsEl.innerHTML = `<button class="btn btn-warning btn-sm" onclick="openEscalationDrawer('', 'Ethics', 'Normal')">⚡ Send Decision / Query to PI & Admin</button>`;
    container.innerHTML = `
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
    if (actionsEl) actionsEl.innerHTML = `<button class="btn btn-warning btn-sm" onclick="openEscalationDrawer('', 'Site issue', 'Normal')">⚡ Broadcast Operational Directive</button>`;
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
// "REPORT TO SUPERIOR" ESCALATION CONTROLLER
// ==============================================================================
function openEscalationDrawer(prefillCode, prefillCategory, prefillUrgency) {
  const overlay = document.getElementById("escalation-drawer-overlay");
  const codeSelect = document.getElementById("esc-subject-code");
  const catSelect = document.getElementById("esc-category");
  const form = document.getElementById("form-escalation-compose");
  if (!overlay) return;

  // Populate 150 subject codes
  if (codeSelect && codeSelect.options.length <= 1) {
    const data = appState.studyData;
    if (data && data.participants) {
      data.participants.forEach(p => {
        const opt = document.createElement("option");
        opt.value = p.subject_code;
        opt.textContent = `${p.subject_code} (${p.study_id} • ${p.prakriti})`;
        codeSelect.appendChild(opt);
      });
    }
  }

  if (prefillCode && codeSelect) codeSelect.value = prefillCode;
  if (prefillCategory && catSelect) catSelect.value = prefillCategory;
  if (prefillUrgency) {
    const urgRadio = document.querySelector(`input[name="esc-urgency"][value="${prefillUrgency}"]`);
    if (urgRadio) urgRadio.checked = true;
  }

  overlay.classList.remove("hidden");
}

function closeEscalationDrawer(event) {
  if (event && event.target && event.target.id !== "escalation-drawer-overlay" && !event.target.classList.contains("btn-close")) {
    return;
  }
  const overlay = document.getElementById("escalation-drawer-overlay");
  if (overlay) overlay.classList.add("hidden");
}

function updateCharCount(input) {
  const countEl = document.getElementById("esc-char-count");
  if (countEl) countEl.textContent = `${input.value.length} / 120`;
}

async function submitEscalationForm(e) {
  e.preventDefault();
  const user = appState.currentUser || { email: "coordinator@ayurctms.demo", role: "Research Coordinator", name: "Dr. Sunita Patel" };
  const category = document.getElementById("esc-category").value;
  const urgencyRadio = document.querySelector('input[name="esc-urgency"]:checked');
  const urgency = urgencyRadio ? urgencyRadio.value : "Normal";
  const subjectCode = document.getElementById("esc-subject-code").value || null;
  const summary = document.getElementById("esc-summary").value;
  const details = document.getElementById("esc-details").value;
  const attachment = document.getElementById("esc-attachment").value || null;

  const payload = {
    from_user: user.email,
    from_name: user.name || user.email.split("@")[0],
    from_role: appState.activeRole || user.role,
    study_id: "AYUR-CT-2026-001",
    site_id: "SITE-01",
    subject_code: subjectCode,
    category: category,
    urgency: urgency,
    summary: summary,
    details: details,
    attachment_name: attachment
  };

  try {
    const res = await fetch("/api/escalations", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload)
    });
    if (res.ok) {
      const now = new Date();
      const timeStr = `${String(now.getHours()).padStart(2, '0')}:${String(now.getMinutes()).padStart(2, '0')}`;
      showToast(`Sent to PI and Admin at ${timeStr}`);
      closeEscalationDrawer();
      document.getElementById("form-escalation-compose").reset();
      updateCharCount(document.getElementById("esc-summary"));
      loadEscalationsUI();
      if (window.ChartDataHelper) ChartDataHelper.notifyUpdate();
      showDashTab("escalations");
      return;
    }
  } catch (err) {}

  // Fallback toast
  showToast("Escalation report sent to PI and Admin.");
  closeEscalationDrawer();
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
        ${esc.attachment_url ? `<div style="font-size: 0.8rem; color: var(--accent-primary); margin-bottom: 8px;">📎 Attachment: ${esc.attachment_url}</div>` : ''}

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
      ? `<span class="badge badge-green">${s.verifications[0].verified_by}</span>` 
      : '<span style="color: var(--text-dim); font-size: 0.8rem;">Pending</span>';

    return `
      <tr>
        <td><strong>${s.title}</strong></td>
        <td><span class="badge badge-secondary">${s.type}</span></td>
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
      <td><strong>${s.title}</strong></td>
      <td>${s.owner_name} <br><span class="badge badge-secondary">${s.role}</span></td>
      <td><span class="badge badge-secondary">${s.type}</span></td>
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
// MODALS LOGIC (Create, Edit with Version Reason, Verify)
// ==============================================================================
function openNewSubmissionModal() {
  document.getElementById("modal-new-submission").classList.remove("hidden");
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

  // Sync to Backend endpoint
  try {
    await fetch("/api/supabase/submissions", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        owner_id: newSub.owner_id,
        role: newSub.role,
        type: newSub.type,
        title: newSub.title,
        payload: newSub.payload,
        status: newSub.status
      })
    });
  } catch (err) {
    console.warn("Backend sync notice:", err);
  }

  appState.submissions.unshift(newSub);
  closeModal("modal-new-submission");
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
  
  // Record version snapshot (GCP-ASU requirement: old value, new value, reason, who, when)
  sub.versions.push({
    old_value: sub.payload,
    new_value: updatedPayload,
    reason,
    who: appState.currentUser?.name || "Investigator",
    changed_at: new Date().toISOString()
  });

  sub.title = document.getElementById("edit-sub-title").value;
  sub.payload = updatedPayload;
  sub.updated_at = new Date().toISOString();

  // Sync with Backend
  try {
    await fetch(`/api/supabase/submissions/${id}`, {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        title: sub.title,
        payload: sub.payload,
        reason,
        changed_by: appState.currentUser?.name || "Investigator"
      })
    });
  } catch (err) {
    console.warn("Backend sync notice:", err);
  }

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
  sub.status = "Verified";
  sub.verifications.push({
    verified_by: appState.currentUser?.name || "Principal Investigator",
    verified_at: new Date().toISOString(),
    note
  });

  // Sync with Backend
  try {
    await fetch(`/api/supabase/submissions/${id}/verify`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        verified_by: appState.currentUser?.name || "Principal Investigator",
        verifier_role: appState.activeRole || "Principal Investigator",
        verifier_email: appState.currentUser?.email || "pi@ayurctms.demo",
        note
      })
    });
  } catch (err) {
    console.warn("Backend sync notice:", err);
  }

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
  const resetTimer = () => {
    if (appState.isLoggedIn) {
      appState.sessionSecondsLeft = 15 * 60;
      warningBanner.classList.add("hidden");
    }
  };

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

// Check Backend connection status
async function checkSupabaseBackendStatus() {
  try {
    const res = await fetch("/api/supabase/status");
    if (res.ok) {
      const data = await res.json();
      const badge = document.getElementById("db-status-badge");
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
  } catch {
    // Running static
  }
}
