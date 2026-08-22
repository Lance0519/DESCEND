import type { QuestionDef } from '../data/questions'
import type { AnswerKey, AssessmentAnswers } from '../types/assessment'

export type NumberFieldError = 'required' | 'range' | null

/** Only these typed inputs get required + min/max error handling. */
export const STRICT_NUMBER_IDS: ReadonlySet<string> = new Set<AnswerKey>([
  'age',
  'heightCm',
  'weightKg',
])

export function isStrictNumberField(questionId: string): boolean {
  return STRICT_NUMBER_IDS.has(questionId)
}

/** Range/required checks for core typed inputs only; others skip custom validation. */
export function validateNumberField(
  question: QuestionDef,
  value: number | '',
  _answers?: AssessmentAnswers,
): NumberFieldError {
  if (!isStrictNumberField(String(question.id))) return null
  if (question.type !== 'number') return null

  if (value === '') return 'required'

  const n = value as number
  if (!Number.isFinite(n)) return 'range'
  if (question.min != null && n < question.min) return 'range'
  if (question.max != null && n > question.max) return 'range'
  return null
}

/** Core fields required before calling the live scorer. */
export function validateAnswersForSubmit(answers: AssessmentAnswers): boolean {
  return (
    answers.sex != null &&
    typeof answers.age === 'number' &&
    Number.isFinite(answers.age) &&
    answers.age >= 18 &&
    answers.age <= 90 &&
    typeof answers.heightCm === 'number' &&
    Number.isFinite(answers.heightCm) &&
    answers.heightCm >= 120 &&
    answers.heightCm <= 220 &&
    typeof answers.weightKg === 'number' &&
    Number.isFinite(answers.weightKg) &&
    answers.weightKg >= 30 &&
    answers.weightKg <= 250
  )
}
