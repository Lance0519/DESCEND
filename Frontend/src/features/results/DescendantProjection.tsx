import { Baby, GitBranch, Users } from 'lucide-react'
import type { PredictionResult } from '../../types/prediction'
import { percentForProjectedKey } from '../../utils/descendantScenarios'
import './DescendantProjection.css'

interface Props {
  result: PredictionResult
  title: string
  childrenTitle: string
  grandchildrenTitle: string
  disclaimer: string
  illustrativeOnly: string
}

function bandClass(pct: number | null): string {
  if (pct == null) return 'desc-card--unknown'
  if (pct < 34) return 'desc-card--low'
  if (pct < 67) return 'desc-card--moderate'
  return 'desc-card--high'
}

function bandLabel(pct: number | null): string {
  if (pct == null) return '—'
  if (pct < 34) return 'Low'
  if (pct < 67) return 'Moderate'
  return 'High'
}

export function DescendantProjection({
  result,
  title,
  childrenTitle,
  grandchildrenTitle,
  disclaimer,
  illustrativeOnly,
}: Props) {
  const scenario = result.scenarioProbabilities
  const fg = result.futureGenerations
  if (!scenario && !result.predictions?.length) return null

  const children = fg?.children ?? [
    { key: 'child_female', label: 'Daughter', gender: 'female' as const },
    { key: 'child_male', label: 'Son', gender: 'male' as const },
  ]
  const grandchildren = fg?.grandchildren ?? []

  return (
    <section className="desc-proj">
      <div className="desc-proj__head">
        <Baby size={22} aria-hidden />
        <h2>{title}</h2>
      </div>
      <p className="desc-proj__note">{illustrativeOnly}</p>

      <h3 className="desc-proj__sub">
        <Users size={18} aria-hidden /> {childrenTitle}
      </h3>
      <div className="desc-proj__grid">
        {children.map((c) => {
          const pct = percentForProjectedKey(c.key, scenario)
          return (
            <article key={c.key} className={`desc-card ${bandClass(pct)}`}>
              <p className="desc-card__label">{c.label}</p>
              <p className="desc-card__pct">{pct != null ? `~${Math.round(pct)}%` : '—'}</p>
              <p className="desc-card__band">{bandLabel(pct)}</p>
            </article>
          )
        })}
      </div>

      {grandchildren.length > 0 ? (
        <>
          <h3 className="desc-proj__sub">
            <GitBranch size={18} aria-hidden /> {grandchildrenTitle}
          </h3>
          <div className="desc-proj__grid desc-proj__grid--gc">
            {grandchildren.map((g) => {
              const pct = percentForProjectedKey(g.key, scenario)
              return (
                <article key={g.key} className={`desc-card ${bandClass(pct)}`}>
                  <p className="desc-card__label">{g.label}</p>
                  <p className="desc-card__meta">
                    {g.parentKey === 'child_female' ? 'via daughter' : 'via son'}
                  </p>
                  <p className="desc-card__pct">{pct != null ? `~${Math.round(pct)}%` : '—'}</p>
                  <p className="desc-card__band">{bandLabel(pct)}</p>
                </article>
              )
            })}
          </div>
        </>
      ) : null}

      <p className="desc-proj__disclaimer">{disclaimer}</p>
    </section>
  )
}
