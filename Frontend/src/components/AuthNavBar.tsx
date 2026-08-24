import { ArrowLeft, Home } from 'lucide-react'
import { Link } from 'react-router-dom'
import { useLanguage } from '../context/LanguageContext'
import { LanguageToggle } from './LanguageToggle'
import './AuthNavBar.css'

interface AuthNavBarProps {
  backTo: string
  showHome?: boolean
}

export function AuthNavBar({ backTo, showHome = true }: AuthNavBarProps) {
  const { t } = useLanguage()

  return (
    <nav className="auth-nav" aria-label={t.back}>
      <Link to={backTo} className="auth-nav__link">
        <ArrowLeft size={18} aria-hidden />
        {t.back}
      </Link>
      <div className="auth-nav__right">
        {showHome ? (
          <Link to="/" className="auth-nav__link">
            <Home size={18} aria-hidden />
            {t.homeNav}
          </Link>
        ) : null}
        <LanguageToggle />
      </div>
    </nav>
  )
}
