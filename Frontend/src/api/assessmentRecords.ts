import { getSupabase } from '../lib/supabaseClient'
import type { AssessmentRecord } from '../types/assessmentRecord'

const TABLE_CANDIDATES = [
  'AssessmentRecord',
  'assessment_records',
  'patient_survey_records',
  'assessments',
] as const

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

export function mapAssessmentRecord(row: Record<string, unknown>): AssessmentRecord {
  const result = nestedObject(row.result ?? row.result_json)
  return {
    id: String(row.id ?? ''),
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
      const record = mapAssessmentRecord(raw as Record<string, unknown>)
      const key = record.id || `${record.created_at}|${record.risk_score}|${record.pre_diagnosed}`
      if (seen.has(key)) continue
      seen.add(key)
      collected.push(record)
    }

    if (table === 'AssessmentRecord' || table === 'assessment_records') {
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
}): Promise<boolean> {
  const supabase = getSupabase()
  if (!supabase) return false

  try {
    const dedicated = {
      user_id: input.userId,
      risk_score: input.riskScore,
      risk_tier: input.riskTier,
      pre_diagnosed: input.preDiagnosed,
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
    })
    if (!assessmentError) return true

    const { error: surveyError } = await supabase.from('patient_survey_records').insert({
      user_id: input.userId,
      diagnosed_t2dm: input.preDiagnosed,
      risk_percentage: input.riskScore,
      risk_band: input.riskTier,
      answers_json: input.answers ?? {},
      result_json: input.result ?? {},
    })
    return !surveyError
  } catch {
    return false
  }
}
