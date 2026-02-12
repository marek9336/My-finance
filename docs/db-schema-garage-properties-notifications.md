# Detailni DB navrh: garaz, nemovitosti, notifikace, Google Calendar

Tento dokument rozsiruje `README.md` o konkretni navrh databazovych tabulek pro PostgreSQL.
Zamereni: vozidla + servis, nemovitosti + naklady + pojisteni, notifikace a synchronizace do Google Kalendare.

## 1) Predpoklady

- Primarni klice jsou `uuid`.
- Casova razitka jsou `timestamptz`.
- Penize jsou `numeric(14,2)`.
- Kilometry jsou `integer`.
- Mena je `char(3)` (ISO kod, napr. `CZK`, `EUR`).

## 2) Typy (enum)

```sql
create type vehicle_type as enum ('car', 'motorcycle', 'other');
create type service_rule_unit as enum ('days', 'months', 'km');
create type property_type as enum ('house', 'apartment', 'land', 'other');
create type insurance_type as enum ('vehicle', 'property', 'household', 'liability', 'life', 'other');
create type notification_channel as enum ('in_app', 'email', 'google_calendar');
create type notification_status as enum ('pending', 'sent', 'failed', 'canceled');
create type reminder_source as enum ('manual', 'service_rule', 'insurance', 'tax', 'recurring_payment');
```

## 3) Vozidla a servis

```sql
create table vehicles (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references users(id) on delete cascade,
  type vehicle_type not null,
  label text not null, -- napr. "Skoda Octavia 2.0 TDI"
  vin text,
  plate_number text,
  make text,
  model text,
  production_year integer,
  purchased_at date,
  current_odometer_km integer not null default 0 check (current_odometer_km >= 0),
  notes text,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique (user_id, vin),
  unique (user_id, plate_number)
);

create table vehicle_services (
  id uuid primary key default gen_random_uuid(),
  vehicle_id uuid not null references vehicles(id) on delete cascade,
  service_type text not null, -- oil_change, brake_pads, stk, insurance_payment...
  service_at date not null,
  odometer_km integer check (odometer_km is null or odometer_km >= 0),
  total_cost numeric(14,2) check (total_cost is null or total_cost >= 0),
  currency char(3),
  vendor text,
  description text,
  receipt_url text,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create index idx_vehicle_services_vehicle_date on vehicle_services(vehicle_id, service_at desc);
create index idx_vehicle_services_vehicle_km on vehicle_services(vehicle_id, odometer_km desc);

create table vehicle_service_rules (
  id uuid primary key default gen_random_uuid(),
  vehicle_id uuid not null references vehicles(id) on delete cascade,
  service_type text not null,
  interval_value integer not null check (interval_value > 0),
  interval_unit service_rule_unit not null,
  lead_days integer not null default 14 check (lead_days >= 0),
  last_service_id uuid references vehicle_services(id) on delete set null,
  next_due_date date,
  next_due_odometer_km integer check (next_due_odometer_km is null or next_due_odometer_km >= 0),
  is_active boolean not null default true,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique (vehicle_id, service_type, interval_unit)
);

create index idx_vehicle_service_rules_due_date on vehicle_service_rules(next_due_date) where is_active = true;
create index idx_vehicle_service_rules_due_km on vehicle_service_rules(next_due_odometer_km) where is_active = true;
```

## 4) Nemovitosti, naklady, pojisteni

```sql
create table properties (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references users(id) on delete cascade,
  type property_type not null,
  name text not null, -- "Rodinny dum Brno"
  address_line1 text,
  city text,
  postal_code text,
  country_code char(2) default 'CZ',
  acquired_at date,
  purchase_price numeric(14,2),
  purchase_currency char(3),
  estimated_value numeric(14,2),
  estimated_value_currency char(3),
  estimated_value_updated_at date,
  floor_area_m2 numeric(10,2),
  land_area_m2 numeric(10,2),
  notes text,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table property_costs (
  id uuid primary key default gen_random_uuid(),
  property_id uuid not null references properties(id) on delete cascade,
  cost_type text not null, -- electricity, water, gas, internet, hoa, maintenance...
  period_start date not null,
  period_end date not null,
  amount numeric(14,2) not null check (amount >= 0),
  currency char(3) not null,
  provider text,
  meter_value numeric(14,3),
  meter_unit text, -- kWh, m3...
  is_recurring boolean not null default false,
  recurring_template_id uuid references recurring_templates(id) on delete set null,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  check (period_end >= period_start)
);

create index idx_property_costs_property_period on property_costs(property_id, period_start desc);
create index idx_property_costs_type_period on property_costs(cost_type, period_start desc);

create table insurances (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references users(id) on delete cascade,
  insurance_type insurance_type not null,
  provider text not null,
  policy_number text,
  subject_vehicle_id uuid references vehicles(id) on delete set null,
  subject_property_id uuid references properties(id) on delete set null,
  coverage_amount numeric(14,2),
  coverage_currency char(3),
  deductible_amount numeric(14,2),
  deductible_currency char(3),
  valid_from date,
  valid_to date,
  payment_frequency text, -- monthly/quarterly/yearly
  is_active boolean not null default true,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  check (
    subject_vehicle_id is not null
    or subject_property_id is not null
    or insurance_type in ('liability', 'life', 'other')
  )
);

create index idx_insurances_user_active on insurances(user_id, is_active);
create index idx_insurances_valid_to on insurances(valid_to) where is_active = true;

create table insurance_premiums (
  id uuid primary key default gen_random_uuid(),
  insurance_id uuid not null references insurances(id) on delete cascade,
  period_start date not null,
  period_end date not null,
  amount numeric(14,2) not null check (amount >= 0),
  currency char(3) not null,
  paid_at date,
  payment_transaction_id uuid references transactions(id) on delete set null,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  check (period_end >= period_start)
);

create index idx_insurance_premiums_insurance_period on insurance_premiums(insurance_id, period_start desc);
```

