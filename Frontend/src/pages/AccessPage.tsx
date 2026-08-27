import { motion } from 'framer-motion'
import { LogIn, UserPlus, UserRound } from 'lucide-react'
import { useNavigate } from 'react-router-dom'
import { AuthNavBar } from '../components/AuthNavBar'
import { PageBackground } from '../components/PageBackground'
import { useAuth } from '../context/AuthContext'
import { useLanguage } from '../context/LanguageContext'
import './AccessPage.css'

export function AccessPage() {
  const { t } = useLanguage()
  const { continueAsGuest } = useAuth()
  const navigate = useNavigate()

  return (
    <PageBackground>
      <div className="access">
        <div className="access__toolbar">
          <AuthNavBar backTo="/" showHome={false} />
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
        </motion.main>
      </div>
    </PageBackground>
  )
}
