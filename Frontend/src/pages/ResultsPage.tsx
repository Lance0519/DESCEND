import { Activity, Droplets, HeartPulse, Scale, Users } from 'lucide-react'
import { Link, Navigate, useNavigate } from 'react-router-dom'
import { LanguageToggle } from '../components/LanguageToggle'
import { PageBackground } from '../components/PageBackground'
import { useAssessment } from '../context/AssessmentContext'
import { useAuth } from '../context/AuthContext'
import { useLanguage } from '../context/LanguageContext'
import { DescendantProjection } from '../features/results/DescendantProjection'
import { FamilyPedigreePanel } from '../features/results/FamilyPedigreePanel'
import { clearDraft } from '../lib/draftStorage'
import './ResultsPage.css'

export function ResultsPage() {
  const { t } = useLanguage()
  const { result, answers, resetAssessment } = useAssessment()
  const { user } = useAuth()
  const navigate = useNavigate()

  if (answers.diagnosedT2dm === 'yes') return <Navigate to="/management" replace />
  if (!result) return <Navigate to="/assessment" replace />

  const bandClass =
    result.riskBand === 'Low'
      ? 'results__band--low'
      : result.riskBand === 'Moderate'
        ? 'results__band--moderate'
        : 'results__band--high'

  const contribLabel = (key: string) => (t.contrib as Record<string, string>)[key] ?? key

  return (
    <PageBackground>
      <div className="results">
        <div className="results__toolbar">
          <LanguageToggle />
          {user ? (
            <Link to="/account" className="results__account">
              {t.accountNav}
            </Link>
          ) : null}
        </div>
        <main className="results__card">
          <h1>{t.resultsTitle}</h1>
          <p
            className={`results__source ${
              result.source === 'api' ? 'results__source--api' : 'results__source--mock'
            }`}
          >
            {result.source === 'api' ? t.resultsModelBadge : t.resultsMockBadge}
          </p>
          <p className="results__percent-label">{t.resultsPercent}</p>
          <p className="results__percent">{result.percentage}%</p>
          <p className={`results__band ${bandClass}`}>
            {t.resultsBand}: {t.bands[result.riskBand]}
          </p>

          <div className="results__icons" aria-hidden>
            <span>
              <Users size={22} />
            </span>
            <span>
              <Activity size={22} />
            </span>
            <span>
              <HeartPulse size={22} />
            </span>
            <span>
              <Scale size={22} />
            </span>
            {(result.softAdjustment.blood !== 0 ||
              result.softAdjustment.contributions.some((c) => c.group === 'blood')) && (
              <span>
                <Droplets size={22} />
              </span>
            )}
          </div>

          {result.bmi != null ? (
            <p className="results__bmi">
              {t.bmiLabel}: {result.bmi.toFixed(1)}
            </p>
          ) : null}

          <FamilyPedigreePanel result={result} title={t.pedigreeTitle} />

          <DescendantProjection
            result={result}
            title={t.descendantsTitle}
            childrenTitle={t.childrenTitle}
            disclaimer={t.descendantsDisclaimer}
            illustrativeOnly={t.illustrativeOnly}
          />

          <h2 className="results__factors-title">{t.resultsFactors}</h2>
          <ul className="results__factors">
            {result.softAdjustment.contributions
              .filter((c) => c.id !== 'base')
              .map((c) => (
                <li key={`${c.id}-${c.delta}`}>
                  <span>{contribLabel(c.label)}</span>
                  <span className={c.delta >= 0 ? 'delta-up' : 'delta-down'}>
                    {c.delta >= 0 ? '+' : ''}
                    {(c.delta * 100).toFixed(1)} pts
                  </span>
                </li>
              ))}
          </ul>

          {result.predictionScopeNote ? (
            <section className="results__scope-block">
              <h2 className="results__scope-heading">{t.resultsScopeHeading}</h2>
              <p className="results__scope">{result.predictionScopeNote}</p>
            </section>
          ) : null}

          <div className="results__disclaimer">{t.resultsDisclaimer}</div>

          <button
            type="button"
            className="results__retake"
            onClick={() => {
              clearDraft()
              resetAssessment()
              navigate('/assessment')
            }}
          >
            {t.retake}
          </button>
        </main>
      </div>
    </PageBackground>
  )
}
