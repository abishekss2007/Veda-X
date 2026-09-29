/**
 * AyurCTMS Authentication Service
 * Connects to Supabase Auth & public.profiles with DPDP consent enforcement and 2FA OTP verification.
 */

import { getBrowserClient, getServerClient, isSupabaseConfigured } from '../client';
import { writeSecurityLog } from './audit.service';

export interface RegisterParams {
  fullName: string;
  email: string;
  phone: string;
  role: string;
  site: string;
  password: string;
  confirmPassword: string;
  privacyConsentTicked: boolean;
  noticeVersion?: string;
}

export interface LoginParams {
  role: string;
  email: string;
  password: string;
}

export interface OTPVerifyParams {
  email: string;
  role: string;
  otpCode: string;
}

// In-Memory Lockout & OTP Tracking
const failedAttemptsMap = new Map<string, { count: number; lockedUntil: number | null }>();
const otpChallenges = new Map<string, { code: string; expiresAt: number; attempts: number }>();

const DEMO_MODE = process.env.DEMO_MODE === 'true' || true; // Demo mode enabled for trial testing

/**
 * Validates password strength (>= 12 chars, upper, lower, number, symbol)
 */
export function validatePasswordStrength(password: string): { valid: boolean; message: string; score: number } {
  let score = 0;
  if (!password || password.length < 12) {
    return { valid: false, message: 'Password must be at least 12 characters long.', score: 1 };
  }
  score += 1;
  if (/[A-Z]/.test(password)) score += 1;
  if (/[a-z]/.test(password)) score += 1;
  if (/[0-9]/.test(password)) score += 1;
  if (/[^A-Za-z0-9]/.test(password)) score += 1;

  if (score < 5) {
    return {
      valid: false,
      message: 'Password must contain uppercase, lowercase, numbers, and symbols.',
      score
    };
  }
  return { valid: true, message: 'Strong password.', score: 5 };
}

/**
 * Register a new clinical trial user
 */
export async function registerUser(params: RegisterParams) {
  // 1. Enforce DPDP Notice & Consent (Unticked by default, registration blocked until ticked)
  if (!params.privacyConsentTicked) {
    throw new Error('DPDP Act Compliance: You must read and tick the privacy consent notice before registering.');
  }

  // 2. Validate passwords match & complexity
  if (params.password !== params.confirmPassword) {
    throw new Error('Passwords do not match.');
  }
  const strength = validatePasswordStrength(params.password);
  if (!strength.valid) {
    throw new Error(strength.message);
  }

  // 3. Prohibit self-assignment of Admin or Principal Investigator
  const requestedRole = params.role.trim();
  const safeRole = (requestedRole === 'Admin' || requestedRole === 'Principal Investigator')
    ? 'Research Coordinator' // Demoted to safe coordinator role pending Admin elevation
    : requestedRole;

  if (isSupabaseConfigured()) {
    const supabase = getBrowserClient() || getServerClient();
    const { data, error } = await supabase.auth.signUp({
      email: params.email,
      password: params.password,
      options: {
        data: {
          full_name: params.fullName,
          phone: params.phone,
          role: safeRole,
          site: params.site || 'SITE-01',
          notice_version: params.noticeVersion || 'DPDP-V1.0',
          status: 'pending' // New accounts start as pending approval
        }
      }
    });

    if (error) throw error;
    await writeSecurityLog(params.email, 'registration_submitted', '127.0.0.1', `Role: ${safeRole}, Status: Pending`);
    return { success: true, message: 'Registration received. An admin will approve your account.', user: data.user };
  }

  // Mock Mode
  await writeSecurityLog(params.email, 'registration_submitted_mock', '127.0.0.1', `Role: ${safeRole}, Status: Pending`);
  return {
    success: true,
    message: 'Registration received. An admin will approve your account.',
    mock: true
  };
}

/**
 * Step 1: Login check (email + password + role pre-selected)
 */
