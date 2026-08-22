import { useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { getSupabase } from '../lib/supabaseClient'

export function AuthCallbackPage() {
  const navigate = useNavigate()

  useEffect(() => {
    const sb = getSupabase()
    if (!sb) {
      navigate('/access', { replace: true })
      return
    }
    void sb.auth.getSession().then(() => {
      navigate('/assessment', { replace: true })
    })
  }, [navigate])

  return <p style={{ padding: '2rem', textAlign: 'center' }}>Signing you in…</p>
}
