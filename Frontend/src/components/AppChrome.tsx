import { Home, LayoutDashboard, LogOut } from 'lucide-react'
import { Link, useNavigate } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'
import { useLanguage } from '../context/LanguageContext'
import { LanguageToggle } from './LanguageToggle'
import './AppChrome.css'

interface AppChromeProps {
  showSignOut?: boolean
}

export function AppChrome({ showSignOut = true }: AppChromeProps) {
  const { t } = useLanguage()
  const { user, signOut } = useAuth()
  const navigate = useNavigate()

  return (
    <div className="app-chrome">
      <LanguageToggle />
      <div className="app-chrome__links">
        <Link to="/" className="app-chrome__link">
          <Home size={16} aria-hidden />
          {t.homeNav}
        </Link>
        {user ? (
          <Link to="/dashboard" className="app-chrome__link">
            <LayoutDashboard size={16} aria-hidden />
            {t.dashboardTitle}
          </Link>
        ) : null}
        {user && showSignOut ? (
          <button
            type="button"
            className="app-chrome__link"
            onClick={() => void signOut().then(() => navigate('/'))}
          >
            <LogOut size={16} aria-hidden />
            {t.signOut}
          </button>
        ) : null}
      </div>
    </div>
  )
}
