import { useCallback, useState } from 'react'
import { persistAssessmentRecord } from '../api/assessmentRecords'
import { getCloudSaveConsent, setCloudSaveConsent } from '../lib/cloudSaveConsent'
import type { PredictionResult } from '../types/prediction'
import type { AssessmentAnswers } from '../types/assessment'

export const PENDING_GUEST_RESULT_KEY = 'descend-pending-guest-result'

export interface PendingGuestResult {
  answers: AssessmentAnswers
  result: PredictionResult
  riskScore: number | null
  riskTier: string | null
  timestamp: number
}

export function cachePendingGuestResult(
  answers: AssessmentAnswers,
  result: PredictionResult,
  riskScore: number | null,
  riskTier: string | null,
) {
  const payload = JSON.stringify({
    answers,
    result,
    riskScore,
    riskTier,
    timestamp: Date.now(),
  })
  try {
    sessionStorage.setItem(PENDING_GUEST_RESULT_KEY, payload)
  } catch (err) {
    console.warn('Failed to cache pending guest result to sessionStorage', err)
  }
  try {
    localStorage.setItem(PENDING_GUEST_RESULT_KEY, payload)
  } catch (err) {
    console.warn('Failed to cache pending guest result to localStorage', err)
  }
}

export function getPendingGuestResult(): PendingGuestResult | null {
  try {
    const raw = sessionStorage.getItem(PENDING_GUEST_RESULT_KEY) ?? localStorage.getItem(PENDING_GUEST_RESULT_KEY)
    if (!raw) return null
    return JSON.parse(raw) as PendingGuestResult
  } catch {
    return null
  }
}

export function clearPendingGuestResult() {
  try {
    sessionStorage.removeItem(PENDING_GUEST_RESULT_KEY)
  } catch {
    // no-op
  }
  try {
    localStorage.removeItem(PENDING_GUEST_RESULT_KEY)
  } catch {
    // no-op
  }
}

export type SaveStatus = 'idle' | 'consent' | 'saving' | 'saved' | 'failed' | 'guest' | 'skipped'

export function useCloudSave() {
  const [status, setStatus] = useState<SaveStatus>('idle')

  const save = useCallback(
    async (input: {
      userId: string
      riskScore: number | null
      riskTier: string | null
      preDiagnosed: boolean
      answers?: unknown
      result?: unknown
    }) => {
      setStatus('saving')
      const ok = await persistAssessmentRecord(input)
      setStatus(ok ? 'saved' : 'failed')
      if (ok) {
        clearPendingGuestResult()
      }
      return ok
    },
    [],
  )

  const begin = useCallback(
    (signedIn: boolean) => {
      if (!signedIn) {
        setStatus('guest')
        return 'guest' as const
      }
      const consent = getCloudSaveConsent()
      if (consent === 'yes') return 'ready' as const
      if (consent === 'no') {
        setStatus('skipped')
        return 'skipped' as const
      }
      setStatus('consent')
      return 'consent' as const
    },
    [],
  )

  const accept = useCallback(() => {
    setCloudSaveConsent('yes')
  }, [])

  const decline = useCallback(() => {
    setCloudSaveConsent('no')
    setStatus('skipped')
  }, [])

  return { status, setStatus, save, begin, accept, decline }
}