## 5) Notifikace a Google Calendar sync

```sql
create table calendar_integrations (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references users(id) on delete cascade,
  provider text not null, -- "google"
  external_calendar_id text not null,
  access_token_encrypted text not null,
  refresh_token_encrypted text not null,
  token_expires_at timestamptz,
  sync_enabled boolean not null default true,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique (user_id, provider, external_calendar_id)
);

create table notification_rules (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references users(id) on delete cascade,
  source reminder_source not null,
  source_entity_id uuid not null, -- napr. vehicle_service_rules.id, insurance.id
  title_template text not null,
  message_template text,
  due_at timestamptz not null,
  lead_days integer not null default 7 check (lead_days >= 0),
  channel notification_channel not null,
  timezone text not null default 'Europe/Prague',
  is_active boolean not null default true,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create index idx_notification_rules_due_at on notification_rules(due_at) where is_active = true;
create index idx_notification_rules_source on notification_rules(source, source_entity_id);

create table notification_deliveries (
  id uuid primary key default gen_random_uuid(),
  notification_rule_id uuid not null references notification_rules(id) on delete cascade,
  scheduled_for timestamptz not null,
  delivered_at timestamptz,
  status notification_status not null default 'pending',
  attempts integer not null default 0 check (attempts >= 0),
  error_message text,
  provider_message_id text, -- id e-mailu nebo push notifikace
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create index idx_notification_deliveries_pending on notification_deliveries(status, scheduled_for);

create table calendar_events (
  id uuid primary key default gen_random_uuid(),
  notification_rule_id uuid not null references notification_rules(id) on delete cascade,
  calendar_integration_id uuid not null references calendar_integrations(id) on delete cascade,
  provider_event_id text not null, -- Google event.id
  event_uid text not null, -- interni stabilni klic pro idempotenci
  event_hash text not null, -- hash payloadu; pokud se zmeni, provede se update
  last_synced_at timestamptz not null default now(),
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique (calendar_integration_id, event_uid),
  unique (calendar_integration_id, provider_event_id)
);
```

## 6) Pravidla idempotence (dulezite pro Google Kalendar)

- `event_uid` je stabilni klic typu: `<source>:<source_entity_id>:<due_date>`.
- Pri sync jobu:
  1. Vypocitat payload a jeho `event_hash`.
  2. Pokud `event_uid` neexistuje: vytvorit event v Google + ulozit mapovani.
  3. Pokud existuje a hash je stejny: nic nemenit.
  4. Pokud existuje a hash je jiny: aktualizovat existujici Google event.
- Pri zruseni pravidla (`is_active=false`) event smazat nebo oznacit `canceled`.

## 7) Minimalni API mapovani (backend)

- `POST /vehicles`
- `POST /vehicles/{id}/services`
- `POST /vehicles/{id}/service-rules`
- `POST /properties`
- `POST /properties/{id}/costs`
- `POST /insurances`
- `POST /insurances/{id}/premiums`
- `POST /integrations/google-calendar/connect`
- `POST /notification-rules`
- `POST /sync/google-calendar/run`

## 8) Poznamky k implementaci

- Tokeny (`access_token_encrypted`, `refresh_token_encrypted`) sifrovat na aplikacni vrstve.
- Na tabulkach s castymi updaty (`notification_deliveries`, `calendar_events`) drzet jednoduche indexy.
- Na `vehicle_service_rules` periodicky prepocitavat `next_due_date` a `next_due_odometer_km` po kazdem novem servisu.
- Pro financni reporty agregovat `property_costs` a `insurance_premiums` po mesicich/rocich.
