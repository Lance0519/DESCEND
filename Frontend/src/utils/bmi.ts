import { computeBmi } from '../types/assessment'

export { computeBmi }

export function formatBmi(bmi: number): string {
  return bmi.toFixed(1)
}
