import { useCallback, useEffect, useMemo, useState } from 'react'
import { Link, Navigate } from 'react-router-dom'
import {
  LayoutDashboard,
  LoaderCircle,
  Shield,
  ShieldCheck,
  Users,
  ClipboardList,
  UserRound,
  ScrollText,
} from 'lucide-react'
import { LanguageToggle } from '../components/LanguageToggle'
import { PageBackground } from '../components/PageBackground'
import { fetchAdminOverview, updateAdminUser, type AdminOverview } from '../api/admin'
import { writeAuditLog, type AuditLogRow } from '../api/audit'
import { useAuth } from '../context/AuthContext'
import { useLanguage } from '../context/LanguageContext'
import './AdminDashboard.css'

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
  const { user, isAdmin, loading: authLoading, sendPasswordReset } = useAuth()
  const [data, setData] = useState<AdminOverview | null>(null)
  const [search, setSearch] = useState('')
  const [error, setError] = useState('')
  const [notice, setNotice] = useState('')
  const [loading, setLoading] = useState(true)

  const load = useCallback(async () => {
    setLoading(true)
    setError('')
    try {
      setData(await fetchAdminOverview())
    } catch (err) {
      setError(err instanceof Error ? err.message : t.adminForbidden)
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
    if (!id) return '—'
    const row = userById.get(id)
    return row?.email || row?.display_name || id.slice(0, 8)
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

  async function changeRole(id: string, role: 'user' | 'admin') {
    setNotice('')
    try {
      await updateAdminUser(id, { role })
      setNotice(t.adminUpdated)
      await load()
    } catch (err) {
      setError(err instanceof Error ? err.message : t.errorRetry)
    }
  }

  async function changeActive(id: string, isActive: boolean) {
    setNotice('')
    try {
      await updateAdminUser(id, { is_active: isActive })
      setNotice(t.adminUpdated)
      await load()
    } catch (err) {
      setError(err instanceof Error ? err.message : t.errorRetry)
    }
  }

  async function sendReset(email: string | null, userId: string) {
    if (!email) return
    setNotice('')
    try {
      await sendPasswordReset(email)
      await writeAuditLog({
        action: 'password_reset_sent',
        targetType: 'profile',
        targetId: userId,
        metadata: { email },
      })
      setNotice(t.adminResetSent)
      await load()
    } catch (err) {
      setError(err instanceof Error ? err.message : t.errorRetry)
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
                      <li key={row.id}>
                        <div>
                          <strong>{row.display_name || row.email || row.id}</strong>
                          <p>{row.email}</p>
                          <p>
                            {t.adminRole}: {row.role} · {row.is_active ? t.adminActive : t.adminInactive}
                          </p>
                        </div>
                        <div className="admin-dash__actions">
                          {row.role === 'admin' ? (
                            <button type="button" onClick={() => void changeRole(row.id, 'user')}>
                              {t.adminDemote}
                            </button>
                          ) : (
                            <button type="button" onClick={() => void changeRole(row.id, 'admin')}>
                              {t.adminPromote}
                            </button>
                          )}
                          {row.is_active ? (
                            <button type="button" onClick={() => void changeActive(row.id, false)}>
                              {t.adminDisable}
                            </button>
                          ) : (
                            <button type="button" onClick={() => void changeActive(row.id, true)}>
                              {t.adminEnable}
                            </button>
                          )}
                          <button type="button" onClick={() => void sendReset(row.email, row.id)}>
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
                {data.auditLogs.length === 0 ? (
                  <p className="admin-dash__empty">{t.adminAuditEmpty}</p>
                ) : (
                  <ul className="admin-dash__audit-list">
                    {data.auditLogs.map((row) => {
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
              </section>
            </>
          ) : null}
        </main>
      </div>
    </PageBackground>
  )
}
