import { LoaderCircle } from 'lucide-react'
import { PageBackground } from './PageBackground'
import './SessionLoading.css'

export function SessionLoading({ label }: { label: string }) {
  return (
    <PageBackground>
      <p className="session-loading" role="status">
        <LoaderCircle size={20} className="session-loading__spin" aria-hidden />
        {label}
      </p>
    </PageBackground>
  )
}
