import type { PredictionResult, RiskBand } from '../types/prediction'
import type { AssessmentAnswers } from '../types/assessment'

/** Strip trailing slashes so `…vercel.app/` + `/api/…` never becomes `…app//api/…`. */
function normalizeApiBase(raw: string | undefined): string {
  return (raw ?? '').trim().replace(/\/+$/, '')
}

const API_BASE = normalizeApiBase(import.meta.env.VITE_API_BASE_URL)

function apiUrl(path: string): string {
  const p = path.startsWith('/') ? path : `/${path}`
  return `${API_BASE}${p}`
}

export type PredictErrorCode = 'config' | 'network' | 'http' | 'invalid'

export class PredictApiError extends Error {
  readonly code: PredictErrorCode
  readonly status?: number

  constructor(code: PredictErrorCode, message?: string, status?: number) {
    super(message ?? code)
    this.name = 'PredictApiError'
    this.code = code
    this.status = status
  }
}

export type EstimatePath = 'management' | 'predictive'

export interface EstimateResponse {
  path: EstimatePath
  diagnosed: boolean
  ageOfOnset?: number | null
  recordId?: number | null
  assessmentId?: number
  message?: string
  featureVector?: number[] | null
  prediction?: PredictionResult
}

function authHeaders(): HeadersInit {
  const token = sessionStorage.getItem('descend-supabase-access-token')
  const headers: Record<string, string> = { 'Content-Type': 'application/json' }
  if (token) headers.Authorization = `Bearer ${token}`
  return headers
}

function mapPredictiveBody(data: Record<string, unknown>): PredictionResult {
  const summary = (data.summary ?? {}) as {
    averagePercentage?: number
    averageProbability?: number
    overallRiskBand?: string
    modelAveragePercentage?: number
    modelAverageProbability?: number
  }
  const features = (data.features ?? {}) as { bmi?: number }

  const probability = summary.averageProbability ?? summary.modelAverageProbability ?? 0.2
  const percentage =
    summary.averagePercentage ??
    summary.modelAveragePercentage ??
    Math.round(probability * 100)
  const riskBand = (summary.overallRiskBand as RiskBand) ?? 'Low'

  if (!Number.isFinite(probability) || !Number.isFinite(percentage)) {
    throw new PredictApiError('invalid', 'Predict response missing numeric score')
  }

  return {
    percentage,
    probability,
    riskBand,
    bmi: features.bmi ?? null,
    source: 'api',
    softAdjustment: (data.softAdjustment as PredictionResult['softAdjustment']) ?? {
      lifestyle: 0,
      blood: 0,
      earlyOnset: 0,
      base: probability,
      net: 0,
      contributions: [],
    },
    predictions: data.predictions as PredictionResult['predictions'],
    scenarioProbabilities:
      (data.scenarioProbabilities as PredictionResult['scenarioProbabilities']) ?? null,
    futureGenerations: data.futureGenerations as PredictionResult['futureGenerations'],
    familyLineage: (data.familyLineage as PredictionResult['familyLineage']) ?? null,
    predictionScopeNote: data.predictionScopeNote as string | undefined,
    chartData: data.chartData as Record<string, number> | undefined,
    onsetHorizon: (data.onsetHorizon as PredictionResult['onsetHorizon']) ?? null,
  }
}

/** Dedicated estimation endpoint — branches diagnosed vs ExtraTrees. */
export async function estimateAssessment(payload: unknown): Promise<EstimateResponse> {
  if (!API_BASE) {
    throw new PredictApiError('config', 'API base URL is not configured')
  }

  let res: Response
  try {
    res = await fetch(apiUrl('/api/estimate'), {
      method: 'POST',
      headers: authHeaders(),
      body: JSON.stringify(payload),
    })
  } catch {
    throw new PredictApiError('network', 'Network request failed')
  }

  if (!res.ok) {
    let detail = ''
    try {
      detail = (await res.text()).slice(0, 280)
    } catch {
      detail = ''
    }
    throw new PredictApiError('http', detail || `Estimate failed (${res.status})`, res.status)
  }

  let data: Record<string, unknown>
  try {
    data = (await res.json()) as Record<string, unknown>
  } catch {
    throw new PredictApiError('invalid', 'Invalid JSON from estimate API')
  }

  const path = (data.path as EstimatePath) || (data.diagnosed ? 'management' : 'predictive')

  if (path === 'management' || data.diagnosed === true) {
    return {
      path: 'management',
      diagnosed: true,
      ageOfOnset: (data.ageOfOnset as number | null | undefined) ?? null,
      recordId: (data.recordId as number | null | undefined) ?? null,
      assessmentId: data.assessmentId as number | undefined,
      message: data.message as string | undefined,
      featureVector: null,
    }
  }

  return {
    path: 'predictive',
    diagnosed: false,
    ageOfOnset: null,
    recordId: (data.recordId as number | null | undefined) ?? null,
    assessmentId: data.assessmentId as number | undefined,
    featureVector: (data.featureVector as number[] | null | undefined) ?? null,
    prediction: mapPredictiveBody(data),
  }
}

/** Undiagnosed survey scoring (uses /api/estimate). */
export async function predictAssessment(payload: unknown): Promise<PredictionResult> {
  const estimated = await estimateAssessment(payload)
  if (estimated.path === 'management' || !estimated.prediction) {
    throw new PredictApiError(
      'invalid',
      'Diagnosed profiles cannot receive a predictive risk score',
    )
  }
  return estimated.prediction
}

/** Minimal payload for already-diagnosed patients (no survey features). */
export function mapDiagnosedPayload(ageOfOnset: number) {
  return {
    personalInfo: {
      diagnosedT2dm: 'yes',
      ageAtDiagnosis: ageOfOnset,
    },
    diagnosisAges: {
      self: ageOfOnset,
    },
    familyHistory: {},
    lifestyle: {},
    labs: {},
  }
}

export function ensureUndiagnosedPayload(answers: AssessmentAnswers) {
  return {
    ...answers,
    diagnosedT2dm: 'no' as const,
  }
}

export async function fetchProfile(): Promise<unknown> {
  const res = await fetch(apiUrl('/api/profile'), { headers: authHeaders() })
  if (!res.ok) throw new Error('Profile fetch failed')
  return res.json()
}

export async function patchProfile(body: Record<string, unknown>): Promise<unknown> {
  const res = await fetch(apiUrl('/api/profile'), {
    method: 'PATCH',
    headers: authHeaders(),
    body: JSON.stringify(body),
  })
  if (!res.ok) throw new Error('Profile update failed')
  return res.json()
}

export async function fetchHistory(): Promise<{ items: unknown[] }> {
  const res = await fetch(apiUrl('/api/profile/history'), { headers: authHeaders() })
  if (!res.ok) throw new Error('History fetch failed')
  return res.json()
}
