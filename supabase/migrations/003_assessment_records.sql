-- Compatibility view exposing a stable AssessmentRecord shape for the user dashboard.
-- Safe to re-run. Underlying table RLS applies via security_invoker.

create or replace view public.assessment_records
with (security_invoker = true) as
select
  concat('psr-', id)::text as id,
  user_id,
  created_at,
  risk_percentage::double precision as risk_score,
  risk_band as risk_tier,
  diagnosed_t2dm as pre_diagnosed
from public.patient_survey_records
union all
select
  concat('asm-', id)::text as id,
  user_id,
  created_at,
  percentage::double precision as risk_score,
  risk_band as risk_tier,
  coalesce(diagnosed_t2dm, false) as pre_diagnosed
from public.assessments;

grant select on public.assessment_records to authenticated;
