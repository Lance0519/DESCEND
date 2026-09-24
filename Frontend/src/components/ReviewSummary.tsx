import { useEffect, useRef } from 'react'
import { QuestionCard } from './QuestionCard'
import { useLanguage } from '../context/LanguageContext'
import type { ReviewGroup } from '../lib/answerSummary'
import './ReviewSummary.css'

interface ReviewSummaryProps {
  groups: ReviewGroup[]
  missingIndex: number | null
  onEdit: (index: number) => void
}

export function ReviewSummary({ groups, missingIndex, onEdit }: ReviewSummaryProps) {
  const { t } = useLanguage()
  const containerRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    containerRef.current?.focus()
  }, [])

  return (
    <div className="review-summary" ref={containerRef} tabIndex={-1}>
      <QuestionCard sectionLabel={t.reviewSectionLabel} title={t.reviewTitle}>
        <p className="review-summary__intro">{t.reviewIntro}</p>

        {missingIndex != null ? (
          <div className="review-summary__warning" role="status">
            <p>{t.reviewIncompleteWarning}</p>
            <button
              type="button"
              className="review-summary__warning-link"
              onClick={() => onEdit(missingIndex)}
            >
              {t.reviewGoToFirstMissing}
            </button>
          </div>
        ) : null}

        {groups.map((group) => (
          <section className="review-summary__group" key={`${group.section}-${group.rows[0]?.index}`}>
            <h3 className="review-summary__group-title">{group.label}</h3>
            <dl className="review-summary__list">
              {group.rows.map((row) => (
                <div
                  key={row.id}
                  className={
                    row.state === 'missing'
                      ? 'review-summary__row review-summary__row--missing'
                      : 'review-summary__row'
                  }
                >
                  <dt className="review-summary__question">{row.question}</dt>
                  <dd className="review-summary__answer">
                    <span
                      className={
                        row.state === 'answered'
                          ? 'review-summary__value'
                          : 'review-summary__value review-summary__value--muted'
                      }
                    >
                      {row.value}
                    </span>
                    <button
                      type="button"
                      className="review-summary__edit"
                      aria-label={t.reviewEditAria.replace('{question}', row.question)}
                      onClick={() => onEdit(row.index)}
                    >
                      {t.reviewEdit}
                    </button>
                  </dd>
                </div>
              ))}
            </dl>
          </section>
        ))}
      </QuestionCard>
    </div>
  )
}
