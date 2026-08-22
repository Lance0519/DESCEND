export type RiskBand = 'Low' | 'Moderate' | 'High'

export interface SoftAdjustmentContribution {
  id: string
  label: string
  delta: number
  group: 'lifestyle' | 'blood' | 'earlyOnset' | 'base' | 'family' | 'clinical' | 'bmi'
}

export interface SoftAdjustment {
  lifestyle: number
  blood: number
  earlyOnset: number
  base: number
  net: number
  contributions: SoftAdjustmentContribution[]
}

export interface PredictionItem {
  key: string
  label: string
  probability: number
  percentage: number
  riskBand: string
}

export interface ScenarioProbabilities {
  childRisk: {
    female: number | null
    male: number | null
  }
  grandchildRisk: {
    fromDaughter: { female: number | null; male: number | null }
    fromSon: { female: number | null; male: number | null }
  }
}

export interface ProjectedGenerationNode {
  key: string
  label: string
  gender: 'male' | 'female'
  generation: 4 | 5
  isProjected: true
  parentKey?: string
}

export interface FutureGenerationsPayload {
  children: ProjectedGenerationNode[]
  grandchildren: ProjectedGenerationNode[]
}

export interface FamilyLineageNode {
  id: string
  label: string
  status?: string
  generation?: number
}

export interface FamilyLineage {
  nodes?: FamilyLineageNode[]
  edges?: { from: string; to: string }[]
  [key: string]: unknown
}

export interface PredictionResult {
  percentage: number
  probability: number
  riskBand: RiskBand
  softAdjustment: SoftAdjustment
  bmi: number | null
  source: 'mock' | 'api'
  predictions?: PredictionItem[]
  scenarioProbabilities?: ScenarioProbabilities | null
  futureGenerations?: FutureGenerationsPayload
  familyLineage?: FamilyLineage | null
  predictionScopeNote?: string
  chartData?: Record<string, number>
}
