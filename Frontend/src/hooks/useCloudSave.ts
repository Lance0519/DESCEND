import { useCallback, useState } from 'react'
import { persistAssessmentRecord } from '../api/assessmentRecords'
import { getCloudSaveConsent, setCloudSaveConsent } from '../lib/cloudSaveConsent'

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
