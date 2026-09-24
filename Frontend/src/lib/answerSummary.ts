import type { QuestionDef } from '../data/questions'
import type { TranslationDict } from '../i18n'
import { computeBmi, type AnswerKey, type AssessmentAnswers } from '../types/assessment'

export type ReviewRowState = 'answered' | 'skipped' | 'missing'

export interface ReviewRow {
  id: string
  /** Position in the visible question list, so editing can jump straight here. */
  index: number
  question: string
  value: string
  state: ReviewRowState
}

export interface ReviewGroup {
  section: QuestionDef['section']
  label: string
  rows: ReviewRow[]
}

function withUnit(value: number, unit?: string): string {
  return unit ? `${value} ${unit}` : String(value)
}

export function formatAnswerValue(
  question: QuestionDef,
  answers: AssessmentAnswers,
  t: TranslationDict,
): { value: string; state: ReviewRowState } {
  if (question.type === 'bmiConfirm') {
    if (answers.heightCm == null || answers.weightKg == null) {
      return { value: t.reviewUnanswered, state: 'missing' }
    }
    return {
      value: computeBmi(answers.heightCm, answers.weightKg).toFixed(1),
      state: 'answered',
    }
  }

  const key = question.id as AnswerKey

  // A skipped optional lab must not read the same as one that was never reached.
  if (key === 'fastingGlucoseMgDl' && answers.fastingGlucoseSkipped === true) {
    return { value: t.reviewSkipped, state: 'skipped' }
  }
  if (key === 'hba1cPercent' && answers.hba1cSkipped === true) {
    return { value: t.reviewSkipped, state: 'skipped' }
  }

  const raw = answers[key]
  if (raw == null) {
    return { value: t.reviewUnanswered, state: 'missing' }
  }

  if (typeof raw === 'number') {
    return { value: withUnit(raw, question.unit), state: 'answered' }
  }

  if (typeof raw === 'boolean') {
    return { value: raw ? t.options.yes : t.options.no, state: 'answered' }
  }

  const options = t.options as Record<string, string>
  return { value: options[raw] ?? raw, state: 'answered' }
}

export function buildReviewGroups(
  visible: QuestionDef[],
  answers: AssessmentAnswers,
  t: TranslationDict,
): ReviewGroup[] {
  const sections = t.section as Record<string, string>
  const groups: ReviewGroup[] = []

  visible.forEach((question, index) => {
    const { value, state } = formatAnswerValue(question, answers, t)
    const row: ReviewRow = {
      id: String(question.id),
      index,
      question: t.questions[question.questionKey],
      value,
      state,
    }

    const last = groups[groups.length - 1]
    if (last && last.section === question.section) {
      last.rows.push(row)
      return
    }

    groups.push({
      section: question.section,
      label: sections[question.section] ?? question.section,
      rows: [row],
    })
  })

  return groups
}

/** Index of the first unanswered question, or null when the survey is complete. */
export function firstMissingIndex(groups: ReviewGroup[]): number | null {
  for (const group of groups) {
    for (const row of group.rows) {
      if (row.state === 'missing') return row.index
    }
  }
  return null
}
