-- Admin email allowlist: any auth user whose email is listed becomes an admin,
-- regardless of which provider they signed in with (email/password, Google, ...).
-- Requires 004_admin_roles.sql. Run in the Supabase SQL editor. Safe to re-run.

create table if not exists public.admin_emails (
  email text primary key,
  note text,
  created_at timestamptz not null default now()
);

comment on table public.admin_emails is
  'Emails promoted to admin automatically on profile insert/update. Manage from the SQL editor only.';

alter table public.admin_emails enable row level security;

-- No anon/authenticated policies: the table is only readable through the
-- security definer trigger below, and only editable from the SQL editor.
drop policy if exists "admin_emails_admin_read" on public.admin_emails;
create policy "admin_emails_admin_read" on public.admin_emails
  for select using (public.is_admin());

create or replace function public.is_admin_email(candidate text)
returns boolean
language sql
stable
security definer
set search_path = public
as $$
  select exists (
    select 1 from public.admin_emails
    where lower(email) = lower(trim(candidate))
  );
$$;

revoke all on function public.is_admin_email(text) from public;

create or replace function public.apply_admin_email_allowlist()
returns trigger
language plpgsql
security definer
set search_path = public
as $$
begin
  if new.email is not null and public.is_admin_email(new.email) then
    new.role := 'admin';
    new.is_active := true;
  end if;
  return new;
end;
$$;

drop trigger if exists profiles_apply_admin_allowlist on public.profiles;
create trigger profiles_apply_admin_allowlist
  before insert or update of email, role on public.profiles
  for each row
  execute procedure public.apply_admin_email_allowlist();

-- Add your admin emails here, then re-run this file (or just this statement).
insert into public.admin_emails (email, note)
values
  ('CHANGE_ME@example.com', 'primary admin')
on conflict (email) do nothing;

-- Backfill anyone who signed up before being allowlisted.
update public.profiles p
set role = 'admin',
    is_active = true
where public.is_admin_email(p.email)
  and (p.role <> 'admin' or p.is_active is not true);
