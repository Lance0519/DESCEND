import { computeBmi, type AssessmentAnswers } from '../types/assessment'

/** Many Asian and Filipino guidelines treat overweight from this BMI. */
export const PREVENTION_BMI_ASIAN_OVERWEIGHT = 23

export const PREVENTION_ACTIVITY_MINUTES = 150

export type PreventionTipId = 'activity' | 'weight' | 'diet' | 'smoking' | 'sleep' | 'screening'

export type PreventionSourceId = 'ada' | 'dpp' | 'cdc' | 'who' | 'pinggang'

export const PREVENTION_TIP_IDS: PreventionTipId[] = [
  'activity',
  'weight',
  'diet',
  'smoking',
  'sleep',
  'screening',
]

export const PREVENTION_SOURCES: { id: PreventionSourceId; href: string }[] = [
  {
    id: 'ada',
    href: 'https://pmc.ncbi.nlm.nih.gov/articles/PMC11635039',
  },
  {
    id: 'dpp',
    href: 'https://www.nejm.org/doi/full/10.1056/NEJMoa012512',
  },
  {
    id: 'cdc',
    href: 'https://www.cdc.gov/diabetes-prevention/programs/what-is-the-national-dpp.html',
  },
  {
    id: 'who',
    href: 'https://www.who.int/news-room/fact-sheets/detail/diabetes',
  },
  {
    id: 'pinggang',
    href: 'https://www.fnri.dost.gov.ph/index.php/programs-and-projects/news-and-announcement/116-pinggang-pinoy',
  },
]

function frequentIntake(value: AssessmentAnswers['sugaryDrinkFrequency']): boolean {
  return value === 'several_week' || value === 'daily'
}

function firstDegreeT2dm(answers: AssessmentAnswers): boolean {
  return answers.fatherT2dm === 'yes' || answers.motherT2dm === 'yes' || answers.siblingT2dm === 'yes'
}

export function preventionBmi(answers: AssessmentAnswers, scoredBmi: number | null): number | null {
  if (scoredBmi != null && Number.isFinite(scoredBmi)) return scoredBmi
  if (answers.heightCm != null && answers.weightKg != null) {
    return computeBmi(answers.heightCm, answers.weightKg)
  }
  return null
}

export function matchesPreventionTip(
  id: PreventionTipId,
  answers: AssessmentAnswers,
  bmi: number | null,
): boolean {
  switch (id) {
    case 'activity':
      return answers.physicalActivityLevel === 'low' || answers.exerciseFrequency === 'rarely'
    case 'weight':
      return bmi != null && bmi >= PREVENTION_BMI_ASIAN_OVERWEIGHT
    case 'diet':
      return frequentIntake(answers.sugaryDrinkFrequency) || frequentIntake(answers.fastFoodFrequency)
    case 'smoking':
      return answers.smokingStatus === 'current'
    case 'sleep':
      return answers.sleepDurationHours === 'under_6'
    case 'screening':
      return firstDegreeT2dm(answers) || answers.hypertension === 'yes'
  }
}
