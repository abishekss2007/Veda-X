/**
 * AyurCTMS Submissions Service
 * Manages clinical trial data submissions, version snapshots, and regulatory verifications.
 */

import { getBrowserClient, getServerClient, isSupabaseConfigured } from '../client';
import { writeAuditEntry } from './audit.service';

export interface CreateSubmissionParams {
  ownerId: string;
  role: string;
  studyId?: string;
  type: string;
  title: string;
  payload: Record<string, any>;
  status?: 'Draft' | 'Submitted';
}

export interface UpdateSubmissionParams {
  id: string;
  ownerId: string;
  role: string;
  title?: string;
  payload: Record<string, any>;
  status?: 'Draft' | 'Submitted' | 'Needs correction';
  reason: string;
  changedBy: string;
}

export interface VerifySubmissionParams {
  submissionId: string;
  verifiedBy: string;
  verifierRole: string;
  verifierEmail: string;
  note: string;
}

// In-Memory Mock Store for development fallback
let mockSubmissions: any[] = [
  {
    id: 'sub-001',
    owner_id: 'user-coord-01',
    owner_name: 'Dr. Sunita Patel',
    role: 'Research Coordinator',
    study_id: 'AYUR-CT-2026-001',
    type: 'consent',
    title: 'Informed Consent Form — Subject SUB-AIIA-001-042',
    payload: { subject_code: 'SUB-AIIA-001-042', language: 'Hindi', oral_explanation: true },
    status: 'Verified',
    created_at: new Date(Date.now() - 3 * 86400000).toISOString(),
    updated_at: new Date(Date.now() - 2 * 86400000).toISOString(),
    versions: [
      { changed_at: new Date(Date.now() - 3 * 86400000).toISOString(), reason: 'Initial entry' }
    ],
    verifications: [
      { verified_by: 'Prof. Sharma (PI)', verified_at: new Date(Date.now() - 2 * 86400000).toISOString(), note: 'Verified against audio recording.' }
    ]
  },
  {
    id: 'sub-002',
    owner_id: 'user-coord-01',
    owner_name: 'Dr. Sunita Patel',
    role: 'Research Coordinator',
    study_id: 'AYUR-CT-2026-001',
    type: 'prakriti_assessment',
    title: 'Deha Prakriti Assessment — Subject SUB-AIIA-001-042',
    payload: { subject_code: 'SUB-AIIA-001-042', vata: 55, pitta: 30, kapha: 15, dominant: 'Vata-Pitta' },
    status: 'Submitted',
    created_at: new Date(Date.now() - 2 * 86400000).toISOString(),
    updated_at: new Date(Date.now() - 2 * 86400000).toISOString(),
    versions: [],
    verifications: []
  },
  {
    id: 'sub-003',
    owner_id: 'user-doc-01',
    owner_name: 'Dr. Arvind Joshi',
    role: 'Doctor / Investigator',
    study_id: 'AYUR-CT-2026-001',
    type: 'ae_report',
    title: 'Adverse Drug Reaction Log — Pitta-Kopa / Ushnata',
    payload: { subject_code: 'SUB-AIIA-001-042', severity: 'Mild', asu_term: 'Pitta-Kopa' },
    status: 'Draft',
    created_at: new Date(Date.now() - 1 * 86400000).toISOString(),
    updated_at: new Date(Date.now() - 1 * 86400000).toISOString(),
    versions: [],
    verifications: []
  }
];

/**
 * Creates a new submission
 */
export async function createSubmission(params: CreateSubmissionParams) {
  if (isSupabaseConfigured()) {
    const supabase = getBrowserClient() || getServerClient();
    const { data, error } = await supabase
      .from('submissions')
      .insert({
        owner_id: params.ownerId,
        role: params.role,
        study_id: params.studyId || 'AYUR-CT-2026-001',
        type: params.type,
        title: params.title,
        payload: params.payload,
        status: params.status || 'Draft'
      })
      .select()
      .single();

    if (error) throw error;

    await writeAuditEntry({
      userEmail: 'user@ayurctms.demo',
      role: params.role,
      action: 'CREATE_SUBMISSION',
      entity: `Submission:${data.id}`,
      newValue: { title: data.title, type: data.type, status: data.status }
    });

    return data;
  }

  // Mock Mode
  const newSub = {
    id: `sub-${Date.now()}`,
    owner_id: params.ownerId,
    owner_name: 'Current User',
    role: params.role,
    study_id: params.studyId || 'AYUR-CT-2026-001',
    type: params.type,
    title: params.title,
    payload: params.payload,
    status: params.status || 'Draft',
    created_at: new Date().toISOString(),
    updated_at: new Date().toISOString(),
    versions: [],
    verifications: []
  };
  mockSubmissions.unshift(newSub);
  return newSub;
}

