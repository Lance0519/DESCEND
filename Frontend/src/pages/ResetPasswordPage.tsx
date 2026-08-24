import { useState, type FormEvent } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { LockKeyhole } from 'lucide-react'
import { LanguageToggle } from '../components/LanguageToggle'
import { PageBackground } from '../components/PageBackground'
import { useAuth } from '../context/AuthContext'
import { useLanguage } from '../context/LanguageContext'
import './AuthForm.css'

export function ResetPasswordPage() {
  const { t } = useLanguage()
  const { updatePassword, configured } = useAuth()
  const navigate = useNavigate()
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)

  async function onSubmit(e: FormEvent) {
    e.preventDefault()
    setBusy(true)
    setError('')
    try {
      if (!configured) throw new Error('Supabase is not configured. You can continue as guest.')
      await updatePassword(password)
      navigate('/login', { replace: true })
    } catch (err) {
      setError(err instanceof Error ? err.message : t.errorRetry)
    } finally {
      setBusy(false)
    }
  }

  return (
    <PageBackground>
      <div className="auth-form-page">
        <LanguageToggle />
        <form className="auth-form" onSubmit={(e) => void onSubmit(e)}>
          <h1>
            <LockKeyhole size={22} aria-hidden /> {t.resetTitle}
          </h1>
          <label>
            {t.password}
            <input
              type="password"
              required
              minLength={6}
              value={password}
              onChange={(e) => setPassword(e.target.value)}
            />
          </label>
          {error ? <p className="auth-form__error">{error}</p> : null}
          <button type="submit" disabled={busy}>
            {t.resetSubmit}
          </button>
          <p className="auth-form__links">
            <Link to="/login">{t.accessSignIn}</Link>
          </p>
        </form>
      </div>
    </PageBackground>
  )
}
