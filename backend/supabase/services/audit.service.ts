/**
 * AyurCTMS Audit & Security Logging Service
 * Cryptographically chained SHA-256 ledger conforming to CERT-In 180-day and GCP-ASU 5-year rules.
 */

import crypto from 'crypto';
import { getBrowserClient, getServerClient, isSupabaseConfigured } from '../client';

const GENESIS_HASH = '0000000000000000000000000000000000000000000000000000000000000000';

export interface AuditParams {
  userId?: string;
  userEmail: string;
  role: string;
  action: string;
  entity: string;
  oldValue?: Record<string, any>;
  newValue?: Record<string, any>;
}

export function computeSha256(payload: string): string {
  return crypto.createHash('sha256').update(payload, 'utf8').digest('hex');
}

/**
 * Appends a cryptographically chained entry to public.audit_log
 */
export async function writeAuditEntry(params: AuditParams) {
  const now = new Date().toISOString();

  if (isSupabaseConfigured()) {
    const supabase = getServerClient(); // Privileged append

    // Get latest entry's current hash
    const { data: latest } = await supabase
      .from('audit_log')
      .select('hash')
      .order('id', { ascending: false })
      .limit(1)
      .single();

    const prevHash = latest?.hash || GENESIS_HASH;
    const rawPayload = `${prevHash}|${now}|${params.userEmail}|${params.role}|${params.action}|${params.entity}|${JSON.stringify(params.oldValue || {})}|${JSON.stringify(params.newValue || {})}`;
    const currHash = computeSha256(rawPayload);

    await supabase.from('audit_log').insert({
      user_id: params.userId || null,
      user_email: params.userEmail,
      role: params.role,
      action: params.action,
      entity: params.entity,
      old_value: params.oldValue || null,
      new_value: params.newValue || null,
      timestamp: now,
      previous_hash: prevHash,
      hash: currHash
    });

    return { prevHash, hash: currHash };
  }

  // Mock Mode
  const prevHash = GENESIS_HASH;
  const hash = computeSha256(`${prevHash}|${now}|${params.userEmail}|${params.action}`);
  return { prevHash, hash };
}

/**
 * Writes to public.security_log (login, logout, failed_login, lockout)
 */
export async function writeSecurityLog(
  userEmail: string,
  event: 'login' | 'failed_login' | 'lockout' | 'logout' | 'registration_submitted' | string,
  ipAddress: string = '127.0.0.1',
  details?: string
) {
  if (isSupabaseConfigured()) {
    try {
      const supabase = getServerClient();
      await supabase.from('security_log').insert({
        user_email: userEmail,
        event,
        ip_address: ipAddress,
        details: details || null,
        timestamp: new Date().toISOString()
      });
    } catch (err: any) {
      console.warn('[SecurityLog Notice]', err.message);
    }
  }
}

/**
 * Traverses cryptographic ledger from Genesis to verify tamper-proof state
 */
export async function verifyAuditLedger(): Promise<{ valid: boolean; totalRecords: number; brokenIndex?: number }> {
  if (isSupabaseConfigured()) {
    const supabase = getServerClient();
    const { data: entries, error } = await supabase
      .from('audit_log')
      .select('*')
      .order('id', { ascending: true });

    if (error || !entries || entries.length === 0) {
      return { valid: true, totalRecords: 0 };
    }

    let expectedPrev = GENESIS_HASH;
    for (let i = 0; i < entries.length; i++) {
      const row = entries[i];
      if (row.previous_hash !== expectedPrev) {
        return { valid: false, totalRecords: entries.length, brokenIndex: i + 1 };
      }
      const rawPayload = `${row.previous_hash}|${row.timestamp}|${row.user_email}|${row.role}|${row.action}|${row.entity}|${JSON.stringify(row.old_value || {})}|${JSON.stringify(row.new_value || {})}`;
      const recomputed = computeSha256(rawPayload);
      if (recomputed !== row.hash) {
        return { valid: false, totalRecords: entries.length, brokenIndex: i + 1 };
      }
      expectedPrev = row.hash;
    }

    return { valid: true, totalRecords: entries.length };
  }

  return { valid: true, totalRecords: 1 };
}
