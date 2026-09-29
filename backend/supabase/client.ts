/**
 * AyurCTMS Supabase Client Initialization
 * Supports both Browser (Publishable Key) and Server (Secret Key) environments.
 * Strictly adheres to OWASP & DPDP Act 2023 security controls.
 */

import { createClient, SupabaseClient } from '@supabase/supabase-js';

// Environment variable extraction with backward-compatible fallbacks
const SUPABASE_URL = 
  process.env.SUPABASE_URL || 
  process.env.NEXT_PUBLIC_SUPABASE_URL || 
  process.env.VITE_SUPABASE_URL || 
  '';

// Browser-safe Publishable Key (respects Row-Level Security)
const SUPABASE_PUBLISHABLE_KEY = 
  process.env.SUPABASE_PUBLISHABLE_KEY || 
  process.env.NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY || 
  process.env.VITE_SUPABASE_PUBLISHABLE_KEY || 
  process.env.SUPABASE_ANON_KEY || 
  process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY || 
  '';

// Backend-Only Secret Key (bypasses RLS for administrative jobs)
// CRITICAL: NEVER expose this key to browser JavaScript or prefix with NEXT_PUBLIC_ / VITE_
const SUPABASE_SECRET_KEY = 
  process.env.SUPABASE_SECRET_KEY || 
  process.env.SUPABASE_SERVICE_ROLE_KEY || 
  '';

/**
 * Returns true if valid Supabase credentials are configured.
 */
export function isSupabaseConfigured(): boolean {
  return Boolean(SUPABASE_URL && (SUPABASE_PUBLISHABLE_KEY || SUPABASE_SECRET_KEY));
}

let browserClientInstance: SupabaseClient | null = null;

/**
 * Browser Client: Uses publishable key and respects Row-Level Security (RLS).
 * Safe for use in frontend applications.
 */
export function getBrowserClient(): SupabaseClient | null {
  if (!SUPABASE_URL || !SUPABASE_PUBLISHABLE_KEY) {
    if (typeof window !== 'undefined') {
      console.warn('[AyurCTMS Supabase] Running in Mock/Offline mode. Database keys not detected.');
    }
    return null;
  }

  if (!browserClientInstance) {
    browserClientInstance = createClient(SUPABASE_URL, SUPABASE_PUBLISHABLE_KEY, {
      auth: {
        persistSession: true,
        autoRefreshToken: true,
        detectSessionInUrl: true,
      },
    });
  }
  return browserClientInstance;
}

let serverClientInstance: SupabaseClient | null = null;

/**
 * Server Client: Uses secret key for privileged backend operations.
 * CRITICAL RULE: Throws error if called in a browser environment.
 */
export function getServerClient(): SupabaseClient {
  if (typeof window !== 'undefined') {
    throw new Error(
      'SECURITY VIOLATION: getServerClient() was called in a browser environment. ' +
      'SUPABASE_SECRET_KEY must NEVER be loaded on client-side code.'
    );
  }

  if (!SUPABASE_URL || !SUPABASE_SECRET_KEY) {
    throw new Error(
      'Supabase server configuration missing. SUPABASE_URL and SUPABASE_SECRET_KEY are required in server environment.'
    );
  }

  if (!serverClientInstance) {
    serverClientInstance = createClient(SUPABASE_URL, SUPABASE_SECRET_KEY, {
      auth: {
        persistSession: false,
        autoRefreshToken: false,
      },
    });
  }
  return serverClientInstance;
}
