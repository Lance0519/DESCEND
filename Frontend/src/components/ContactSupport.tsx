import { Mail } from 'lucide-react'
import { useLanguage } from '../context/LanguageContext'
import './ContactSupport.css'

const SUPPORT_EMAIL = 'justinelance0067@gmail.com'

export function ContactSupport() {
  const { t } = useLanguage()

  return (
    <p className="contact-support">
      <Mail size={16} aria-hidden />
      <span>
        {t.contactSupportText}{' '}
        <a href={`mailto:${SUPPORT_EMAIL}`}>{SUPPORT_EMAIL}</a>
      </span>
    </p>
  )
}
