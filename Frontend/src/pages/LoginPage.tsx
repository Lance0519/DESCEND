import { useState, type FormEvent } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { LogIn } from 'lucide-react'
import { AuthNavBar } from '../components/AuthNavBar'
import { GoogleSignInButton, isGoogleSignInEnabled } from '../components/GoogleSignInButton'
import { PageBackground } from '../components/PageBackground'
import { useAuth } from '../context/AuthContext'
import { useLanguage } from '../context/LanguageContext'
import { authErrorMessage } from '../lib/authErrors'
import './AuthForm.css'

export function LoginPage() {
  const { t } = useLanguage()
  const { signIn, configured } = useAuth()
  const navigate = useNavigate()
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)
  const showGoogle = configured && isGoogleSignInEnabled()

  async function onSubmit(e: FormEvent) {
    e.preventDefault()
    setBusy(true)
    setError('')
    try {
      if (!configured) throw new Error('Supabase is not configured. You can continue as guest.')
      await signIn(email, password)
      navigate('/dashboard')
    } catch (err) {
      setError(authErrorMessage(err, t))
    } finally {
      setBusy(false)
    }
  }

  return (
    <PageBackground>
      <div className="auth-form-page">
        <AuthNavBar backTo="/access" />
        <form className="auth-form" onSubmit={(e) => void onSubmit(e)}>
          <h1>
            <LogIn size={22} aria-hidden /> {t.accessSignIn}
          </h1>
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
            {busy ? t.signingIn : t.signInSubmit}
          </button>
          {showGoogle ? (
            <>
              <div className="auth-form__divider">
                <span>{t.authDividerOr}</span>
              </div>
              <GoogleSignInButton />
            </>
          ) : null}
          <p className="auth-form__links">
            <Link to="/forgot-password">{t.forgotPassword}</Link>
            <Link to="/register">{t.accessRegister}</Link>
          </p>
        </form>
      </div>
    </PageBackground>
  )
}
