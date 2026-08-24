import { useState, type FormEvent } from 'react'
import { Link } from 'react-router-dom'
import { KeyRound } from 'lucide-react'
import { LanguageToggle } from '../components/LanguageToggle'
import { PageBackground } from '../components/PageBackground'
import { useAuth } from '../context/AuthContext'
import { useLanguage } from '../context/LanguageContext'
import './AuthForm.css'

export function ForgotPasswordPage() {
  const { t } = useLanguage()
  const { sendPasswordReset, configured } = useAuth()
  const [email, setEmail] = useState('')
  const [error, setError] = useState('')
  const [sent, setSent] = useState(false)
  const [busy, setBusy] = useState(false)

  async function onSubmit(e: FormEvent) {
    e.preventDefault()
    setBusy(true)
    setError('')
    try {
      if (!configured) throw new Error('Supabase is not configured. You can continue as guest.')
      await sendPasswordReset(email)
      setSent(true)
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
            <KeyRound size={22} aria-hidden /> {t.forgotTitle}
          </h1>
          <p className="auth-form__hint">{t.forgotHelp}</p>
          <label>
            {t.email}
            <input type="email" required value={email} onChange={(e) => setEmail(e.target.value)} />
          </label>
          {error ? <p className="auth-form__error">{error}</p> : null}
          {sent ? <p className="auth-form__ok">{t.forgotSent}</p> : null}
          <button type="submit" disabled={busy || sent}>
            {t.forgotSubmit}
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
