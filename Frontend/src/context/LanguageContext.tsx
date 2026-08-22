import { createContext, useContext, useEffect, useMemo, useState, type ReactNode } from 'react'
import { getDictionary, type TranslationDict } from '../i18n'
import { loadSavedLanguage, saveLanguage } from '../lib/draftStorage'
import type { Language } from '../types/assessment'

interface LanguageContextValue {
  language: Language
  setLanguage: (lang: Language) => void
  t: TranslationDict
}

const LanguageContext = createContext<LanguageContextValue | null>(null)

export function LanguageProvider({ children }: { children: ReactNode }) {
  const [language, setLanguageState] = useState<Language>(() => loadSavedLanguage() ?? 'tl')

  const setLanguage = (lang: Language) => {
    setLanguageState(lang)
    saveLanguage(lang)
  }

  useEffect(() => {
    saveLanguage(language)
  }, [language])

  const value = useMemo(
    () => ({
      language,
      setLanguage,
      t: getDictionary(language),
    }),
    [language],
  )
  return <LanguageContext.Provider value={value}>{children}</LanguageContext.Provider>
}

export function useLanguage() {
  const ctx = useContext(LanguageContext)
  if (!ctx) throw new Error('useLanguage must be used within LanguageProvider')
  return ctx
}
