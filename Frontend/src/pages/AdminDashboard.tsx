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
} from 'lucide-react'
import { LanguageToggle } from '../components/LanguageToggle'
import { PageBackground } from '../components/PageBackground'
import { fetchAdminOverview, updateAdminUser, type AdminOverview } from '../api/admin'
import { useAuth } from '../context/AuthContext'
import { useLanguage } from '../context/LanguageContext'
import './AdminDashboard.css'

export function AdminDashboard() {
  const { t } = useLanguage()
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

  async function sendReset(email: string | null) {
    if (!email) return
    setNotice('')
    try {
      await sendPasswordReset(email)
      setNotice(t.adminResetSent)
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
                          <button type="button" onClick={() => void sendReset(row.email)}>
                            {t.adminSendReset}
                          </button>
                        </div>
                      </li>
                    ))}
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
