import { useEffect, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { PageBackground } from '../components/PageBackground'
import { useLanguage } from '../context/LanguageContext'
import { ensureUserProfile } from '../lib/ensureProfile'
import { getSupabase } from '../lib/supabaseClient'
import type { EmailOtpType } from '@supabase/supabase-js'

const OTP_TYPES: EmailOtpType[] = [
  'signup',
  'invite',
  'magiclink',
  'recovery',
  'email_change',
  'email',
]

function asOtpType(value: string | null): EmailOtpType | null {
  if (!value) return null
  return OTP_TYPES.includes(value as EmailOtpType) ? (value as EmailOtpType) : null
}

export function AuthCallbackPage() {
  const navigate = useNavigate()
  const { t } = useLanguage()
  const [message, setMessage] = useState(t.callbackSigningIn)

  useEffect(() => {
    const sb = getSupabase()
    if (!sb) {
      navigate('/access', { replace: true })
      return
    }

    let cancelled = false

    async function finish() {
      const url = new URL(window.location.href)
      const tokenHash = url.searchParams.get('token_hash')
      const otpType = asOtpType(url.searchParams.get('type'))
      const hasCode = url.searchParams.has('code') || url.hash.includes('access_token')

      if (tokenHash && otpType) {
        const { error } = await sb!.auth.verifyOtp({ token_hash: tokenHash, type: otpType })
        if (error && !cancelled) {
          setMessage(error.message || t.callbackFailed)
          window.setTimeout(() => navigate('/access', { replace: true }), 2500)
          return
        }
      } else if (hasCode) {
        const { error } = await sb!.auth.exchangeCodeForSession(window.location.href)
        if (error) {
          const { data } = await sb!.auth.getSession()
          if (!data.session) {
            if (!cancelled) {
              setMessage(error.message || t.callbackFailed)
              window.setTimeout(() => navigate('/access', { replace: true }), 2500)
            }
            return
          }
        }
      }

      const { data } = await sb!.auth.getSession()
      if (cancelled) return
      const session = data.session
      if (session?.access_token && session.user) {
        sessionStorage.setItem('descend-supabase-access-token', session.access_token)
        const meta = session.user.user_metadata ?? {}
        await ensureUserProfile({
          id: session.user.id,
          email: session.user.email,
          displayName: String(meta.full_name ?? meta.name ?? ''),
        })
        const next = otpType === 'recovery' ? '/reset-password' : '/dashboard'
        navigate(next, { replace: true })
        return
      }
      setMessage(t.callbackFailed)
      window.setTimeout(() => navigate('/access', { replace: true }), 2500)
    }

    void finish()
    return () => {
      cancelled = true
    }
  }, [navigate, t.callbackFailed, t.callbackSigningIn])

  return (
    <PageBackground>
      <div style={{ padding: '2rem', textAlign: 'center' }}>
        <p style={{ color: 'var(--color-text-muted)' }}>{message}</p>
        <Link to="/access">{t.callbackCancel}</Link>
      </div>
    </PageBackground>
  )
}
