import { useEffect, useMemo, useState } from 'react'
import { getVisibleQuestions, type QuestionDef } from '../data/questions'
import type { AnswerKey, AssessmentAnswers } from '../types/assessment'

export function useAssessmentFlow(
  answers: AssessmentAnswers,
  externalIndex?: number,
  onIndexChange?: (i: number) => void,
) {
  const visible = useMemo(() => getVisibleQuestions(answers), [answers])
  const [index, setIndex] = useState(externalIndex ?? 0)

  useEffect(() => {
    if (externalIndex != null && externalIndex !== index) {
      setIndex(externalIndex)
    }
  }, [externalIndex])

  const safeIndex = Math.min(index, Math.max(visible.length - 1, 0))
  const current: QuestionDef | undefined = visible[safeIndex]
  const isFirst = safeIndex <= 0
  const isLast = safeIndex >= visible.length - 1

  function setBoth(next: number) {
    setIndex(next)
    onIndexChange?.(next)
  }

  function goNext() {
    setBoth(Math.min(safeIndex + 1, visible.length - 1))
  }

  function goBack() {
    setBoth(Math.max(safeIndex - 1, 0))
  }

  function isAnswered(q: QuestionDef): boolean {
    if (q.type === 'bmiConfirm') {
      return answers.heightCm != null && answers.weightKg != null
    }
    if (q.id === 'fastingGlucoseMgDl') {
      return answers.fastingGlucoseSkipped === true || answers.fastingGlucoseMgDl != null
    }
    if (q.id === 'hba1cPercent') {
      return answers.hba1cSkipped === true || answers.hba1cPercent != null
    }
    const key = q.id as AnswerKey
    const val = answers[key]
    return val !== undefined && val !== null
  }

  return {
    visible,
    index: safeIndex,
    current,
    isFirst,
    isLast,
    goNext,
    goBack,
    isAnswered,
    total: visible.length,
  }
}
