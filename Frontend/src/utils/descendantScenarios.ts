import type {
  FutureGenerationsPayload,
  PredictionItem,
  RiskBand,
  ScenarioProbabilities,
} from '../types/prediction'

function bandFromPct(pct: number): RiskBand {
  if (pct < 34) return 'Low'
  if (pct < 67) return 'Moderate'
  return 'High'
}

/** Heuristic child/grandchild projections from respondent probability (legacy-compatible). */
export function buildDescendantScenarios(respondentProbability: number): {
  predictions: PredictionItem[]
  scenarioProbabilities: ScenarioProbabilities
  futureGenerations: FutureGenerationsPayload
} {
  const p = Math.min(0.98, Math.max(0.02, respondentProbability))
  const childBase = p * 0.92
  const femaleChild = Math.min(0.98, childBase / 1.048)
  const maleChild = Math.min(0.98, childBase * 1.048)
  const femaleGcFromD = Math.min(0.98, femaleChild * 0.92 / 1.048)
  const maleGcFromD = Math.min(0.98, femaleChild * 0.92 * 1.048)
  const femaleGcFromS = Math.min(0.98, maleChild * 0.92 / 1.048)
  const maleGcFromS = Math.min(0.98, maleChild * 0.92 * 1.048)

  const pct = (x: number) => Math.round(x * 1000) / 10

  const predictions: PredictionItem[] = [
    {
      key: 'female_child',
      label: 'Female Child',
      probability: femaleChild,
      percentage: pct(femaleChild),
      riskBand: bandFromPct(pct(femaleChild)),
    },
    {
      key: 'male_child',
      label: 'Male Child',
      probability: maleChild,
      percentage: pct(maleChild),
      riskBand: bandFromPct(pct(maleChild)),
    },
    {
      key: 'female_grandchild',
      label: 'Female Grandchild',
      probability: (femaleGcFromD + femaleGcFromS) / 2,
      percentage: pct((femaleGcFromD + femaleGcFromS) / 2),
      riskBand: bandFromPct(pct((femaleGcFromD + femaleGcFromS) / 2)),
    },
    {
      key: 'male_grandchild',
      label: 'Male Grandchild',
      probability: (maleGcFromD + maleGcFromS) / 2,
      percentage: pct((maleGcFromD + maleGcFromS) / 2),
      riskBand: bandFromPct(pct((maleGcFromD + maleGcFromS) / 2)),
    },
  ]

  const scenarioProbabilities: ScenarioProbabilities = {
    childRisk: {
      female: pct(femaleChild),
      male: pct(maleChild),
    },
    grandchildRisk: {
      fromDaughter: { female: pct(femaleGcFromD), male: pct(maleGcFromD) },
      fromSon: { female: pct(femaleGcFromS), male: pct(maleGcFromS) },
    },
  }

  const futureGenerations: FutureGenerationsPayload = {
    children: [
      { key: 'child_female', label: 'Daughter', gender: 'female', generation: 4, isProjected: true },
      { key: 'child_male', label: 'Son', gender: 'male', generation: 4, isProjected: true },
    ],
    grandchildren: [
      {
        key: 'gc_daughter_female',
        label: 'Granddaughter',
        gender: 'female',
        generation: 5,
        parentKey: 'child_female',
        isProjected: true,
      },
      {
        key: 'gc_daughter_male',
        label: 'Grandson',
        gender: 'male',
        generation: 5,
        parentKey: 'child_female',
        isProjected: true,
      },
      {
        key: 'gc_son_female',
        label: 'Granddaughter',
        gender: 'female',
        generation: 5,
        parentKey: 'child_male',
        isProjected: true,
      },
      {
        key: 'gc_son_male',
        label: 'Grandson',
        gender: 'male',
        generation: 5,
        parentKey: 'child_male',
        isProjected: true,
      },
    ],
  }

  return { predictions, scenarioProbabilities, futureGenerations }
}

export function percentForProjectedKey(
  key: string,
  scenario: ScenarioProbabilities | null | undefined,
): number | null {
  if (!scenario) return null
  switch (key) {
    case 'child_female':
      return scenario.childRisk.female
    case 'child_male':
      return scenario.childRisk.male
    case 'gc_daughter_female':
      return scenario.grandchildRisk.fromDaughter.female
    case 'gc_daughter_male':
      return scenario.grandchildRisk.fromDaughter.male
    case 'gc_son_female':
      return scenario.grandchildRisk.fromSon.female
    case 'gc_son_male':
      return scenario.grandchildRisk.fromSon.male
    default:
      return null
  }
}
