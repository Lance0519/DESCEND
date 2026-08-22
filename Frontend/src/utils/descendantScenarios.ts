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

/** Heuristic child projections from respondent probability. */
export function buildDescendantScenarios(respondentProbability: number): {
  predictions: PredictionItem[]
  scenarioProbabilities: ScenarioProbabilities
  futureGenerations: FutureGenerationsPayload
} {
  const p = Math.min(0.98, Math.max(0.02, respondentProbability))
  const childBase = p * 0.92
  const femaleChild = Math.min(0.98, childBase / 1.048)
  const maleChild = Math.min(0.98, childBase * 1.048)

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
  ]

  const scenarioProbabilities: ScenarioProbabilities = {
    childRisk: {
      female: pct(femaleChild),
      male: pct(maleChild),
    },
  }

  const futureGenerations: FutureGenerationsPayload = {
    children: [
      { key: 'child_female', label: 'Daughter', gender: 'female', generation: 4, isProjected: true },
      { key: 'child_male', label: 'Son', gender: 'male', generation: 4, isProjected: true },
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
    default:
      return null
  }
}
