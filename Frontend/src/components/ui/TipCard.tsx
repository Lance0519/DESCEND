import type { ComponentType, ReactNode } from 'react'
import type { LucideProps } from 'lucide-react'
import './TipCard.css'

export interface TipCardProps {
  icon?: ComponentType<LucideProps>
  title: string
  text: string
  badge?: ReactNode
  highlighted?: boolean
  as?: 'li' | 'div'
  className?: string
}

export function TipCard({
  icon: Icon,
  title,
  text,
  badge,
  highlighted = false,
  as: Component = 'li',
  className = '',
}: TipCardProps) {
  const classes = [
    'tip-card',
    highlighted ? 'tip-card--highlighted' : '',
    className,
  ]
    .filter(Boolean)
    .join(' ')

  return (
    <Component className={classes}>
      {Icon && <Icon size={22} aria-hidden className="tip-card__icon" />}
      <div className="tip-card__content">
        {badge && <span className="tip-card__badge">{badge}</span>}
        <h3 className="tip-card__title">{title}</h3>
        <p className="tip-card__text">{text}</p>
      </div>
    </Component>
  )
}
