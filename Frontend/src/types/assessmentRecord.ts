export interface AssessmentRecord {
  id: string
  user_id: string
  created_at: string
  risk_score: number | null
  risk_tier: string | null
  pre_diagnosed: boolean
}
