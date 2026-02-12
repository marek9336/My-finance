-- Migration: auth, accounts and transaction details
-- Target DB: PostgreSQL

alter table users
  add column if not exists full_name text;

create table if not exists user_credentials (
  user_id uuid primary key references users(id) on delete cascade,
  password_hash text not null,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table if not exists accounts (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references users(id) on delete cascade,
  name text not null,
  account_type text not null default 'checking',
  currency char(3) not null default 'CZK',
  initial_balance numeric(14,2) not null default 0,
  current_balance numeric(14,2) not null default 0,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create index if not exists idx_accounts_user on accounts(user_id, created_at desc);

alter table transactions
  add column if not exists direction text not null default 'expense',
  add column if not exists category text,
  add column if not exists note text;

create index if not exists idx_transactions_user_time on transactions(user_id, transaction_at desc);
