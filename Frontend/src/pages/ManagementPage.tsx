import { motion } from 'framer-motion'
import { Activity, Apple, HeartPulse, Moon } from 'lucide-react'
import { Link, Navigate, useNavigate } from 'react-router-dom'
import { ContactSupport } from '../components/ContactSupport'
import { LanguageToggle } from '../components/LanguageToggle'
import { PageBackground } from '../components/PageBackground'
import { useAssessment } from '../context/AssessmentContext'
import { useLanguage } from '../context/LanguageContext'
import './ManagementPage.css'

export function ManagementPage() {
  const { t } = useLanguage()
  const { answers, resetAssessment } = useAssessment()
  const navigate = useNavigate()
  const onset = answers.ageAtDiagnosis

  if (answers.diagnosedT2dm !== 'yes') {
    return <Navigate to="/assessment" replace />
  }

  const tips = [
    { icon: Apple, title: t.mgmtTipDietTitle, text: t.mgmtTipDietText },
    { icon: Activity, title: t.mgmtTipActivityTitle, text: t.mgmtTipActivityText },
    { icon: HeartPulse, title: t.mgmtTipCareTitle, text: t.mgmtTipCareText },
    { icon: Moon, title: t.mgmtTipLifestyleTitle, text: t.mgmtTipLifestyleText },
  ]

  return (
    <PageBackground>
      <div className="mgmt">
        <div className="mgmt__toolbar">
          <LanguageToggle />
          <Link to="/account">{t.accountNav}</Link>
        </div>
        <motion.main
          className="mgmt__card"
          initial={{ opacity: 0, y: 14 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.35 }}
        >
          <p className="mgmt__badge">{t.mgmtBadge}</p>
          <h1>{t.mgmtTitle}</h1>
          <p className="mgmt__lead">{t.mgmtLead}</p>
          {onset != null ? (
            <p className="mgmt__onset">
              {t.mgmtOnsetLabel}: <strong>{onset}</strong>
            </p>
          ) : null}

          <ul className="mgmt__tips">
            {tips.map(({ icon: Icon, title, text }) => (
              <li key={title}>
                <Icon size={22} aria-hidden className="mgmt__tip-icon" />
                <div>
                  <h2>{title}</h2>
                  <p>{text}</p>
                </div>
              </li>
            ))}
          </ul>

          <p className="mgmt__disclaimer">{t.mgmtDisclaimer}</p>
          <ContactSupport />

          <div className="mgmt__actions">
            <button
              type="button"
              className="btn btn--primary"
              onClick={() => {
                resetAssessment()
                navigate('/assessment')
              }}
            >
              {t.mgmtRestart}
            </button>
            <Link to="/" className="btn btn--ghost">
              {t.brand}
            </Link>
          </div>
        </motion.main>
      </div>
    </PageBackground>
  )
}
