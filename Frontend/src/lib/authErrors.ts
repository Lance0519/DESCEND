export function authErrorMessage(
  err: unknown,
  copy: {
    accountDisabled: string
    errorRetry: string
    alreadyRegistered: string
    emailNotConfirmed: string
    invalidCredentials: string
    authNotConfigured: string
  },
): string {
  const raw = err instanceof Error ? err.message : ''
  const normalized = raw.toLowerCase()

  if (!raw || normalized.includes('supabase is not configured')) return copy.authNotConfigured
  if (normalized === 'disabled' || normalized.includes('user is disabled')) return copy.accountDisabled
  if (
    normalized.includes('already_registered') ||
    normalized.includes('already registered') ||
    normalized.includes('already been registered') ||
    normalized.includes('user already exists')
  ) {
    return copy.alreadyRegistered
  }
  if (normalized.includes('email not confirmed') || normalized.includes('not confirmed')) {
    return copy.emailNotConfirmed
  }
  if (normalized.includes('invalid login') || normalized.includes('invalid credentials')) {
    return copy.invalidCredentials
  }
  if (raw.length > 0 && raw.length < 180) return raw
  return copy.errorRetry
}
