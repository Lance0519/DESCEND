import type { AssessmentAnswers, Language } from '../types/assessment'

const DRAFT_KEY = 'descend-assessment-draft-v1'
const LANG_KEY = 'descend-language-v1'

export interface AssessmentDraft {
  answers: AssessmentAnswers
  questionIndex: number
  language: Language
  updatedAt: number
}

export function loadDraft(): AssessmentDraft | null {
  try {
    const raw = localStorage.getItem(DRAFT_KEY)
    if (!raw) return null
    return JSON.parse(raw) as AssessmentDraft
  } catch {
    return null
  }
}

export function saveDraft(draft: AssessmentDraft): void {
  try {
    localStorage.setItem(DRAFT_KEY, JSON.stringify({ ...draft, updatedAt: Date.now() }))
  } catch {
    /* ignore quota */
  }
}

export function clearDraft(): void {
  try {
    localStorage.removeItem(DRAFT_KEY)
  } catch {
    /* ignore */
  }
}

export function loadSavedLanguage(): Language | null {
  try {
    const v = localStorage.getItem(LANG_KEY)
    if (v === 'en' || v === 'tl') return v
  } catch {
    /* ignore */
  }
  return null
}

export function saveLanguage(lang: Language): void {
  try {
    localStorage.setItem(LANG_KEY, lang)
  } catch {
    /* ignore */
  }
}
