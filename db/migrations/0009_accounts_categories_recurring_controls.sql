alter table if exists accounts
  add column if not exists initial_balance_at timestamptz;

alter table if exists transactions
  add column if not exists recurring_day_of_month integer,
  add column if not exists recurring_weekend_policy text;
