-- Audit log retention: entries older than 6 months are deleted.
-- Requires 007_audit_logs.sql. Run in the Supabase SQL editor. Safe to re-run.

create or replace function public.purge_audit_logs()
returns integer
language plpgsql
security definer
set search_path = public
as $$
declare
  removed integer;
begin
  delete from public.audit_logs
  where created_at < now() - interval '6 months';
  get diagnostics removed = row_count;
  return removed;
end;
$$;

comment on function public.purge_audit_logs() is
  'Deletes audit_logs rows older than 6 months. Callable by admins; also scheduled via pg_cron when available.';

revoke all on function public.purge_audit_logs() from public;

-- Admin-only wrapper so the dashboard can trigger a purge without owning delete rights.
create or replace function public.purge_audit_logs_as_admin()
returns integer
language plpgsql
security definer
set search_path = public
as $$
begin
  if not public.is_admin() then
    raise exception 'admin required';
  end if;
  return public.purge_audit_logs();
end;
$$;

revoke all on function public.purge_audit_logs_as_admin() from public;
grant execute on function public.purge_audit_logs_as_admin() to authenticated;

-- Remove anything already past the window.
select public.purge_audit_logs();

-- Optional: run the purge nightly without relying on an admin visiting the dashboard.
-- Requires the pg_cron extension (Database → Extensions → enable "pg_cron").
--
--   select cron.schedule(
--     'purge-audit-logs-daily',
--     '15 3 * * *',
--     $$select public.purge_audit_logs();$$
--   );
--
-- To remove the schedule:
--
--   select cron.unschedule('purge-audit-logs-daily');
