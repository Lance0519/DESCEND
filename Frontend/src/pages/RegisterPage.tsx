import { useState, type FormEvent } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { UserPlus } from 'lucide-react'
import { AuthNavBar } from '../components/AuthNavBar'
import { PageBackground } from '../components/PageBackground'
import { useAuth } from '../context/AuthContext'
import { useLanguage } from '../context/LanguageContext'
import { authErrorMessage } from '../lib/authErrors'
import './AuthForm.css'

export function RegisterPage() {
  const { t } = useLanguage()
  const { signUp, configured } = useAuth()
  const navigate = useNavigate()
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [displayName, setDisplayName] = useState('')
  const [error, setError] = useState('')
  const [info, setInfo] = useState('')
  const [busy, setBusy] = useState(false)

  async function onSubmit(e: FormEvent) {
    e.preventDefault()
    setBusy(true)
    setError('')
    setInfo('')
    try {
      if (!configured) throw new Error('Supabase is not configured. You can continue as guest.')
      const { needsEmailConfirm } = await signUp(email, password, displayName)
      if (needsEmailConfirm) {
        setInfo(`${t.checkEmailTitle}. ${t.checkEmailText}`)
        return
      }
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
            <UserPlus size={22} aria-hidden /> {t.accessRegister}
          </h1>
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
          {info ? <p className="auth-form__ok">{info}</p> : null}
          <button type="submit" disabled={busy}>
            {busy ? t.creatingAccount : t.registerSubmit}
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
