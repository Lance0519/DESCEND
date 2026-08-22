import type { PredictionResult, RiskBand } from '../types/prediction'

const API_BASE = import.meta.env.VITE_API_BASE_URL ?? ''

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

function authHeaders(): HeadersInit {
  const token = sessionStorage.getItem('descend-supabase-access-token')
  const headers: Record<string, string> = { 'Content-Type': 'application/json' }
  if (token) headers.Authorization = `Bearer ${token}`
  return headers
}

export async function predictAssessment(payload: unknown): Promise<PredictionResult> {
  if (!API_BASE) {
    throw new PredictApiError('config', 'API base URL is not configured')
  }

  let res: Response
  try {
    res = await fetch(`${API_BASE}/api/predict`, {
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
    throw new PredictApiError(
      'http',
      detail || `Predict failed (${res.status})`,
      res.status,
    )
  }

  let data: {
    summary?: {
      averagePercentage?: number
      averageProbability?: number
      overallRiskBand?: string
    }
    softAdjustment?: PredictionResult['softAdjustment']
    features?: { bmi?: number }
    predictions?: PredictionResult['predictions']
    scenarioProbabilities?: PredictionResult['scenarioProbabilities']
    futureGenerations?: PredictionResult['futureGenerations']
    familyLineage?: PredictionResult['familyLineage']
    predictionScopeNote?: string
    chartData?: Record<string, number>
  }

  try {
    data = (await res.json()) as typeof data
  } catch {
    throw new PredictApiError('invalid', 'Invalid JSON from predict API')
  }

  if (!data || typeof data !== 'object') {
    throw new PredictApiError('invalid', 'Empty predict response')
  }

  const probability = data.summary?.averageProbability ?? 0.2
  const percentage = data.summary?.averagePercentage ?? Math.round(probability * 100)
  const riskBand = (data.summary?.overallRiskBand as RiskBand) ?? 'Low'

  if (!Number.isFinite(probability) || !Number.isFinite(percentage)) {
    throw new PredictApiError('invalid', 'Predict response missing numeric score')
  }

  return {
    percentage,
    probability,
    riskBand,
    bmi: data.features?.bmi ?? null,
    source: 'api',
    softAdjustment: data.softAdjustment ?? {
      lifestyle: 0,
      blood: 0,
      earlyOnset: 0,
      base: probability,
      net: 0,
      contributions: [],
    },
    predictions: data.predictions,
    scenarioProbabilities: data.scenarioProbabilities ?? null,
    futureGenerations: data.futureGenerations,
    familyLineage: data.familyLineage ?? null,
    predictionScopeNote: data.predictionScopeNote,
    chartData: data.chartData,
  }
}

export async function fetchProfile(): Promise<unknown> {
  const res = await fetch(`${API_BASE}/api/profile`, { headers: authHeaders() })
  if (!res.ok) throw new Error('Profile fetch failed')
  return res.json()
}

export async function patchProfile(body: Record<string, unknown>): Promise<unknown> {
  const res = await fetch(`${API_BASE}/api/profile`, {
    method: 'PATCH',
    headers: authHeaders(),
    body: JSON.stringify(body),
  })
  if (!res.ok) throw new Error('Profile update failed')
  return res.json()
}

export async function fetchHistory(): Promise<{ items: unknown[] }> {
  const res = await fetch(`${API_BASE}/api/profile/history`, { headers: authHeaders() })
  if (!res.ok) throw new Error('History fetch failed')
  return res.json()
}
