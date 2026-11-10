import type { ReactNode } from 'react'
import type { RiskBand } from '../../types/prediction'
import { resolveRiskLevel, type RiskLevel } from '../../utils/risk'
import './RiskBadge.css'

export type { RiskLevel }

export interface RiskBadgeProps {
  band?: RiskBand | string | null
  level?: RiskLevel
  size?: 'sm' | 'md' | 'lg'
  children?: ReactNode
  className?: string
}

export function RiskBadge({
  band,
  level,
  size = 'md',
  children,
  className = '',
}: RiskBadgeProps) {
  const resolvedLevel = level ?? resolveRiskLevel(band)
  const classes = ['risk-badge', `risk-badge--${size}`, `risk-badge--${resolvedLevel}`, className]
    .filter(Boolean)
    .join(' ')

  return <span className={classes}>{children ?? band}</span>
}