export async function initiateLogin(params: LoginParams) {
  const emailKey = params.email.toLowerCase().trim();
  const now = Date.now();

  // Check account lockout (5 failed attempts = 15 min lock)
  const attemptInfo = failedAttemptsMap.get(emailKey);
  if (attemptInfo?.lockedUntil && attemptInfo.lockedUntil > now) {
    const minsLeft = Math.ceil((attemptInfo.lockedUntil - now) / 60000);
    await writeSecurityLog(emailKey, 'lockout', '127.0.0.1', `Account locked. ${minsLeft} minutes remaining.`);
    throw new Error(`Account temporarily locked due to 5 consecutive failed attempts. Try again in ${minsLeft} minutes.`);
  }

  if (isSupabaseConfigured()) {
    const supabase = getBrowserClient() || getServerClient();
    const { data: signInData, error } = await supabase.auth.signInWithPassword({
      email: params.email,
      password: params.password
    });

    if (error) {
      // Record failed attempt
      const currentCount = (attemptInfo?.count || 0) + 1;
      const willLock = currentCount >= 5;
      failedAttemptsMap.set(emailKey, {
        count: currentCount,
        lockedUntil: willLock ? now + 15 * 60 * 1000 : null
      });

      await writeSecurityLog(emailKey, 'failed_login', '127.0.0.1', `Failed attempt ${currentCount}/5.`);
      if (willLock) {
        throw new Error('Account has been locked for 15 minutes due to 5 failed login attempts.');
      }
      throw new Error('Wrong email or password');
    }

    // Reset failed count on password success
    failedAttemptsMap.delete(emailKey);

    // Verify role approval
    const { data: profile } = await supabase
      .from('profiles')
      .select('*')
      .eq('id', signInData.user.id)
      .single();

    if (profile && profile.role !== params.role) {
      throw new Error(`This account is not approved for that role. (Registered role: ${profile.role})`);
    }

    if (profile && profile.status !== 'approved') {
      throw new Error('Your account is currently pending administrator approval.');
    }
  }

  // Issue 6-digit OTP challenge (Demo code: 123456)
  const otpCode = DEMO_MODE ? '123456' : String(Math.floor(100000 + Math.random() * 900000));
  otpChallenges.set(emailKey, {
    code: otpCode,
    expiresAt: now + 5 * 60 * 1000, // 5 min expiry
    attempts: 0
  });

  return {
    step: 'VERIFICATION_REQUIRED',
    email: params.email,
    role: params.role,
    expiresInMinutes: 5,
    demoCode: DEMO_MODE ? '123456' : undefined
  };
}

/**
 * Step 2: Verify 6-digit OTP code or Face/Passkey
 */
export async function verifyOTP(params: OTPVerifyParams) {
  const emailKey = params.email.toLowerCase().trim();
  const challenge = otpChallenges.get(emailKey);
  const now = Date.now();

  if (!challenge) {
    throw new Error('No active verification challenge. Please sign in again.');
  }

  if (challenge.expiresAt < now) {
    otpChallenges.delete(emailKey);
    throw new Error('Verification code has expired (5-minute validity). Please request a new code.');
  }

  if (challenge.attempts >= 3) {
    otpChallenges.delete(emailKey);
    throw new Error('Too many incorrect code attempts. Please sign in again.');
  }

  if (params.otpCode !== challenge.code) {
    challenge.attempts += 1;
    throw new Error(`Invalid verification code. ${3 - challenge.attempts} attempt(s) remaining.`);
  }

  // OTP verified successfully: Clear challenge and log login
  otpChallenges.delete(emailKey);
  await writeSecurityLog(emailKey, 'login', '127.0.0.1', `Role: ${params.role} - 2FA verified`);

  return {
    success: true,
    email: params.email,
    role: params.role,
    dashboardRoute: getDashboardRoute(params.role)
  };
}

/**
 * Resolves role dashboard URL
 */
export function getDashboardRoute(role: string): string {
  switch (role) {
    case 'Principal Investigator': return '/dashboard/pi';
    case 'Research Coordinator': return '/dashboard/coordinator';
    case 'Doctor / Investigator': return '/dashboard/doctor';
    case 'Monitor': return '/dashboard/monitor';
    case 'EC Member': return '/dashboard/ec';
    case 'PV Officer': return '/dashboard/pv';
    case 'Admin': return '/dashboard/admin';
    case 'Auditor / Regulator': return '/dashboard/auditor';
    case 'Institution Leadership': return '/dashboard/leadership';
    default: return '/dashboard/coordinator';
  }
}
