import type { AssessmentAnswers } from '../types/assessment'

/** Maps DESCEND answers to the backend predict payload (Track 2). */
export function mapPayload(answers: AssessmentAnswers) {
  const physicalActivityScore = derivePhysicalActivityScore(answers)
  const dietQualityScore = deriveDietQualityScore(answers)

  const maternalDiabetes =
    (answers.maternalUnclesWithT2dm ?? 0) + (answers.maternalAuntsWithT2dm ?? 0)
  const paternalDiabetes =
    (answers.paternalUnclesWithT2dm ?? 0) + (answers.paternalAuntsWithT2dm ?? 0)

  return {
    personalInfo: {
      age: answers.age ?? 30,
      sex: answers.sex ?? 'female',
      heightCm: answers.heightCm ?? 160,
      weightKg: answers.weightKg ?? 60,
      diagnosedT2dm: answers.diagnosedT2dm ?? 'no',
      diagnosedHypertension: answers.hypertension ?? 'no',
      isFilipino: 'yes',
      diagnosedT2dmConfirmationMethod:
        answers.diagnosedT2dm === 'yes' ? 'doctor_diagnosis' : 'not_applicable',
      fatherHypertension: 'unsure',
      motherHypertension: 'unsure',
    },
    familyHistory: {
      maternalGrandmother: answers.maternalGrandmotherT2dm ?? 'unknown',
      maternalGrandfather: answers.maternalGrandfatherT2dm ?? 'unknown',
      paternalGrandmother: answers.paternalGrandmotherT2dm ?? 'unknown',
      paternalGrandfather: answers.paternalGrandfatherT2dm ?? 'unknown',
      mother: answers.motherT2dm ?? 'unknown',
      father: answers.fatherT2dm ?? 'unknown',
      motherGdmDuringIndexPregnancy: 'unsure',
      siblingsCount: answers.siblingT2dm === 'no_siblings' ? 0 : 1,
      siblingsDiabetesCount: answers.siblingT2dm === 'yes' ? 1 : 0,
      siblingsHypertensionCount: 0,
      paternalAuntsUnclesCount: Math.max(paternalDiabetes, paternalDiabetes),
      paternalAuntsUnclesDiabetesCount: paternalDiabetes,
      maternalAuntsUnclesCount: Math.max(maternalDiabetes, maternalDiabetes),
      maternalAuntsUnclesDiabetesCount: maternalDiabetes,
      physicalActivityScore,
      dietQualityScore,
    },
    diagnosisAges: {
      self: answers.ageAtDiagnosis ?? null,
      father: answers.fatherAgeAtDx ?? null,
      mother: answers.motherAgeAtDx ?? null,
      sibling: answers.siblingAgeAtDx ?? null,
      maternalGrandfather: answers.maternalGrandfatherAgeAtDx ?? null,
      maternalGrandmother: answers.maternalGrandmotherAgeAtDx ?? null,
      paternalGrandfather: answers.paternalGrandfatherAgeAtDx ?? null,
      paternalGrandmother: answers.paternalGrandmotherAgeAtDx ?? null,
      maternalAuntsUnclesEarliest: answers.maternalAuntsUnclesEarliestAgeAtDx ?? null,
      paternalAuntsUnclesEarliest: answers.paternalAuntsUnclesEarliestAgeAtDx ?? null,
    },
    lifestyle: {
      physicalActivityLevel: answers.physicalActivityLevel ?? null,
      exerciseFrequency: answers.exerciseFrequency ?? null,
      exerciseDurationMin: answers.exerciseDurationMin ?? null,
      sugaryDrinkFrequency: answers.sugaryDrinkFrequency ?? null,
      fastFoodFrequency: answers.fastFoodFrequency ?? null,
      smokingStatus: answers.smokingStatus ?? null,
      alcoholConsumption: answers.alcoholConsumption ?? null,
      sleepDurationHours: answers.sleepDurationHours ?? null,
    },
    labs: {
      fastingGlucoseMgDl: answers.fastingGlucoseSkipped ? null : (answers.fastingGlucoseMgDl ?? null),
      hba1cPercent: answers.hba1cSkipped ? null : (answers.hba1cPercent ?? null),
    },
  }
}

function derivePhysicalActivityScore(answers: AssessmentAnswers): 1 | 2 | 3 | 4 {
  if (answers.exerciseFrequency === '5_plus_week') return 4
  if (answers.exerciseFrequency === '3_4_week') return 3
  if (answers.exerciseFrequency === '1_2_week') return 2
  if (answers.physicalActivityLevel === 'high') return 3
  if (answers.physicalActivityLevel === 'moderate') return 2
  return 1
}

function deriveDietQualityScore(answers: AssessmentAnswers): 1 | 2 | 3 {
  const sugary = answers.sugaryDrinkFrequency
  const fast = answers.fastFoodFrequency
  if (sugary === 'daily' || fast === 'daily') return 1
  if (sugary === 'several_week' || fast === 'several_week') return 1
  if (sugary === 'weekly' || fast === 'weekly') return 2
  return 3
}
