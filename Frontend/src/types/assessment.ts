export type Language = 'en' | 'tl';

export type YesNo = 'yes' | 'no';
export type FamilyStatus = 'yes' | 'no' | 'unknown';
export type SiblingStatus = 'yes' | 'no' | 'unknown' | 'no_siblings';
export type BiologicalSex = 'male' | 'female';

export type ActivityLevel = 'low' | 'moderate' | 'high';
export type ExerciseFrequency = 'rarely' | '1_2_week' | '3_4_week' | '5_plus_week';
export type ExerciseDuration = 'under_15' | '15_30' | '30_60' | '60_plus';
export type FoodDrinkFrequency = 'rarely' | 'weekly' | 'several_week' | 'daily';
export type SmokingStatus = 'never' | 'former' | 'current';
export type AlcoholConsumption = 'none' | 'occasional' | 'regular';
export type SleepDuration = 'under_6' | '6_7' | '7_8' | 'over_8';

export interface AssessmentAnswers {
  // F Demographic
  sex?: BiologicalSex;
  age?: number;

  // B Anthropometric
  heightCm?: number;
  weightKg?: number;

  // C Clinical
  hypertension?: YesNo;

  // E Target
  diagnosedT2dm?: YesNo;
  ageAtDiagnosis?: number;

  // Optional blood
  fastingGlucoseMgDl?: number | null;
  hba1cPercent?: number | null;
  fastingGlucoseSkipped?: boolean;
  hba1cSkipped?: boolean;

  // D Lifestyle
  physicalActivityLevel?: ActivityLevel;
  exerciseFrequency?: ExerciseFrequency;
  exerciseDurationMin?: ExerciseDuration;
  sugaryDrinkFrequency?: FoodDrinkFrequency;
  fastFoodFrequency?: FoodDrinkFrequency;
  smokingStatus?: SmokingStatus;
  alcoholConsumption?: AlcoholConsumption;
  sleepDurationHours?: SleepDuration;

  // A First-degree
  fatherT2dm?: FamilyStatus;
  fatherAgeAtDx?: number;
  motherT2dm?: FamilyStatus;
  motherAgeAtDx?: number;
  siblingT2dm?: SiblingStatus;
  siblingAgeAtDx?: number;

  // A Maternal
  maternalGrandfatherT2dm?: FamilyStatus;
  maternalGrandfatherAgeAtDx?: number;
  maternalGrandmotherT2dm?: FamilyStatus;
  maternalGrandmotherAgeAtDx?: number;
  maternalUnclesWithT2dm?: number;
  maternalAuntsWithT2dm?: number;
  maternalAuntsUnclesEarliestAgeAtDx?: number;

  // A Paternal
  paternalGrandfatherT2dm?: FamilyStatus;
  paternalGrandfatherAgeAtDx?: number;
  paternalGrandmotherT2dm?: FamilyStatus;
  paternalGrandmotherAgeAtDx?: number;
  paternalUnclesWithT2dm?: number;
  paternalAuntsWithT2dm?: number;
  paternalAuntsUnclesEarliestAgeAtDx?: number;
}

export type AnswerKey = keyof AssessmentAnswers;

export function computeBmi(heightCm: number, weightKg: number): number {
  const heightM = Math.max(heightCm / 100, 0.1);
  return Math.round((weightKg / (heightM * heightM)) * 10) / 10;
}
