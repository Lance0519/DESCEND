-- Dashboard CRUD fields for saved assessments.
-- Safe to re-run. Run after 003_assessment_records.sql.

alter table public.assessments
  add column if not exists label text,
  add column if not exists notes text;

alter table public.patient_survey_records
  add column if not exists label text,
  add column if not exists notes text;

create or replace view public.assessment_records
with (security_invoker = true) as
select
  concat('psr-', id)::text as id,
  user_id,
  created_at,
  risk_percentage::double precision as risk_score,
  risk_band as risk_tier,
  diagnosed_t2dm as pre_diagnosed,
  label,
  notes
from public.patient_survey_records
union all
select
  concat('asm-', id)::text as id,
  user_id,
  created_at,
  percentage::double precision as risk_score,
  risk_band as risk_tier,
  coalesce(diagnosed_t2dm, false) as pre_diagnosed,
  label,
  notes
from public.assessments;

grant select on public.assessment_records to authenticated;
