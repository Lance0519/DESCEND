import { Network } from 'lucide-react'
import type { FamilyLineageNode, PredictionResult } from '../../types/prediction'
import { useLanguage } from '../../context/LanguageContext'
import './FamilyPedigreePanel.css'

interface Props {
  result: PredictionResult
  title: string
}

type NodeView = FamilyLineageNode & { nodeKey: string }

function nodeKeyOf(n: FamilyLineageNode, index: number): string {
  return n.key || n.id || `node-${index}`
}

/** API uses gen 0=grandparents, 1=parents, 2=you; older mocks used 1–3. */
function normalizeGeneration(n: FamilyLineageNode): number {
  const g = n.generation
  if (typeof g === 'number' && Number.isFinite(g)) {
    // Legacy/API: 0..2. Mock legacy: 1..3 → shift down when no gen-0 nodes exist elsewhere.
    return g
  }
  const key = (n.key || n.id || '').toLowerCase()
  if (key.includes('grand')) return 0
  if (key === 'mother' || key === 'father') return 1
  if (key === 'user' || n.isRespondent) return 2
  return 1
}

function statusClass(status?: string): string {
  const s = String(status ?? 'unknown').toLowerCase()
  if (s === 'yes' || s === 'no' || s === 'unknown') return s
  return 'unknown'
}

export function FamilyPedigreePanel({ result, title }: Props) {
  const { t } = useLanguage()
  const raw = result.familyLineage?.nodes
  if (!raw?.length) return null

  const nodes: NodeView[] = raw.map((n, i) => ({
    ...n,
    nodeKey: nodeKeyOf(n, i),
    generation: normalizeGeneration(n),
  }))

  // Prefer API numbering (0–2). If data only has 1–3 (old mock), remap to 0–2.
  const gensPresent = new Set(nodes.map((n) => n.generation ?? -1))
  const usesApiGens = gensPresent.has(0) || (gensPresent.has(2) && !gensPresent.has(3))
  const displayNodes = usesApiGens
    ? nodes
    : nodes.map((n) => ({
        ...n,
        generation: Math.max(0, (n.generation ?? 1) - 1),
      }))

  const byGen = (g: number) => displayNodes.filter((n) => n.generation === g)

  const grandparents = byGen(0)
  const maternalGp = grandparents.filter((n) => n.nodeKey.toLowerCase().includes('maternal'))
  const paternalGp = grandparents.filter((n) => n.nodeKey.toLowerCase().includes('paternal'))
  const otherGp = grandparents.filter(
    (n) =>
      !n.nodeKey.toLowerCase().includes('maternal') &&
      !n.nodeKey.toLowerCase().includes('paternal'),
  )
  const parents = byGen(1)
  const present = byGen(2)

  const renderNode = (n: NodeView) => (
    <div
      key={n.nodeKey}
      className={`pedigree-node pedigree-node--${statusClass(n.status)}${
        n.isRespondent || n.nodeKey === 'user' ? ' pedigree-node--you' : ''
      }`}
    >
      <span className="pedigree-node__label">{n.label}</span>
      <span className="pedigree-node__status">{String(n.status ?? 'unknown')}</span>
    </div>
  )

  return (
    <section className="pedigree-panel">
      <div className="pedigree-panel__head">
        <Network size={22} aria-hidden />
        <h2>{title}</h2>
      </div>
      <p className="pedigree-panel__caption">{t.pedigreeCaption}</p>

      {grandparents.length > 0 ? (
        <div className="pedigree-panel__generation">
          <h3 className="pedigree-panel__gen-label">{t.pedigreeGrandparents}</h3>
          <div className="pedigree-panel__branches">
            {maternalGp.length > 0 ? (
              <div className="pedigree-panel__branch">
                <p className="pedigree-panel__branch-label">{t.pedigreeMaternal}</p>
                <div className="pedigree-panel__row">{maternalGp.map(renderNode)}</div>
              </div>
            ) : null}
            {paternalGp.length > 0 ? (
              <div className="pedigree-panel__branch">
                <p className="pedigree-panel__branch-label">{t.pedigreePaternal}</p>
                <div className="pedigree-panel__row">{paternalGp.map(renderNode)}</div>
              </div>
            ) : null}
            {otherGp.length > 0 ? (
              <div className="pedigree-panel__row">{otherGp.map(renderNode)}</div>
            ) : null}
          </div>
        </div>
      ) : null}

      {parents.length > 0 ? (
        <div className="pedigree-panel__generation">
          <h3 className="pedigree-panel__gen-label">{t.pedigreeParents}</h3>
          <div className="pedigree-panel__row">{parents.map(renderNode)}</div>
        </div>
      ) : null}

      {present.length > 0 ? (
        <div className="pedigree-panel__generation">
          <h3 className="pedigree-panel__gen-label">{t.pedigreePresent}</h3>
          <div className="pedigree-panel__row">{present.map(renderNode)}</div>
        </div>
      ) : null}
    </section>
  )
}
