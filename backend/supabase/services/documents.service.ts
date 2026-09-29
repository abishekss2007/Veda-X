/**
 * AyurCTMS Documents Service
 * Manages secure file uploads and 5-minute signed URLs using Supabase Storage.
 */

import { getBrowserClient, getServerClient, isSupabaseConfigured } from '../client';
import { writeAuditEntry } from './audit.service';

const BUCKET_NAME = 'trial-documents';
const MAX_FILE_SIZE_BYTES = 10 * 1024 * 1024; // 10 MB limit (OWASP)

export interface UploadDocumentParams {
  ownerId: string;
  submissionId?: string;
  file: File | { name: string; size: number; type: string; buffer: Buffer };
  userEmail: string;
  role: string;
}

export async function uploadDocument(params: UploadDocumentParams) {
  // Validate file size
  if (params.file.size > MAX_FILE_SIZE_BYTES) {
    throw new Error('File size exceeds the 10 MB maximum permitted limit.');
  }

  // Generate safe random path: owner_id/timestamp_uuid_filename
  const sanitizedName = params.file.name.replace(/[^a-zA-Z0-9._-]/g, '_');
  const filePath = `${params.ownerId}/${Date.now()}_${sanitizedName}`;

  if (isSupabaseConfigured()) {
    const supabase = getBrowserClient() || getServerClient();

    // 1. Upload to Supabase Storage
    const fileBody = 'buffer' in params.file ? params.file.buffer : params.file;
    const { error: storageError } = await supabase.storage
      .from(BUCKET_NAME)
      .upload(filePath, fileBody as any, {
        contentType: params.file.type,
        upsert: false
      });

    if (storageError) throw storageError;

    // 2. Insert record in public.documents
    const { data, error: dbError } = await supabase
      .from('documents')
      .insert({
        owner_id: params.ownerId,
        submission_id: params.submissionId || null,
        file_path: filePath,
        file_name: params.file.name,
        file_size: params.file.size,
        mime_type: params.file.type,
        version: 1
      })
      .select()
      .single();

    if (dbError) throw dbError;

    await writeAuditEntry({
      userEmail: params.userEmail,
      role: params.role,
      action: 'UPLOAD_TRIAL_DOCUMENT',
      entity: `Document:${data.id}`,
      newValue: { fileName: params.file.name, size: params.file.size, path: filePath }
    });

    return data;
  }

  // Mock Mode
  return {
    id: `doc-${Date.now()}`,
    owner_id: params.ownerId,
    submission_id: params.submissionId,
    file_path: filePath,
    file_name: params.file.name,
    file_size: params.file.size,
    mime_type: params.file.type,
    version: 1,
    uploaded_at: new Date().toISOString()
  };
}

/**
 * Generates 5-minute signed URL for secure document viewing
 */
export async function getDocumentSignedUrl(filePath: string): Promise<string> {
  if (isSupabaseConfigured()) {
    const supabase = getBrowserClient() || getServerClient();
    const { data, error } = await supabase.storage
      .from(BUCKET_NAME)
      .createSignedUrl(filePath, 300); // 300 seconds = 5 minutes

    if (error) throw error;
    return data.signedUrl;
  }

  // Mock Mode signed link
  return `https://demo.ayurctms.local/storage/trial-documents/${filePath}?token=mock_signed_5m_token`;
}
