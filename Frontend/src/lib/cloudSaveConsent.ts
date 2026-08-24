const KEY = 'descend-cloud-save-consent'

export type CloudSaveConsent = 'yes' | 'no'

export function getCloudSaveConsent(): CloudSaveConsent | null {
  try {
    const value = sessionStorage.getItem(KEY)
    if (value === 'yes' || value === 'no') return value
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
}
