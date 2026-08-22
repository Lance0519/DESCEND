-- DESCEND Supabase schema (run in Supabase SQL editor)
-- Mirrors app tables; RLS for client-side access. Flask also keeps SQLite mirrors for local/dev.

create table if not exists public.profiles (
  id uuid primary key references auth.users(id) on delete cascade,
  email text,
  display_name text,
  preferred_lang text default 'tl',
  sex text,
  age int,
  avatar_url text,
  created_at timestamptz default now(),
  updated_at timestamptz default now()
);

create table if not exists public.assessments (
  id bigserial primary key,
  user_id uuid references auth.users(id) on delete set null,
  answers jsonb,
  result jsonb,
  soft_adjustment jsonb,
  percentage numeric,
  risk_band text,
  created_at timestamptz default now()
);

create table if not exists public.assessment_drafts (
  user_id uuid primary key references auth.users(id) on delete cascade,
  draft jsonb not null,
  updated_at timestamptz default now()
);

alter table public.profiles enable row level security;
alter table public.assessments enable row level security;
alter table public.assessment_drafts enable row level security;

create policy "profiles_own" on public.profiles
  for all using (auth.uid() = id) with check (auth.uid() = id);

create policy "assessments_own" on public.assessments
  for all using (auth.uid() = user_id) with check (auth.uid() = user_id);

create policy "drafts_own" on public.assessment_drafts
  for all using (auth.uid() = user_id) with check (auth.uid() = user_id);

-- Auto-create profile on signup
create or replace function public.handle_new_user()
returns trigger
language plpgsql
security definer set search_path = public
as $$
begin
  insert into public.profiles (id, email, display_name, avatar_url)
  values (
    new.id,
    new.email,
    coalesce(new.raw_user_meta_data->>'full_name', ''),
    new.raw_user_meta_data->>'avatar_url'
  )
  on conflict (id) do nothing;
  return new;
end;
$$;

drop trigger if exists on_auth_user_created on auth.users;
create trigger on_auth_user_created
  after insert on auth.users
  for each row execute procedure public.handle_new_user();
