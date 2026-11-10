const HIDE_VALUES = new Set(['false', '0', 'no', 'off'])

export function isGoogleSignInEnabled(): boolean {
  const flag = String(import.meta.env.VITE_ENABLE_GOOGLE_SIGNIN ?? '')
    .trim()
    .toLowerCase()
  return !HIDE_VALUES.has(flag)
}
