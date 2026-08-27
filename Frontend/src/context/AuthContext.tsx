import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from 'react'
import { ensureUserProfile } from '../lib/ensureProfile'
import { getSupabase, isSupabaseConfigured } from '../lib/supabaseClient'

export type UserRole = 'user' | 'admin'

export interface AuthUser {
  id: string
  email: string | null
  displayName: string | null
  avatarUrl: string | null
  provider: string
  role: UserRole
  isActive: boolean
  preferredAge: number | null
  preferredSex: string | null
  preferredLang: string | null
}

interface AuthContextValue {
  user: AuthUser | null
  isGuest: boolean
  isAdmin: boolean
  loading: boolean
  configured: boolean
  continueAsGuest: () => void
  signIn: (email: string, password: string) => Promise<void>
  signUp: (email: string, password: string, displayName?: string) => Promise<{ needsEmailConfirm: boolean }>
  signInWithGoogle: () => Promise<void>
  signOut: () => Promise<void>
  sendPasswordReset: (email: string) => Promise<void>
  reauthenticate: (password: string) => Promise<boolean>
  updatePassword: (password: string) => Promise<void>
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
    role: 'user',
    isActive: true,
    preferredAge: null,
    preferredSex: null,
    preferredLang: null,
  }
}

async function enrichFromProfile(base: AuthUser): Promise<AuthUser> {
  const sb = getSupabase()
  if (!sb) return base
  const { data } = await sb
    .from('profiles')
    .select('display_name, preferred_lang, sex, age, role, is_active, avatar_url')
    .eq('id', base.id)
    .maybeSingle()
  if (!data) return base
  const role = data.role === 'admin' ? 'admin' : 'user'
  return {
    ...base,
    displayName: (data.display_name as string) || base.displayName,
    avatarUrl: (data.avatar_url as string) || base.avatarUrl,
    role,
    isActive: data.is_active !== false,
    preferredAge: typeof data.age === 'number' ? data.age : null,
    preferredSex: typeof data.sex === 'string' ? data.sex : null,
    preferredLang: typeof data.preferred_lang === 'string' ? data.preferred_lang : null,
  }
}

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<AuthUser | null>(null)
  const [isGuest, setIsGuest] = useState(false)
  const [loading, setLoading] = useState(true)
  const configured = isSupabaseConfigured()

  const applySessionUser = useCallback(async (sessionUser: Parameters<typeof mapUser>[0]) => {
    const mapped = mapUser(sessionUser)
    try {
      const enriched = await enrichFromProfile(mapped)
      if (!enriched.isActive) {
        const sb = getSupabase()
        if (sb) await sb.auth.signOut()
        sessionStorage.removeItem('descend-supabase-access-token')
        setUser(null)
        throw new Error('disabled')
      }
      setUser(enriched)
      setIsGuest(false)
    } catch (err) {
      if (err instanceof Error && err.message === 'disabled') throw err
      setUser(mapped)
      setIsGuest(false)
    }
  }, [])

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
      try {
        await applySessionUser(session.user)
      } catch {
        setUser(null)
      }
    } else {
      sessionStorage.removeItem('descend-supabase-access-token')
      setUser(null)
    }
    setLoading(false)
  }, [applySessionUser])

  useEffect(() => {
    void syncToken()
    const sb = getSupabase()
    if (!sb) return
    const { data: sub } = sb.auth.onAuthStateChange((_event, session) => {
      if (session?.access_token) {
        sessionStorage.setItem('descend-supabase-access-token', session.access_token)
        void applySessionUser(session.user).catch(() => setUser(null))
      } else {
        sessionStorage.removeItem('descend-supabase-access-token')
        setUser(null)
      }
    })
    return () => sub.subscription.unsubscribe()
  }, [syncToken, applySessionUser])

  const continueAsGuest = useCallback(() => {
    setIsGuest(true)
    setUser(null)
  }, [])

  const signIn = useCallback(async (email: string, password: string) => {
    const sb = getSupabase()
    if (!sb) throw new Error('Supabase is not configured')
    const { data, error } = await sb.auth.signInWithPassword({ email, password })
    if (error) throw error
    if (data.user) {
      try {
        await applySessionUser(data.user)
      } catch {
        throw new Error('disabled')
      }
    }
    setIsGuest(false)
  }, [applySessionUser])

  const signUp = useCallback(async (email: string, password: string, displayName?: string) => {
    const sb = getSupabase()
    if (!sb) throw new Error('Supabase is not configured')
    const name = displayName?.trim() ?? ''
    const { data, error } = await sb.auth.signUp({
      email: email.trim(),
      password,
      options: {
        data: { full_name: name },
        emailRedirectTo: `${window.location.origin}/auth/callback`,
      },
    })
    if (error) throw error
    if (data.user && (data.user.identities?.length ?? 0) === 0) {
      throw new Error('already_registered')
    }
    setIsGuest(false)
    if (data.session?.user) {
      await ensureUserProfile({
        id: data.session.user.id,
        email: data.session.user.email,
        displayName: name,
      })
      await applySessionUser(data.session.user)
    }
    return { needsEmailConfirm: !data.session }
  }, [applySessionUser])

  const signInWithGoogle = useCallback(async () => {
    const sb = getSupabase()
    if (!sb) throw new Error('Supabase is not configured')
    const { error } = await sb.auth.signInWithOAuth({
      provider: 'google',
      options: { redirectTo: `${window.location.origin}/auth/callback` },
    })
    if (error) throw error
  }, [])

  const sendPasswordReset = useCallback(async (email: string) => {
    const sb = getSupabase()
    if (!sb) throw new Error('Supabase is not configured')
    const { error } = await sb.auth.resetPasswordForEmail(email, {
      redirectTo: `${window.location.origin}/reset-password`,
    })
    if (error) throw error
  }, [])

  /** Confirms the signed-in admin still knows their password, for sensitive views. */
  const reauthenticate = useCallback(async (password: string) => {
    const sb = getSupabase()
    if (!sb) return false
    const { data } = await sb.auth.getSession()
    const email = data.session?.user.email
    if (!email) return false
    const { error } = await sb.auth.signInWithPassword({ email, password })
    return !error
  }, [])

  const updatePassword = useCallback(async (password: string) => {
    const sb = getSupabase()
    if (!sb) throw new Error('Supabase is not configured')
    const { error } = await sb.auth.updateUser({ password })
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
      isAdmin: user?.role === 'admin',
      loading,
      configured,
      continueAsGuest,
      signIn,
      signUp,
      signInWithGoogle,
      signOut,
      sendPasswordReset,
      reauthenticate,
      updatePassword,
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
      sendPasswordReset,
      reauthenticate,
      updatePassword,
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
