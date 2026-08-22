import type { OnsetHorizon } from '../types/prediction'

/** Client-side fallback matching backend ``build_onset_horizon`` (educational only). */
export function buildOnsetHorizon(probability: number, age?: number | null): OnsetHorizon {
  const p = Math.max(0, Math.min(1, probability))
  let mid = 2 + 36 * (1 - p) ** 1.25
  mid = Math.max(2, Math.min(40, mid))
  const spread = Math.max(2, Math.min(8, mid * 0.28))
  let yearsMin = Math.max(1, Math.round(mid - spread))
  let yearsMax = Math.min(45, Math.round(mid + spread))
  if (yearsMax < yearsMin) yearsMax = yearsMin

  const yearNow = new Date().getFullYear()
  const horizon: OnsetHorizon = {
    illustrative: true,
    yearsMin,
    yearsMax,
    midYears: Math.round(mid),
    calendarYearMin: yearNow + yearsMin,
    calendarYearMax: yearNow + yearsMax,
  }

  if (typeof age === 'number' && Number.isFinite(age)) {
    const fromAge = Math.max(1, Math.min(120, Math.round(age)))
    horizon.fromAge = fromAge
    horizon.possibleAgeMin = fromAge + yearsMin
    horizon.possibleAgeMax = fromAge + yearsMax
  }

  return horizon
}
