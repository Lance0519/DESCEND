import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from 'react'
import { getSupabase, isSupabaseConfigured } from '../lib/supabaseClient'

export interface AuthUser {
  id: string
  email: string | null
  displayName: string | null
  avatarUrl: string | null
  provider: string
}

interface AuthContextValue {
  user: AuthUser | null
  isGuest: boolean
  loading: boolean
  configured: boolean
  continueAsGuest: () => void
  signIn: (email: string, password: string) => Promise<void>
  signUp: (email: string, password: string, displayName?: string) => Promise<void>
  signInWithGoogle: () => Promise<void>
  signOut: () => Promise<void>
  refreshSession: () => Promise<void>
}

const AuthContext = createContext<AuthContextValue | null>(null)

function mapUser(sessionUser: {
  id: string
  email?: string | null
  user_metadata?: Record<string, unknown>
  app_metadata?: Record<string, unknown>
}): AuthUser {
  const meta = sessionUser.user_metadata ?? {}
  return {
    id: sessionUser.id,
    email: sessionUser.email ?? null,
    displayName: (meta.full_name as string) || (meta.name as string) || null,
    avatarUrl: (meta.avatar_url as string) || null,
    provider: String(sessionUser.app_metadata?.provider ?? 'email'),
  }
}

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<AuthUser | null>(null)
  const [isGuest, setIsGuest] = useState(false)
  const [loading, setLoading] = useState(true)
  const configured = isSupabaseConfigured()

  const syncToken = useCallback(async () => {
    const sb = getSupabase()
    if (!sb) {
      setLoading(false)
      return
    }
    const { data } = await sb.auth.getSession()
    const session = data.session
    if (session?.access_token) {
      sessionStorage.setItem('descend-supabase-access-token', session.access_token)
      setUser(mapUser(session.user))
      setIsGuest(false)
    } else {
      sessionStorage.removeItem('descend-supabase-access-token')
      setUser(null)
    }
    setLoading(false)
  }, [])

  useEffect(() => {
    void syncToken()
    const sb = getSupabase()
    if (!sb) return
    const { data: sub } = sb.auth.onAuthStateChange((_event, session) => {
      if (session?.access_token) {
        sessionStorage.setItem('descend-supabase-access-token', session.access_token)
        setUser(mapUser(session.user))
        setIsGuest(false)
      } else {
        sessionStorage.removeItem('descend-supabase-access-token')
        setUser(null)
      }
    })
    return () => sub.subscription.unsubscribe()
  }, [syncToken])

  const continueAsGuest = useCallback(() => {
    setIsGuest(true)
    setUser(null)
  }, [])

  const signIn = useCallback(async (email: string, password: string) => {
    const sb = getSupabase()
    if (!sb) throw new Error('Supabase is not configured')
    const { error } = await sb.auth.signInWithPassword({ email, password })
    if (error) throw error
    setIsGuest(false)
  }, [])

  const signUp = useCallback(async (email: string, password: string, displayName?: string) => {
    const sb = getSupabase()
    if (!sb) throw new Error('Supabase is not configured')
    const { error } = await sb.auth.signUp({
      email,
      password,
      options: { data: { full_name: displayName ?? '' } },
    })
    if (error) throw error
    setIsGuest(false)
  }, [])

  const signInWithGoogle = useCallback(async () => {
    const sb = getSupabase()
    if (!sb) throw new Error('Supabase is not configured')
    const { error } = await sb.auth.signInWithOAuth({
      provider: 'google',
      options: { redirectTo: `${window.location.origin}/auth/callback` },
    })
    if (error) throw error
  }, [])

  const signOut = useCallback(async () => {
    const sb = getSupabase()
    if (sb) await sb.auth.signOut()
    sessionStorage.removeItem('descend-supabase-access-token')
    setUser(null)
    setIsGuest(false)
  }, [])

  const value = useMemo(
    () => ({
      user,
      isGuest,
      loading,
      configured,
      continueAsGuest,
      signIn,
      signUp,
      signInWithGoogle,
      signOut,
      refreshSession: syncToken,
    }),
    [
      user,
      isGuest,
      loading,
      configured,
      continueAsGuest,
      signIn,
      signUp,
      signInWithGoogle,
      signOut,
      syncToken,
    ],
  )

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}

export function useAuth() {
  const ctx = useContext(AuthContext)
  if (!ctx) throw new Error('useAuth must be used within AuthProvider')
  return ctx
}
