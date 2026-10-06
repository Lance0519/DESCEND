import type { ReactNode } from 'react'
import { LanguageToggle } from '../LanguageToggle'
import './AppNavBar.css'

export interface AppNavBarProps {
  left?: ReactNode
  right?: ReactNode
  showLanguageToggle?: boolean
  maxWidth?: string | number
  className?: string
}

export function AppNavBar({
  left,
  right,
  showLanguageToggle = true,
  maxWidth,
  className = '',
}: AppNavBarProps) {
  const customStyle = maxWidth ? { '--nav-max-width': typeof maxWidth === 'number' ? `${maxWidth}px` : maxWidth } as React.CSSProperties : undefined

  return (
    <header className={`app-nav ${className}`.trim()} style={customStyle}>
      <div className="app-nav__left">
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
