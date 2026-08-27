import { useEffect, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { PageBackground } from '../components/PageBackground'
import { useLanguage } from '../context/LanguageContext'
import { ensureUserProfile } from '../lib/ensureProfile'
import { getSupabase } from '../lib/supabaseClient'
import type { EmailOtpType } from '@supabase/supabase-js'
import './AuthCallbackPage.css'

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

/** Providers return failures either as query params or in the URL fragment. */
function readProviderError(url: URL): string | null {
  const hash = new URLSearchParams(url.hash.replace(/^#/, ''))
  const description =
    url.searchParams.get('error_description') ?? hash.get('error_description')
  const code =
    url.searchParams.get('error_code') ??
    hash.get('error_code') ??
    url.searchParams.get('error') ??
    hash.get('error')
  if (!description && !code) return null
  return [description, code ? `(${code})` : null].filter(Boolean).join(' ')
}

export function AuthCallbackPage() {
  const navigate = useNavigate()
  const { t } = useLanguage()
  const [message, setMessage] = useState(t.callbackSigningIn)
  const [detail, setDetail] = useState('')

  useEffect(() => {
    const sb = getSupabase()
    if (!sb) {
      navigate('/access', { replace: true })
      return
    }

    let cancelled = false

    function fail(reason: string, detailText?: string) {
      if (cancelled) return
      setMessage(reason)
      setDetail(detailText ?? '')
    }

    async function finish() {
      const url = new URL(window.location.href)
      const providerError = readProviderError(url)
      if (providerError) {
        fail(t.callbackFailed, providerError)
        return
      }

      const tokenHash = url.searchParams.get('token_hash')
      const otpType = asOtpType(url.searchParams.get('type'))
      const hasCode = url.searchParams.has('code') || url.hash.includes('access_token')

      if (tokenHash && otpType) {
        const { error } = await sb!.auth.verifyOtp({ token_hash: tokenHash, type: otpType })
        if (error) {
          fail(t.callbackFailed, error.message)
          return
        }
      } else if (hasCode) {
        const { error } = await sb!.auth.exchangeCodeForSession(window.location.href)
        if (error) {
          const { data } = await sb!.auth.getSession()
          if (!data.session) {
            fail(t.callbackFailed, error.message)
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

      fail(t.callbackFailed, hasCode ? t.callbackNoSession : t.callbackNoCode)
    }

    void finish()
    return () => {
      cancelled = true
    }
  }, [navigate, t.callbackFailed, t.callbackNoCode, t.callbackNoSession, t.callbackSigningIn])

  return (
    <PageBackground>
      <div className="auth-callback">
        <p className="auth-callback__message">{message}</p>
        {detail ? <p className="auth-callback__detail">{detail}</p> : null}
        <Link to="/login">{t.callbackCancel}</Link>
      </div>
    </PageBackground>
  )
}
