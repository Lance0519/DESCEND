import { motion } from 'framer-motion'
import { Activity, ArrowRight, Info, ShieldCheck } from 'lucide-react'
import { useNavigate } from 'react-router-dom'
import { ContactSupport } from '../components/ContactSupport'
import { DisclaimerBox } from '../components/DisclaimerBox'
import { LanguageToggle } from '../components/LanguageToggle'
import { PageBackground } from '../components/PageBackground'
import { useLanguage } from '../context/LanguageContext'
import './LandingPage.css'

export function LandingPage() {
  const { t } = useLanguage()
  const navigate = useNavigate()

  return (
    <PageBackground>
      <div className="landing">
        <motion.main
          className="landing__card"
          initial={{ opacity: 0, y: 18 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.4 }}
        >
          <div className="landing__header">
            <div className="landing__brand">
              <Activity size={32} color="var(--color-primary)" aria-hidden />
              <h1>{t.brand}</h1>
            </div>
            <LanguageToggle />
          </div>

          <h2 className="landing__subtitle">{t.subtitle}</h2>
          <p className="landing__desc">{t.description}</p>

          <div className="landing__disclaimers">
            <DisclaimerBox title={t.disclaimerTitle} text={t.disclaimerText} icon={Info} variant="neutral" />
            <DisclaimerBox title={t.privacyTitle} text={t.privacyText} icon={ShieldCheck} variant="primary" />
          </div>

          <ContactSupport />

          <button type="button" className="landing__cta" onClick={() => navigate('/access')}>
            {t.startAssessment}
            <ArrowRight size={22} aria-hidden />
          </button>
        </motion.main>
      </div>
    </PageBackground>
  )
}
