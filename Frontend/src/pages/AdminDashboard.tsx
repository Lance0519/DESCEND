import { useCallback, useEffect, useMemo, useState, type FormEvent } from 'react'
import { Link, Navigate } from 'react-router-dom'
import {
  LayoutDashboard,
  LoaderCircle,
  Lock,
  Shield,
  ShieldCheck,
  Users,
  ClipboardList,
  UserRound,
  ScrollText,
} from 'lucide-react'
import { ConfirmDialog } from '../components/ConfirmDialog'
import { LanguageToggle } from '../components/LanguageToggle'
import { PageBackground } from '../components/PageBackground'
import { fetchAdminOverview, updateAdminUser, type AdminOverview, type AdminProfileRow } from '../api/admin'
import {
  fetchAuditLogs,
  purgeExpiredAuditLogs,
  writeAuditLog,
  type AuditLogRow,
} from '../api/audit'
import { useAuth } from '../context/AuthContext'
import { useLanguage } from '../context/LanguageContext'
import './AdminDashboard.css'

type PendingAction =
  | { kind: 'promote'; row: AdminProfileRow }
  | { kind: 'demote'; row: AdminProfileRow }
  | { kind: 'disable'; row: AdminProfileRow }
  | { kind: 'enable'; row: AdminProfileRow }
  | { kind: 'reset'; row: AdminProfileRow }

function formatAuditWhen(iso: string, locale: string) {
  const ms = Date.parse(iso)
  if (!Number.isFinite(ms)) return iso || '—'
  return new Intl.DateTimeFormat(locale, {
    dateStyle: 'medium',
    timeStyle: 'short',
  }).format(new Date(ms))
}

