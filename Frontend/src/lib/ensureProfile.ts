import { getSupabase } from './supabaseClient'

export type RegistrationConsent = {
  terms_accepted: boolean
  health_consent_accepted: boolean
  age_confirmed: boolean
  consent_timestamp: string
}

export function consentFromUserMetadata(
  meta: Record<string, unknown> | undefined,
): RegistrationConsent | null {
  if (!meta) return null
  const terms = meta.terms_accepted === true || meta.terms_accepted === 'true'
  const health = meta.health_consent_accepted === true || meta.health_consent_accepted === 'true'
  const age = meta.age_confirmed === true || meta.age_confirmed === 'true'
  const timestamp = typeof meta.consent_timestamp === 'string' ? meta.consent_timestamp : ''
  if (!terms && !health && !age && !timestamp) return null
  return {
    terms_accepted: terms,
    health_consent_accepted: health,
    age_confirmed: age,
    consent_timestamp: timestamp,
  }
}

export async function ensureUserProfile(input: {
  id: string
  email?: string | null
  displayName?: string | null
  consent?: RegistrationConsent | null
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
  if (input.consent) {
    row.terms_accepted = input.consent.terms_accepted
    row.health_consent_accepted = input.consent.health_consent_accepted
    row.age_confirmed = input.consent.age_confirmed
    if (input.consent.consent_timestamp) {
      row.consent_timestamp = input.consent.consent_timestamp
    }
  }

  const { error } = await sb.from('profiles').upsert(row, { onConflict: 'id' })
  if (!error) return

  await sb.from('profiles').insert({
    id: input.id,
    email: input.email ?? null,
    display_name: name ?? '',
    ...(input.consent
      ? {
          terms_accepted: input.consent.terms_accepted,
          health_consent_accepted: input.consent.health_consent_accepted,
          age_confirmed: input.consent.age_confirmed,
          consent_timestamp: input.consent.consent_timestamp || null,
        }
      : {}),
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