/**
 * Lists submissions belonging to the active user (My Submissions)
 */
export async function listMySubmissions(ownerId?: string) {
  if (isSupabaseConfigured() && ownerId) {
    const supabase = getBrowserClient() || getServerClient();
    const { data, error } = await supabase
      .from('submissions')
      .select(`
        *,
        submission_versions(*),
        verifications(*)
      `)
      .order('created_at', { ascending: false });

    if (error) throw error;
    return data || [];
  }

  return mockSubmissions;
}

/**
 * Lists all submissions across users with filters (Admin & PI Team Activity)
 */
export async function listTeamActivity(filters?: {
  role?: string;
  studyId?: string;
  type?: string;
  status?: string;
}) {
  if (isSupabaseConfigured()) {
    const supabase = getBrowserClient() || getServerClient();
    let query = supabase
      .from('submissions')
      .select(`
        *,
        profiles!owner_id(full_name, email, role, site),
        submission_versions(*),
        verifications(*)
      `)
      .order('created_at', { ascending: false });

    if (filters?.role) query = query.eq('role', filters.role);
    if (filters?.studyId) query = query.eq('study_id', filters.studyId);
    if (filters?.type) query = query.eq('type', filters.type);
    if (filters?.status) query = query.eq('status', filters.status);

    const { data, error } = await query;
    if (error) throw error;
    return data || [];
  }

  // Filter mock submissions
  let result = [...mockSubmissions];
  if (filters?.role) result = result.filter(s => s.role === filters.role);
  if (filters?.type) result = result.filter(s => s.type === filters.type);
  if (filters?.status) result = result.filter(s => s.status === filters.status);
  return result;
}

/**
 * Updates a submission (Allowed only while Draft or Needs correction)
 */
export async function updateSubmission(params: UpdateSubmissionParams) {
  if (isSupabaseConfigured()) {
    const supabase = getBrowserClient() || getServerClient();

    // Check status condition
    const { data: existing } = await supabase
      .from('submissions')
      .select('status, payload')
      .eq('id', params.id)
      .single();

    if (existing && existing.status !== 'Draft' && existing.status !== 'Needs correction') {
      throw new Error(`Cannot edit submission in '${existing.status}' status. Only Draft or Needs correction can be edited.`);
    }

    const { data, error } = await supabase
      .from('submissions')
      .update({
        title: params.title,
        payload: params.payload,
        status: params.status || existing?.status,
        updated_at: new Date().toISOString()
      })
      .eq('id', params.id)
      .select()
      .single();

    if (error) throw error;

    // Record version history entry
    await supabase.from('submission_versions').insert({
      submission_id: params.id,
      old_value: existing?.payload || {},
      new_value: params.payload,
      reason: params.reason,
      changed_by: params.changedBy
    });

    return data;
  }

  // Mock Mode
  const sub = mockSubmissions.find(s => s.id === params.id);
  if (sub) {
    if (sub.status !== 'Draft' && sub.status !== 'Needs correction') {
      throw new Error(`Cannot edit submission in '${sub.status}' status.`);
    }
    sub.versions.push({
      old_value: sub.payload,
      new_value: params.payload,
      reason: params.reason,
      changed_at: new Date().toISOString()
    });
    if (params.title) sub.title = params.title;
    sub.payload = params.payload;
    if (params.status) sub.status = params.status;
    sub.updated_at = new Date().toISOString();
    return sub;
  }
  throw new Error('Submission not found.');
}

/**
 * Formal verification sign-off
 */
export async function verifySubmission(params: VerifySubmissionParams) {
  if (isSupabaseConfigured()) {
    const supabase = getBrowserClient() || getServerClient();

    // Update submission status to Verified
    await supabase
      .from('submissions')
      .update({ status: 'Verified', updated_at: new Date().toISOString() })
      .eq('id', params.submissionId);

    // Record verification row
    const { data, error } = await supabase
      .from('verifications')
      .insert({
        submission_id: params.submissionId,
        verified_by: params.verifiedBy,
        note: params.note,
        verified_at: new Date().toISOString()
      })
      .select()
      .single();

    if (error) throw error;

    await writeAuditEntry({
      userEmail: params.verifierEmail,
      role: params.verifierRole,
      action: 'VERIFY_SUBMISSION',
      entity: `Submission:${params.submissionId}`,
      newValue: { status: 'Verified', note: params.note }
    });

    return data;
  }

  // Mock Mode
  const sub = mockSubmissions.find(s => s.id === params.submissionId);
  if (sub) {
    sub.status = 'Verified';
    sub.verifications.push({
      verified_by: params.verifierRole,
      verified_at: new Date().toISOString(),
      note: params.note
    });
    return sub;
  }
  throw new Error('Submission not found.');
}
