import { getSupabase } from './supabaseClient'

export async function ensureUserProfile(input: {
  id: string
  email?: string | null
  displayName?: string | null
}): Promise<void> {
  const sb = getSupabase()
  if (!sb) return

  const row: Record<string, unknown> = {
    id: input.id,
    email: input.email ?? null,
    updated_at: new Date().toISOString(),
  }
  const name = input.displayName?.trim()
  if (name) row.display_name = name

  const { error } = await sb.from('profiles').upsert(row, { onConflict: 'id' })
  if (!error) return

  await sb.from('profiles').insert({
    id: input.id,
    email: input.email ?? null,
    display_name: name ?? '',
  })
}

export async function fetchOwnProfile(userId: string): Promise<{
  display_name?: string
  preferred_lang?: string
  sex?: string
  age?: number | null
  email?: string
  avatar_url?: string
} | null> {
  const sb = getSupabase()
  if (!sb) return null
  const { data, error } = await sb
    .from('profiles')
    .select('display_name, preferred_lang, sex, age, email, avatar_url')
    .eq('id', userId)
    .maybeSingle()
  if (error || !data) return null
  return data
}
