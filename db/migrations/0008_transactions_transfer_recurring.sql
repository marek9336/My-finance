alter table if exists transactions
  add column if not exists transfer_group_id uuid,
  add column if not exists recurring_group_id uuid,
  add column if not exists recurring_frequency text,
  add column if not exists recurring_index integer;

create index if not exists idx_transactions_user_category on transactions(user_id, category);
create index if not exists idx_transactions_transfer_group on transactions(transfer_group_id);
