import { useCallback, useEffect, useRef } from 'react'
import { Activity, Droplets, HeartPulse, Printer, Scale, Users } from 'lucide-react'
import { Link, Navigate, useNavigate } from 'react-router-dom'
import { ConfirmDialog } from '../components/ConfirmDialog'
import { LanguageToggle } from '../components/LanguageToggle'
import { PageBackground } from '../components/PageBackground'
import { useAssessment } from '../context/AssessmentContext'
import { useAuth } from '../context/AuthContext'
import { useLanguage } from '../context/LanguageContext'
import { DescendantProjection } from '../features/results/DescendantProjection'
import { PreventionPanel } from '../features/results/PreventionPanel'
import { FamilyPedigreePanel } from '../features/results/FamilyPedigreePanel'
import { preventionBmi } from '../data/preventionTips'
import { useCloudSave } from '../hooks/useCloudSave'
import { clearDraft } from '../lib/draftStorage'
import './ResultsPage.css'

export function ResultsPage() {
  const { t, language } = useLanguage()
  const { result, answers, resetAssessment } = useAssessment()
  const { user, loading: authLoading } = useAuth()
  const navigate = useNavigate()
  const { status, save, begin, accept, decline } = useCloudSave()
  const saveStarted = useRef(false)

  const persist = useCallback(async () => {
    if (!user || !result) return
    await save({
      userId: user.id,
      riskScore: result.percentage,
      riskTier: result.riskBand,
      preDiagnosed: false,
      answers,
      result,
    })
  }, [user, result, answers, save])

  useEffect(() => {
    if (authLoading) return
    if (!result || answers.diagnosedT2dm === 'yes') return
    if (saveStarted.current) return
    saveStarted.current = true
    const mode = begin(Boolean(user))
    if (mode === 'ready') void persist()
  }, [authLoading, result, answers.diagnosedT2dm, user, begin, persist])

  if (answers.diagnosedT2dm === 'yes') return <Navigate to="/management" replace />
  if (!result) return <Navigate to="/assessment" replace />

  const bandClass =
    result.riskBand === 'Low'
      ? 'results__band--low'
      : result.riskBand === 'Moderate'
        ? 'results__band--moderate'
        : 'results__band--high'

  const contribLabel = (key: string) => (t.contrib as Record<string, string>)[key] ?? key

  const printedAt = new Intl.DateTimeFormat(language === 'tl' ? 'fil-PH' : 'en-PH', {
    dateStyle: 'medium',
    timeStyle: 'short',
  }).format(new Date())

  function onPrint() {
    const previous = document.title
    document.title = t.printDocumentTitle
    window.print()
    document.title = previous
  }

  return (
    <PageBackground>
      <div className="results">
        <div className="results__toolbar results__no-print">
          <LanguageToggle />
          {user ? (
            <>
              <Link to="/dashboard" className="results__account">
                {t.dashboardTitle}
              </Link>
              <Link to="/account" className="results__account">
                {t.accountNav}
              </Link>
            </>
          ) : null}
        </div>
        <main className="results__card">
          <h1>{t.resultsTitle}</h1>
          <p className="results__print-meta">
            {t.printDateLabel}: {printedAt}
          </p>
          <p
            className={`results__source results__no-print ${
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

          <div className="results__icons results__no-print" aria-hidden>
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

          <div className="results__no-print">
            <FamilyPedigreePanel result={result} title={t.pedigreeTitle} />

            <DescendantProjection
              result={result}
              title={t.descendantsTitle}
              childrenTitle={t.childrenTitle}
              disclaimer={t.descendantsDisclaimer}
              illustrativeOnly={t.illustrativeOnly}
            />
          </div>

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

          <PreventionPanel answers={answers} bmi={preventionBmi(answers, result.bmi)} />

          {result.predictionScopeNote ? (
            <section className="results__scope-block results__no-print">
              <h2 className="results__scope-heading">{t.resultsScopeHeading}</h2>
              <p className="results__scope">{result.predictionScopeNote}</p>
            </section>
          ) : null}

          <div className="results__disclaimer">{t.resultsDisclaimer}</div>

          {status === 'saving' ? (
            <p className="results__save results__no-print" role="status">
              {t.savingResult}
            </p>
          ) : null}
          {status === 'saved' ? (
            <p className="results__save results__save--ok results__no-print" role="status">
              {t.saveSuccess}
            </p>
          ) : null}
          {status === 'failed' ? (
            <div className="results__save results__save--fail results__no-print" role="alert">
              <p>{t.saveFailed}</p>
              <button type="button" className="results__text-btn" onClick={() => void persist()}>
                {t.saveRetry}
              </button>
            </div>
          ) : null}
          {status === 'guest' ? (
            <p className="results__save results__no-print">
              <Link to="/register">{t.saveGuestCta}</Link>
            </p>
          ) : null}

          <div className="results__actions results__no-print">
            {status === 'skipped' ? (
              <button
                type="button"
                className="results__retake"
                onClick={() => {
                  accept()
                  void persist()
                }}
              >
                {t.saveConsentYes}
              </button>
            ) : null}
            <button type="button" className="results__secondary" onClick={onPrint}>
              <Printer size={18} aria-hidden />
              {t.printResult}
            </button>
            <button
              type="button"
              className={status === 'skipped' ? 'results__secondary' : 'results__retake'}
              onClick={() => {
                clearDraft()
                resetAssessment()
                navigate('/assessment')
              }}
            >
              {t.retake}
            </button>
          </div>
        </main>
      </div>
      {status === 'consent' ? (
        <ConfirmDialog
          title={t.saveConsentTitle}
          text={t.saveConsentText}
          confirmLabel={t.saveConsentYes}
          cancelLabel={t.saveConsentNo}
          onCancel={decline}
          onConfirm={() => {
            accept()
            void persist()
          }}
        />
      ) : null}
    </PageBackground>
  )
}
