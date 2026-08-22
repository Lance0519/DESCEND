import { useEffect, useState } from 'react'
import { Link, Navigate } from 'react-router-dom'
import { LanguageToggle } from '../components/LanguageToggle'
import { PageBackground } from '../components/PageBackground'
import { useAuth } from '../context/AuthContext'
import { useLanguage } from '../context/LanguageContext'
import { fetchHistory } from '../api/client'
import './HistoryPage.css'

interface HistoryItem {
  id: string | number
  created_at?: string
  percentage?: number
  risk_band?: string
  result?: { percentage?: number; riskBand?: string }
}

export function HistoryPage() {
  const { t } = useLanguage()
  const { user, loading } = useAuth()
  const [items, setItems] = useState<HistoryItem[]>([])
  const [error, setError] = useState('')

  useEffect(() => {
    if (!user) return
    void fetchHistory()
      .then((data) => setItems((data.items as HistoryItem[]) ?? []))
      .catch(() => {
        // Local fallback: show empty with message when API unavailable
        setError('')
        setItems([])
      })
  }, [user])

  if (loading) return null
  if (!user) return <Navigate to="/access" replace />

  return (
    <PageBackground>
      <div className="history-page">
        <div className="history-page__toolbar">
          <LanguageToggle />
          <Link to="/account">{t.accountNav}</Link>
        </div>
        <main className="history-page__card">
          <h1>{t.historyTitle}</h1>
          {error ? <p>{error}</p> : null}
          {items.length === 0 ? (
            <p className="history-page__empty">{t.historyEmpty}</p>
          ) : (
            <ul className="history-page__list">
              {items.map((item) => {
                const pct = item.percentage ?? item.result?.percentage
                const band = item.risk_band ?? item.result?.riskBand
                return (
                  <li key={String(item.id)}>
                    <span>{item.created_at ? new Date(item.created_at).toLocaleString() : '—'}</span>
                    <strong>{pct != null ? `${pct}%` : '—'}</strong>
                    <span>{band ?? '—'}</span>
                  </li>
                )
              })}
            </ul>
          )}
          <Link className="history-page__cta" to="/assessment">
            {t.retake}
          </Link>
        </main>
      </div>
    </PageBackground>
  )
}
