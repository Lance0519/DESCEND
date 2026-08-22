import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { PageBackground } from '../components/PageBackground'
import { getSupabase } from '../lib/supabaseClient'

export function AuthCallbackPage() {
  const navigate = useNavigate()
  const [message, setMessage] = useState('Signing you in…')

  useEffect(() => {
    const sb = getSupabase()
    if (!sb) {
      navigate('/access', { replace: true })
      return
    }

    let cancelled = false

    async function finish() {
      // Prefer exchange if URL has OAuth params; otherwise read existing session
      const url = new URL(window.location.href)
      const hasCode = url.searchParams.has('code') || url.hash.includes('access_token')

      if (hasCode) {
        const { error } = await sb!.auth.exchangeCodeForSession(window.location.href)
        if (error) {
          // Some flows already have a session via detectSessionInUrl
          const { data } = await sb!.auth.getSession()
          if (!data.session) {
            if (!cancelled) {
              setMessage(error.message)
              window.setTimeout(() => navigate('/access', { replace: true }), 1500)
            }
            return
          }
        }
      }

      const { data } = await sb!.auth.getSession()
      if (cancelled) return
      if (data.session?.access_token) {
        sessionStorage.setItem('descend-supabase-access-token', data.session.access_token)
        navigate('/assessment', { replace: true })
        return
      }
      setMessage('Could not complete Google sign-in.')
      window.setTimeout(() => navigate('/access', { replace: true }), 1500)
    }

    void finish()
    return () => {
      cancelled = true
    }
  }, [navigate])

  return (
    <PageBackground>
      <p style={{ padding: '2rem', textAlign: 'center', color: 'var(--color-text-muted)' }}>{message}</p>
    </PageBackground>
  )
}
