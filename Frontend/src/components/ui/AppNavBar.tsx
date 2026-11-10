import type { ReactNode } from 'react'
import { Link } from 'react-router-dom'
import { Home } from 'lucide-react'
import { LanguageToggle } from '../LanguageToggle'
import { useLanguage } from '../../context/LanguageContext'
import './AppNavBar.css'

export interface AppNavBarProps {
  left?: ReactNode
  right?: ReactNode
  showHome?: boolean
  homeUrl?: string
  onHomeClick?: () => void
  showLanguageToggle?: boolean
  maxWidth?: string | number
  className?: string
}

export function AppNavBar({
  left,
  right,
  showHome = false,
  homeUrl = '/',
  onHomeClick,
  showLanguageToggle = true,
  maxWidth,
  className = '',
}: AppNavBarProps) {
  const { t } = useLanguage()
  const customStyle = maxWidth
    ? ({ '--nav-max-width': typeof maxWidth === 'number' ? `${maxWidth}px` : maxWidth } as React.CSSProperties)
    : undefined

  const homeElement = showHome ? (
    onHomeClick ? (
      <button
        type="button"
        className="app-nav__link app-nav__home"
        onClick={onHomeClick}
        title={t.navHomeAria}
        aria-label={t.navHomeAria}
      >
        <Home size={16} aria-hidden />
        <span>{t.navHome}</span>
      </button>
    ) : (
      <Link
        to={homeUrl}
        className="app-nav__link app-nav__home"
        title={t.navHomeAria}
        aria-label={t.navHomeAria}
      >
        <Home size={16} aria-hidden />
        <span>{t.navHome}</span>
      </Link>
    )
  ) : null

  return (
    <header className={`app-nav ${className}`.trim()} style={customStyle}>
      <div className="app-nav__left">
        {homeElement}
        {left}
        {showLanguageToggle && !left ? <LanguageToggle /> : null}
      </div>
      <div className="app-nav__right">
        {showLanguageToggle && left ? <LanguageToggle /> : null}
        {right}
      </div>
    </header>
  )
}
