import { motion } from 'framer-motion'
import { LogIn, UserPlus, UserRound } from 'lucide-react'
import { useNavigate } from 'react-router-dom'
import { LanguageToggle } from '../components/LanguageToggle'
import { PageBackground } from '../components/PageBackground'
import { useAuth } from '../context/AuthContext'
import { useLanguage } from '../context/LanguageContext'
import './AccessPage.css'

export function AccessPage() {
  const { t } = useLanguage()
  const { continueAsGuest, signInWithGoogle, configured } = useAuth()
  const navigate = useNavigate()
  const googleFlag = String(import.meta.env.VITE_ENABLE_GOOGLE_SIGNIN ?? '')
    .trim()
    .toLowerCase()
  const googleEnabled = googleFlag === 'true' || googleFlag === '1' || googleFlag === 'yes'
  const showGoogle = googleEnabled && configured

  return (
    <PageBackground>
      <div className="access">
        <div className="access__toolbar">
          <LanguageToggle />
        </div>
        <motion.main
          className="access__card"
          initial={{ opacity: 0, y: 16 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.35 }}
        >
          <h1>{t.accessTitle}</h1>
          <button
            type="button"
            className="access__btn access__btn--primary"
            onClick={() => {
              continueAsGuest()
              navigate('/assessment')
            }}
          >
            <UserRound size={20} aria-hidden />
            {t.accessGuest}
          </button>
          <p className="access__hint">{t.accessGuestHint}</p>
          <button type="button" className="access__btn" onClick={() => navigate('/login')}>
            <LogIn size={20} aria-hidden />
            {t.accessSignIn}
          </button>
          <button type="button" className="access__btn" onClick={() => navigate('/register')}>
            <UserPlus size={20} aria-hidden />
            {t.accessRegister}
          </button>

          {showGoogle ? (
            <>
              <button
                type="button"
                className="access__btn access__btn--google"
                onClick={() => void signInWithGoogle()}
              >
                <LogIn size={20} aria-hidden />
                {t.accessGoogle}
              </button>
              <p className="access__hint">{t.accessGoogleHint}</p>
            </>
          ) : null}
          {googleEnabled && !configured ? (
            <p className="access__hint access__hint--muted">{t.accessGoogleNeedsConfig}</p>
          ) : null}
        </motion.main>
      </div>
    </PageBackground>
  )
}
