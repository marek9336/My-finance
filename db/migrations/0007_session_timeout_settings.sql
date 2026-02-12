alter table if exists app_settings
  add column if not exists session_timeout_minutes integer;
