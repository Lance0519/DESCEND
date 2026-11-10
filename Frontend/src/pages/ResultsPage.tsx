import { useCallback, useEffect, useRef, useState } from 'react'
import {
  Activity,
  Droplets,
  HeartPulse,
  Home,
  LogIn,
  Printer,
  Scale,
  ShieldCheck,
  UserPlus,
  Users,
} from 'lucide-react'
import { Link, Navigate, useNavigate } from 'react-router-dom'
import { ConfirmDialog } from '../components/ConfirmDialog'
import { ContactSupport } from '../components/ContactSupport'
import { PageBackground } from '../components/PageBackground'
import { useAssessment } from '../context/AssessmentContext'
import { useAuth } from '../context/AuthContext'
import { useLanguage } from '../context/LanguageContext'
import { DescendantProjection } from '../features/results/DescendantProjection'
import { PreventionPanel } from '../features/results/PreventionPanel'
import { FamilyPedigreePanel } from '../features/results/FamilyPedigreePanel'
import { preventionBmi } from '../data/preventionTips'
import {
  cachePendingGuestResult,
  clearPendingGuestResult,
  getPendingGuestResult,
  useCloudSave,
} from '../hooks/useCloudSave'
import { clearDraft } from '../lib/draftStorage'
import { setCloudSaveConsent } from '../lib/cloudSaveConsent'
import { RiskBadge } from '../components/ui/RiskBadge'
import { resolveRiskLevel } from '../utils/risk'
import { AppNavBar } from '../components/ui/AppNavBar'
import './ResultsPage.css'

