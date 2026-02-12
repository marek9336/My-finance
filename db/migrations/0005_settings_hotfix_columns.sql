-- Migration hotfix: ensure app_settings has all required columns
-- Target DB: PostgreSQL

alter table if exists app_settings
  add column if not exists default_locale text not null default 'en',
  add column if not exists auto_backup_enabled boolean not null default false,
  add column if not exists auto_backup_interval_minutes integer not null default 1440,
  add column if not exists auto_backup_retention_days integer not null default 30,
  add column if not exists auto_backup_last_run_at timestamptz;
