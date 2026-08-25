-- Scoped audit trail for sensitive actions (admin role/status, assessment deletes).
-- Requires 004_admin_roles.sql (public.is_admin). Safe to re-run.

create table if not exists public.audit_logs (
  id bigserial primary key,
  actor_id uuid references auth.users(id) on delete set null,
  action text not null,
  target_type text not null,
  target_id text,
  metadata jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now()
);

create index if not exists audit_logs_created_at_idx
  on public.audit_logs (created_at desc);

create index if not exists audit_logs_action_idx
  on public.audit_logs (action);

create index if not exists audit_logs_actor_id_idx
  on public.audit_logs (actor_id);

alter table public.audit_logs enable row level security;

drop policy if exists "audit_logs_admin_read" on public.audit_logs;
create policy "audit_logs_admin_read" on public.audit_logs
  for select using (public.is_admin());

-- No direct client inserts; writes go through security definer helpers/triggers.
revoke insert, update, delete on public.audit_logs from anon, authenticated;
grant select on public.audit_logs to authenticated;

create or replace function public.insert_audit_log(
  p_actor_id uuid,
  p_action text,
  p_target_type text,
  p_target_id text,
  p_metadata jsonb default '{}'::jsonb
)
returns void
language plpgsql
security definer
set search_path = public
as $$
begin
  insert into public.audit_logs (actor_id, action, target_type, target_id, metadata)
  values (
    p_actor_id,
    p_action,
    p_target_type,
    p_target_id,
    coalesce(p_metadata, '{}'::jsonb)
  );
end;
$$;

revoke all on function public.insert_audit_log(uuid, text, text, text, jsonb) from public;
-- Intentionally not granted to authenticated: only security-definer triggers/RPC may call it.

-- Explicit audit write for actions without a natural row trigger (e.g. password reset email).
create or replace function public.write_audit_log(
  p_action text,
  p_target_type text,
  p_target_id text default null,
  p_metadata jsonb default '{}'::jsonb
)
returns void
language plpgsql
security definer
set search_path = public
as $$
begin
  if auth.uid() is null then
    raise exception 'authentication required';
  end if;
  if p_action not in ('password_reset_sent') then
    raise exception 'unsupported audit action';
  end if;
  if not public.is_admin() then
    raise exception 'admin required';
  end if;

  perform public.insert_audit_log(
    auth.uid(),
    p_action,
    p_target_type,
    p_target_id,
    coalesce(p_metadata, '{}'::jsonb)
  );
end;
$$;

revoke all on function public.write_audit_log(text, text, text, jsonb) from public;
grant execute on function public.write_audit_log(text, text, text, jsonb) to authenticated;

create or replace function public.audit_profile_sensitive_change()
returns trigger
language plpgsql
security definer
set search_path = public
as $$
declare
  meta jsonb := '{}'::jsonb;
begin
  if tg_op = 'UPDATE' then
    if new.role is distinct from old.role then
      meta := jsonb_build_object(
        'before', old.role,
        'after', new.role,
        'email', coalesce(new.email, old.email)
      );
      perform public.insert_audit_log(
        auth.uid(),
        'role_change',
        'profile',
        new.id::text,
        meta
      );
    end if;

    if new.is_active is distinct from old.is_active then
      meta := jsonb_build_object(
        'before', old.is_active,
        'after', new.is_active,
        'email', coalesce(new.email, old.email)
      );
      perform public.insert_audit_log(
        auth.uid(),
        case when new.is_active then 'account_enable' else 'account_disable' end,
        'profile',
        new.id::text,
        meta
      );
    end if;
  end if;
  return new;
end;
$$;

drop trigger if exists audit_profiles_sensitive on public.profiles;
create trigger audit_profiles_sensitive
  after update of role, is_active on public.profiles
  for each row
  execute procedure public.audit_profile_sensitive_change();

create or replace function public.audit_assessment_delete()
returns trigger
language plpgsql
security definer
set search_path = public
as $$
begin
  perform public.insert_audit_log(
    auth.uid(),
    'assessment_delete',
    tg_table_name,
    old.id::text,
    jsonb_build_object(
      'user_id', old.user_id,
      'risk_band', coalesce(
        to_jsonb(old) ->> 'risk_band',
        null
      ),
      'label', coalesce(to_jsonb(old) ->> 'label', null)
    )
  );
  return old;
end;
$$;

drop trigger if exists audit_assessments_delete on public.assessments;
create trigger audit_assessments_delete
  after delete on public.assessments
  for each row
  execute procedure public.audit_assessment_delete();

drop trigger if exists audit_patient_survey_delete on public.patient_survey_records;
create trigger audit_patient_survey_delete
  after delete on public.patient_survey_records
  for each row
  execute procedure public.audit_assessment_delete();
