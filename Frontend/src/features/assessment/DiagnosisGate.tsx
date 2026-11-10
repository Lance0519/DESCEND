import type { ReactNode } from 'react'
import { Info } from 'lucide-react'
import { PageBackground } from '../../components/PageBackground'
import { useLanguage } from '../../context/LanguageContext'

interface DiagnosisGateProps {
  toolbar?: ReactNode
  onYes: () => void
  onNo: () => void
}

export function DiagnosisGate({ toolbar, onYes, onNo }: DiagnosisGateProps) {
  const { t } = useLanguage()

  return (
    <PageBackground>
      <div className="assessment-page assessment-page--resume">
        <div className="resume-card" style={{ textAlign: 'left', maxWidth: 500 }}>
          {toolbar}
          <div
            style={{
              display: 'flex',
              alignItems: 'flex-start',
              gap: '0.65rem',
              padding: '0.75rem 0.9rem',
              borderRadius: '8px',
              background: 'rgba(232, 244, 252, 0.75)',
              border: '1px solid var(--surface-card-border)',
              margin: '0.5rem 0 1rem',
              fontSize: '13px',
              color: 'var(--color-primary-dark)',
              lineHeight: 1.45,
            }}
          >
            <Info size={18} style={{ flexShrink: 0, marginTop: '2px' }} aria-hidden />
            <span>{t.diagnosisGateContext}</span>
          </div>

          <h2>{t.diagnosisGateTitle}</h2>
          <p style={{ margin: '0.75rem 0 1.25rem', color: 'var(--color-text-muted)' }}>
            {t.diagnosisGateQuestion}
          </p>

          <div style={{ display: 'flex', flexDirection: 'column', gap: '0.65rem' }}>
            <button
              type="button"
              className="btn btn--primary"
              onClick={onYes}
              style={{ width: '100%', minHeight: '48px' }}
            >
              {t.diagnosisGateYes}
            </button>
            <button
              type="button"
              className="btn btn--ghost"
              onClick={onNo}
              style={{ width: '100%', minHeight: '48px' }}
            >
              {t.diagnosisGateNo}
            </button>
          </div>
        </div>
      </div>
    </PageBackground>
  )
}
