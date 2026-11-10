import type { ReactNode } from 'react'
import { PageBackground } from '../../components/PageBackground'
import { useLanguage } from '../../context/LanguageContext'

interface ResumeModalProps {
  toolbar?: ReactNode
  onResume: () => void
  onStartOver: () => void
}

export function ResumeModal({ toolbar, onResume, onStartOver }: ResumeModalProps) {
  const { t } = useLanguage()

  return (
    <PageBackground>
      <div className="assessment-page assessment-page--resume">
        <div className="resume-card">
          {toolbar}
          <h2>{t.resumeTitle}</h2>
          <p>{t.resumeText}</p>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '0.65rem', marginTop: '1.25rem' }}>
            <button
              type="button"
              className="btn btn--primary"
              onClick={onResume}
              style={{ width: '100%', minHeight: '48px' }}
            >
              {t.resumeContinue}
            </button>
            <button
              type="button"
              className="btn btn--ghost"
              onClick={onStartOver}
              style={{ width: '100%', minHeight: '48px' }}
            >
              {t.resumeStartOver}
            </button>
          </div>
        </div>
      </div>
    </PageBackground>
  )
}
