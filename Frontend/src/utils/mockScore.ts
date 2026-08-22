import { computeBmi, type AssessmentAnswers } from '../types/assessment'
import type {
  PredictionResult,
  RiskBand,
  SoftAdjustmentContribution,
} from '../types/prediction'
import { buildDescendantScenarios } from './descendantScenarios'

function clamp(n: number, min: number, max: number) {
  return Math.min(max, Math.max(min, n))
}

function bandFromProbability(p: number): RiskBand {
  if (p < 0.34) return 'Low'
  if (p < 0.67) return 'Moderate'
  return 'High'
}

function familyBurden(answers: AssessmentAnswers): number {
  let score = 0
  if (answers.fatherT2dm === 'yes') score += 0.12
  if (answers.motherT2dm === 'yes') score += 0.12
  if (answers.siblingT2dm === 'yes') score += 0.08
  if (answers.maternalGrandfatherT2dm === 'yes') score += 0.04
  if (answers.maternalGrandmotherT2dm === 'yes') score += 0.04
  if (answers.paternalGrandfatherT2dm === 'yes') score += 0.04
  if (answers.paternalGrandmotherT2dm === 'yes') score += 0.04
  const auntUncle =
    (answers.maternalUnclesWithT2dm ?? 0) +
    (answers.maternalAuntsWithT2dm ?? 0) +
    (answers.paternalUnclesWithT2dm ?? 0) +
    (answers.paternalAuntsWithT2dm ?? 0)
  score += Math.min(auntUncle, 6) * 0.015
  return clamp(score, 0, 0.35)
}

function bmiDelta(bmi: number | null): { delta: number; contrib?: SoftAdjustmentContribution } {
  if (bmi == null) return { delta: 0 }
  let delta = 0
  if (bmi >= 30) delta = 0.08
  else if (bmi >= 25) delta = 0.045
  else if (bmi < 18.5) delta = 0.01
  else delta = -0.01
  return {
    delta,
    contrib: { id: 'bmi', label: 'bmi', delta, group: 'bmi' },
  }
}

function lifestyleDeltas(answers: AssessmentAnswers): {
  total: number
  contributions: SoftAdjustmentContribution[]
} {
  const contributions: SoftAdjustmentContribution[] = []
  let total = 0

  const rareShort =
    answers.exerciseFrequency === 'rarely' ||
    answers.physicalActivityLevel === 'low' ||
    answers.exerciseDurationMin === 'under_15'
  const highExercise =
    answers.exerciseFrequency === '5_plus_week' &&
    (answers.exerciseDurationMin === '30_60' || answers.exerciseDurationMin === '60_plus')

  if (highExercise) {
    total += -0.03
    contributions.push({ id: 'activity', label: 'activity', delta: -0.03, group: 'lifestyle' })
  } else if (rareShort) {
    total += 0.04
    contributions.push({ id: 'activity', label: 'activity', delta: 0.04, group: 'lifestyle' })
  }

  if (answers.sugaryDrinkFrequency === 'daily') {
    total += 0.035
    contributions.push({ id: 'sugary', label: 'sugary', delta: 0.035, group: 'lifestyle' })
  } else if (answers.sugaryDrinkFrequency === 'several_week') {
    total += 0.02
    contributions.push({ id: 'sugary', label: 'sugary', delta: 0.02, group: 'lifestyle' })
  }

  if (answers.fastFoodFrequency === 'daily') {
    total += 0.03
    contributions.push({ id: 'fastFood', label: 'fastFood', delta: 0.03, group: 'lifestyle' })
  } else if (answers.fastFoodFrequency === 'several_week') {
    total += 0.015
    contributions.push({ id: 'fastFood', label: 'fastFood', delta: 0.015, group: 'lifestyle' })
  }

  if (answers.smokingStatus === 'current') {
    total += 0.04
    contributions.push({ id: 'smoking', label: 'smoking', delta: 0.04, group: 'lifestyle' })
  } else if (answers.smokingStatus === 'former') {
    total += 0.015
    contributions.push({ id: 'smoking', label: 'smoking', delta: 0.015, group: 'lifestyle' })
  }

  if (answers.alcoholConsumption === 'regular') {
    total += 0.025
    contributions.push({ id: 'alcohol', label: 'alcohol', delta: 0.025, group: 'lifestyle' })
  }

  if (answers.sleepDurationHours === 'under_6') {
    total += 0.03
    contributions.push({ id: 'sleep', label: 'sleep', delta: 0.03, group: 'lifestyle' })
  } else if (answers.sleepDurationHours === '7_8') {
    total += -0.01
    contributions.push({ id: 'sleep', label: 'sleep', delta: -0.01, group: 'lifestyle' })
  }

  total = clamp(total, -0.12, 0.12)
  return { total, contributions }
}

function bloodDeltas(answers: AssessmentAnswers): {
  total: number
  contributions: SoftAdjustmentContribution[]
} {
  const contributions: SoftAdjustmentContribution[] = []
  let total = 0

  if (
    answers.fastingGlucoseMgDl != null &&
    !answers.fastingGlucoseSkipped &&
    Number.isFinite(answers.fastingGlucoseMgDl)
  ) {
    const g = answers.fastingGlucoseMgDl
    let d = 0
    if (g < 100) d = -0.01
    else if (g < 126) d = 0.04
    else d = 0.07
    total += d
    contributions.push({ id: 'glucose', label: 'glucose', delta: d, group: 'blood' })
  }

  if (
    answers.hba1cPercent != null &&
    !answers.hba1cSkipped &&
    Number.isFinite(answers.hba1cPercent)
  ) {
    const h = answers.hba1cPercent
    let d = 0
    if (h < 5.7) d = -0.01
    else if (h < 6.5) d = 0.045
    else d = 0.08
    total += d
    contributions.push({ id: 'hba1c', label: 'hba1c', delta: d, group: 'blood' })
  }

  total = clamp(total, -0.1, 0.1)
  return { total, contributions }
}

