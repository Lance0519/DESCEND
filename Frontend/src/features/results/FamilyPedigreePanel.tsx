import { Network } from 'lucide-react'
import type { PredictionResult } from '../../types/prediction'
import './FamilyPedigreePanel.css'

interface Props {
  result: PredictionResult
  title: string
}

export function FamilyPedigreePanel({ result, title }: Props) {
  const nodes = result.familyLineage?.nodes
  if (!nodes?.length) return null

  const byGen = (g: number) => nodes.filter((n) => n.generation === g)

  return (
    <section className="pedigree-panel">
      <div className="pedigree-panel__head">
        <Network size={22} aria-hidden />
        <h2>{title}</h2>
      </div>
      {[1, 2, 3].map((gen) => {
        const row = byGen(gen)
        if (!row.length) return null
        return (
          <div key={gen} className="pedigree-panel__row">
            {row.map((n) => (
              <div
                key={n.id}
                className={`pedigree-node pedigree-node--${String(n.status ?? 'unknown')}`}
              >
                <span className="pedigree-node__label">{n.label}</span>
                <span className="pedigree-node__status">{String(n.status ?? 'unknown')}</span>
              </div>
            ))}
          </div>
        )
      })}
    </section>
  )
}
