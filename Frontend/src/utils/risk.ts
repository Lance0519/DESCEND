import type { RiskBand } from '../types/prediction'

export type RiskLevel = 'low' | 'moderate' | 'high' | 'neutral'

export function resolveRiskLevel(input?: RiskBand | string | null): RiskLevel {
  if (!input) return 'neutral'
  const normalized = input.toLowerCase()
  if (normalized.includes('low')) return 'low'
  if (normalized.includes('high')) return 'high'
  if (normalized.includes('mod') || normalized.includes('med')) return 'moderate'
  return 'neutral'
}
