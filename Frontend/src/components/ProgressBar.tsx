import './ProgressBar.css'

interface ProgressBarProps {
  current: number
  total: number
  label: string
}

export function ProgressBar({ current, total, label }: ProgressBarProps) {
  const pct = total <= 0 ? 0 : Math.round(((current + 1) / total) * 100)
  return (
    <div className="progress-bar" role="progressbar" aria-valuenow={pct} aria-valuemin={0} aria-valuemax={100} aria-label={label}>
      <div className="progress-bar__meta">
        <span>{label}</span>
        <span>
          {current + 1} / {total}
        </span>
      </div>
      <div className="progress-bar__track">
        <div className="progress-bar__fill" style={{ width: `${pct}%` }} />
      </div>
    </div>
  )
}
