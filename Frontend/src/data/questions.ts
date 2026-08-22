import type { AnswerKey, AssessmentAnswers } from '../types/assessment'

export type QuestionType = 'choice' | 'number' | 'bmiConfirm' | 'optionalNumber'

export interface QuestionOption {
  value: string | number
  labelKey: string
}

export interface QuestionDef {
  id: AnswerKey | 'bmiConfirm'
  type: QuestionType
  section:
    | 'demographic'
    | 'anthropometric'
    | 'clinical'
    | 'target'
    | 'blood'
    | 'lifestyle'
    | 'hereditaryFirst'
    | 'hereditaryMaternal'
    | 'hereditaryPaternal'
  questionKey: keyof import('../i18n/en').TranslationDict['questions']
  options?: QuestionOption[]
  min?: number
  max?: number
  step?: number
  unit?: string
  showIf?: (answers: AssessmentAnswers) => boolean
  optional?: boolean
}

const yesNoUnknown = [
  { value: 'yes', labelKey: 'yes' },
  { value: 'no', labelKey: 'no' },
  { value: 'unknown', labelKey: 'unknown' },
]

const yesNo = [
  { value: 'yes', labelKey: 'yes' },
  { value: 'no', labelKey: 'no' },
]

const foodFreq = [
  { value: 'rarely', labelKey: 'rarely' },
  { value: 'weekly', labelKey: 'weekly' },
  { value: 'several_week', labelKey: 'several_week' },
  { value: 'daily', labelKey: 'daily' },
]

