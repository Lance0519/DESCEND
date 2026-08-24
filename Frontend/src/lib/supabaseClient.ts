import { createClient, type SupabaseClient } from '@supabase/supabase-js'

const url = String(import.meta.env.VITE_SUPABASE_URL ?? '').trim()
const anon = String(import.meta.env.VITE_SUPABASE_ANON_KEY ?? '').trim()

let client: SupabaseClient | null = null

export function isSupabaseConfigured(): boolean {
  return Boolean(url && anon)
}

export function getSupabase(): SupabaseClient | null {
  if (!isSupabaseConfigured()) return null
  if (!client) {
    client = createClient(url, anon, {
      auth: {
        persistSession: true,
        autoRefreshToken: true,
        detectSessionInUrl: true,
      },
    })
  }
  return client
}
