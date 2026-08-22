-- Patient survey records with strict typed columns for diagnosed vs undiagnosed profiles.
-- Run in Supabase SQL editor after 001_descend_schema.sql. Safe to re-run.

create table if not exists public.patient_survey_records (
  id bigserial primary key,
  user_id uuid references auth.users(id) on delete set null,

  -- Profile branch (strict)
  diagnosed_t2dm boolean not null,
  age_of_onset integer
    check (age_of_onset is null or (age_of_onset >= 1 and age_of_onset <= 120)),

  -- Numerical survey answers (undiagnosed path; nullable when diagnosed)
  age integer check (age is null or (age >= 1 and age <= 120)),
  height_cm numeric(6, 2) check (height_cm is null or (height_cm >= 50 and height_cm <= 250)),
  weight_kg numeric(6, 2) check (weight_kg is null or (weight_kg >= 20 and weight_kg <= 400)),
  hypertension boolean,
  physical_activity_score smallint check (physical_activity_score is null or (physical_activity_score between 1 and 4)),
  diet_quality_score smallint check (diet_quality_score is null or (diet_quality_score between 1 and 3)),
  fasting_glucose_mg_dl numeric(6, 2),
  hba1c_percent numeric(4, 2),
  maternal_aunts_uncles_diabetes_count integer default 0,
  paternal_aunts_uncles_diabetes_count integer default 0,
  siblings_diabetes_count integer default 0,

  -- Calculated metrics
  bmi numeric(5, 2),
  weighted_family_score numeric(10, 4),
  risk_percentage numeric(5, 2),
  risk_probability numeric(8, 6),
  risk_band text,

  -- Normalized ExtraTrees feature row (undiagnosed only)
  feature_vector jsonb,

  -- Full payload / response for future improvement
  answers_json jsonb,
  result_json jsonb,

  created_at timestamptz not null default now(),

  constraint patient_survey_onset_consistency check (
    (diagnosed_t2dm = false)
    or (diagnosed_t2dm = true and age_of_onset is not null)
  )
);

create index if not exists patient_survey_records_user_id_idx
  on public.patient_survey_records (user_id);

create index if not exists patient_survey_records_diagnosed_idx
  on public.patient_survey_records (diagnosed_t2dm);

alter table public.patient_survey_records enable row level security;

drop policy if exists "patient_survey_own" on public.patient_survey_records;
create policy "patient_survey_own" on public.patient_survey_records
  for all using (auth.uid() = user_id) with check (auth.uid() = user_id);

-- Typed columns on legacy assessments table (additive; JSON remains for compatibility)
alter table public.assessments
  add column if not exists diagnosed_t2dm boolean,
  add column if not exists age_of_onset integer
    check (age_of_onset is null or (age_of_onset >= 1 and age_of_onset <= 120));