function earlyOnsetDelta(answers: AssessmentAnswers): {
  total: number
  contributions: SoftAdjustmentContribution[]
} {
  const ages: number[] = []
  if (answers.fatherT2dm === 'yes' && answers.fatherAgeAtDx != null) ages.push(answers.fatherAgeAtDx)
  if (answers.motherT2dm === 'yes' && answers.motherAgeAtDx != null) ages.push(answers.motherAgeAtDx)
  if (answers.siblingT2dm === 'yes' && answers.siblingAgeAtDx != null) ages.push(answers.siblingAgeAtDx)

  let total = 0
  ages
    .sort((a, b) => a - b)
    .slice(0, 2)
    .forEach((age) => {
      if (age < 40) total += 0.025
      else if (age <= 50) total += 0.015
      else total += 0.005
    })

  const gpAges: number[] = []
  if (answers.maternalGrandfatherT2dm === 'yes' && answers.maternalGrandfatherAgeAtDx != null)
    gpAges.push(answers.maternalGrandfatherAgeAtDx)
  if (answers.maternalGrandmotherT2dm === 'yes' && answers.maternalGrandmotherAgeAtDx != null)
    gpAges.push(answers.maternalGrandmotherAgeAtDx)
  if (answers.paternalGrandfatherT2dm === 'yes' && answers.paternalGrandfatherAgeAtDx != null)
    gpAges.push(answers.paternalGrandfatherAgeAtDx)
  if (answers.paternalGrandmotherT2dm === 'yes' && answers.paternalGrandmotherAgeAtDx != null)
    gpAges.push(answers.paternalGrandmotherAgeAtDx)

  gpAges
    .filter((a) => a < 50)
    .slice(0, 2)
    .forEach(() => {
      total += 0.01
    })

  total = clamp(total, 0, 0.06)
  const contributions: SoftAdjustmentContribution[] =
    total > 0 ? [{ id: 'earlyOnset', label: 'earlyOnset', delta: total, group: 'earlyOnset' }] : []
  return { total, contributions }
}

/** Client mock scorer mirroring planned backend soft-adjust weights. */
export function mockScore(answers: AssessmentAnswers): PredictionResult {
  const bmi =
    answers.heightCm != null && answers.weightKg != null
      ? computeBmi(answers.heightCm, answers.weightKg)
      : null

  const ageFactor = answers.age != null ? clamp((answers.age - 18) / 200, 0, 0.2) : 0.05
  const sexFactor = answers.sex === 'male' ? 0.02 : 0
  const hyp = answers.hypertension === 'yes' ? 0.05 : 0
  const diagnosed = answers.diagnosedT2dm === 'yes' ? 0.15 : 0
  const family = familyBurden(answers)
  const bmiPart = bmiDelta(bmi)
  const life = lifestyleDeltas(answers)
  const blood = bloodDeltas(answers)
  const early = earlyOnsetDelta(answers)

  const baseCore = clamp(0.12 + ageFactor + sexFactor + diagnosed, 0.05, 0.5)

  const contributions: SoftAdjustmentContribution[] = [
    { id: 'base', label: 'base', delta: baseCore, group: 'base' },
  ]
  if (family > 0) {
    contributions.push({ id: 'family', label: 'family', delta: family, group: 'family' })
  }
  if (hyp > 0) {
    contributions.push({ id: 'hypertension', label: 'hypertension', delta: hyp, group: 'clinical' })
  }
  if (bmiPart.contrib) contributions.push(bmiPart.contrib)
  contributions.push(...life.contributions, ...blood.contributions, ...early.contributions)

  const probability = clamp(
    baseCore + family + hyp + bmiPart.delta + life.total + blood.total + early.total,
    0.02,
    0.98,
  )
  const percentage = Math.round(probability * 100)
  const descendants = buildDescendantScenarios(probability)

  return {
    percentage,
    probability,
    riskBand: bandFromProbability(probability),
    bmi,
    source: 'mock',
    softAdjustment: {
      lifestyle: life.total,
      blood: blood.total,
      earlyOnset: early.total,
      base: baseCore,
      net: life.total + blood.total + early.total,
      contributions,
    },
    ...descendants,
    predictionScopeNote:
      'Child percentages are illustrative projections from your awareness score, not a medical diagnosis.',
    familyLineage: buildSimpleLineage(answers),
  }
}

function buildSimpleLineage(answers: AssessmentAnswers) {
  const nodes = [
    { id: 'mgm', label: 'Maternal Grandmother', status: answers.maternalGrandmotherT2dm ?? 'unknown', generation: 1 },
    { id: 'mgf', label: 'Maternal Grandfather', status: answers.maternalGrandfatherT2dm ?? 'unknown', generation: 1 },
    { id: 'pgm', label: 'Paternal Grandmother', status: answers.paternalGrandmotherT2dm ?? 'unknown', generation: 1 },
    { id: 'pgf', label: 'Paternal Grandfather', status: answers.paternalGrandfatherT2dm ?? 'unknown', generation: 1 },
    { id: 'mother', label: 'Mother', status: answers.motherT2dm ?? 'unknown', generation: 2 },
    { id: 'father', label: 'Father', status: answers.fatherT2dm ?? 'unknown', generation: 2 },
    { id: 'user', label: 'You', status: answers.diagnosedT2dm ?? 'no', generation: 3 },
  ]
  return { nodes }
}
