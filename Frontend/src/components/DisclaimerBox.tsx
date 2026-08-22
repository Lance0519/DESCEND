import type { LucideIcon } from 'lucide-react'
import './DisclaimerBox.css'

interface DisclaimerBoxProps {
  title: string
  text: string
  icon: LucideIcon
  variant?: 'neutral' | 'primary'
}

export function DisclaimerBox({ title, text, icon: Icon, variant = 'neutral' }: DisclaimerBoxProps) {
  return (
    <div className={`disclaimer disclaimer--${variant}`}>
      <Icon size={24} className="disclaimer__icon" aria-hidden />
      <div>
        <strong className="disclaimer__title">{title}</strong>
        <p className="disclaimer__text">{text}</p>
      </div>
    </div>
  )
}
