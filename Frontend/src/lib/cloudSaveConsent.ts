const KEY = 'descend-cloud-save-consent'

export type CloudSaveConsent = 'yes' | 'no'

export function getCloudSaveConsent(): CloudSaveConsent | null {
  try {
    const sessionVal = sessionStorage.getItem(KEY)
    if (sessionVal === 'yes' || sessionVal === 'no') return sessionVal
  } catch {
    /* ignore */
  }
  try {
    const localVal = localStorage.getItem(KEY)
    if (localVal === 'yes' || localVal === 'no') return localVal
  } catch {
    /* ignore */
  }
  return null
}

export function setCloudSaveConsent(value: CloudSaveConsent): void {
  try {
    sessionStorage.setItem(KEY, value)
  } catch {
    /* ignore */
  }
  try {
    localStorage.setItem(KEY, value)
  } catch {
    /* ignore */
  }
}

export function clearCloudSaveConsent(): void {
  try {
    sessionStorage.removeItem(KEY)
  } catch {
    /* ignore */
  }
  try {
    localStorage.removeItem(KEY)
  } catch {
    /* ignore */
  }
}
