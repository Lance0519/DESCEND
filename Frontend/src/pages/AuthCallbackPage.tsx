import { useEffect, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { PageBackground } from '../components/PageBackground'
import { useLanguage } from '../context/LanguageContext'
import { ensureUserProfile } from '../lib/ensureProfile'
import { getSupabase } from '../lib/supabaseClient'
import type { EmailOtpType, Session } from '@supabase/supabase-js'
import './AuthCallbackPage.css'

const OTP_TYPES: EmailOtpType[] = [
  'signup',
  'invite',
  'magiclink',
  'recovery',
  'email_change',
  'email',
]

/** How long to wait for supabase-js to finish its own code exchange. */
const SESSION_WAIT_MS = 12000
const POLL_INTERVAL_MS = 250

function asOtpType(value: string | null): EmailOtpType | null {
  if (!value) return null
  return OTP_TYPES.includes(value as EmailOtpType) ? (value as EmailOtpType) : null
}

/**
 * Providers return failures either as query params or in the URL fragment.
 * The raw code is logged rather than shown, so users see plain language.
 */
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
  console.warn('auth callback provider error', { description, code })
  return description
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

    function fail(detailText: string) {
      if (cancelled) return
      setMessage(t.callbackFailed)
      setDetail(detailText)
    }

    // The client is created with detectSessionInUrl, so it performs the OAuth code
    // exchange itself. Exchanging here as well would reuse a spent code.
    async function waitForSession(): Promise<Session | null> {
      const deadline = Date.now() + SESSION_WAIT_MS
      while (!cancelled && Date.now() < deadline) {
        const { data } = await sb!.auth.getSession()
        if (data.session?.access_token) return data.session
        await new Promise((resolve) => window.setTimeout(resolve, POLL_INTERVAL_MS))
      }
      return null
    }

    async function finish() {
      const url = new URL(window.location.href)
      const providerError = readProviderError(url)
      if (providerError) {
        fail(providerError)
        return
      }

      const tokenHash = url.searchParams.get('token_hash')
      const otpType = asOtpType(url.searchParams.get('type'))
      const hasCode = url.searchParams.has('code') || url.hash.includes('access_token')

      if (tokenHash && otpType) {
        const { error } = await sb!.auth.verifyOtp({ token_hash: tokenHash, type: otpType })
        if (error) {
          fail(error.message)
          return
        }
      } else if (!hasCode) {
        const { data } = await sb!.auth.getSession()
        if (!data.session) {
          fail(t.callbackNoCode)
          return
        }
      }

      const session = await waitForSession()
      if (cancelled) return
      if (!session?.user) {
        fail(t.callbackNoSession)
        return
      }

      sessionStorage.setItem('descend-supabase-access-token', session.access_token)
      const meta = session.user.user_metadata ?? {}
      await ensureUserProfile({
        id: session.user.id,
        email: session.user.email,
        displayName: String(meta.full_name ?? meta.name ?? ''),
      })
      if (cancelled) return
      navigate(otpType === 'recovery' ? '/reset-password' : '/dashboard', { replace: true })
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
