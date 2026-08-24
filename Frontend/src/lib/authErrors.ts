export function authErrorMessage(
  err: unknown,
  copy: { accountDisabled: string; errorRetry: string },
): string {
  const raw = err instanceof Error ? err.message : ''
  if (raw === 'disabled') return copy.accountDisabled
  return copy.errorRetry
}
