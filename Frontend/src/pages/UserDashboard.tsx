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
  Pencil,
  Shield,
  Stethoscope,
  Trash2,
  UserRound,
} from 'lucide-react'
import { ConfirmDialog } from '../components/ConfirmDialog'
import { LanguageToggle } from '../components/LanguageToggle'
import { PageBackground } from '../components/PageBackground'
import { useAuth } from '../context/AuthContext'
import { useLanguage } from '../context/LanguageContext'
import {
  deleteAssessmentRecord,
  fetchAssessmentRecords,
  updateAssessmentRecord,
} from '../api/assessmentRecords'
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
  const [actionError, setActionError] = useState('')
  const [editingId, setEditingId] = useState<string | null>(null)
  const [draftLabel, setDraftLabel] = useState('')
  const [draftNotes, setDraftNotes] = useState('')
  const [savingId, setSavingId] = useState<string | null>(null)
  const [pendingDelete, setPendingDelete] = useState<AssessmentRecord | null>(null)
  const [expandedId, setExpandedId] = useState<string | null>(null)

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

  function beginEdit(record: AssessmentRecord) {
    setActionError('')
    setEditingId(record.id)
    setExpandedId(record.id)
    setDraftLabel(record.label ?? '')
    setDraftNotes(record.notes ?? '')
  }

  function cancelEdit() {
    setEditingId(null)
    setDraftLabel('')
    setDraftNotes('')
  }

  async function saveEdit(record: AssessmentRecord) {
    if (!user) return
    setSavingId(record.id)
    setActionError('')
    const ok = await updateAssessmentRecord(user.id, record, {
      label: draftLabel,
      notes: draftNotes,
    })
    setSavingId(null)
    if (!ok) {
      setActionError(t.dashboardActionFailed)
      return
    }
    setRecords((prev) =>
      prev.map((row) =>
        row.id === record.id
          ? {
              ...row,
              label: draftLabel.trim() || null,
              notes: draftNotes.trim() || null,
            }
          : row,
      ),
    )
    cancelEdit()
  }

  async function confirmDelete() {
    if (!user || !pendingDelete) return
    const target = pendingDelete
    setPendingDelete(null)
    setSavingId(target.id)
    setActionError('')
    const ok = await deleteAssessmentRecord(user.id, target)
    setSavingId(null)
    if (!ok) {
      setActionError(t.dashboardActionFailed)
      return
    }
    setRecords((prev) => prev.filter((row) => row.id !== target.id))
    if (editingId === target.id) cancelEdit()
    if (expandedId === target.id) setExpandedId(null)
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

          {actionError ? (
            <div className="user-dash__error" role="alert">
              <p>
                <AlertCircle size={18} aria-hidden />
                {actionError}
              </p>
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
              {records.map((record) => {
                const isEditing = editingId === record.id
                const isExpanded = expandedId === record.id || isEditing
                const canMutate = Boolean(record.sourceTable && record.sourceId)
                const title = record.label?.trim() || t.dashboardUntitled

                return (
                  <li key={record.id || record.created_at} className="user-dash__item">
                    <p className="user-dash__item-title">{title}</p>

                    <div className="user-dash__item-main">
                      <div className="user-dash__meta">
                        <span className="user-dash__label">
                          <CalendarDays size={16} aria-hidden />
                          {t.dashboardDateLabel}
                        </span>
                        <strong>{formatAssessmentDate(record.created_at, language)}</strong>
                      </div>

                      {record.pre_diagnosed ? (
                        <div className="user-dash__meta user-dash__meta--wide">
                          <span className="user-dash__label">
                            <Stethoscope size={16} aria-hidden />
                            {t.dashboardRiskTier}
                          </span>
                          <span className="user-dash__tier user-dash__tier--low">
                            {t.dashboardManagementMode}
                          </span>
                        </div>
                      ) : (
                        <>
                          <div className="user-dash__meta">
                            <span className="user-dash__label">
                              <Gauge size={16} aria-hidden />
                              {t.dashboardRiskScore}
                            </span>
                            <strong>{formatRiskScore(record.risk_score, language)}</strong>
                          </div>
                          <div className="user-dash__meta">
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
                        </>
                      )}
                    </div>

                    <div className="user-dash__item-actions">
                      <button
                        type="button"
                        className="user-dash__action"
                        onClick={() =>
                          setExpandedId((current) => (current === record.id ? null : record.id))
                        }
                      >
                        {t.dashboardView}
                      </button>
                      {canMutate ? (
                        <>
                          <button
                            type="button"
                            className="user-dash__action"
                            onClick={() => beginEdit(record)}
                            disabled={savingId === record.id}
                          >
                            <Pencil size={16} aria-hidden />
                            {t.dashboardEdit}
                          </button>
                          <button
                            type="button"
                            className="user-dash__action user-dash__action--danger"
                            onClick={() => setPendingDelete(record)}
                            disabled={savingId === record.id}
                          >
                            <Trash2 size={16} aria-hidden />
                            {t.dashboardDelete}
                          </button>
                        </>
                      ) : null}
                    </div>

                    {isExpanded ? (
                      <div className="user-dash__detail">
                        {isEditing ? (
                          <>
                            <label className="user-dash__field">
                              <span>{t.dashboardLabel}</span>
                              <input
                                type="text"
                                value={draftLabel}
                                onChange={(e) => setDraftLabel(e.target.value)}
                                placeholder={t.dashboardLabelPlaceholder}
                                maxLength={120}
                              />
                            </label>
                            <label className="user-dash__field">
                              <span>{t.dashboardNotes}</span>
                              <textarea
                                value={draftNotes}
                                onChange={(e) => setDraftNotes(e.target.value)}
                                placeholder={t.dashboardNotesPlaceholder}
                                rows={3}
                                maxLength={1000}
                              />
                            </label>
                            <div className="user-dash__edit-actions">
                              <button
                                type="button"
                                className="user-dash__retry"
                                disabled={savingId === record.id}
                                onClick={() => void saveEdit(record)}
                              >
                                {savingId === record.id ? t.dashboardLoading : t.dashboardSaveEdit}
                              </button>
                              <button
                                type="button"
                                className="user-dash__action"
                                disabled={savingId === record.id}
                                onClick={cancelEdit}
                              >
                                {t.dashboardCancelEdit}
                              </button>
                            </div>
                          </>
                        ) : (
                          <>
                            <p>
                              <span className="user-dash__label">{t.dashboardLabel}</span>
                              <strong> {title}</strong>
                            </p>
                            <p className="user-dash__notes">
                              <span className="user-dash__label">{t.dashboardNotes}</span>
                              <span>{record.notes?.trim() || '—'}</span>
                            </p>
                          </>
                        )}
                      </div>
                    ) : null}
                  </li>
                )
              })}
            </ul>
          ) : null}

          <p className="user-dash__create-hint">{t.dashboardCreateHint}</p>
          <Link className="user-dash__cta" to="/assessment">
            <ClipboardPlus size={20} aria-hidden />
            {t.dashboardNewAssessment}
          </Link>
        </motion.main>
      </div>

      {pendingDelete ? (
        <ConfirmDialog
          title={t.dashboardDeleteTitle}
          text={t.dashboardDeleteText}
          confirmLabel={t.dashboardDeleteConfirm}
          cancelLabel={t.dashboardCancelEdit}
          danger
          onCancel={() => setPendingDelete(null)}
          onConfirm={() => void confirmDelete()}
        />
      ) : null}
    </PageBackground>
  )
}
