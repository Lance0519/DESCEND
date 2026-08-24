-- Make signup always create a profiles row. Safe to re-run.
-- Does not require 004_admin_roles.sql (role / is_active stay at table defaults if those columns exist).

create or replace function public.handle_new_user()
returns trigger
language plpgsql
security definer
set search_path = public
as $$
begin
  insert into public.profiles (id, email, display_name, avatar_url)
  values (
    new.id,
    new.email,
    coalesce(new.raw_user_meta_data->>'full_name', new.raw_user_meta_data->>'name', ''),
    new.raw_user_meta_data->>'avatar_url'
  )
  on conflict (id) do update
    set email = excluded.email,
        display_name = case
          when excluded.display_name <> '' then excluded.display_name
          else public.profiles.display_name
        end,
        avatar_url = coalesce(excluded.avatar_url, public.profiles.avatar_url),
        updated_at = now();
  return new;
end;
$$;

drop trigger if exists on_auth_user_created on auth.users;
create trigger on_auth_user_created
  after insert on auth.users
  for each row execute procedure public.handle_new_user();

grant usage on schema public to anon, authenticated;
grant select, insert, update on table public.profiles to authenticated;
