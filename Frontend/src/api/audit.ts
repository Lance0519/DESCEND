import { getSupabase } from '../lib/supabaseClient'

export type AuditAction =
  | 'role_change'
  | 'account_enable'
  | 'account_disable'
  | 'assessment_delete'
  | 'password_reset_sent'

export interface AuditLogRow {
  id: number
  actor_id: string | null
  action: AuditAction | string
  target_type: string
  target_id: string | null
  metadata: Record<string, unknown>
  created_at: string
}

function asMetadata(value: unknown): Record<string, unknown> {
  if (value && typeof value === 'object' && !Array.isArray(value)) {
    return value as Record<string, unknown>
  }
  return {}
}

export async function fetchAuditLogs(limit = 40): Promise<AuditLogRow[]> {
  const sb = getSupabase()
  if (!sb) throw new Error('Supabase is not configured')

  const { data, error } = await sb
    .from('audit_logs')
    .select('id, actor_id, action, target_type, target_id, metadata, created_at')
    .order('created_at', { ascending: false })
    .limit(limit)

  if (error) throw new Error(error.message)

  return (data ?? []).map((row) => ({
    id: Number(row.id),
    actor_id: row.actor_id ? String(row.actor_id) : null,
    action: String(row.action),
    target_type: String(row.target_type),
    target_id: row.target_id != null ? String(row.target_id) : null,
    metadata: asMetadata(row.metadata),
    created_at: String(row.created_at ?? ''),
  }))
}

/** Entries older than six months are removed server-side; see migration 009. */
export async function purgeExpiredAuditLogs(): Promise<void> {
  const sb = getSupabase()
  if (!sb) return
  const { error } = await sb.rpc('purge_audit_logs_as_admin')
  if (error) console.warn('audit log purge failed', error.message)
}

export async function writeAuditLog(input: {
  action: AuditAction
  targetType: string
  targetId?: string | null
  metadata?: Record<string, unknown>
}): Promise<void> {
  const sb = getSupabase()
  if (!sb) return

  const { error } = await sb.rpc('write_audit_log', {
    p_action: input.action,
    p_target_type: input.targetType,
    p_target_id: input.targetId ?? null,
    p_metadata: input.metadata ?? {},
  })

  if (error) {
    // Non-blocking: admin action already succeeded; audit write should not undo it.
    console.warn('audit log write failed', error.message)
  }
}
