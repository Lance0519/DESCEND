import { getSupabase } from '../lib/supabaseClient'
import type { AssessmentRecord, AssessmentSourceTable } from '../types/assessmentRecord'

const TABLE_CANDIDATES = [
  'assessment_records',
  'AssessmentRecord',
  'patient_survey_records',
  'assessments',
] as const

type CandidateTable = (typeof TABLE_CANDIDATES)[number]

function asBoolean(value: unknown): boolean {
  if (typeof value === 'boolean') return value
  if (typeof value === 'number') return value === 1
  if (typeof value === 'string') {
    const normalized = value.trim().toLowerCase()
    return normalized === 'true' || normalized === 'yes' || normalized === '1'
  }
  return false
}

function asNumber(value: unknown): number | null {
  if (typeof value === 'number' && Number.isFinite(value)) return value
  if (typeof value === 'string' && value.trim() !== '') {
    const parsed = Number(value)
    return Number.isFinite(parsed) ? parsed : null
  }
  return null
}

function asString(value: unknown): string | null {
  if (typeof value === 'string' && value.trim() !== '') return value.trim()
  return null
}

function nestedObject(value: unknown): Record<string, unknown> {
  return value && typeof value === 'object' ? (value as Record<string, unknown>) : {}
}

function resolveSource(
  displayId: string,
  table: CandidateTable,
): { sourceTable: AssessmentSourceTable | null; sourceId: string | null } {
  if (table === 'assessments') {
    return { sourceTable: 'assessments', sourceId: displayId || null }
  }
  if (table === 'patient_survey_records') {
    return { sourceTable: 'patient_survey_records', sourceId: displayId || null }
  }

  if (displayId.startsWith('psr-')) {
    return { sourceTable: 'patient_survey_records', sourceId: displayId.slice(4) }
  }
  if (displayId.startsWith('asm-')) {
    return { sourceTable: 'assessments', sourceId: displayId.slice(4) }
  }
  return { sourceTable: null, sourceId: null }
}

export function mapAssessmentRecord(
  row: Record<string, unknown>,
  table: CandidateTable = 'assessment_records',
): AssessmentRecord {
  const result = nestedObject(row.result ?? row.result_json)
  const displayId = String(row.id ?? '')
  const { sourceTable, sourceId } = resolveSource(displayId, table)
  const label =
    asString(row.label) ??
    asString(result.dashboardLabel) ??
    asString(result.label)
  const notes =
    asString(row.notes) ??
    asString(result.dashboardNotes) ??
    asString(result.notes)

  return {
    id: displayId,
    user_id: String(row.user_id ?? ''),
    created_at: String(row.created_at ?? ''),
    risk_score: asNumber(
      row.risk_score ?? row.risk_percentage ?? row.percentage ?? result.percentage ?? result.risk_score,
    ),
    risk_tier: asString(
      row.risk_tier ?? row.risk_band ?? result.riskBand ?? result.risk_band ?? result.risk_tier,
    ),
    pre_diagnosed: asBoolean(
      row.pre_diagnosed ?? row.diagnosed_t2dm ?? row.diagnosedT2dm ?? result.diagnosed,
    ),
    label,
    notes,
    sourceTable,
    sourceId,
  }
}

/**
 * Fetch every survey row for the signed-in Supabase user from AssessmentRecord
 * (with fallbacks to the project's existing survey tables), newest first.
 */
export async function fetchAssessmentRecords(userId: string): Promise<AssessmentRecord[]> {
  const supabase = getSupabase()
  if (!supabase) {
    throw new Error('Supabase is not configured')
  }

  const collected: AssessmentRecord[] = []
  const seen = new Set<string>()
  let lastError: string | null = null
  let anyTableAvailable = false

  for (const table of TABLE_CANDIDATES) {
    const { data, error } = await supabase
      .from(table)
      .select('*')
      .eq('user_id', userId)
      .order('created_at', { ascending: false })

    if (error) {
      lastError = error.message
      continue
    }

    anyTableAvailable = true
    for (const raw of data ?? []) {
      const record = mapAssessmentRecord(raw as Record<string, unknown>, table)
      const key = record.id || `${record.created_at}|${record.risk_score}|${record.pre_diagnosed}`
      if (seen.has(key)) continue
      seen.add(key)
      collected.push(record)
    }

    if (table === 'assessment_records' || table === 'AssessmentRecord') {
      break
    }
  }

  if (!anyTableAvailable && lastError) {
    throw new Error(lastError)
  }

  collected.sort((a, b) => Date.parse(b.created_at) - Date.parse(a.created_at) || 0)
  return collected
}

