-- Migration: minimal core prerequisites for standalone setup
-- Target DB: PostgreSQL

create extension if not exists pgcrypto;

create table if not exists users (
  id uuid primary key,
  email text unique,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table if not exists recurring_templates (
  id uuid primary key default gen_random_uuid(),
  user_id uuid references users(id) on delete cascade,
  title text,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table if not exists transactions (
  id uuid primary key default gen_random_uuid(),
  user_id uuid references users(id) on delete cascade,
  account_id uuid,
  amount numeric(14,2),
  currency char(3),
  transaction_at timestamptz,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

insert into users (id, email)
values ('00000000-0000-0000-0000-000000000001', 'default@local')
on conflict (id) do nothing;
