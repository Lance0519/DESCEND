import type { PredictionResult, RiskBand } from '../types/prediction'

const API_BASE = import.meta.env.VITE_API_BASE_URL ?? ''

function authHeaders(): HeadersInit {
  const token = sessionStorage.getItem('descend-supabase-access-token')
  const headers: Record<string, string> = { 'Content-Type': 'application/json' }
  if (token) headers.Authorization = `Bearer ${token}`
  return headers
}

export async function predictAssessment(payload: unknown): Promise<PredictionResult> {
  const res = await fetch(`${API_BASE}/api/predict`, {
    method: 'POST',
    headers: authHeaders(),
    body: JSON.stringify(payload),
  })
  if (!res.ok) {
    const text = await res.text()
    throw new Error(text || `Predict failed (${res.status})`)
  }
  const data = (await res.json()) as {
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

  const probability = data.summary?.averageProbability ?? 0.2
  const percentage = data.summary?.averagePercentage ?? Math.round(probability * 100)
  const riskBand = (data.summary?.overallRiskBand as RiskBand) ?? 'Low'

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

export async function fetchTtsAudio(text: string, language: 'en' | 'tl'): Promise<Blob | null> {
  try {
    const res = await fetch(`${API_BASE}/api/tts`, {
      method: 'POST',
      headers: authHeaders(),
      body: JSON.stringify({ text, language }),
    })
    if (!res.ok) return null
    return await res.blob()
  } catch {
    return null
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
