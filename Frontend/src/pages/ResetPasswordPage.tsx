import { useState, type FormEvent } from 'react'
import { Link } from 'react-router-dom'
import { LockKeyhole } from 'lucide-react'
import { AuthNavBar } from '../components/AuthNavBar'
import { PageBackground } from '../components/PageBackground'
import { useAuth } from '../context/AuthContext'
import { useLanguage } from '../context/LanguageContext'
import { authErrorMessage } from '../lib/authErrors'
import './AuthForm.css'

export function ResetPasswordPage() {
  const { t } = useLanguage()
  const { updatePassword, configured } = useAuth()
  const [password, setPassword] = useState('')
  const [confirm, setConfirm] = useState('')
  const [error, setError] = useState('')
  const [done, setDone] = useState(false)
  const [busy, setBusy] = useState(false)

  async function onSubmit(e: FormEvent) {
    e.preventDefault()
    setError('')
    if (password !== confirm) {
      setError(t.passwordMismatch)
      return
    }
    setBusy(true)
    try {
      if (!configured) throw new Error('Supabase is not configured. You can continue as guest.')
      await updatePassword(password)
      setDone(true)
    } catch (err) {
      setError(authErrorMessage(err, t))
    } finally {
      setBusy(false)
    }
  }

  return (
    <PageBackground>
      <div className="auth-form-page">
        <AuthNavBar backTo="/login" />
        <form className="auth-form" onSubmit={(e) => void onSubmit(e)}>
          <h1>
            <LockKeyhole size={22} aria-hidden /> {t.resetTitle}
          </h1>
          {done ? (
            <>
              <p className="auth-form__ok">{t.passwordUpdated}</p>
              <Link to="/login" className="auth-form__submit-link">
                {t.goToSignIn}
              </Link>
            </>
          ) : (
            <>
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
              <label>
                {t.confirmPassword}
                <input
                  type="password"
                  required
                  minLength={6}
                  value={confirm}
                  onChange={(e) => setConfirm(e.target.value)}
                />
              </label>
              {error ? <p className="auth-form__error">{error}</p> : null}
              <button type="submit" disabled={busy}>
                {busy ? t.updatingPassword : t.resetSubmit}
              </button>
              <p className="auth-form__links">
                <Link to="/login">{t.accessSignIn}</Link>
              </p>
            </>
          )}
        </form>
      </div>
    </PageBackground>
  )
}