export async function persistAssessmentRecord(input: {
  userId: string
  riskScore: number | null
  riskTier: string | null
  preDiagnosed: boolean
  answers?: unknown
  result?: unknown
  label?: string | null
  notes?: string | null
}): Promise<boolean> {
  const supabase = getSupabase()
  if (!supabase) return false

  try {
    const dedicated = {
      user_id: input.userId,
      risk_score: input.riskScore,
      risk_tier: input.riskTier,
      pre_diagnosed: input.preDiagnosed,
      label: input.label ?? null,
      notes: input.notes ?? null,
    }

    const { error: viewError } = await supabase.from('assessment_records').insert(dedicated)
    if (!viewError) return true

    const { error: namedError } = await supabase.from('AssessmentRecord').insert(dedicated)
    if (!namedError) return true

    const { error: assessmentError } = await supabase.from('assessments').insert({
      user_id: input.userId,
      percentage: input.riskScore,
      risk_band: input.riskTier,
      diagnosed_t2dm: input.preDiagnosed,
      answers: input.answers ?? {},
      result: input.result ?? {},
      label: input.label ?? null,
      notes: input.notes ?? null,
    })
    if (!assessmentError) return true

    const { error: surveyError } = await supabase.from('patient_survey_records').insert({
      user_id: input.userId,
      diagnosed_t2dm: input.preDiagnosed,
      risk_percentage: input.riskScore,
      risk_band: input.riskTier,
      answers_json: input.answers ?? {},
      result_json: input.result ?? {},
      label: input.label ?? null,
      notes: input.notes ?? null,
    })
    return !surveyError
  } catch {
    return false
  }
}

export async function updateAssessmentRecord(
  userId: string,
  record: AssessmentRecord,
  patch: { label?: string | null; notes?: string | null },
): Promise<boolean> {
  const supabase = getSupabase()
  if (!supabase || !record.sourceTable || !record.sourceId) return false

  const nextLabel = patch.label !== undefined ? patch.label?.trim() || null : undefined
  const nextNotes = patch.notes !== undefined ? patch.notes?.trim() || null : undefined
  if (nextLabel === undefined && nextNotes === undefined) return true

  const columnPayload: Record<string, string | null> = {}
  if (nextLabel !== undefined) columnPayload.label = nextLabel
  if (nextNotes !== undefined) columnPayload.notes = nextNotes

  const { error } = await supabase
    .from(record.sourceTable)
    .update(columnPayload)
    .eq('id', record.sourceId)
    .eq('user_id', userId)

  if (!error) return true

  // Fallback when label/notes columns are not migrated yet: merge into JSON result.
  const jsonColumn = record.sourceTable === 'assessments' ? 'result' : 'result_json'
  const { data, error: readError } = await supabase
    .from(record.sourceTable)
    .select(jsonColumn)
    .eq('id', record.sourceId)
    .eq('user_id', userId)
    .maybeSingle()

  if (readError || !data) return false

  const current = nestedObject((data as Record<string, unknown>)[jsonColumn])
  const merged = {
    ...current,
    ...(nextLabel !== undefined ? { dashboardLabel: nextLabel } : {}),
    ...(nextNotes !== undefined ? { dashboardNotes: nextNotes } : {}),
  }

  const { error: jsonError } = await supabase
    .from(record.sourceTable)
    .update({ [jsonColumn]: merged })
    .eq('id', record.sourceId)
    .eq('user_id', userId)

  return !jsonError
}

export async function deleteAssessmentRecord(
  userId: string,
  record: AssessmentRecord,
): Promise<boolean> {
  const supabase = getSupabase()
  if (!supabase || !record.sourceTable || !record.sourceId) return false

  const { error } = await supabase
    .from(record.sourceTable)
    .delete()
    .eq('id', record.sourceId)
    .eq('user_id', userId)

  return !error
}
