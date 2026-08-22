import { Globe } from 'lucide-react'
import { useLanguage } from '../context/LanguageContext'
import type { Language } from '../types/assessment'
import './LanguageToggle.css'

export function LanguageToggle() {
  const { language, setLanguage, t } = useLanguage()

  const set = (lang: Language) => setLanguage(lang)

  return (
    <div className="lang-toggle" aria-label={t.langLabel}>
      <Globe size={18} aria-hidden />
      <button
        type="button"
        className={language === 'tl' ? 'lang-toggle__btn lang-toggle__btn--active' : 'lang-toggle__btn'}
        onClick={() => set('tl')}
      >
        Tagalog
      </button>
      <button
        type="button"
        className={language === 'en' ? 'lang-toggle__btn lang-toggle__btn--active' : 'lang-toggle__btn'}
        onClick={() => set('en')}
      >
        English
      </button>
    </div>
  )
}
