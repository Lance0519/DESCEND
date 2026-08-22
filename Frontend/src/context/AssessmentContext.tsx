import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from 'react'
import { clearDraft, loadDraft, saveDraft } from '../lib/draftStorage'
import type { AnswerKey, AssessmentAnswers } from '../types/assessment'
import type { PredictionResult } from '../types/prediction'

interface AssessmentContextValue {
  answers: AssessmentAnswers
  setAnswer: <K extends AnswerKey>(key: K, value: AssessmentAnswers[K]) => void
  setAnswersBulk: (next: AssessmentAnswers) => void
  resetAssessment: () => void
  result: PredictionResult | null
  setResult: (result: PredictionResult | null) => void
  questionIndex: number
  setQuestionIndex: (i: number) => void
  hasDraft: boolean
  clearSavedDraft: () => void
  persistDraftNow: (language: 'en' | 'tl') => void
}

const AssessmentContext = createContext<AssessmentContextValue | null>(null)

export function AssessmentProvider({ children }: { children: ReactNode }) {
  const initial = loadDraft()
  const [answers, setAnswers] = useState<AssessmentAnswers>(initial?.answers ?? {})
  const [questionIndex, setQuestionIndex] = useState(initial?.questionIndex ?? 0)
  const [result, setResult] = useState<PredictionResult | null>(null)
  const [hasDraft, setHasDraft] = useState(Boolean(initial && Object.keys(initial.answers).length > 0))

  const setAnswer = useCallback(<K extends AnswerKey>(key: K, value: AssessmentAnswers[K]) => {
    setAnswers((prev) => ({ ...prev, [key]: value }))
  }, [])

  const setAnswersBulk = useCallback((next: AssessmentAnswers) => {
    setAnswers(next)
  }, [])

  const clearSavedDraft = useCallback(() => {
    clearDraft()
    setHasDraft(false)
  }, [])

  const resetAssessment = useCallback(() => {
    setAnswers({})
    setResult(null)
    setQuestionIndex(0)
    clearDraft()
    setHasDraft(false)
  }, [])

  const persistDraftNow = useCallback(
    (language: 'en' | 'tl') => {
      if (Object.keys(answers).length === 0) return
      saveDraft({ answers, questionIndex, language, updatedAt: Date.now() })
      setHasDraft(true)
    },
    [answers, questionIndex],
  )

  useEffect(() => {
    if (Object.keys(answers).length === 0) return
    const lang = (localStorage.getItem('descend-language-v1') as 'en' | 'tl') || 'tl'
    saveDraft({ answers, questionIndex, language: lang, updatedAt: Date.now() })
    setHasDraft(true)
  }, [answers, questionIndex])

  const value = useMemo(
    () => ({
      answers,
      setAnswer,
      setAnswersBulk,
      resetAssessment,
      result,
      setResult,
      questionIndex,
      setQuestionIndex,
      hasDraft,
      clearSavedDraft,
      persistDraftNow,
    }),
    [
      answers,
      setAnswer,
      setAnswersBulk,
      resetAssessment,
      result,
      questionIndex,
      hasDraft,
      clearSavedDraft,
      persistDraftNow,
    ],
  )

  return <AssessmentContext.Provider value={value}>{children}</AssessmentContext.Provider>
}

export function useAssessment() {
  const ctx = useContext(AssessmentContext)
  if (!ctx) throw new Error('useAssessment must be used within AssessmentProvider')
  return ctx
}
