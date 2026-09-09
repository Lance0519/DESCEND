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
  const [confirm, setConfirm] = useState('')
  const [displayName, setDisplayName] = useState('')
  const [termsAccepted, setTermsAccepted] = useState(false)
  const [healthConsent, setHealthConsent] = useState(false)
  const [ageConfirmed, setAgeConfirmed] = useState(false)
  const [error, setError] = useState('')
  const [info, setInfo] = useState('')
  const [busy, setBusy] = useState(false)

  const consentsReady = termsAccepted && healthConsent && ageConfirmed

  async function onSubmit(e: FormEvent) {
    e.preventDefault()
    setBusy(true)
    setError('')
    setInfo('')
    try {
      if (password !== confirm) {
        setError(t.passwordMismatch)
        return
      }
      if (!consentsReady) {
        setError(t.consentRequired)
        return
      }
      if (!configured) throw new Error('Supabase is not configured')
      const { needsEmailConfirm } = await signUp(email, password, displayName, {
        terms_accepted: true,
        health_consent_accepted: true,
        age_confirmed: true,
        consent_timestamp: new Date().toISOString(),
      })
      if (needsEmailConfirm) {
        setInfo(`${t.checkEmailTitle}. ${t.checkEmailText} ${t.checkEmailNext}`)
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
        <div className="auth-form-stack">
          <aside className="auth-form-emergency" role="note">
            <strong>{t.registerEmergencyTitle}</strong>
            {t.registerEmergencyText}
          </aside>
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
            {info ? (
              <>
                <p className="auth-form__ok">{info}</p>
                <Link to="/login" className="auth-form__submit-link">
                  {t.goToSignIn}
                </Link>
              </>
            ) : (
              <>
                <div className="auth-form__consents">
                  <label className="auth-form__check">
                    <input
                      type="checkbox"
                      required
                      checked={termsAccepted}
                      onChange={(e) => setTermsAccepted(e.target.checked)}
                    />
                    <span>
                      {t.consentTermsPrefix}
                      <Link to="/terms" target="_blank" rel="noopener noreferrer">
                        {t.consentTermsLink}
                      </Link>
                      {t.consentTermsMid}
                      <Link to="/privacy" target="_blank" rel="noopener noreferrer">
                        {t.consentPrivacyLink}
                      </Link>
                      {t.consentTermsSuffix}
                    </span>
                  </label>
                  <label className="auth-form__check">
                    <input
                      type="checkbox"
                      required
                      checked={healthConsent}
                      onChange={(e) => setHealthConsent(e.target.checked)}
                    />
                    <span>{t.consentHealth}</span>
                  </label>
                  <label className="auth-form__check">
                    <input
                      type="checkbox"
                      required
                      checked={ageConfirmed}
                      onChange={(e) => setAgeConfirmed(e.target.checked)}
                    />
                    <span>{t.consentAge}</span>
                  </label>
                </div>
                <p className="auth-form__medical">
                  <strong>{t.registerMedicalTitle}</strong> {t.registerMedicalText}
                </p>
                <button type="submit" disabled={busy || !consentsReady}>
                  {busy ? t.creatingAccount : t.registerSubmit}
                </button>
              </>
            )}
            <p className="auth-form__links">
              <Link to="/login">{t.accessSignIn}</Link>
              <Link to="/access">{t.accessGuest}</Link>
            </p>
          </form>
        </div>
      </div>
    </PageBackground>
  )
}
