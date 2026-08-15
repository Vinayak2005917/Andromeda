create table if not exists public.profiles (
  id uuid primary key references auth.users(id) on delete cascade,
  username text unique,
  created_at timestamptz not null default now()
);

create table if not exists public.conversations (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references public.profiles(id) on delete cascade,
  title text not null default 'New conversation',
  thread_id text not null unique,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create index if not exists conversations_user_updated_idx
on public.conversations(user_id, updated_at desc);

alter table public.profiles enable row level security;
alter table public.conversations enable row level security;

create policy "users can read own profile" on public.profiles
for select using (auth.uid() = id);

create policy "users can update own profile" on public.profiles
for update using (auth.uid() = id);

create policy "users can read own conversations" on public.conversations
for select using (auth.uid() = user_id);

create policy "users can create own conversations" on public.conversations
for insert with check (auth.uid() = user_id);

create policy "users can update own conversations" on public.conversations
for update using (auth.uid() = user_id);

create policy "users can delete own conversations" on public.conversations
for delete using (auth.uid() = user_id);

create or replace function public.handle_new_user()
returns trigger
language plpgsql
security definer set search_path = ''
as $$
begin
  insert into public.profiles (id, username)
  values (new.id, new.raw_user_meta_data ->> 'name');
  return new;
end;
$$;

drop trigger if exists on_auth_user_created on auth.users;
create trigger on_auth_user_created
after insert on auth.users
for each row execute procedure public.handle_new_user();
