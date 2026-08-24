-- Admin role on profiles + RLS for admin dashboards.
-- Run in Supabase SQL editor after 001–003. Safe to re-run.

alter table public.profiles
  add column if not exists role text not null default 'user'
    check (role in ('user', 'admin'));

alter table public.profiles
  add column if not exists is_active boolean not null default true;

create index if not exists profiles_role_idx on public.profiles (role);

create or replace function public.is_admin()
returns boolean
language sql
stable
security definer
set search_path = public
as $$
  select exists (
    select 1 from public.profiles
    where id = auth.uid() and role = 'admin' and is_active = true
  );
$$;

revoke all on function public.is_admin() from public;
grant execute on function public.is_admin() to authenticated;

drop policy if exists "profiles_admin_read" on public.profiles;
create policy "profiles_admin_read" on public.profiles
  for select using (public.is_admin());

drop policy if exists "profiles_admin_update" on public.profiles;
create policy "profiles_admin_update" on public.profiles
  for update using (public.is_admin()) with check (public.is_admin());

drop policy if exists "assessments_admin_read" on public.assessments;
create policy "assessments_admin_read" on public.assessments
  for select using (public.is_admin());

drop policy if exists "patient_survey_admin_read" on public.patient_survey_records;
create policy "patient_survey_admin_read" on public.patient_survey_records
  for select using (public.is_admin());

-- Promote an admin after first signup (edit the email, then run):
-- update public.profiles set role = 'admin' where email = 'you@example.com';
