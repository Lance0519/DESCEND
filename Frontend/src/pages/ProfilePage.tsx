import { useEffect, useState, type FormEvent } from 'react'
import { Link, Navigate, useNavigate } from 'react-router-dom'
import { LayoutDashboard, LogOut, Save, Shield, UserRound } from 'lucide-react'
import { LanguageToggle } from '../components/LanguageToggle'
import { PageBackground } from '../components/PageBackground'
import { persistProfileToSupabase } from '../api/admin'
import { useAuth } from '../context/AuthContext'
import { fetchOwnProfile } from '../lib/ensureProfile'
import { useLanguage } from '../context/LanguageContext'
import './ProfilePage.css'

interface ProfileData {
  display_name?: string
  preferred_lang?: string
  sex?: string
  age?: number | null
  email?: string
  avatar_url?: string
}

export function ProfilePage() {
  const { t, language, setLanguage } = useLanguage()
  const { user, signOut, loading, configured, isAdmin, refreshSession } = useAuth()
  const navigate = useNavigate()
  const [profile, setProfile] = useState<ProfileData>({})
  const [message, setMessage] = useState('')

  useEffect(() => {
    if (!user) return
    void fetchOwnProfile(user.id).then((data) => {
      setProfile({
        display_name: data?.display_name || user.displayName || '',
        email: data?.email || user.email || '',
        avatar_url: data?.avatar_url || user.avatarUrl || '',
        preferred_lang: data?.preferred_lang || user.preferredLang || language,
        sex: data?.sex || user.preferredSex || '',
        age: data?.age ?? user.preferredAge,
      })
    })
  }, [user, language])

  if (loading) return null
  if (!user) return <Navigate to="/access" replace />
  const signedIn = user

  async function onSave(e: FormEvent) {
    e.preventDefault()
    setMessage('')
    try {
      if (configured) {
        await persistProfileToSupabase({
          userId: signedIn.id,
          email: signedIn.email,
          displayName: profile.display_name,
          preferredLang: profile.preferred_lang ?? language,
          sex: profile.sex,
          age: profile.age ?? null,
        })
      }
      if (profile.preferred_lang === 'en' || profile.preferred_lang === 'tl') {
        setLanguage(profile.preferred_lang)
      }
      await refreshSession()
      setMessage(t.profileSaved)
    } catch (err) {
      setMessage(err instanceof Error ? err.message : t.errorRetry)
    }
  }

  return (
    <PageBackground>
      <div className="profile-page">
        <div className="profile-page__toolbar">
          <LanguageToggle />
          <button type="button" className="profile-page__signout" onClick={() => void signOut().then(() => navigate('/'))}>
            <LogOut size={18} aria-hidden />
            {t.signOut}
          </button>
        </div>
        <main className="profile-page__card">
          <h1>
            <UserRound size={24} aria-hidden /> {t.profileTitle}
          </h1>
          {profile.avatar_url ? (
            <img className="profile-page__avatar" src={profile.avatar_url} alt="" />
          ) : null}
          <p className="profile-page__email">{user.email}</p>
          <p className="profile-page__provider">Provider: {user.provider}</p>
          <form onSubmit={(e) => void onSave(e)} className="profile-page__form">
            <label>
              {t.displayName}
              <input
                value={profile.display_name ?? ''}
                onChange={(e) => setProfile((p) => ({ ...p, display_name: e.target.value }))}
              />
            </label>
            <label>
              {t.preferredSex}
              <select
                value={profile.sex ?? ''}
                onChange={(e) => setProfile((p) => ({ ...p, sex: e.target.value }))}
              >
                <option value="">—</option>
                <option value="female">{t.options.female}</option>
                <option value="male">{t.options.male}</option>
              </select>
            </label>
            <label>
              {t.preferredAge}
              <input
                type="number"
                min={18}
                max={90}
                value={profile.age ?? ''}
                onChange={(e) =>
                  setProfile((p) => ({
                    ...p,
                    age: e.target.value === '' ? null : Number(e.target.value),
                  }))
                }
              />
            </label>
            <label>
              {t.langLabel}
              <select
                value={profile.preferred_lang ?? language}
                onChange={(e) => setProfile((p) => ({ ...p, preferred_lang: e.target.value }))}
              >
                <option value="tl">Tagalog</option>
                <option value="en">English</option>
              </select>
            </label>
            <button type="submit">
              <Save size={18} aria-hidden /> {t.profileSave}
            </button>
          </form>
          {message ? <p className="profile-page__msg">{message}</p> : null}
          <div className="profile-page__links">
            <Link to="/dashboard">
              <LayoutDashboard size={16} aria-hidden /> {t.openHistory}
            </Link>
            <Link to="/assessment">{t.retake}</Link>
            {isAdmin ? (
              <Link to="/admin">
                <Shield size={16} aria-hidden /> {t.adminNav}
              </Link>
            ) : null}
          </div>
        </main>
      </div>
    </PageBackground>
  )
}
