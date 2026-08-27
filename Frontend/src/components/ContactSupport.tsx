import { Mail } from 'lucide-react'
import { useLanguage } from '../context/LanguageContext'
import './ContactSupport.css'

const SUPPORT_EMAIL =
  String(import.meta.env.VITE_SUPPORT_EMAIL ?? '').trim() || 'justinelance0067@gmail.com'

export function ContactSupport() {
  const { t } = useLanguage()
  const href = `mailto:${SUPPORT_EMAIL}?subject=${encodeURIComponent(t.contactSupportSubject)}`

  return (
    <p className="contact-support">
      <Mail size={16} aria-hidden />
      <span>
        {t.contactSupportText}{' '}
        <a className="contact-support__link" href={href}>
          {t.contactSupportCta}
        </a>
      </span>
    </p>
  )
}
