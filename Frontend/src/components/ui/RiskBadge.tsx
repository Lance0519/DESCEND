import type { ReactNode } from 'react'
import type { RiskBand } from '../../types/prediction'
import './RiskBadge.css'

export type RiskLevel = 'low' | 'moderate' | 'high' | 'neutral'

export interface RiskBadgeProps {
  band?: RiskBand | string | null
  level?: RiskLevel
  size?: 'sm' | 'md' | 'lg'
  children?: ReactNode
  className?: string
}

function resolveRiskLevel(input?: string | null): RiskLevel {
  if (!input) return 'neutral'
  const normalized = input.toLowerCase()
  if (normalized.includes('low')) return 'low'
  if (normalized.includes('high')) return 'high'
  if (normalized.includes('mod')) return 'moderate'
  return 'neutral'
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
