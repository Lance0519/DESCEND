-- Registration consent flags on profiles. Safe to re-run.

alter table public.profiles
  add column if not exists terms_accepted boolean not null default false;

alter table public.profiles
  add column if not exists health_consent_accepted boolean not null default false;

alter table public.profiles
  add column if not exists age_confirmed boolean not null default false;

alter table public.profiles
  add column if not exists consent_timestamp timestamptz;

create or replace function public.handle_new_user()
returns trigger
language plpgsql
security definer
set search_path = public
as $$
begin
  insert into public.profiles (
    id,
    email,
    display_name,
    avatar_url,
    terms_accepted,
    health_consent_accepted,
    age_confirmed,
    consent_timestamp
  )
  values (
    new.id,
    new.email,
    coalesce(new.raw_user_meta_data->>'full_name', new.raw_user_meta_data->>'name', ''),
    new.raw_user_meta_data->>'avatar_url',
    coalesce((new.raw_user_meta_data->>'terms_accepted')::boolean, false),
    coalesce((new.raw_user_meta_data->>'health_consent_accepted')::boolean, false),
    coalesce((new.raw_user_meta_data->>'age_confirmed')::boolean, false),
    nullif(new.raw_user_meta_data->>'consent_timestamp', '')::timestamptz
  )
  on conflict (id) do update
    set email = excluded.email,
        display_name = case
          when excluded.display_name <> '' then excluded.display_name
          else public.profiles.display_name
        end,
        avatar_url = coalesce(excluded.avatar_url, public.profiles.avatar_url),
        terms_accepted = public.profiles.terms_accepted or excluded.terms_accepted,
        health_consent_accepted = public.profiles.health_consent_accepted or excluded.health_consent_accepted,
        age_confirmed = public.profiles.age_confirmed or excluded.age_confirmed,
        consent_timestamp = coalesce(public.profiles.consent_timestamp, excluded.consent_timestamp),
        updated_at = now();
  return new;
end;
$$;

drop trigger if exists on_auth_user_created on auth.users;
create trigger on_auth_user_created
  after insert on auth.users
  for each row execute procedure public.handle_new_user();
