import type { ReactNode } from 'react'
import './PageBackground.css'

export function PageBackground({ children }: { children: ReactNode }) {
  return (
    <div className="page-bg">
      <div className="page-bg__gradient" aria-hidden />
      <div className="page-bg__blob page-bg__blob--a" aria-hidden />
      <div className="page-bg__blob page-bg__blob--b" aria-hidden />
      <div className="page-bg__blob page-bg__blob--c" aria-hidden />
      <div className="page-bg__grain" aria-hidden />
      <div className="page-bg__content">{children}</div>
    </div>
  )
}
