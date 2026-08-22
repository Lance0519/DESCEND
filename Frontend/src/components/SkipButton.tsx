import './SkipButton.css'

interface SkipButtonProps {
  label: string
  onClick: () => void
}

export function SkipButton({ label, onClick }: SkipButtonProps) {
  return (
    <button type="button" className="skip-btn" onClick={onClick}>
      {label}
    </button>
  )
}
