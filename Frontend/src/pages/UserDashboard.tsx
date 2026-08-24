import { useCallback, useEffect, useState } from 'react'
import { Link, Navigate, useNavigate } from 'react-router-dom'
import { motion } from 'framer-motion'
import {
  AlertCircle,
  CalendarDays,
  ClipboardPlus,
  Gauge,
  Inbox,
  LayoutDashboard,
  LoaderCircle,
  LogOut,
  Shield,
  Stethoscope,
  UserRound,
} from 'lucide-react'
import { LanguageToggle } from '../components/LanguageToggle'
import { PageBackground } from '../components/PageBackground'
import { useAuth } from '../context/AuthContext'
import { useLanguage } from '../context/LanguageContext'
import { fetchAssessmentRecords } from '../api/assessmentRecords'
import type { AssessmentRecord } from '../types/assessmentRecord'
import type { Language } from '../types/assessment'
import type { RiskBand } from '../types/prediction'
import './UserDashboard.css'

function formatAssessmentDate(iso: string, language: Language): string {
  const date = new Date(iso)
  if (Number.isNaN(date.getTime())) return '—'
  return new Intl.DateTimeFormat(language === 'tl' ? 'fil-PH' : 'en-PH', {
    dateStyle: 'medium',
    timeStyle: 'short',
  }).format(date)
}

function formatRiskScore(score: number | null, language: Language): string {
  if (score == null) return '—'
  const percent = score >= 0 && score <= 1 ? score * 100 : score
  return `${new Intl.NumberFormat(language === 'tl' ? 'fil-PH' : 'en-PH', {
    maximumFractionDigits: 1,
  }).format(percent)}%`
}

function isRiskBand(value: string): value is RiskBand {
  return value === 'Low' || value === 'Moderate' || value === 'High'
}

function tierClass(tier: string | null): string {
  const normalized = (tier ?? '').toLowerCase()
  if (normalized.includes('low')) return 'user-dash__tier--low'
  if (normalized.includes('high')) return 'user-dash__tier--high'
  if (normalized.includes('mod')) return 'user-dash__tier--moderate'
  return 'user-dash__tier--neutral'
}

export function UserDashboard() {
  const { t, language } = useLanguage()
  const { user, signOut, loading: authLoading, isAdmin } = useAuth()
  const navigate = useNavigate()
  const [records, setRecords] = useState<AssessmentRecord[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  const loadRecords = useCallback(async () => {
    if (!user) return
    setLoading(true)
    setError('')
    try {
      const rows = await fetchAssessmentRecords(user.id)
      setRecords(rows)
    } catch {
      setRecords([])
      setError(t.dashboardError)
    } finally {
      setLoading(false)
    }
  }, [user, t.dashboardError])

  useEffect(() => {
    void loadRecords()
  }, [loadRecords])

  async function onSignOut() {
    await signOut()
    navigate('/', { replace: true })
  }

  if (authLoading) return null
  if (!user) return <Navigate to="/access" replace />

  const greetingName = user.displayName || user.email || t.brand

  return (
    <PageBackground>
      <div className="user-dash">
        <div className="user-dash__toolbar">
          <LanguageToggle />
          <div className="user-dash__toolbar-actions">
            <Link className="user-dash__text-link" to="/account">
              <UserRound size={18} aria-hidden />
              {t.accountNav}
            </Link>
            {isAdmin ? (
              <Link className="user-dash__text-link" to="/admin">
                <Shield size={18} aria-hidden />
                {t.adminNav}
              </Link>
            ) : null}
            <button type="button" className="user-dash__signout" onClick={() => void onSignOut()}>
              <LogOut size={18} aria-hidden />
              {t.signOut}
            </button>
          </div>
        </div>

        <motion.main
          className="user-dash__card"
          initial={{ opacity: 0, y: 14 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.35 }}
        >
          <header className="user-dash__header">
            <LayoutDashboard size={28} color="var(--color-primary)" aria-hidden />
            <div>
              <p className="user-dash__welcome">
                {t.dashboardWelcome}, {greetingName}
              </p>
              <h1>{t.dashboardTitle}</h1>
              <p className="user-dash__subtitle">{t.dashboardSubtitle}</p>
            </div>
          </header>

          {loading ? (
            <p className="user-dash__status" role="status">
              <LoaderCircle size={20} className="user-dash__spin" aria-hidden />
              {t.dashboardLoading}
            </p>
          ) : null}

          {!loading && error ? (
            <div className="user-dash__error">
              <p>
                <AlertCircle size={18} aria-hidden />
                {t.dashboardError}
              </p>
              <button type="button" className="user-dash__retry" onClick={() => void loadRecords()}>
                {t.dashboardRetry}
              </button>
            </div>
          ) : null}

          {!loading && !error && records.length === 0 ? (
            <p className="user-dash__empty">
              <Inbox size={22} aria-hidden />
              {t.dashboardEmpty}
            </p>
          ) : null}

          {!loading && !error && records.length > 0 ? (
            <ul className="user-dash__list">
              {records.map((record) => (
                <li key={record.id || record.created_at} className="user-dash__item">
                  <div className="user-dash__date">
                    <CalendarDays size={18} aria-hidden />
                    <div>
                      <span className="user-dash__label">{t.dashboardDateLabel}</span>
                      <strong>{formatAssessmentDate(record.created_at, language)}</strong>
                    </div>
                  </div>

                  {record.pre_diagnosed ? (
                    <div className="user-dash__mgmt">
                      <Stethoscope size={18} aria-hidden />
                      <span>{t.dashboardManagementMode}</span>
                    </div>
                  ) : (
                    <div className="user-dash__metrics">
                      <div>
                        <span className="user-dash__label">
                          <Gauge size={16} aria-hidden />
                          {t.dashboardRiskScore}
                        </span>
                        <strong>{formatRiskScore(record.risk_score, language)}</strong>
                      </div>
                      <div>
                        <span className="user-dash__label">
                          <Shield size={16} aria-hidden />
                          {t.dashboardRiskTier}
                        </span>
                        <span className={`user-dash__tier ${tierClass(record.risk_tier)}`}>
                          {record.risk_tier && isRiskBand(record.risk_tier)
                            ? t.bands[record.risk_tier]
                            : (record.risk_tier ?? '—')}
                        </span>
                      </div>
                    </div>
                  )}
                </li>
              ))}
            </ul>
          ) : null}

          <Link className="user-dash__cta" to="/assessment">
            <ClipboardPlus size={20} aria-hidden />
            {t.dashboardNewAssessment}
          </Link>
        </motion.main>
      </div>
    </PageBackground>
  )
}
