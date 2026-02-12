-- Migration: app-level settings and custom locale overrides
-- Target DB: PostgreSQL
--
-- Prerequisite:
-- - Existing table: users(id uuid primary key)

create extension if not exists pgcrypto;

create table if not exists app_settings (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null unique references users(id) on delete cascade,
  default_timezone text not null default 'Europe/Prague',
  calendar_provider text not null default 'google',
  calendar_sync_enabled boolean not null default true,
  self_registration_enabled boolean not null default true,
  smtp_enabled boolean not null default false,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table if not exists locale_custom_messages (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references users(id) on delete cascade,
  locale text not null,
  message_key text not null,
  message_value text not null,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique (user_id, locale, message_key)
);

create index if not exists idx_locale_custom_messages_locale
  on locale_custom_messages(user_id, locale);