export const QUESTIONS: QuestionDef[] = [
  {
    id: 'sex',
    type: 'choice',
    section: 'demographic',
    questionKey: 'sex',
    options: [
      { value: 'male', labelKey: 'male' },
      { value: 'female', labelKey: 'female' },
    ],
  },
  {
    id: 'age',
    type: 'number',
    section: 'demographic',
    questionKey: 'age',
    min: 18,
    max: 90,
    step: 1,
  },
  {
    id: 'heightCm',
    type: 'number',
    section: 'anthropometric',
    questionKey: 'heightCm',
    min: 120,
    max: 220,
    step: 1,
    unit: 'cm',
  },
  {
    id: 'weightKg',
    type: 'number',
    section: 'anthropometric',
    questionKey: 'weightKg',
    min: 30,
    max: 250,
    step: 0.1,
    unit: 'kg',
  },
  {
    id: 'bmiConfirm',
    type: 'bmiConfirm',
    section: 'anthropometric',
    questionKey: 'bmiConfirm',
  },
  {
    id: 'hypertension',
    type: 'choice',
    section: 'clinical',
    questionKey: 'hypertension',
    options: yesNo,
  },
  {
    id: 'fastingGlucoseMgDl',
    type: 'optionalNumber',
    section: 'blood',
    questionKey: 'fastingGlucoseMgDl',
    min: 50,
    max: 400,
    step: 1,
    unit: 'mg/dL',
    optional: true,
  },
  {
    id: 'hba1cPercent',
    type: 'optionalNumber',
    section: 'blood',
    questionKey: 'hba1cPercent',
    min: 3,
    max: 15,
    step: 0.1,
    unit: '%',
    optional: true,
  },
  {
    id: 'physicalActivityLevel',
    type: 'choice',
    section: 'lifestyle',
    questionKey: 'physicalActivityLevel',
    options: [
      { value: 'low', labelKey: 'low' },
      { value: 'moderate', labelKey: 'moderate' },
      { value: 'high', labelKey: 'high' },
    ],
  },
  {
    id: 'exerciseFrequency',
    type: 'choice',
    section: 'lifestyle',
    questionKey: 'exerciseFrequency',
    options: [
      { value: 'rarely', labelKey: 'rarely' },
      { value: '1_2_week', labelKey: '1_2_week' },
      { value: '3_4_week', labelKey: '3_4_week' },
      { value: '5_plus_week', labelKey: '5_plus_week' },
    ],
  },
  {
    id: 'exerciseDurationMin',
    type: 'choice',
    section: 'lifestyle',
    questionKey: 'exerciseDurationMin',
    options: [
      { value: 'under_15', labelKey: 'under_15' },
      { value: '15_30', labelKey: '15_30' },
      { value: '30_60', labelKey: '30_60' },
      { value: '60_plus', labelKey: '60_plus' },
    ],
  },
  {
    id: 'sugaryDrinkFrequency',
    type: 'choice',
    section: 'lifestyle',
    questionKey: 'sugaryDrinkFrequency',
    options: foodFreq,
  },
  {
    id: 'fastFoodFrequency',
    type: 'choice',
    section: 'lifestyle',
    questionKey: 'fastFoodFrequency',
    options: foodFreq,
  },
  {
    id: 'smokingStatus',
    type: 'choice',
    section: 'lifestyle',
    questionKey: 'smokingStatus',
    options: [
      { value: 'never', labelKey: 'never' },
      { value: 'former', labelKey: 'former' },
      { value: 'current', labelKey: 'current' },
    ],
  },
  {
    id: 'alcoholConsumption',
    type: 'choice',
    section: 'lifestyle',
    questionKey: 'alcoholConsumption',
    options: [
      { value: 'none', labelKey: 'none' },
      { value: 'occasional', labelKey: 'occasional' },
      { value: 'regular', labelKey: 'regular' },
    ],
  },
  {
    id: 'sleepDurationHours',
    type: 'choice',
    section: 'lifestyle',
    questionKey: 'sleepDurationHours',
    options: [
      { value: 'under_6', labelKey: 'under_6' },
      { value: '6_7', labelKey: '6_7' },
      { value: '7_8', labelKey: '7_8' },
      { value: 'over_8', labelKey: 'over_8' },
    ],
  },
  {
    id: 'fatherT2dm',
    type: 'choice',
    section: 'hereditaryFirst',
    questionKey: 'fatherT2dm',
    options: yesNoUnknown,
  },
  {
    id: 'fatherAgeAtDx',
    type: 'number',
    section: 'hereditaryFirst',
    questionKey: 'fatherAgeAtDx',
    min: 1,
    max: 100,
    showIf: (a) => a.fatherT2dm === 'yes',
  },
  {
    id: 'motherT2dm',
    type: 'choice',
    section: 'hereditaryFirst',
    questionKey: 'motherT2dm',
    options: yesNoUnknown,
  },
  {
    id: 'motherAgeAtDx',
    type: 'number',
    section: 'hereditaryFirst',
    questionKey: 'motherAgeAtDx',
    min: 1,
    max: 100,
    showIf: (a) => a.motherT2dm === 'yes',
  },
  {
    id: 'siblingT2dm',
    type: 'choice',
    section: 'hereditaryFirst',
    questionKey: 'siblingT2dm',
    options: [
      { value: 'yes', labelKey: 'yes' },
      { value: 'no', labelKey: 'no' },
      { value: 'no_siblings', labelKey: 'no_siblings' },
      { value: 'unknown', labelKey: 'unknown' },
    ],
  },
  {
    id: 'siblingAgeAtDx',
    type: 'number',
    section: 'hereditaryFirst',
    questionKey: 'siblingAgeAtDx',
    min: 1,
    max: 100,
    showIf: (a) => a.siblingT2dm === 'yes',
  },
  {
    id: 'maternalGrandfatherT2dm',
    type: 'choice',
    section: 'hereditaryMaternal',
    questionKey: 'maternalGrandfatherT2dm',
    options: yesNoUnknown,
  },
  {
    id: 'maternalGrandfatherAgeAtDx',
    type: 'number',
    section: 'hereditaryMaternal',
    questionKey: 'maternalGrandfatherAgeAtDx',
    min: 1,
    max: 110,
    showIf: (a) => a.maternalGrandfatherT2dm === 'yes',
  },
  {
    id: 'maternalGrandmotherT2dm',
    type: 'choice',
    section: 'hereditaryMaternal',
    questionKey: 'maternalGrandmotherT2dm',
    options: yesNoUnknown,
  },
  {
    id: 'maternalGrandmotherAgeAtDx',
    type: 'number',
    section: 'hereditaryMaternal',
    questionKey: 'maternalGrandmotherAgeAtDx',
    min: 1,
    max: 110,
    showIf: (a) => a.maternalGrandmotherT2dm === 'yes',
  },
  {
    id: 'maternalUnclesWithT2dm',
    type: 'number',
    section: 'hereditaryMaternal',
    questionKey: 'maternalUnclesWithT2dm',
    min: 0,
    max: 10,
  },
  {
    id: 'maternalAuntsWithT2dm',
    type: 'number',
    section: 'hereditaryMaternal',
    questionKey: 'maternalAuntsWithT2dm',
    min: 0,
    max: 10,
  },
  {
    id: 'maternalAuntsUnclesEarliestAgeAtDx',
    type: 'number',
    section: 'hereditaryMaternal',
    questionKey: 'maternalAuntsUnclesEarliestAgeAtDx',
    min: 1,
    max: 110,
    showIf: (a) => (a.maternalUnclesWithT2dm ?? 0) + (a.maternalAuntsWithT2dm ?? 0) > 0,
  },
  {
    id: 'paternalGrandfatherT2dm',
    type: 'choice',
    section: 'hereditaryPaternal',
    questionKey: 'paternalGrandfatherT2dm',
    options: yesNoUnknown,
  },
  {
    id: 'paternalGrandfatherAgeAtDx',
    type: 'number',
    section: 'hereditaryPaternal',
    questionKey: 'paternalGrandfatherAgeAtDx',
    min: 1,
    max: 110,
    showIf: (a) => a.paternalGrandfatherT2dm === 'yes',
  },
  {
    id: 'paternalGrandmotherT2dm',
    type: 'choice',
    section: 'hereditaryPaternal',
    questionKey: 'paternalGrandmotherT2dm',
    options: yesNoUnknown,
  },
  {
    id: 'paternalGrandmotherAgeAtDx',
    type: 'number',
    section: 'hereditaryPaternal',
    questionKey: 'paternalGrandmotherAgeAtDx',
    min: 1,
    max: 110,
    showIf: (a) => a.paternalGrandmotherT2dm === 'yes',
  },
  {
    id: 'paternalUnclesWithT2dm',
    type: 'number',
    section: 'hereditaryPaternal',
    questionKey: 'paternalUnclesWithT2dm',
    min: 0,
    max: 10,
  },
  {
    id: 'paternalAuntsWithT2dm',
    type: 'number',
    section: 'hereditaryPaternal',
    questionKey: 'paternalAuntsWithT2dm',
    min: 0,
    max: 10,
  },
  {
    id: 'paternalAuntsUnclesEarliestAgeAtDx',
    type: 'number',
    section: 'hereditaryPaternal',
    questionKey: 'paternalAuntsUnclesEarliestAgeAtDx',
    min: 1,
    max: 110,
    showIf: (a) => (a.paternalUnclesWithT2dm ?? 0) + (a.paternalAuntsWithT2dm ?? 0) > 0,
  },
]

export function getVisibleQuestions(answers: AssessmentAnswers): QuestionDef[] {
  return QUESTIONS.filter((q) => (q.showIf ? q.showIf(answers) : true))
}