export function AdminDashboard() {
  const { t, language } = useLanguage()
  const { user, isAdmin, loading: authLoading, sendPasswordReset, reauthenticate } = useAuth()
  const [data, setData] = useState<AdminOverview | null>(null)
  const [search, setSearch] = useState('')
  const [error, setError] = useState('')
  const [notice, setNotice] = useState('')
  const [loading, setLoading] = useState(true)
  const [pending, setPending] = useState<PendingAction | null>(null)
  const [busyRowId, setBusyRowId] = useState<string | null>(null)

  const [auditLogs, setAuditLogs] = useState<AuditLogRow[] | null>(null)
  const [auditPassword, setAuditPassword] = useState('')
  const [auditBusy, setAuditBusy] = useState(false)
  const [auditError, setAuditError] = useState('')

  const load = useCallback(async () => {
    setLoading(true)
    setError('')
    try {
      setData(await fetchAdminOverview())
    } catch (err) {
      console.warn('admin overview failed', err)
      setError(t.adminForbidden)
      setData(null)
    } finally {
      setLoading(false)
    }
  }, [t.adminForbidden])

  useEffect(() => {
    if (isAdmin) void load()
  }, [isAdmin, load])

  const userById = useMemo(() => {
    const map = new Map<string, { email: string | null; display_name: string | null }>()
    for (const row of data?.users ?? []) {
      map.set(row.id, { email: row.email, display_name: row.display_name })
    }
    return map
  }, [data?.users])

  const filteredUsers = useMemo(() => {
    if (!data) return []
    const q = search.trim().toLowerCase()
    if (!q) return data.users
    return data.users.filter(
      (row) =>
        (row.email ?? '').toLowerCase().includes(q) ||
        (row.display_name ?? '').toLowerCase().includes(q),
    )
  }, [data, search])

  const locale = language === 'tl' ? 'fil-PH' : 'en-PH'

  function actionLabel(action: string) {
    switch (action) {
      case 'role_change':
        return t.adminAuditRoleChange
      case 'account_enable':
        return t.adminAuditAccountEnable
      case 'account_disable':
        return t.adminAuditAccountDisable
      case 'assessment_delete':
        return t.adminAuditAssessmentDelete
      case 'password_reset_sent':
        return t.adminAuditPasswordReset
      default:
        return action
    }
  }

  function personLabel(id: string | null | undefined) {
    if (!id) return t.adminUnknownUser
    const row = userById.get(id)
    return row?.email || row?.display_name || t.adminUnknownUser
  }

  function targetLabel(row: AuditLogRow) {
    const email = typeof row.metadata.email === 'string' ? row.metadata.email : null
    if (email) return email
    if (row.target_type === 'profile') return personLabel(row.target_id)
    if (row.target_id) return `${row.target_type} #${row.target_id}`
    return row.target_type
  }

  function detailLabel(row: AuditLogRow) {
    if (row.action === 'role_change') {
      const before = row.metadata.before
      const after = row.metadata.after
      if (before != null && after != null) return `${String(before)} → ${String(after)}`
    }
    if (row.action === 'assessment_delete') {
      const band = row.metadata.risk_band
      const label = row.metadata.label
      const parts = [
        typeof band === 'string' && band ? band : null,
        typeof label === 'string' && label ? label : null,
      ].filter(Boolean)
      return parts.length ? parts.join(' · ') : null
    }
    return null
  }

  if (authLoading) return null
  if (!user) return <Navigate to="/access" replace />
  if (!isAdmin) return <Navigate to="/dashboard" replace />

  const signsInWithGoogleOnly = user.provider === 'google'

  function confirmText(action: PendingAction) {
    switch (action.kind) {
      case 'promote':
        return t.adminConfirmPromote
      case 'demote':
        return t.adminConfirmDemote
      case 'disable':
        return t.adminConfirmDisable
      case 'enable':
        return t.adminConfirmEnable
      case 'reset':
        return t.adminConfirmReset
    }
  }

  function confirmLabel(action: PendingAction) {
    switch (action.kind) {
      case 'promote':
        return t.adminPromote
      case 'demote':
        return t.adminDemote
      case 'disable':
        return t.adminDisable
      case 'enable':
        return t.adminEnable
      case 'reset':
        return t.adminSendReset
    }
  }

  function requestAction(action: PendingAction) {
    setNotice('')
    setError('')
    if (action.kind === 'disable' && action.row.id === user!.id) {
      setError(t.adminCannotDisableSelf)
      return
    }
    setPending(action)
  }

  async function runPending() {
    if (!pending) return
    const { kind, row } = pending
    setPending(null)
    setNotice('')
    setBusyRowId(row.id)
    try {
      if (kind === 'promote' || kind === 'demote') {
        await updateAdminUser(row.id, { role: kind === 'promote' ? 'admin' : 'user' })
      } else if (kind === 'disable' || kind === 'enable') {
        await updateAdminUser(row.id, { is_active: kind === 'enable' })
      } else if (kind === 'reset') {
        if (!row.email) return
        await sendPasswordReset(row.email)
        await writeAuditLog({
          action: 'password_reset_sent',
          targetType: 'profile',
          targetId: row.id,
          metadata: { email: row.email },
        })
        setNotice(t.adminResetSent)
        await load()
        return
      }
      setNotice(
        row.email ? t.adminActionNamed.replace('{email}', row.email) : t.adminUpdated,
      )
      await load()
      if (auditLogs) setAuditLogs(await fetchAuditLogs(40))
    } catch (err) {
      console.warn('admin action failed', err)
      setError(t.errorRetry)
    } finally {
      setBusyRowId(null)
    }
  }

  async function unlockAudit(e: FormEvent) {
    e.preventDefault()
    setAuditBusy(true)
    setAuditError('')
    try {
      const ok = await reauthenticate(auditPassword)
      if (!ok) {
        setAuditError(signsInWithGoogleOnly ? t.adminAuditNoPassword : t.adminAuditWrongPassword)
        return
      }
      setAuditPassword('')
      await purgeExpiredAuditLogs()
      setAuditLogs(await fetchAuditLogs(40))
    } catch (err) {
      console.warn('audit unlock failed', err)
      setAuditError(t.errorRetry)
    } finally {
      setAuditBusy(false)
    }
  }

  const mix = data?.riskMix
  const mixTotal = mix ? mix.Low + mix.Moderate + mix.High + mix.Other : 0

  return (
    <PageBackground>
      <div className="admin-dash">
        <div className="admin-dash__toolbar">
          <LanguageToggle />
          <div className="admin-dash__toolbar-actions">
            <Link className="admin-dash__link" to="/dashboard">
              <LayoutDashboard size={18} aria-hidden /> {t.dashboardTitle}
            </Link>
            <Link className="admin-dash__link" to="/account">
              <UserRound size={18} aria-hidden /> {t.accountNav}
            </Link>
          </div>
        </div>

        <main className="admin-dash__card">
          <header className="admin-dash__header">
            <ShieldCheck size={28} color="var(--color-primary)" aria-hidden />
            <div>
              <h1>{t.adminTitle}</h1>
              <p>{t.adminSubtitle}</p>
            </div>
          </header>

          {loading ? (
            <p className="admin-dash__status">
              <LoaderCircle size={20} className="admin-dash__spin" aria-hidden />
              {t.dashboardLoading}
            </p>
          ) : null}
          {error ? <p className="admin-dash__error">{error}</p> : null}
          {notice ? <p className="admin-dash__ok">{notice}</p> : null}

          {data ? (
            <>
              <ul className="admin-dash__stats">
                <li>
                  <Users size={18} aria-hidden />
                  <strong>{data.userCount}</strong>
                  <span>{t.adminUsers}</span>
                </li>
                <li>
                  <ClipboardList size={18} aria-hidden />
                  <strong>{data.assessmentCount}</strong>
                  <span>{t.adminAssessments}</span>
                </li>
                <li>
                  <Shield size={18} aria-hidden />
                  <strong>{data.adminCount}</strong>
                  <span>{t.adminAdmins}</span>
                </li>
                <li>
                  <strong>{data.guestCount}</strong>
                  <span>{t.adminGuests}</span>
                </li>
                <li>
                  <strong>{data.savedCount}</strong>
                  <span>{t.adminSaved}</span>
                </li>
                <li>
                  <strong>{data.disabledCount}</strong>
                  <span>{t.adminDisabled}</span>
                </li>
              </ul>

              <section>
                <h2>{t.adminRiskMix}</h2>
                <div className="admin-dash__bars">
                  {(['Low', 'Moderate', 'High'] as const).map((band) => {
                    const value = mix?.[band] ?? 0
                    const pct = mixTotal ? Math.round((value / mixTotal) * 100) : 0
                    return (
                      <div key={band} className="admin-dash__bar">
                        <span>{t.bands[band]}</span>
                        <div className="admin-dash__bar-track">
                          <div className={`admin-dash__bar-fill admin-dash__bar-fill--${band.toLowerCase()}`} style={{ width: `${pct}%` }} />
                        </div>
                        <strong>{value}</strong>
                      </div>
                    )
                  })}
                </div>
              </section>

              <section>
                <h2>{t.adminUserMgmt}</h2>
                <label className="admin-dash__search">
                  {t.adminSearch}
                  <input value={search} onChange={(e) => setSearch(e.target.value)} />
                </label>
                {filteredUsers.length === 0 ? (
                  <p className="admin-dash__empty">{t.adminEmpty}</p>
                ) : (
                  <ul className="admin-dash__users">
                    {filteredUsers.map((row) => (
                      <li key={row.id} className={row.role === 'admin' ? 'is-admin' : undefined}>
                        <div>
                          <strong>
                            {row.display_name || row.email || t.adminUnknownUser}
                            {row.role === 'admin' ? (
                              <span className="admin-dash__badge">
                                <Shield size={13} aria-hidden /> {t.adminAdmins}
                              </span>
                            ) : null}
                            {row.id === user.id ? (
                              <span className="admin-dash__badge admin-dash__badge--you">{t.adminYou}</span>
                            ) : null}
                          </strong>
                          <p>{row.email}</p>
                          <p>
                            {t.adminRole}: {row.role === 'admin' ? t.adminRoleAdmin : t.adminRoleUser} ·{' '}
                            {row.is_active ? t.adminActive : t.adminInactive}
                          </p>
                        </div>
                        <div className="admin-dash__actions">
                          {row.role === 'admin' ? (
                            <button
                              type="button"
                              disabled={busyRowId === row.id}
                              onClick={() => requestAction({ kind: 'demote', row })}
                            >
                              {t.adminDemote}
                            </button>
                          ) : (
                            <button
                              type="button"
                              disabled={busyRowId === row.id}
                              onClick={() => requestAction({ kind: 'promote', row })}
                            >
                              {t.adminPromote}
                            </button>
                          )}
                          {row.is_active ? (
                            <button
                              type="button"
                              disabled={busyRowId === row.id}
                              onClick={() => requestAction({ kind: 'disable', row })}
                            >
                              {t.adminDisable}
                            </button>
                          ) : (
                            <button
                              type="button"
                              disabled={busyRowId === row.id}
                              onClick={() => requestAction({ kind: 'enable', row })}
                            >
                              {t.adminEnable}
                            </button>
                          )}
                          <button
                            type="button"
                            disabled={!row.email || busyRowId === row.id}
                            onClick={() => requestAction({ kind: 'reset', row })}
                          >
                            {t.adminSendReset}
                          </button>
                        </div>
                      </li>
                    ))}
                  </ul>
                )}
              </section>

              <section className="admin-dash__audit">
                <h2>
                  <ScrollText size={18} aria-hidden /> {t.adminAuditTitle}
                </h2>
                <p className="admin-dash__audit-retention">{t.adminAuditRetention}</p>

                {auditLogs === null ? (
                  <form className="admin-dash__audit-gate" onSubmit={(e) => void unlockAudit(e)}>
                    <p className="admin-dash__audit-locked">
                      <Lock size={16} aria-hidden /> {t.adminAuditLocked}
                    </p>
                    <label>
                      {t.password}
                      <input
                        type="password"
                        autoComplete="current-password"
                        value={auditPassword}
                        onChange={(e) => setAuditPassword(e.target.value)}
                        required
                      />
                    </label>
                    {auditError ? <p className="admin-dash__error">{auditError}</p> : null}
                    <button type="submit" disabled={auditBusy || !auditPassword}>
                      {auditBusy ? t.adminAuditUnlocking : t.adminAuditUnlock}
                    </button>
                  </form>
                ) : (
                  <>
                    <button
                      type="button"
                      className="admin-dash__audit-hide"
                      onClick={() => setAuditLogs(null)}
                    >
                      {t.adminAuditHide}
                    </button>
                    {auditLogs.length === 0 ? (
                      <p className="admin-dash__empty">{t.adminAuditEmpty}</p>
                    ) : (
                      <ul className="admin-dash__audit-list">
                        {auditLogs.map((row) => {
                          const detail = detailLabel(row)
                          return (
                            <li key={row.id}>
                              <div className="admin-dash__audit-main">
                                <strong>{actionLabel(row.action)}</strong>
                                <span>{targetLabel(row)}</span>
                                {detail ? <p>{detail}</p> : null}
                              </div>
                              <div className="admin-dash__audit-meta">
                                <span>
                                  {t.adminAuditActor}: {personLabel(row.actor_id)}
                                </span>
                                <time dateTime={row.created_at}>{formatAuditWhen(row.created_at, locale)}</time>
                              </div>
                            </li>
                          )
                        })}
                      </ul>
                    )}
                  </>
                )}
              </section>
            </>
          ) : null}
        </main>

        {pending ? (
          <ConfirmDialog
            title={t.adminConfirmTitle}
            text={
              pending.row.email
                ? `${confirmText(pending)} (${pending.row.email})`
                : confirmText(pending)
            }
            confirmLabel={confirmLabel(pending)}
            cancelLabel={t.confirmCancel}
            danger={pending.kind === 'disable' || pending.kind === 'demote'}
            onConfirm={() => void runPending()}
            onCancel={() => setPending(null)}
          />
        ) : null}
      </div>
    </PageBackground>
  )
}
