import type { ReactNode } from 'react'
import './QuestionCard.css'

interface QuestionCardProps {
  sectionLabel: string
  title: string
  headerAction?: ReactNode
  children: ReactNode
}

export function QuestionCard({ sectionLabel, title, headerAction, children }: QuestionCardProps) {
  return (
    <section className="question-card">
      <div className="question-card__top">
        <p className="question-card__section">{sectionLabel}</p>
        {headerAction}
      </div>
      <h2 className="question-card__title">{title}</h2>
      <div className="question-card__body">{children}</div>
    </section>
  )
}
