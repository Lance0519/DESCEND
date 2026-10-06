import type { ReactNode } from 'react'
import { HelpTooltip } from './HelpTooltip'
import './QuestionCard.css'

interface QuestionCardProps {
  sectionLabel: string
  title: string
  headerAction?: ReactNode
  tooltip?: {
    title: string
    body: string
    triggerLabel?: string
    closeLabel?: string
    buttonAriaLabel?: string
  }
  children: ReactNode
}

export function QuestionCard({
  sectionLabel,
  title,
  headerAction,
  tooltip,
  children,
}: QuestionCardProps) {
  return (
    <section className="question-card">
      <div className="question-card__top">
        <div className="question-card__top-left">
          <p className="question-card__section">{sectionLabel}</p>
        </div>
        {headerAction}
      </div>
      <div className="question-card__title-row">
        <h2 className="question-card__title">{title}</h2>
        {tooltip ? (
          <HelpTooltip
            title={tooltip.title}
            body={tooltip.body}
            triggerLabel={tooltip.triggerLabel}
            closeLabel={tooltip.closeLabel}
            buttonAriaLabel={tooltip.buttonAriaLabel}
          />
        ) : null}
      </div>
      <div className="question-card__body">{children}</div>
    </section>
  )
}

