import { useState, type FormEvent } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { LanguageToggle } from '../components/LanguageToggle'
import { PageBackground } from '../components/PageBackground'
import { useAuth } from '../context/AuthContext'
import { useLanguage } from '../context/LanguageContext'
import './AuthForm.css'

export function RegisterPage() {
  const { t } = useLanguage()
  const { signUp, configured } = useAuth()
  const navigate = useNavigate()
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [displayName, setDisplayName] = useState('')
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)

  async function onSubmit(e: FormEvent) {
    e.preventDefault()
    setBusy(true)
    setError('')
    try {
      if (!configured) throw new Error('Supabase is not configured. You can continue as guest.')
      await signUp(email, password, displayName)
      navigate('/assessment')
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
          <h1>{t.accessRegister}</h1>
          <label>
            {t.displayName}
            <input value={displayName} onChange={(e) => setDisplayName(e.target.value)} />
          </label>
          <label>
            {t.email}
            <input type="email" required value={email} onChange={(e) => setEmail(e.target.value)} />
          </label>
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
            {t.registerSubmit}
          </button>
          <p className="auth-form__links">
            <Link to="/login">{t.accessSignIn}</Link>
            <Link to="/access">{t.accessGuest}</Link>
          </p>
        </form>
      </div>
    </PageBackground>
  )
}
