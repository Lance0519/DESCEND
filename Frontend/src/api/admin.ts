import { getSupabase } from '../lib/supabaseClient'
import { fetchAuditLogs, type AuditLogRow } from './audit'

export interface AdminProfileRow {
  id: string
  email: string | null
  display_name: string | null
  role: string
  is_active: boolean
  created_at: string | null
}

export interface AdminAssessmentRow {
  id: string
  user_id: string | null
  created_at: string
  percentage: number | null
  risk_band: string | null
  diagnosed_t2dm: boolean
}

export interface AdminOverview {
  userCount: number
  adminCount: number
  disabledCount: number
  assessmentCount: number
  guestCount: number
  savedCount: number
  riskMix: { Low: number; Moderate: number; High: number; Other: number }
  recentUsers: AdminProfileRow[]
  recentAssessments: AdminAssessmentRow[]
  users: AdminProfileRow[]
  auditLogs: AuditLogRow[]
}

function bandKey(value: string | null): keyof AdminOverview['riskMix'] {
  if (value === 'Low' || value === 'Moderate' || value === 'High') return value
  return 'Other'
}

export async function fetchAdminOverview(): Promise<AdminOverview> {
  const sb = getSupabase()
  if (!sb) throw new Error('Supabase is not configured')

  const { data: profiles, error: profileError } = await sb
    .from('profiles')
    .select('id, email, display_name, role, is_active, created_at')
    .order('created_at', { ascending: false })

  if (profileError) throw new Error(profileError.message)

  let assessments: AdminAssessmentRow[] = []
  const fromAssessments = await sb
    .from('assessments')
    .select('id, user_id, created_at, percentage, risk_band, diagnosed_t2dm')
    .order('created_at', { ascending: false })

  if (!fromAssessments.error && fromAssessments.data) {
    assessments = fromAssessments.data.map((row) => ({
      id: String(row.id),
      user_id: row.user_id ? String(row.user_id) : null,
      created_at: String(row.created_at ?? ''),
      percentage: typeof row.percentage === 'number' ? row.percentage : null,
      risk_band: row.risk_band ? String(row.risk_band) : null,
      diagnosed_t2dm: Boolean(row.diagnosed_t2dm),
    }))
  }

  const users: AdminProfileRow[] = (profiles ?? []).map((row) => ({
    id: String(row.id),
    email: row.email ? String(row.email) : null,
    display_name: row.display_name ? String(row.display_name) : null,
    role: row.role === 'admin' ? 'admin' : 'user',
    is_active: row.is_active !== false,
    created_at: row.created_at ? String(row.created_at) : null,
  }))

  const riskMix = { Low: 0, Moderate: 0, High: 0, Other: 0 }
  for (const row of assessments) {
    if (row.diagnosed_t2dm) continue
    riskMix[bandKey(row.risk_band)] += 1
  }

  let auditLogs: AuditLogRow[] = []
  try {
    auditLogs = await fetchAuditLogs(40)
  } catch {
    auditLogs = []
  }

  return {
    userCount: users.length,
    adminCount: users.filter((u) => u.role === 'admin').length,
    disabledCount: users.filter((u) => !u.is_active).length,
    assessmentCount: assessments.length,
    guestCount: assessments.filter((a) => !a.user_id).length,
    savedCount: assessments.filter((a) => Boolean(a.user_id)).length,
    riskMix,
    recentUsers: users.slice(0, 8),
    recentAssessments: assessments.slice(0, 8),
    users,
    auditLogs,
  }
}

export async function updateAdminUser(
  userId: string,
  patch: { role?: 'user' | 'admin'; is_active?: boolean },
): Promise<void> {
  const sb = getSupabase()
  if (!sb) throw new Error('Supabase is not configured')
  const { error } = await sb.from('profiles').update(patch).eq('id', userId)
  if (error) throw new Error(error.message)
}

export async function persistProfileToSupabase(input: {
  userId: string
  email?: string | null
  displayName?: string
  preferredLang?: string
  sex?: string
  age?: number | null
}): Promise<void> {
  const sb = getSupabase()
  if (!sb) return
  const { error } = await sb.from('profiles').upsert({
    id: input.userId,
    email: input.email ?? null,
    display_name: input.displayName ?? '',
    preferred_lang: input.preferredLang ?? 'tl',
    sex: input.sex || null,
    age: input.age ?? null,
    updated_at: new Date().toISOString(),
  })
  if (error) throw new Error(error.message)
}
