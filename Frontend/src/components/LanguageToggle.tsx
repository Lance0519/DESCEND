import { Globe } from 'lucide-react'
import { useLanguage } from '../context/LanguageContext'
import type { Language } from '../types/assessment'
import './LanguageToggle.css'

export function LanguageToggle() {
  const { language, setLanguage, t } = useLanguage()

  const set = (lang: Language) => setLanguage(lang)

  return (
    <div className="lang-toggle" role="group" aria-label={t.langLabel}>
      <Globe className="lang-toggle__icon" size={16} aria-hidden />
      <button
        type="button"
        className={language === 'tl' ? 'lang-toggle__btn lang-toggle__btn--active' : 'lang-toggle__btn'}
        onClick={() => set('tl')}
        aria-pressed={language === 'tl'}
        aria-label="Tagalog"
      >
        <span className="lang-toggle__full">Tagalog</span>
        <span className="lang-toggle__short" aria-hidden>
          TL
        </span>
      </button>
      <button
        type="button"
        className={language === 'en' ? 'lang-toggle__btn lang-toggle__btn--active' : 'lang-toggle__btn'}
        onClick={() => set('en')}
        aria-pressed={language === 'en'}
        aria-label="English"
      >
        <span className="lang-toggle__full">English</span>
        <span className="lang-toggle__short" aria-hidden>
          EN
        </span>
      </button>
    </div>
  )
}
