import type { ReactNode } from 'react'
import medicalBackground from '../assets/backgrounds/medical-background.png'
import './PageBackground.css'

export function PageBackground({ children }: { children: ReactNode }) {
  return (
    <div className="page-bg">
      <div
        className="page-bg__photo"
        style={{ backgroundImage: `url(${medicalBackground})` }}
        aria-hidden
      />
      <div className="page-bg__scrim" aria-hidden />
      <div className="page-bg__content">{children}</div>
    </div>
  )
}
