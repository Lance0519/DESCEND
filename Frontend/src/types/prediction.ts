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
}

export interface ProjectedGenerationNode {
  key: string
  label: string
  gender: 'male' | 'female'
  generation: 4
  isProjected: true
  parentKey?: string
}

export interface FutureGenerationsPayload {
  children: ProjectedGenerationNode[]
}

export interface FamilyLineageNode {
  /** API field */
  key?: string
  /** Older mock field */
  id?: string
  label: string
  status?: string
  /** 0 = grandparents, 1 = parents, 2 = present (you) */
  generation?: number
  isRespondent?: boolean
  gender?: 'male' | 'female'
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
