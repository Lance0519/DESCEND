import { useState, type ReactNode } from 'react'
import { NumberInput } from '../../components/NumberInput'
import { PageBackground } from '../../components/PageBackground'
import { useLanguage } from '../../context/LanguageContext'

interface OnsetGateProps {
  toolbar?: ReactNode
  initialAge?: number | ''
  submitting?: boolean
  onBack: () => void
  onSubmit: (age: number) => Promise<void> | void
}

export function OnsetGate({
  toolbar,
  initialAge = '',
  submitting = false,
  onBack,
  onSubmit,
}: OnsetGateProps) {
  const { t } = useLanguage()
  const [onsetAge, setOnsetAge] = useState<number | ''>(initialAge)
  const [error, setError] = useState<string | null>(null)

  function handleSubmit() {
    if (onsetAge === '' || onsetAge < 1 || onsetAge > 90) {
      setError(
        onsetAge === ''
          ? t.fieldRequired
          : t.fieldOutOfRange.replace('{min}', '1').replace('{max}', '90'),
      )
      return
    }
    setError(null)
    void onSubmit(onsetAge)
  }

  return (
    <PageBackground>
      <div className="assessment-page assessment-page--resume">
        <div className="resume-card" style={{ textAlign: 'left', maxWidth: 480 }}>
          {toolbar}
          <h2>{t.diagnosisOnsetTitle}</h2>
          <p style={{ margin: '0.75rem 0 1rem', color: 'var(--color-text-muted)' }}>
            {t.diagnosisOnsetHelp}
          </p>

          <NumberInput
            id="ageOfOnset"
            value={onsetAge}
            min={1}
            max={90}
            step={1}
            error={error}
            onChange={(v) => {
              setOnsetAge(v)
              if (v === '') {
                setError(t.fieldRequired)
                return
              }
              if (v < 1 || v > 90) {
                setError(t.fieldOutOfRange.replace('{min}', '1').replace('{max}', '90'))
                return
              }
              setError(null)
            }}
          />

          <div style={{ display: 'flex', flexDirection: 'column', gap: '0.65rem', marginTop: '1.25rem' }}>
            <button
              type="button"
              className="btn btn--primary"
              disabled={submitting}
              onClick={handleSubmit}
              style={{ width: '100%', minHeight: '48px' }}
            >
              {submitting ? t.loading : t.diagnosisOnsetContinue}
            </button>
            <button
              type="button"
              className="btn btn--ghost"
              disabled={submitting}
              onClick={onBack}
              style={{ width: '100%', minHeight: '48px' }}
            >
              {t.back}
            </button>
          </div>
        </div>
      </div>
    </PageBackground>
  )
}