export function ResultsPage() {
  const { t, language } = useLanguage()
  const { result, answers, setResult, setAnswersBulk, resetAssessment } = useAssessment()
  const { user, loading: authLoading } = useAuth()
  const navigate = useNavigate()
  const { status, save, begin, accept, decline } = useCloudSave()
  const saveStarted = useRef(false)

  const [cachedPending] = useState(() => getPendingGuestResult())

  useEffect(() => {
    if (!result && cachedPending) {
      setResult(cachedPending.result)
      setAnswersBulk(cachedPending.answers)
    }
  }, [result, cachedPending, setResult, setAnswersBulk])

  const activeResult = result ?? cachedPending?.result
  const activeAnswers =
    answers && Object.keys(answers).length > 0
      ? answers
      : (cachedPending?.answers ?? answers)

  // Cache results for guest so they can sign in or register without losing data
  useEffect(() => {
    if (activeResult && !user) {
      cachePendingGuestResult(
        activeAnswers,
        activeResult,
        activeResult.percentage,
        activeResult.riskBand,
      )
    }
  }, [activeResult, activeAnswers, user])

  const persist = useCallback(async () => {
    if (!user || !activeResult) return
    await save({
      userId: user.id,
      riskScore: activeResult.percentage,
      riskTier: activeResult.riskBand,
      preDiagnosed: false,
      answers: activeAnswers,
      result: activeResult,
    })
    clearPendingGuestResult()
  }, [user, activeResult, activeAnswers, save])

  useEffect(() => {
    if (authLoading) return
    if (!activeResult || activeAnswers.diagnosedT2dm === 'yes') return
    if (saveStarted.current) return
    saveStarted.current = true
    const mode = begin(Boolean(user))
    if (mode === 'ready') void persist()
  }, [authLoading, activeResult, activeAnswers.diagnosedT2dm, user, begin, persist])

  if (activeAnswers.diagnosedT2dm === 'yes') return <Navigate to="/management" replace />
  if (!activeResult) return <Navigate to="/assessment" replace />

  const resolvedRiskLevel = resolveRiskLevel(activeResult.riskBand)
  const riskLevel =
    resolvedRiskLevel !== 'neutral'
      ? resolvedRiskLevel
      : activeResult.percentage < 34
        ? 'low'
        : activeResult.percentage < 67
          ? 'moderate'
          : 'high'

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
        <AppNavBar
          className="results__no-print"
          showHome={true}
          right={
            user ? (
              <>
                <Link to="/dashboard" className="app-nav__link">
                  {t.dashboardTitle}
                </Link>
                <Link to="/account" className="app-nav__link">
                  {t.accountNav}
                </Link>
              </>
            ) : null
          }
        />
        <main className="results__card">
          <h1>{t.resultsTitle}</h1>
          <p className="results__print-meta">
            {t.printDateLabel}: {printedAt}
          </p>
          <p
            className={`results__source results__no-print ${
              activeResult.source === 'api' ? 'results__source--api' : 'results__source--mock'
            }`}
          >
            {activeResult.source === 'api' ? t.resultsModelBadge : t.resultsMockBadge}
          </p>
          <p className="results__percent-label">{t.resultsPercent}</p>
          <p className={`results__percent results__percent--${riskLevel}`}>{activeResult.percentage}%</p>
          <div style={{ marginBottom: '1.25rem' }}>
            <RiskBadge band={activeResult.riskBand} size="lg">
              {t.resultsBand}: {t.bands[activeResult.riskBand]}
            </RiskBadge>
          </div>

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
            {(activeResult.softAdjustment.blood !== 0 ||
              activeResult.softAdjustment.contributions.some((c) => c.group === 'blood')) && (
              <span>
                <Droplets size={22} />
              </span>
            )}
          </div>

          {activeResult.bmi != null ? (
            <p className="results__bmi">
              {t.bmiLabel}: {activeResult.bmi.toFixed(1)}
            </p>
          ) : null}

          <div className="results__no-print">
            <FamilyPedigreePanel result={activeResult} title={t.pedigreeTitle} />

            <DescendantProjection
              result={activeResult}
              title={t.descendantsTitle}
              childrenTitle={t.childrenTitle}
              disclaimer={t.descendantsDisclaimer}
              illustrativeOnly={t.illustrativeOnly}
            />
          </div>

          <h2 className="results__factors-title">{t.resultsFactors}</h2>
          <ul className="results__factors">
            {activeResult.softAdjustment.contributions
              .filter((c) => c.id !== 'base')
              .map((c) => (
                <li key={`${c.id}-${c.delta}`}>
                  <span>{contribLabel(c.label)}</span>
                  <span className={c.delta >= 0 ? 'delta-up' : 'delta-down'}>
                    {c.delta >= 0 ? '+' : ''}
                    {(c.delta * 100).toFixed(1)} {t.pointsUnit}
                  </span>
                </li>
              ))}
          </ul>

          <PreventionPanel answers={activeAnswers} bmi={preventionBmi(activeAnswers, activeResult.bmi)} />

          {activeResult.predictionScopeNote ? (
            <section className="results__scope-block results__no-print">
              <h2 className="results__scope-heading">{t.resultsScopeHeading}</h2>
              <p className="results__scope">{activeResult.predictionScopeNote}</p>
            </section>
          ) : null}

          <div className="results__disclaimer">{t.resultsDisclaimer}</div>
          <div className="results__contact results__no-print">
            <ContactSupport />
          </div>

          {status === 'saving' ? (
            <p className="results__save results__no-print" role="status">
              {t.savingResult}
            </p>
          ) : null}
          {status === 'saved' ? (
            <p className="results__save results__save--ok results__no-print" role="status">
              {t.guestSaveSuccess || t.saveSuccess}
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
            <div className="results__guest-card results__no-print">
              <div className="results__guest-icon" aria-hidden>
                <ShieldCheck size={28} />
              </div>
              <div className="results__guest-info">
                <h3>{t.guestSaveTitle}</h3>
                <p>{t.guestSaveDesc}</p>
              </div>
              <div className="results__guest-actions">
                <Link
                  to="/login?redirect=/results"
                  className="results__guest-btn results__guest-btn--primary"
                  onClick={() => {
                    setCloudSaveConsent('yes')
                    cachePendingGuestResult(
                      activeAnswers,
                      activeResult,
                      activeResult.percentage,
                      activeResult.riskBand,
                    )
                  }}
                >
                  <LogIn size={18} aria-hidden />
                  {t.guestSaveLogin}
                </Link>
                <Link
                  to="/register?redirect=/results"
                  className="results__guest-btn results__guest-btn--secondary"
                  onClick={() => {
                    setCloudSaveConsent('yes')
                    cachePendingGuestResult(
                      activeAnswers,
                      activeResult,
                      activeResult.percentage,
                      activeResult.riskBand,
                    )
                  }}
                >
                  <UserPlus size={18} aria-hidden />
                  {t.guestSaveRegister}
                </Link>
              </div>
            </div>
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
            <Link to="/" className="results__secondary">
              <Home size={18} aria-hidden />
              {t.navHome}
            </Link>
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
