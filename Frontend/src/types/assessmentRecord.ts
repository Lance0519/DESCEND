export type AssessmentSourceTable = 'assessments' | 'patient_survey_records'

export interface AssessmentRecord {
  id: string
  user_id: string
  created_at: string
  risk_score: number | null
  risk_tier: string | null
  pre_diagnosed: boolean
  label: string | null
  notes: string | null
  /** Writable base table used for update/delete. */
  sourceTable: AssessmentSourceTable | null
  /** Numeric/uuid id in the writable base table. */
  sourceId: string | null
}
