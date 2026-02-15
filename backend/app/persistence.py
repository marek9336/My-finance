from __future__ import annotations

from calendar import monthrange
from datetime import date, datetime, timedelta
from decimal import Decimal
from typing import Any
from uuid import UUID, uuid4

from fastapi import HTTPException
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine
from sqlalchemy.exc import SQLAlchemyError

from .config import settings
from .auth_utils import hash_password, verify_password
from .schemas import (
    AccountDeleteAction,
    AccountCreate,
    AccountUpdate,
    AppSettings,
    AppSettingsUpdate,
    GoogleCalendarConnectRequest,
    InsuranceCreate,
    InsurancePremiumCreate,
    NotificationRuleCreate,
    PropertyCostCreate,
    PropertyCreate,
    RateSnapshotUpsert,
    RatesWatchlistUpdate,
    TransactionCategoryStatsResponse,
    TransactionCategoryRename,
    TransactionCreate,
    TransactionTransferCreate,
    TransactionUpdate,
    VehicleCreate,
    VehicleServiceCreate,
    VehicleServiceRuleCreate,
)
from .store import store


def _to_float(value: Decimal | None) -> float | None:
    return float(value) if value is not None else None


def _tx_sign(direction: str) -> Decimal:
    return Decimal("1") if direction == "income" else Decimal("-1")


def _move_from_weekend(moment: datetime, weekend_policy: str | None) -> datetime:
    policy = (weekend_policy or "exact").lower()
    weekday = moment.weekday()
    if weekday < 5 or policy == "exact":
        return moment
    if policy == "monday":
        return moment + timedelta(days=(7 - weekday))
    if policy == "friday":
        return moment - timedelta(days=weekday - 4)
    if policy == "thursday":
        return moment - timedelta(days=weekday - 3)
    return moment


def _add_months(base: datetime, months: int, day_anchor: int | None = None) -> datetime:
    total_month = (base.month - 1) + months
    year = base.year + total_month // 12
    month = (total_month % 12) + 1
    target_day = day_anchor or base.day
    target_day = min(target_day, monthrange(year, month)[1])
    return base.replace(year=year, month=month, day=target_day)


def _shift_recurring(base: datetime, frequency: str, step: int, day_anchor: int | None = None, weekend_policy: str | None = None) -> datetime:
    if frequency == "daily":
        return _move_from_weekend(base + timedelta(days=step), weekend_policy)
    if frequency == "weekly":
        return _move_from_weekend(base + timedelta(days=step * 7), weekend_policy)
    if frequency == "monthly":
        return _move_from_weekend(_add_months(base, step, day_anchor), weekend_policy)
    if frequency == "yearly":
        return _move_from_weekend(_add_months(base, step * 12, day_anchor), weekend_policy)
    return _move_from_weekend(base, weekend_policy)


class Persistence:
    def get_app_settings(self, user_id: UUID) -> AppSettings:
        raise NotImplementedError

    def update_app_settings(self, user_id: UUID, payload: AppSettingsUpdate) -> AppSettings:
        raise NotImplementedError

    def export_backup(self, user_id: UUID) -> dict[str, Any]:
        raise NotImplementedError

    def import_backup(self, user_id: UUID, payload: dict[str, Any]) -> dict[str, int]:
        raise NotImplementedError

    def mark_auto_backup_run(self, user_id: UUID, when: datetime) -> None:
        raise NotImplementedError

    def register_user(self, email: str, password: str, full_name: str | None) -> dict[str, Any]:
        raise NotImplementedError

    def authenticate_user(self, email: str, password: str) -> dict[str, Any] | None:
        raise NotImplementedError

    def get_user_by_id(self, user_id: UUID) -> dict[str, Any] | None:
        raise NotImplementedError

    def update_user_profile(self, user_id: UUID, email: str | None, full_name: str | None) -> dict[str, Any]:
        raise NotImplementedError

    def change_user_password(self, user_id: UUID, current_password: str, new_password: str) -> None:
        raise NotImplementedError

    def list_locales(self, user_id: UUID) -> list[str]:
        raise NotImplementedError

    def get_locale_bundle(self, user_id: UUID, locale: str) -> dict[str, str]:
        raise NotImplementedError

    def get_custom_locale(self, user_id: UUID, locale: str) -> dict[str, str]:
        raise NotImplementedError

    def upsert_custom_locale(self, user_id: UUID, locale: str, payload: dict[str, str]) -> dict[str, str]:
        raise NotImplementedError

    def get_rates_state(self, user_id: UUID) -> dict[str, Any]:
        raise NotImplementedError

    def update_rates_watchlist(self, user_id: UUID, payload: RatesWatchlistUpdate) -> dict[str, Any]:
        raise NotImplementedError

    def upsert_rate_snapshot(self, user_id: UUID, payload: RateSnapshotUpsert) -> dict[str, Any]:
        raise NotImplementedError

    def delete_rate_symbol(self, user_id: UUID, symbol: str) -> dict[str, Any]:
        raise NotImplementedError

    def create_account(self, user_id: UUID, payload: AccountCreate) -> dict[str, Any]:
        raise NotImplementedError

    def list_accounts(self, user_id: UUID) -> list[dict[str, Any]]:
        raise NotImplementedError

    def create_transaction(self, user_id: UUID, payload: TransactionCreate) -> dict[str, Any]:
        raise NotImplementedError

    def list_transactions(self, user_id: UUID) -> list[dict[str, Any]]:
        raise NotImplementedError

    def update_account(self, user_id: UUID, account_id: UUID, payload: AccountUpdate) -> dict[str, Any]:
        raise NotImplementedError

    def delete_account(self, user_id: UUID, account_id: UUID, action: AccountDeleteAction, target_account_id: UUID | None = None) -> None:
        raise NotImplementedError

    def update_transaction(self, user_id: UUID, transaction_id: UUID, payload: TransactionUpdate) -> dict[str, Any]:
        raise NotImplementedError

    def delete_transaction(self, user_id: UUID, transaction_id: UUID) -> None:
        raise NotImplementedError

    def transfer_between_accounts(self, user_id: UUID, payload: TransactionTransferCreate) -> dict[str, Any]:
        raise NotImplementedError

    def list_transaction_category_stats(self, user_id: UUID) -> TransactionCategoryStatsResponse:
        raise NotImplementedError

    def rename_transaction_category(self, user_id: UUID, category: str, payload: TransactionCategoryRename) -> TransactionCategoryStatsResponse:
        raise NotImplementedError

    def delete_transaction_category(self, user_id: UUID, category: str, delete_transactions: bool) -> TransactionCategoryStatsResponse:
        raise NotImplementedError

    def delete_user(self, user_id: UUID) -> None:
        raise NotImplementedError


class InMemoryPersistence(Persistence):
    def get_app_settings(self, user_id: UUID) -> AppSettings:
        return AppSettings(**store.settings)

    def update_app_settings(self, user_id: UUID, payload: AppSettingsUpdate) -> AppSettings:
        store.settings.update(payload.model_dump(exclude_unset=True))
        return AppSettings(**store.settings)

    def list_locales(self, user_id: UUID) -> list[str]:
        return sorted(set(store.base_locales.keys()) | set(store.custom_locales.keys()))

    def get_locale_bundle(self, user_id: UUID, locale: str) -> dict[str, str]:
        return {**store.base_locales.get(locale, {}), **store.custom_locales.get(locale, {})}

    def get_custom_locale(self, user_id: UUID, locale: str) -> dict[str, str]:
        return store.custom_locales.get(locale, {})

    def upsert_custom_locale(self, user_id: UUID, locale: str, payload: dict[str, str]) -> dict[str, str]:
        if locale not in store.custom_locales:
            store.custom_locales[locale] = {}
        store.custom_locales[locale].update(payload)
        return self.get_locale_bundle(user_id, locale)

    def get_rates_state(self, user_id: UUID) -> dict[str, Any]:
        watch = store.rate_watchlists.get(user_id, [])
        snaps = store.rate_snapshots.get(user_id, {})
        return {"watchlist": watch, "snapshots": snaps}

    def update_rates_watchlist(self, user_id: UUID, payload: RatesWatchlistUpdate) -> dict[str, Any]:
        watch = payload.symbols
        store.rate_watchlists[user_id] = watch
        existing = store.rate_snapshots.get(user_id, {})
        store.rate_snapshots[user_id] = {sym: existing[sym] for sym in watch if sym in existing}
        return self.get_rates_state(user_id)

    def upsert_rate_snapshot(self, user_id: UUID, payload: RateSnapshotUpsert) -> dict[str, Any]:
        sym = payload.symbol
        if user_id not in store.rate_watchlists:
            store.rate_watchlists[user_id] = []
        if sym not in store.rate_watchlists[user_id]:
            store.rate_watchlists[user_id].append(sym)
        if user_id not in store.rate_snapshots:
            store.rate_snapshots[user_id] = {}
        store.rate_snapshots[user_id][sym] = {
            "symbol": sym,
            "price": payload.price,
            "currency": payload.currency,
            "source": payload.source,
            "updatedAt": payload.updatedAt or datetime.utcnow(),
        }
        return self.get_rates_state(user_id)

    def delete_rate_symbol(self, user_id: UUID, symbol: str) -> dict[str, Any]:
        sym = symbol.strip().upper()
        watch = store.rate_watchlists.get(user_id, [])
        store.rate_watchlists[user_id] = [s for s in watch if s != sym]
        if user_id in store.rate_snapshots and sym in store.rate_snapshots[user_id]:
            del store.rate_snapshots[user_id][sym]
        return self.get_rates_state(user_id)

    def create_vehicle(self, payload: VehicleCreate) -> dict[str, Any]:
        entity_id = uuid4()
        now = datetime.utcnow()
        row = {
            "id": entity_id,
            "type": payload.type.value,
            "label": payload.label,
            "current_odometer_km": payload.currentOdometerKm,
            "created_at": now,
        }
        store.vehicles[entity_id] = row
        return row

    def create_vehicle_service(self, vehicle_id: UUID, payload: VehicleServiceCreate) -> dict[str, Any]:
        if vehicle_id not in store.vehicles:
            raise HTTPException(status_code=404, detail=f"vehicle not found: {vehicle_id}")
        entity_id = uuid4()
        row = {
            "id": entity_id,
            "vehicle_id": vehicle_id,
            "service_type": payload.serviceType,
            "service_at": payload.serviceAt,
            "odometer_km": payload.odometerKm,
        }
        store.vehicle_services[entity_id] = row
        return row

    def create_vehicle_service_rule(self, vehicle_id: UUID, payload: VehicleServiceRuleCreate, next_due_date: date | None) -> dict[str, Any]:
        if vehicle_id not in store.vehicles:
            raise HTTPException(status_code=404, detail=f"vehicle not found: {vehicle_id}")
        entity_id = uuid4()
        row = {
            "id": entity_id,
            "vehicle_id": vehicle_id,
            "service_type": payload.serviceType,
            "next_due_date": next_due_date,
            "is_active": True,
        }
        store.vehicle_service_rules[entity_id] = row
        return row

    def create_property(self, payload: PropertyCreate) -> dict[str, Any]:
        entity_id = uuid4()
        row = {
            "id": entity_id,
            "type": payload.type.value,
            "name": payload.name,
            "estimated_value": payload.estimatedValue,
        }
        store.properties[entity_id] = row
        return row

    def create_property_cost(self, property_id: UUID, payload: PropertyCostCreate) -> dict[str, Any]:
        if property_id not in store.properties:
            raise HTTPException(status_code=404, detail=f"property not found: {property_id}")
        entity_id = uuid4()
        row = {
            "id": entity_id,
            "property_id": property_id,
            "cost_type": payload.costType,
            "amount": payload.amount,
            "currency": payload.currency,
        }
        store.property_costs[entity_id] = row
        return row

    def create_insurance(self, payload: InsuranceCreate) -> dict[str, Any]:
        entity_id = uuid4()
        row = {
            "id": entity_id,
            "insurance_type": payload.insuranceType.value,
            "provider": payload.provider,
            "valid_to": payload.validTo,
            "is_active": True,
        }
        store.insurances[entity_id] = row
        return row

    def create_insurance_premium(self, insurance_id: UUID, payload: InsurancePremiumCreate) -> dict[str, Any]:
        if insurance_id not in store.insurances:
            raise HTTPException(status_code=404, detail=f"insurance not found: {insurance_id}")
        entity_id = uuid4()
        row = {"id": entity_id, "insurance_id": insurance_id, "amount": payload.amount, "currency": payload.currency}
        store.insurance_premiums[entity_id] = row
        return row

    def create_calendar_integration(self, payload: GoogleCalendarConnectRequest) -> dict[str, Any]:
        entity_id = uuid4()
        row = {
            "id": entity_id,
            "provider": "google",
            "external_calendar_id": payload.externalCalendarId,
            "sync_enabled": True,
        }
        store.calendar_integrations[entity_id] = row
        return row

    def create_notification_rule(self, payload: NotificationRuleCreate) -> dict[str, Any]:
        entity_id = uuid4()
        row = {
            "id": entity_id,
            "channel": payload.channel.value,
            "due_at": payload.dueAt,
            "is_active": payload.isActive,
            "source": payload.source.value,
            "source_entity_id": payload.sourceEntityId,
            "title_template": payload.titleTemplate,
            "message_template": payload.messageTemplate,
            "timezone": payload.timezone,
        }
        store.notification_rules[entity_id] = row
        return row

    def list_google_notification_rules(self) -> list[dict[str, Any]]:
        return [r for r in store.notification_rules.values() if r.get("channel") == "google_calendar"]

    def any_calendar_integration_id(self) -> UUID | None:
        return next(iter(store.calendar_integrations.keys()), None)

    def get_calendar_event(self, integration_id: UUID, event_uid: str) -> dict[str, Any] | None:
        return store.calendar_events.get(f"{integration_id}:{event_uid}")

    def create_calendar_event(self, integration_id: UUID, rule_id: UUID, event_uid: str, event_hash: str, provider_event_id: str) -> None:
        store.calendar_events[f"{integration_id}:{event_uid}"] = {
            "id": uuid4(),
            "calendar_integration_id": integration_id,
            "event_uid": event_uid,
            "event_hash": event_hash,
            "provider_event_id": provider_event_id,
            "notification_rule_id": rule_id,
        }

    def update_calendar_event_hash(self, event_id: UUID, event_hash: str) -> None:
        for key, row in store.calendar_events.items():
            if row.get("id") == event_id:
                row["event_hash"] = event_hash
                store.calendar_events[key] = row
                return

    def debug_counts(self) -> dict[str, int]:
        return {
            "users": len(store.users),
            "accounts": len(store.accounts),
            "transactions": len(store.transactions),
            "vehicles": len(store.vehicles),
            "vehicleServices": len(store.vehicle_services),
            "vehicleServiceRules": len(store.vehicle_service_rules),
            "properties": len(store.properties),
            "propertyCosts": len(store.property_costs),
            "insurances": len(store.insurances),
            "insurancePremiums": len(store.insurance_premiums),
            "calendarIntegrations": len(store.calendar_integrations),
            "notificationRules": len(store.notification_rules),
            "notificationDeliveries": len(store.notification_deliveries),
            "calendarEvents": len(store.calendar_events),
            "rateWatchlists": len(store.rate_watchlists),
            "rateSnapshotsUsers": len(store.rate_snapshots),
        }

    def export_backup(self, user_id: UUID) -> dict[str, Any]:
        vehicle_ids = {k for k, v in store.vehicles.items() if v.get("user_id") == user_id}
        property_ids = {k for k, v in store.properties.items() if v.get("user_id") == user_id}
        insurance_ids = {k for k, v in store.insurances.items() if v.get("user_id") == user_id}
        integration_ids = {k for k, v in store.calendar_integrations.items() if v.get("user_id") == user_id}
        rule_ids = {k for k, v in store.notification_rules.items() if v.get("user_id") == user_id}
        return {
            "meta": {
                "version": 1,
                "exportedAt": datetime.utcnow().isoformat() + "Z",
                "storageBackend": "memory",
            },
            "data": {
                "appSettings": store.settings,
                "customLocales": store.custom_locales,
                "users": [u for u in store.users.values() if u.get("id") == user_id],
                "userCredentials": [{"user_id": uid, "password_hash": pwd_hash} for uid, pwd_hash in store.user_credentials.items() if uid == user_id],
                "accounts": [a for a in store.accounts.values() if a.get("user_id") == user_id],
                "transactions": [t for t in store.transactions.values() if t.get("user_id") == user_id],
                "rateWatchlist": store.rate_watchlists.get(user_id, []),
                "rateSnapshots": list(store.rate_snapshots.get(user_id, {}).values()),
                "vehicles": [v for v in store.vehicles.values() if v.get("user_id") == user_id],
                "vehicleServices": [vs for vs in store.vehicle_services.values() if vs.get("vehicle_id") in vehicle_ids],
                "vehicleServiceRules": [vr for vr in store.vehicle_service_rules.values() if vr.get("vehicle_id") in vehicle_ids],
                "properties": [p for p in store.properties.values() if p.get("user_id") == user_id],
                "propertyCosts": [pc for pc in store.property_costs.values() if pc.get("property_id") in property_ids],
                "insurances": [i for i in store.insurances.values() if i.get("user_id") == user_id],
                "insurancePremiums": [ip for ip in store.insurance_premiums.values() if ip.get("insurance_id") in insurance_ids],
                "calendarIntegrations": [ci for ci in store.calendar_integrations.values() if ci.get("user_id") == user_id],
                "notificationRules": [nr for nr in store.notification_rules.values() if nr.get("user_id") == user_id],
                "notificationDeliveries": [nd for nd in store.notification_deliveries.values() if nd.get("notification_rule_id") in rule_ids],
                "calendarEvents": [ce for ce in store.calendar_events.values() if ce.get("calendar_integration_id") in integration_ids],
            },
        }

    def import_backup(self, user_id: UUID, payload: dict[str, Any]) -> dict[str, int]:
        data = payload.get("data", {})
        store.settings = data.get("appSettings", store.settings)
        store.custom_locales = data.get("customLocales", {})

        def map_by_id(rows: list[dict[str, Any]]) -> dict[UUID, dict[str, Any]]:
            out: dict[UUID, dict[str, Any]] = {}
            for row in rows:
                row_id = row.get("id")
                if not row_id:
                    continue
                if not isinstance(row_id, UUID):
                    row["id"] = UUID(str(row_id))
                out[row["id"]] = row
            return out

        store.users = map_by_id(data.get("users", []))
        store.user_credentials = {}
        for row in data.get("userCredentials", []):
            uid = row.get("user_id")
            if uid is None:
                continue
            store.user_credentials[UUID(str(uid))] = row.get("password_hash", "")
        store.accounts = map_by_id(data.get("accounts", []))
        store.transactions = map_by_id(data.get("transactions", []))
        store.rate_watchlists[user_id] = [str(s).strip().upper() for s in data.get("rateWatchlist", []) if str(s).strip()]
        store.rate_snapshots[user_id] = {}
        for row in data.get("rateSnapshots", []):
            if not isinstance(row, dict):
                continue
            sym = str(row.get("symbol", "")).strip().upper()
            if not sym:
                continue
            store.rate_snapshots[user_id][sym] = {
                "symbol": sym,
                "price": row.get("price"),
                "currency": str(row.get("currency", "USD")).strip().upper(),
                "source": str(row.get("source", "manual")).strip().lower(),
                "updatedAt": row.get("updatedAt") or row.get("updated_at") or datetime.utcnow(),
            }
        store.vehicles = map_by_id(data.get("vehicles", []))
        store.vehicle_services = map_by_id(data.get("vehicleServices", []))
        store.vehicle_service_rules = map_by_id(data.get("vehicleServiceRules", []))
        store.properties = map_by_id(data.get("properties", []))
        store.property_costs = map_by_id(data.get("propertyCosts", []))
        store.insurances = map_by_id(data.get("insurances", []))
        store.insurance_premiums = map_by_id(data.get("insurancePremiums", []))
        store.calendar_integrations = map_by_id(data.get("calendarIntegrations", []))
        store.notification_rules = map_by_id(data.get("notificationRules", []))
        store.notification_deliveries = map_by_id(data.get("notificationDeliveries", []))

        store.calendar_events = {}
        for row in data.get("calendarEvents", []):
            key = f"{row.get('calendar_integration_id')}:{row.get('event_uid')}"
            store.calendar_events[key] = row

        return self.debug_counts()

    def mark_auto_backup_run(self, user_id: UUID, when: datetime) -> None:
        store.settings["autoBackupLastRunAt"] = when

    def register_user(self, email: str, password: str, full_name: str | None) -> dict[str, Any]:
        for row in store.users.values():
            if row["email"] == email:
                raise HTTPException(status_code=409, detail="email already registered")
        user_id = uuid4()
        user_row = {"id": user_id, "email": email, "full_name": full_name, "created_at": datetime.utcnow()}
        store.users[user_id] = user_row
        store.user_credentials[user_id] = hash_password(password)
        return user_row

    def authenticate_user(self, email: str, password: str) -> dict[str, Any] | None:
        for user_id, row in store.users.items():
            if row["email"] == email:
                stored_hash = store.user_credentials.get(user_id)
                if stored_hash and verify_password(password, stored_hash):
                    return row
                return None
        return None

    def get_user_by_id(self, user_id: UUID) -> dict[str, Any] | None:
        return store.users.get(user_id)

    def update_user_profile(self, user_id: UUID, email: str | None, full_name: str | None) -> dict[str, Any]:
        row = store.users.get(user_id)
        if row is None:
            raise HTTPException(status_code=404, detail="user not found")
        if email is not None:
            for uid, user_row in store.users.items():
                if uid != user_id and user_row.get("email", "").lower() == email.lower():
                    raise HTTPException(status_code=409, detail="email already registered")
            row["email"] = email
        if full_name is not None:
            row["full_name"] = full_name
        store.users[user_id] = row
        return row

    def change_user_password(self, user_id: UUID, current_password: str, new_password: str) -> None:
        row = store.users.get(user_id)
        if row is None:
            raise HTTPException(status_code=404, detail="user not found")
        current_hash = store.user_credentials.get(user_id)
        if not current_hash or not verify_password(current_password, current_hash):
            raise HTTPException(status_code=401, detail="invalid current password")
        store.user_credentials[user_id] = hash_password(new_password)

    def create_account(self, user_id: UUID, payload: AccountCreate) -> dict[str, Any]:
        entity_id = uuid4()
        now = datetime.utcnow()
        initial_at = payload.initialBalanceAt or now
        row = {
            "id": entity_id,
            "user_id": user_id,
            "name": payload.name,
            "account_type": payload.accountType,
            "currency": payload.currency,
            "initial_balance": payload.initialBalance,
            "initial_balance_at": initial_at,
            "current_balance": payload.initialBalance,
            "created_at": now,
        }
        store.accounts[entity_id] = row
        return row

    def list_accounts(self, user_id: UUID) -> list[dict[str, Any]]:
        return sorted([a for a in store.accounts.values() if a["user_id"] == user_id], key=lambda a: a.get("created_at", datetime.min), reverse=True)

    def create_transaction(self, user_id: UUID, payload: TransactionCreate) -> dict[str, Any]:
        account = store.accounts.get(payload.accountId)
        if not account or account["user_id"] != user_id:
            raise HTTPException(status_code=404, detail=f"account not found: {payload.accountId}")
        recurring_group_id = uuid4() if payload.recurringFrequency else None
        day_anchor = payload.recurringDayOfMonth or payload.occurredAt.day
        weekend_policy = payload.recurringWeekendPolicy or "exact"
        first_row: dict[str, Any] | None = None
        for idx in range(payload.recurringCount):
            tx_time = (
                _move_from_weekend(payload.occurredAt, weekend_policy)
                if not payload.recurringFrequency
                else _shift_recurring(payload.occurredAt, payload.recurringFrequency, idx, day_anchor, weekend_policy)
            )
            entity_id = uuid4()
            account["current_balance"] = Decimal(account["current_balance"]) + (payload.amount * _tx_sign(payload.direction))
            row = {
                "id": entity_id,
                "user_id": user_id,
                "account_id": payload.accountId,
                "direction": payload.direction,
                "amount": payload.amount,
                "currency": payload.currency,
                "transaction_at": tx_time,
                "category": payload.category,
                "note": payload.note,
                "transfer_group_id": None,
                "recurring_group_id": recurring_group_id,
                "recurring_frequency": payload.recurringFrequency,
                "recurring_index": idx + 1 if payload.recurringFrequency else None,
                "recurring_day_of_month": day_anchor if payload.recurringFrequency in {"monthly", "yearly"} else None,
                "recurring_weekend_policy": weekend_policy if payload.recurringFrequency else None,
            }
            store.transactions[entity_id] = row
            if first_row is None:
                first_row = row
        return first_row or {}

    def list_transactions(self, user_id: UUID) -> list[dict[str, Any]]:
        def _ts(val: Any) -> float:
            if isinstance(val, datetime):
                return val.timestamp()
            return 0.0
        return sorted(
            [t for t in store.transactions.values() if t["user_id"] == user_id],
            key=lambda x: _ts(x.get("transaction_at")),
            reverse=True,
        )

    def update_account(self, user_id: UUID, account_id: UUID, payload: AccountUpdate) -> dict[str, Any]:
        row = store.accounts.get(account_id)
        if not row or row["user_id"] != user_id:
            raise HTTPException(status_code=404, detail=f"account not found: {account_id}")
        updates = payload.model_dump(exclude_none=True)
        if "name" in updates:
            row["name"] = updates["name"]
        if "accountType" in updates:
            row["account_type"] = updates["accountType"]
        if "currency" in updates:
            row["currency"] = updates["currency"]
        if "initialBalanceAt" in updates:
            row["initial_balance_at"] = updates["initialBalanceAt"]
        if "initialBalance" in updates:
            row["initial_balance"] = updates["initialBalance"]
            tx_total = Decimal("0")
            for tx in store.transactions.values():
                if tx.get("account_id") == account_id and tx.get("user_id") == user_id:
                    tx_total += Decimal(tx["amount"]) * _tx_sign(tx["direction"])
            row["current_balance"] = Decimal(row["initial_balance"]) + tx_total
        store.accounts[account_id] = row
        return row

    def delete_account(self, user_id: UUID, account_id: UUID, action: AccountDeleteAction, target_account_id: UUID | None = None) -> None:
        row = store.accounts.get(account_id)
        if not row or row.get("user_id") != user_id:
            raise HTTPException(status_code=404, detail=f"account not found: {account_id}")
        account_transactions = [tx_id for tx_id, tx in store.transactions.items() if tx.get("account_id") == account_id and tx.get("user_id") == user_id]
        if action == AccountDeleteAction.transfer_balance:
            if target_account_id is None:
                raise HTTPException(status_code=400, detail="targetAccountId is required for transfer_balance")
            if target_account_id == account_id:
                raise HTTPException(status_code=400, detail="targetAccountId must be different from account_id")
            target = store.accounts.get(target_account_id)
            if not target or target.get("user_id") != user_id:
                raise HTTPException(status_code=404, detail=f"account not found: {target_account_id}")
            target["current_balance"] = Decimal(target["current_balance"]) + Decimal(row["current_balance"])
        for tx_id in account_transactions:
            del store.transactions[tx_id]
        del store.accounts[account_id]

    def update_transaction(self, user_id: UUID, transaction_id: UUID, payload: TransactionUpdate) -> dict[str, Any]:
        original = store.transactions.get(transaction_id)
        if not original or original["user_id"] != user_id:
            raise HTTPException(status_code=404, detail=f"transaction not found: {transaction_id}")
        row = original.copy()
        account = store.accounts.get(row["account_id"])
        if not account or account["user_id"] != user_id:
            raise HTTPException(status_code=404, detail=f"account not found: {row['account_id']}")
        old_delta = Decimal(row["amount"]) * _tx_sign(row["direction"])
        updates = payload.model_dump(exclude_none=True)
        if "accountId" in updates:
            target_account = store.accounts.get(updates["accountId"])
            if not target_account or target_account.get("user_id") != user_id:
                raise HTTPException(status_code=404, detail=f"account not found: {updates['accountId']}")
            if updates["accountId"] != row["account_id"]:
                account["current_balance"] = Decimal(account["current_balance"]) - old_delta
                row["account_id"] = updates["accountId"]
                account = target_account
                old_delta = Decimal("0")
        if "direction" in updates:
            row["direction"] = updates["direction"]
        if "amount" in updates:
            row["amount"] = updates["amount"]
        if "currency" in updates:
            row["currency"] = updates["currency"]
        if "occurredAt" in updates:
            row["transaction_at"] = updates["occurredAt"]
        if "category" in updates:
            row["category"] = updates["category"]
        if "note" in updates:
            row["note"] = updates["note"]
        new_delta = Decimal(row["amount"]) * _tx_sign(row["direction"])
        account["current_balance"] = Decimal(account["current_balance"]) - old_delta + new_delta
        store.transactions[transaction_id] = row
        return row

    def delete_transaction(self, user_id: UUID, transaction_id: UUID) -> None:
        row = store.transactions.get(transaction_id)
        if not row or row["user_id"] != user_id:
            raise HTTPException(status_code=404, detail=f"transaction not found: {transaction_id}")
        account = store.accounts.get(row["account_id"])
        if account and account.get("user_id") == user_id:
            delta = Decimal(row["amount"]) * _tx_sign(row["direction"])
            account["current_balance"] = Decimal(account["current_balance"]) - delta
        del store.transactions[transaction_id]

    def transfer_between_accounts(self, user_id: UUID, payload: TransactionTransferCreate) -> dict[str, Any]:
        from_account = store.accounts.get(payload.fromAccountId)
        to_account = store.accounts.get(payload.toAccountId)
        if not from_account or from_account.get("user_id") != user_id:
            raise HTTPException(status_code=404, detail=f"account not found: {payload.fromAccountId}")
        if not to_account or to_account.get("user_id") != user_id:
            raise HTTPException(status_code=404, detail=f"account not found: {payload.toAccountId}")
        transfer_group_id = uuid4()
        from_account["current_balance"] = Decimal(from_account["current_balance"]) - payload.amount
        to_account["current_balance"] = Decimal(to_account["current_balance"]) + payload.amount
        out_id = uuid4()
        in_id = uuid4()
        outgoing = {
            "id": out_id,
            "user_id": user_id,
            "account_id": payload.fromAccountId,
            "direction": "expense",
            "amount": payload.amount,
            "currency": payload.currency,
            "transaction_at": payload.occurredAt,
            "category": payload.category,
            "note": payload.note,
            "transfer_group_id": transfer_group_id,
            "recurring_group_id": None,
            "recurring_frequency": None,
            "recurring_index": None,
        }
        incoming = {
            "id": in_id,
            "user_id": user_id,
            "account_id": payload.toAccountId,
            "direction": "income",
            "amount": payload.amount,
            "currency": payload.currency,
            "transaction_at": payload.occurredAt,
            "category": payload.category,
            "note": payload.note,
            "transfer_group_id": transfer_group_id,
            "recurring_group_id": None,
            "recurring_frequency": None,
            "recurring_index": None,
        }
        store.transactions[out_id] = outgoing
        store.transactions[in_id] = incoming
        return {"transferGroupId": transfer_group_id, "outgoing": outgoing, "incoming": incoming}

    def list_transaction_category_stats(self, user_id: UUID) -> TransactionCategoryStatsResponse:
        counts: dict[str, int] = {}
        for tx in store.transactions.values():
            if tx.get("user_id") != user_id:
                continue
            category = (tx.get("category") or "").strip()
            if not category:
                continue
            counts[category] = counts.get(category, 0) + 1
        sorted_items = sorted(counts.items(), key=lambda item: (-item[1], item[0].lower()))
        most_used = sorted_items[0][0] if sorted_items else None
        categories = [{"category": name, "usageCount": cnt} for name, cnt in sorted_items]
        return TransactionCategoryStatsResponse(mostUsedCategory=most_used, categories=categories)

    def rename_transaction_category(self, user_id: UUID, category: str, payload: TransactionCategoryRename) -> TransactionCategoryStatsResponse:
        old_name = category.strip()
        if not old_name:
            raise HTTPException(status_code=400, detail="category must not be empty")
        changed = False
        for tx in store.transactions.values():
            if tx.get("user_id") != user_id:
                continue
            if (tx.get("category") or "").strip() == old_name:
                tx["category"] = payload.newCategory
                changed = True
        if not changed:
            raise HTTPException(status_code=404, detail=f"category not found: {category}")
        return self.list_transaction_category_stats(user_id)

    def delete_transaction_category(self, user_id: UUID, category: str, delete_transactions: bool) -> TransactionCategoryStatsResponse:
        name = category.strip()
        if not name:
            raise HTTPException(status_code=400, detail="category must not be empty")
        hits = []
        for tx_id, tx in store.transactions.items():
            if tx.get("user_id") != user_id:
                continue
            if (tx.get("category") or "").strip() == name:
                hits.append((tx_id, tx))
        if not hits:
            raise HTTPException(status_code=404, detail=f"category not found: {category}")
        if delete_transactions:
            for tx_id, tx in hits:
                account = store.accounts.get(tx.get("account_id"))
                if account and account.get("user_id") == user_id:
                    delta = Decimal(tx["amount"]) * _tx_sign(tx["direction"])
                    account["current_balance"] = Decimal(account["current_balance"]) - delta
                del store.transactions[tx_id]
        else:
            for _, tx in hits:
                tx["category"] = None
        return self.list_transaction_category_stats(user_id)

    def delete_user(self, user_id: UUID) -> None:
        if user_id in store.users:
            del store.users[user_id]
        if user_id in store.user_credentials:
            del store.user_credentials[user_id]
        vehicle_ids = {k for k, v in store.vehicles.items() if v.get("user_id") == user_id}
        property_ids = {k for k, v in store.properties.items() if v.get("user_id") == user_id}
        insurance_ids = {k for k, v in store.insurances.items() if v.get("user_id") == user_id}
        integration_ids = {k for k, v in store.calendar_integrations.items() if v.get("user_id") == user_id}
        rule_ids = {k for k, v in store.notification_rules.items() if v.get("user_id") == user_id}
        store.accounts = {k: v for k, v in store.accounts.items() if v.get("user_id") != user_id}
        store.transactions = {k: v for k, v in store.transactions.items() if v.get("user_id") != user_id}
        store.vehicles = {k: v for k, v in store.vehicles.items() if v.get("user_id") != user_id}
        store.vehicle_services = {k: v for k, v in store.vehicle_services.items() if v.get("vehicle_id") not in vehicle_ids}
        store.vehicle_service_rules = {k: v for k, v in store.vehicle_service_rules.items() if v.get("vehicle_id") not in vehicle_ids}
        store.properties = {k: v for k, v in store.properties.items() if v.get("user_id") != user_id}
        store.property_costs = {k: v for k, v in store.property_costs.items() if v.get("property_id") not in property_ids}
        store.insurances = {k: v for k, v in store.insurances.items() if v.get("user_id") != user_id}
        store.insurance_premiums = {k: v for k, v in store.insurance_premiums.items() if v.get("insurance_id") not in insurance_ids}
        store.calendar_integrations = {k: v for k, v in store.calendar_integrations.items() if v.get("user_id") != user_id}
        store.notification_rules = {k: v for k, v in store.notification_rules.items() if v.get("user_id") != user_id}
        store.notification_deliveries = {k: v for k, v in store.notification_deliveries.items() if v.get("notification_rule_id") not in rule_ids}
        store.calendar_events = {
            k: v for k, v in store.calendar_events.items() if v.get("calendar_integration_id") not in integration_ids
        }
        if user_id in store.rate_watchlists:
            del store.rate_watchlists[user_id]
        if user_id in store.rate_snapshots:
            del store.rate_snapshots[user_id]


class PostgresPersistence(Persistence):
    def __init__(self, database_url: str, default_user_id: str) -> None:
        self.engine: Engine = create_engine(database_url, future=True, pool_pre_ping=True)
        self.default_user_id = default_user_id

    def _run(self, sql: str, params: dict[str, Any] | None = None) -> list[dict[str, Any]]:
        try:
            with self.engine.begin() as conn:
                result = conn.execute(text(sql), params or {})
                if result.returns_rows:
                    return [dict(row._mapping) for row in result.fetchall()]
                return []
        except SQLAlchemyError as exc:
            raise HTTPException(status_code=500, detail=f"postgres error: {exc.__class__.__name__}") from exc

    def _exists(self, table: str, entity_id: UUID) -> bool:
        rows = self._run(f"select 1 as ok from {table} where id = :id limit 1", {"id": entity_id})
        return bool(rows)

    def _ensure_app_settings_columns(self) -> None:
        self._run(
            """
            alter table if exists app_settings
              add column if not exists default_locale text not null default 'en',
              add column if not exists default_display_currency text not null default 'CZK',
              add column if not exists secondary_display_currency text not null default 'USD',
              add column if not exists auto_backup_enabled boolean not null default false,
              add column if not exists auto_backup_interval_minutes integer not null default 1440,
              add column if not exists auto_backup_retention_days integer not null default 30,
              add column if not exists auto_backup_last_run_at timestamptz,
              add column if not exists session_timeout_minutes integer
            """
        )

    def _ensure_auth_columns(self) -> None:
        self._run("alter table if exists users add column if not exists full_name text")
        self._run(
            """
            create table if not exists user_credentials (
              user_id uuid primary key references users(id) on delete cascade,
              password_hash text not null,
              created_at timestamptz not null default now(),
              updated_at timestamptz not null default now()
            )
            """
        )
        self._run(
            """
            create table if not exists accounts (
              id uuid primary key default gen_random_uuid(),
              user_id uuid not null references users(id) on delete cascade,
              name text not null,
              account_type text not null default 'checking',
              currency char(3) not null default 'CZK',
              initial_balance numeric(14,2) not null default 0,
              initial_balance_at timestamptz,
              current_balance numeric(14,2) not null default 0,
              created_at timestamptz not null default now(),
              updated_at timestamptz not null default now()
            )
            """
        )
        self._run("alter table if exists accounts add column if not exists initial_balance_at timestamptz")
        self._run("create index if not exists idx_accounts_user on accounts(user_id, created_at desc)")
        self._run(
            """
            alter table if exists transactions
              add column if not exists direction text not null default 'expense',
              add column if not exists category text,
              add column if not exists note text,
              add column if not exists transfer_group_id uuid,
              add column if not exists recurring_group_id uuid,
              add column if not exists recurring_frequency text,
              add column if not exists recurring_index integer,
              add column if not exists recurring_day_of_month integer,
              add column if not exists recurring_weekend_policy text
            """
        )

    def _ensure_rates_tables(self) -> None:
        self._run(
            """
            create table if not exists rate_assets (
              id uuid primary key default gen_random_uuid(),
              user_id uuid not null references users(id) on delete cascade,
              symbol text not null,
              created_at timestamptz not null default now(),
              updated_at timestamptz not null default now(),
              unique (user_id, symbol)
            )
            """
        )
        self._run(
            """
            create table if not exists rate_snapshots (
              id uuid primary key default gen_random_uuid(),
              user_id uuid not null references users(id) on delete cascade,
              symbol text not null,
              price numeric(30,10) not null,
              currency text not null default 'USD',
              source text not null default 'manual',
              last_updated_at timestamptz not null,
              created_at timestamptz not null default now(),
              updated_at timestamptz not null default now(),
              unique (user_id, symbol)
            )
            """
        )
        self._run("create index if not exists idx_rate_assets_user on rate_assets(user_id, symbol)")
        self._run("create index if not exists idx_rate_snapshots_user on rate_snapshots(user_id, symbol)")

    def get_app_settings(self, user_id: UUID) -> AppSettings:
        self._ensure_app_settings_columns()
        rows = self._run(
            """
            select default_locale, default_timezone, calendar_provider, calendar_sync_enabled, self_registration_enabled, smtp_enabled,
                   default_display_currency, secondary_display_currency,
                   auto_backup_enabled, auto_backup_interval_minutes, auto_backup_retention_days, auto_backup_last_run_at,
                   session_timeout_minutes
            from app_settings
            where user_id = :user_id
            """,
            {"user_id": user_id},
        )
        if not rows:
            self._run(
                """
                insert into app_settings (
                  id, user_id, default_timezone, calendar_provider, calendar_sync_enabled, self_registration_enabled, smtp_enabled,
                  default_locale, default_display_currency, secondary_display_currency, auto_backup_enabled, auto_backup_interval_minutes, auto_backup_retention_days, auto_backup_last_run_at,
                  session_timeout_minutes
                )
                values (:id, :user_id, 'Europe/Prague', 'google', true, true, false, 'en', 'CZK', 'USD', false, 1440, 30, null, null)
                """,
                {"id": str(uuid4()), "user_id": user_id},
            )
            rows = self._run(
                """
                select default_locale, default_timezone, calendar_provider, calendar_sync_enabled, self_registration_enabled, smtp_enabled,
                       default_display_currency, secondary_display_currency,
                       auto_backup_enabled, auto_backup_interval_minutes, auto_backup_retention_days, auto_backup_last_run_at,
                       session_timeout_minutes
                from app_settings where user_id = :user_id
                """,
                {"user_id": user_id},
            )
        row = rows[0]
        return AppSettings(
            defaultLocale=row.get("default_locale", "en"),
            defaultTimezone=row["default_timezone"],
            defaultDisplayCurrency=row.get("default_display_currency", "CZK"),
            secondaryDisplayCurrency=row.get("secondary_display_currency", "USD"),
            calendarProvider=row["calendar_provider"],
            calendarSyncEnabled=row["calendar_sync_enabled"],
            selfRegistrationEnabled=row["self_registration_enabled"],
            smtpEnabled=row["smtp_enabled"],
            autoBackupEnabled=row["auto_backup_enabled"],
            autoBackupIntervalMinutes=row["auto_backup_interval_minutes"],
            autoBackupRetentionDays=row["auto_backup_retention_days"],
            autoBackupLastRunAt=row["auto_backup_last_run_at"],
            sessionTimeoutMinutes=row.get("session_timeout_minutes"),
        )

    def update_app_settings(self, user_id: UUID, payload: AppSettingsUpdate) -> AppSettings:
        current = self.get_app_settings(user_id)
        merged = current.model_dump()
        merged.update(payload.model_dump(exclude_unset=True))
        self._run(
            """
            update app_settings
            set default_locale = :default_locale,
                default_timezone = :default_timezone,
                default_display_currency = :default_display_currency,
                secondary_display_currency = :secondary_display_currency,
                calendar_provider = :calendar_provider,
                calendar_sync_enabled = :calendar_sync_enabled,
                self_registration_enabled = :self_registration_enabled,
                smtp_enabled = :smtp_enabled,
                auto_backup_enabled = :auto_backup_enabled,
                auto_backup_interval_minutes = :auto_backup_interval_minutes,
                auto_backup_retention_days = :auto_backup_retention_days,
                auto_backup_last_run_at = :auto_backup_last_run_at,
                session_timeout_minutes = :session_timeout_minutes,
                updated_at = now()
            where user_id = :user_id
            """,
            {
                "default_locale": merged["defaultLocale"],
                "default_timezone": merged["defaultTimezone"],
                "default_display_currency": merged["defaultDisplayCurrency"],
                "secondary_display_currency": merged["secondaryDisplayCurrency"],
                "calendar_provider": merged["calendarProvider"],
                "calendar_sync_enabled": merged["calendarSyncEnabled"],
                "self_registration_enabled": merged["selfRegistrationEnabled"],
                "smtp_enabled": merged["smtpEnabled"],
                "auto_backup_enabled": merged["autoBackupEnabled"],
                "auto_backup_interval_minutes": merged["autoBackupIntervalMinutes"],
                "auto_backup_retention_days": merged["autoBackupRetentionDays"],
                "auto_backup_last_run_at": merged["autoBackupLastRunAt"],
                "session_timeout_minutes": merged.get("sessionTimeoutMinutes"),
                "user_id": user_id,
            },
        )
        return AppSettings(**merged)

    def list_locales(self, user_id: UUID) -> list[str]:
        rows = self._run("select locale from locale_custom_messages where user_id = :user_id group by locale", {"user_id": user_id})
        custom = [r["locale"] for r in rows]
        return sorted(set(store.base_locales.keys()) | set(custom))

    def get_locale_bundle(self, user_id: UUID, locale: str) -> dict[str, str]:
        rows = self._run(
            "select message_key, message_value from locale_custom_messages where user_id = :user_id and locale = :locale",
            {"user_id": user_id, "locale": locale},
        )
        custom = {r["message_key"]: r["message_value"] for r in rows}
        return {**store.base_locales.get(locale, {}), **custom}

    def get_custom_locale(self, user_id: UUID, locale: str) -> dict[str, str]:
        rows = self._run(
            "select message_key, message_value from locale_custom_messages where user_id = :user_id and locale = :locale",
            {"user_id": user_id, "locale": locale},
        )
        return {r["message_key"]: r["message_value"] for r in rows}

    def upsert_custom_locale(self, user_id: UUID, locale: str, payload: dict[str, str]) -> dict[str, str]:
        for k, v in payload.items():
            self._run(
                """
                insert into locale_custom_messages (id, user_id, locale, message_key, message_value, created_at, updated_at)
                values (:id, :user_id, :locale, :message_key, :message_value, now(), now())
                on conflict (user_id, locale, message_key)
                do update set message_value = excluded.message_value, updated_at = now()
                """,
                {
                    "id": str(uuid4()),
                    "user_id": user_id,
                    "locale": locale,
                    "message_key": k,
                    "message_value": v,
                },
            )
        return self.get_locale_bundle(user_id, locale)

    def get_rates_state(self, user_id: UUID) -> dict[str, Any]:
        self._ensure_rates_tables()
        watch_rows = self._run(
            "select symbol from rate_assets where user_id = :user_id order by symbol asc",
            {"user_id": user_id},
        )
        snap_rows = self._run(
            """
            select symbol, price, currency, source, last_updated_at
            from rate_snapshots
            where user_id = :user_id
            """,
            {"user_id": user_id},
        )
        snapshots = {
            row["symbol"]: {
                "symbol": row["symbol"],
                "price": row["price"],
                "currency": row["currency"],
                "source": row["source"],
                "updatedAt": row["last_updated_at"],
            }
            for row in snap_rows
        }
        return {"watchlist": [r["symbol"] for r in watch_rows], "snapshots": snapshots}

    def update_rates_watchlist(self, user_id: UUID, payload: RatesWatchlistUpdate) -> dict[str, Any]:
        self._ensure_rates_tables()
        symbols = payload.symbols
        for sym in symbols:
            self._run(
                """
                insert into rate_assets (id, user_id, symbol, created_at, updated_at)
                values (:id, :user_id, :symbol, now(), now())
                on conflict (user_id, symbol)
                do update set updated_at = now()
                """,
                {"id": str(uuid4()), "user_id": user_id, "symbol": sym},
            )
        if symbols:
            self._run(
                "delete from rate_assets where user_id = :user_id and symbol <> all(:symbols)",
                {"user_id": user_id, "symbols": symbols},
            )
            self._run(
                "delete from rate_snapshots where user_id = :user_id and symbol <> all(:symbols)",
                {"user_id": user_id, "symbols": symbols},
            )
        else:
            self._run("delete from rate_assets where user_id = :user_id", {"user_id": user_id})
            self._run("delete from rate_snapshots where user_id = :user_id", {"user_id": user_id})
        return self.get_rates_state(user_id)

    def upsert_rate_snapshot(self, user_id: UUID, payload: RateSnapshotUpsert) -> dict[str, Any]:
        self._ensure_rates_tables()
        self._run(
            """
            insert into rate_assets (id, user_id, symbol, created_at, updated_at)
            values (:id, :user_id, :symbol, now(), now())
            on conflict (user_id, symbol)
            do update set updated_at = now()
            """,
            {"id": str(uuid4()), "user_id": user_id, "symbol": payload.symbol},
        )
        self._run(
            """
            insert into rate_snapshots (id, user_id, symbol, price, currency, source, last_updated_at, created_at, updated_at)
            values (:id, :user_id, :symbol, :price, :currency, :source, :last_updated_at, now(), now())
            on conflict (user_id, symbol)
            do update set price = excluded.price, currency = excluded.currency, source = excluded.source, last_updated_at = excluded.last_updated_at, updated_at = now()
            """,
            {
                "id": str(uuid4()),
                "user_id": user_id,
                "symbol": payload.symbol,
                "price": _to_float(payload.price),
                "currency": payload.currency,
                "source": payload.source,
                "last_updated_at": payload.updatedAt or datetime.utcnow(),
            },
        )
        return self.get_rates_state(user_id)

    def delete_rate_symbol(self, user_id: UUID, symbol: str) -> dict[str, Any]:
        self._ensure_rates_tables()
        sym = symbol.strip().upper()
        self._run("delete from rate_snapshots where user_id = :user_id and symbol = :symbol", {"user_id": user_id, "symbol": sym})
        self._run("delete from rate_assets where user_id = :user_id and symbol = :symbol", {"user_id": user_id, "symbol": sym})
        return self.get_rates_state(user_id)

    def create_vehicle(self, payload: VehicleCreate) -> dict[str, Any]:
        row = self._run(
            """
            insert into vehicles (id, user_id, type, label, vin, plate_number, make, model, production_year, purchased_at, current_odometer_km, notes)
            values (:id, :user_id, :type, :label, :vin, :plate_number, :make, :model, :production_year, :purchased_at, :current_odometer_km, :notes)
            returning id, type, label, current_odometer_km, created_at
            """,
            {
                "id": str(uuid4()),
                "user_id": self.default_user_id,
                "type": payload.type.value,
                "label": payload.label,
                "vin": payload.vin,
                "plate_number": payload.plateNumber,
                "make": payload.make,
                "model": payload.model,
                "production_year": payload.productionYear,
                "purchased_at": payload.purchasedAt,
                "current_odometer_km": payload.currentOdometerKm,
                "notes": payload.notes,
            },
        )[0]
        return row

    def create_vehicle_service(self, vehicle_id: UUID, payload: VehicleServiceCreate) -> dict[str, Any]:
        if not self._exists("vehicles", vehicle_id):
            raise HTTPException(status_code=404, detail=f"vehicle not found: {vehicle_id}")
        row = self._run(
            """
            insert into vehicle_services (id, vehicle_id, service_type, service_at, odometer_km, total_cost, currency, vendor, description)
            values (:id, :vehicle_id, :service_type, :service_at, :odometer_km, :total_cost, :currency, :vendor, :description)
            returning id, vehicle_id, service_type, service_at, odometer_km
            """,
            {
                "id": str(uuid4()),
                "vehicle_id": vehicle_id,
                "service_type": payload.serviceType,
                "service_at": payload.serviceAt,
                "odometer_km": payload.odometerKm,
                "total_cost": _to_float(payload.totalCost),
                "currency": payload.currency,
                "vendor": payload.vendor,
                "description": payload.description,
            },
        )[0]
        return row

    def create_vehicle_service_rule(self, vehicle_id: UUID, payload: VehicleServiceRuleCreate, next_due_date: date | None) -> dict[str, Any]:
        if not self._exists("vehicles", vehicle_id):
            raise HTTPException(status_code=404, detail=f"vehicle not found: {vehicle_id}")
        row = self._run(
            """
            insert into vehicle_service_rules (id, vehicle_id, service_type, interval_value, interval_unit, lead_days, next_due_date, is_active)
            values (:id, :vehicle_id, :service_type, :interval_value, :interval_unit, :lead_days, :next_due_date, true)
            returning id, vehicle_id, service_type, next_due_date, is_active
            """,
            {
                "id": str(uuid4()),
                "vehicle_id": vehicle_id,
                "service_type": payload.serviceType,
                "interval_value": payload.intervalValue,
                "interval_unit": payload.intervalUnit.value,
                "lead_days": payload.leadDays,
                "next_due_date": next_due_date,
            },
        )[0]
        return row

    def create_property(self, payload: PropertyCreate) -> dict[str, Any]:
        row = self._run(
            """
            insert into properties (id, user_id, type, name, address_line1, city, postal_code, country_code, acquired_at, purchase_price, purchase_currency, estimated_value, estimated_value_currency, estimated_value_updated_at)
            values (:id, :user_id, :type, :name, :address_line1, :city, :postal_code, :country_code, :acquired_at, :purchase_price, :purchase_currency, :estimated_value, :estimated_value_currency, :estimated_value_updated_at)
            returning id, type, name, estimated_value
            """,
            {
                "id": str(uuid4()),
                "user_id": self.default_user_id,
                "type": payload.type.value,
                "name": payload.name,
                "address_line1": payload.addressLine1,
                "city": payload.city,
                "postal_code": payload.postalCode,
                "country_code": payload.countryCode,
                "acquired_at": payload.acquiredAt,
                "purchase_price": _to_float(payload.purchasePrice),
                "purchase_currency": payload.purchaseCurrency,
                "estimated_value": _to_float(payload.estimatedValue),
                "estimated_value_currency": payload.estimatedValueCurrency,
                "estimated_value_updated_at": payload.estimatedValueUpdatedAt,
            },
        )[0]
        return row

    def create_property_cost(self, property_id: UUID, payload: PropertyCostCreate) -> dict[str, Any]:
        if not self._exists("properties", property_id):
            raise HTTPException(status_code=404, detail=f"property not found: {property_id}")
        row = self._run(
            """
            insert into property_costs (id, property_id, cost_type, period_start, period_end, amount, currency, provider, meter_value, meter_unit, is_recurring)
            values (:id, :property_id, :cost_type, :period_start, :period_end, :amount, :currency, :provider, :meter_value, :meter_unit, :is_recurring)
            returning id, property_id, cost_type, amount, currency
            """,
            {
                "id": str(uuid4()),
                "property_id": property_id,
                "cost_type": payload.costType,
                "period_start": payload.periodStart,
                "period_end": payload.periodEnd,
                "amount": _to_float(payload.amount),
                "currency": payload.currency,
                "provider": payload.provider,
                "meter_value": _to_float(payload.meterValue),
                "meter_unit": payload.meterUnit,
                "is_recurring": payload.isRecurring,
            },
        )[0]
        return row

    def create_insurance(self, payload: InsuranceCreate) -> dict[str, Any]:
        row = self._run(
            """
            insert into insurances (id, user_id, insurance_type, provider, policy_number, subject_vehicle_id, subject_property_id, coverage_amount, coverage_currency, deductible_amount, deductible_currency, valid_from, valid_to, payment_frequency, is_active)
            values (:id, :user_id, :insurance_type, :provider, :policy_number, :subject_vehicle_id, :subject_property_id, :coverage_amount, :coverage_currency, :deductible_amount, :deductible_currency, :valid_from, :valid_to, :payment_frequency, true)
            returning id, insurance_type, provider, valid_to, is_active
            """,
            {
                "id": str(uuid4()),
                "user_id": self.default_user_id,
                "insurance_type": payload.insuranceType.value,
                "provider": payload.provider,
                "policy_number": payload.policyNumber,
                "subject_vehicle_id": payload.subjectVehicleId,
                "subject_property_id": payload.subjectPropertyId,
                "coverage_amount": _to_float(payload.coverageAmount),
                "coverage_currency": payload.coverageCurrency,
                "deductible_amount": _to_float(payload.deductibleAmount),
                "deductible_currency": payload.deductibleCurrency,
                "valid_from": payload.validFrom,
                "valid_to": payload.validTo,
                "payment_frequency": payload.paymentFrequency,
            },
        )[0]
        return row

    def create_insurance_premium(self, insurance_id: UUID, payload: InsurancePremiumCreate) -> dict[str, Any]:
        if not self._exists("insurances", insurance_id):
            raise HTTPException(status_code=404, detail=f"insurance not found: {insurance_id}")
        row = self._run(
            """
            insert into insurance_premiums (id, insurance_id, period_start, period_end, amount, currency, paid_at, payment_transaction_id)
            values (:id, :insurance_id, :period_start, :period_end, :amount, :currency, :paid_at, :payment_transaction_id)
            returning id, insurance_id, amount, currency
            """,
            {
                "id": str(uuid4()),
                "insurance_id": insurance_id,
                "period_start": payload.periodStart,
                "period_end": payload.periodEnd,
                "amount": _to_float(payload.amount),
                "currency": payload.currency,
                "paid_at": payload.paidAt,
                "payment_transaction_id": payload.paymentTransactionId,
            },
        )[0]
        return row

    def create_calendar_integration(self, payload: GoogleCalendarConnectRequest) -> dict[str, Any]:
        row = self._run(
            """
            insert into calendar_integrations (id, user_id, provider, external_calendar_id, access_token_encrypted, refresh_token_encrypted, sync_enabled)
            values (:id, :user_id, 'google', :external_calendar_id, :access_token, :refresh_token, true)
            returning id, provider, external_calendar_id, sync_enabled
            """,
            {
                "id": str(uuid4()),
                "user_id": self.default_user_id,
                "external_calendar_id": payload.externalCalendarId,
                "access_token": "pending-oauth-exchange",
                "refresh_token": "pending-oauth-exchange",
            },
        )[0]
        return row

    def create_notification_rule(self, payload: NotificationRuleCreate) -> dict[str, Any]:
        row = self._run(
            """
            insert into notification_rules (id, user_id, source, source_entity_id, title_template, message_template, due_at, lead_days, channel, timezone, is_active)
            values (:id, :user_id, :source, :source_entity_id, :title_template, :message_template, :due_at, :lead_days, :channel, :timezone, :is_active)
            returning id, channel, due_at, is_active
            """,
            {
                "id": str(uuid4()),
                "user_id": self.default_user_id,
                "source": payload.source.value,
                "source_entity_id": payload.sourceEntityId,
                "title_template": payload.titleTemplate,
                "message_template": payload.messageTemplate,
                "due_at": payload.dueAt,
                "lead_days": payload.leadDays,
                "channel": payload.channel.value,
                "timezone": payload.timezone,
                "is_active": payload.isActive,
            },
        )[0]
        return row

    def list_google_notification_rules(self) -> list[dict[str, Any]]:
        return self._run(
            """
            select id, source, source_entity_id, title_template, message_template, due_at, timezone
            from notification_rules
            where channel = 'google_calendar' and is_active = true and user_id = :user_id
            """,
            {"user_id": self.default_user_id},
        )

    def any_calendar_integration_id(self) -> UUID | None:
        rows = self._run(
            """
            select id from calendar_integrations
            where user_id = :user_id and provider = 'google' and sync_enabled = true
            order by created_at asc
            limit 1
            """,
            {"user_id": self.default_user_id},
        )
        return rows[0]["id"] if rows else None

    def get_calendar_event(self, integration_id: UUID, event_uid: str) -> dict[str, Any] | None:
        rows = self._run(
            """
            select id, event_hash, provider_event_id from calendar_events
            where calendar_integration_id = :integration_id and event_uid = :event_uid
            limit 1
            """,
            {"integration_id": integration_id, "event_uid": event_uid},
        )
        return rows[0] if rows else None

    def create_calendar_event(self, integration_id: UUID, rule_id: UUID, event_uid: str, event_hash: str, provider_event_id: str) -> None:
        self._run(
            """
            insert into calendar_events (id, notification_rule_id, calendar_integration_id, provider_event_id, event_uid, event_hash)
            values (:id, :notification_rule_id, :calendar_integration_id, :provider_event_id, :event_uid, :event_hash)
            """,
            {
                "id": str(uuid4()),
                "notification_rule_id": rule_id,
                "calendar_integration_id": integration_id,
                "provider_event_id": provider_event_id,
                "event_uid": event_uid,
                "event_hash": event_hash,
            },
        )

    def update_calendar_event_hash(self, event_id: UUID, event_hash: str) -> None:
        self._run(
            "update calendar_events set event_hash = :event_hash, updated_at = now(), last_synced_at = now() where id = :id",
            {"id": event_id, "event_hash": event_hash},
        )

    def debug_counts(self) -> dict[str, int]:
        self._ensure_rates_tables()
        queries = {
            "users": "select count(*) as c from users",
            "accounts": "select count(*) as c from accounts where user_id = :user_id",
            "transactions": "select count(*) as c from transactions where user_id = :user_id",
            "vehicles": "select count(*) as c from vehicles where user_id = :user_id",
            "vehicleServices": "select count(*) as c from vehicle_services vs join vehicles v on v.id = vs.vehicle_id where v.user_id = :user_id",
            "vehicleServiceRules": "select count(*) as c from vehicle_service_rules vr join vehicles v on v.id = vr.vehicle_id where v.user_id = :user_id",
            "properties": "select count(*) as c from properties where user_id = :user_id",
            "propertyCosts": "select count(*) as c from property_costs pc join properties p on p.id = pc.property_id where p.user_id = :user_id",
            "insurances": "select count(*) as c from insurances where user_id = :user_id",
            "insurancePremiums": "select count(*) as c from insurance_premiums ip join insurances i on i.id = ip.insurance_id where i.user_id = :user_id",
            "calendarIntegrations": "select count(*) as c from calendar_integrations where user_id = :user_id",
            "notificationRules": "select count(*) as c from notification_rules where user_id = :user_id",
            "notificationDeliveries": "select count(*) as c from notification_deliveries nd join notification_rules nr on nr.id = nd.notification_rule_id where nr.user_id = :user_id",
            "calendarEvents": "select count(*) as c from calendar_events ce join calendar_integrations ci on ci.id = ce.calendar_integration_id where ci.user_id = :user_id",
            "rateAssets": "select count(*) as c from rate_assets where user_id = :user_id",
            "rateSnapshots": "select count(*) as c from rate_snapshots where user_id = :user_id",
        }
        out: dict[str, int] = {}
        for key, query in queries.items():
            rows = self._run(query, {"user_id": self.default_user_id})
            out[key] = int(rows[0]["c"])
        return out

    def export_backup(self, user_id: UUID) -> dict[str, Any]:
        return {
            "meta": {
                "version": 1,
                "exportedAt": datetime.utcnow().isoformat() + "Z",
                "storageBackend": "postgres",
            },
            "data": {
                "appSettings": self.get_app_settings(user_id).model_dump(),
                "customLocales": self._run(
                    "select locale, message_key, message_value from locale_custom_messages where user_id = :user_id order by locale, message_key",
                    {"user_id": user_id},
                ),
                "users": self._run("select id, email, full_name, created_at, updated_at from users where id = :user_id", {"user_id": user_id}),
                "userCredentials": self._run("select user_id, password_hash, created_at, updated_at from user_credentials where user_id = :user_id", {"user_id": user_id}),
                "accounts": self._run("select * from accounts where user_id = :user_id order by created_at", {"user_id": user_id}),
                "transactions": self._run("select * from transactions where user_id = :user_id order by created_at", {"user_id": user_id}),
                "rateWatchlist": [row["symbol"] for row in self._run("select symbol from rate_assets where user_id = :user_id order by symbol", {"user_id": user_id})],
                "rateSnapshots": self._run(
                    "select symbol, price, currency, source, last_updated_at as updated_at from rate_snapshots where user_id = :user_id order by symbol",
                    {"user_id": user_id},
                ),
                "vehicles": self._run("select * from vehicles where user_id = :user_id order by created_at", {"user_id": user_id}),
                "vehicleServices": self._run(
                    """
                    select vs.* from vehicle_services vs
                    join vehicles v on v.id = vs.vehicle_id
                    where v.user_id = :user_id
                    order by vs.created_at
                    """,
                    {"user_id": user_id},
                ),
                "vehicleServiceRules": self._run(
                    """
                    select vr.* from vehicle_service_rules vr
                    join vehicles v on v.id = vr.vehicle_id
                    where v.user_id = :user_id
                    order by vr.created_at
                    """,
                    {"user_id": user_id},
                ),
                "properties": self._run("select * from properties where user_id = :user_id order by created_at", {"user_id": user_id}),
                "propertyCosts": self._run(
                    """
                    select pc.* from property_costs pc
                    join properties p on p.id = pc.property_id
                    where p.user_id = :user_id
                    order by pc.created_at
                    """,
                    {"user_id": user_id},
                ),
                "insurances": self._run("select * from insurances where user_id = :user_id order by created_at", {"user_id": user_id}),
                "insurancePremiums": self._run(
                    """
                    select ip.* from insurance_premiums ip
                    join insurances i on i.id = ip.insurance_id
                    where i.user_id = :user_id
                    order by ip.created_at
                    """,
                    {"user_id": user_id},
                ),
                "calendarIntegrations": self._run(
                    "select * from calendar_integrations where user_id = :user_id order by created_at",
                    {"user_id": user_id},
                ),
                "notificationRules": self._run(
                    "select * from notification_rules where user_id = :user_id order by created_at",
                    {"user_id": user_id},
                ),
                "notificationDeliveries": self._run(
                    """
                    select nd.* from notification_deliveries nd
                    join notification_rules nr on nr.id = nd.notification_rule_id
                    where nr.user_id = :user_id
                    order by nd.created_at
                    """,
                    {"user_id": user_id},
                ),
                "calendarEvents": self._run(
                    """
                    select ce.* from calendar_events ce
                    join calendar_integrations ci on ci.id = ce.calendar_integration_id
                    where ci.user_id = :user_id
                    order by ce.created_at
                    """,
                    {"user_id": user_id},
                ),
            },
        }

    def import_backup(self, user_id: UUID, payload: dict[str, Any]) -> dict[str, int]:
        self._ensure_auth_columns()
        self._ensure_app_settings_columns()
        self._ensure_rates_tables()
        data = payload.get("data", {})
        with self.engine.begin() as conn:
            conn.execute(
                text("insert into users (id, email) values (:id, :email) on conflict (id) do nothing"),
                {"id": user_id, "email": "default@local"},
            )
            cleanup_sql = [
                "delete from transactions where user_id = :user_id",
                "delete from accounts where user_id = :user_id",
                "delete from rate_snapshots where user_id = :user_id",
                "delete from rate_assets where user_id = :user_id",
                "delete from calendar_events ce using calendar_integrations ci where ce.calendar_integration_id = ci.id and ci.user_id = :user_id",
                "delete from notification_deliveries nd using notification_rules nr where nd.notification_rule_id = nr.id and nr.user_id = :user_id",
                "delete from notification_rules where user_id = :user_id",
                "delete from calendar_integrations where user_id = :user_id",
                "delete from insurance_premiums ip using insurances i where ip.insurance_id = i.id and i.user_id = :user_id",
                "delete from insurances where user_id = :user_id",
                "delete from property_costs pc using properties p where pc.property_id = p.id and p.user_id = :user_id",
                "delete from properties where user_id = :user_id",
                "delete from vehicle_service_rules vr using vehicles v where vr.vehicle_id = v.id and v.user_id = :user_id",
                "delete from vehicle_services vs using vehicles v where vs.vehicle_id = v.id and v.user_id = :user_id",
                "delete from vehicles where user_id = :user_id",
                "delete from locale_custom_messages where user_id = :user_id",
                "delete from app_settings where user_id = :user_id",
                "delete from user_credentials where user_id = :user_id",
            ]
            for q in cleanup_sql:
                conn.execute(text(q), {"user_id": user_id})

            users_rows = data.get("users", [])
            if users_rows:
                for u in users_rows:
                    conn.execute(
                        text(
                            """
                            insert into users (id, email, full_name)
                            values (:id, :email, :full_name)
                            on conflict (id) do update set email = excluded.email, full_name = excluded.full_name, updated_at = now()
                            """
                        ),
                        {
                            "id": u.get("id", user_id),
                            "email": u.get("email", "default@local"),
                            "full_name": u.get("full_name"),
                        },
                    )

            for c in data.get("userCredentials", []):
                conn.execute(
                    text(
                        "insert into user_credentials (user_id, password_hash) values (:user_id, :password_hash) on conflict (user_id) do update set password_hash = excluded.password_hash, updated_at = now()"
                    ),
                    {"user_id": c.get("user_id", user_id), "password_hash": c.get("password_hash", hash_password("ChangeMe123!"))},
                )

            app_settings = data.get("appSettings", {})
            if app_settings:
                conn.execute(
                    text(
                        """
                        insert into app_settings (
                          id, user_id, default_timezone, calendar_provider, calendar_sync_enabled, self_registration_enabled, smtp_enabled,
                          default_locale, default_display_currency, secondary_display_currency, auto_backup_enabled, auto_backup_interval_minutes, auto_backup_retention_days, auto_backup_last_run_at,
                          session_timeout_minutes
                        )
                        values (
                          :id, :user_id, :default_timezone, :calendar_provider, :calendar_sync_enabled, :self_registration_enabled, :smtp_enabled,
                          :default_locale, :default_display_currency, :secondary_display_currency, :auto_backup_enabled, :auto_backup_interval_minutes, :auto_backup_retention_days, :auto_backup_last_run_at,
                          :session_timeout_minutes
                        )
                        """
                    ),
                    {
                        "id": str(uuid4()),
                        "user_id": user_id,
                        "default_timezone": app_settings.get("defaultTimezone", "Europe/Prague"),
                        "calendar_provider": app_settings.get("calendarProvider", "google"),
                        "calendar_sync_enabled": app_settings.get("calendarSyncEnabled", True),
                        "self_registration_enabled": app_settings.get("selfRegistrationEnabled", True),
                        "smtp_enabled": app_settings.get("smtpEnabled", False),
                        "default_locale": app_settings.get("defaultLocale", "en"),
                        "default_display_currency": app_settings.get("defaultDisplayCurrency", "CZK"),
                        "secondary_display_currency": app_settings.get("secondaryDisplayCurrency", "USD"),
                        "auto_backup_enabled": app_settings.get("autoBackupEnabled", False),
                        "auto_backup_interval_minutes": app_settings.get("autoBackupIntervalMinutes", 1440),
                        "auto_backup_retention_days": app_settings.get("autoBackupRetentionDays", 30),
                        "auto_backup_last_run_at": app_settings.get("autoBackupLastRunAt"),
                        "session_timeout_minutes": app_settings.get("sessionTimeoutMinutes"),
                    },
                )

            custom_locales = data.get("customLocales", [])
            if isinstance(custom_locales, dict):
                custom_rows: list[dict[str, Any]] = []
                for locale, messages in custom_locales.items():
                    for key, value in (messages or {}).items():
                        custom_rows.append({"locale": locale, "message_key": key, "message_value": value})
            else:
                custom_rows = custom_locales

            for row in custom_rows:
                if isinstance(row, dict) and "locale" in row and "message_key" in row:
                    conn.execute(
                        text(
                            """
                            insert into locale_custom_messages (id, user_id, locale, message_key, message_value)
                            values (:id, :user_id, :locale, :message_key, :message_value)
                            """
                        ),
                        {
                            "id": str(uuid4()),
                            "user_id": user_id,
                            "locale": row["locale"],
                            "message_key": row["message_key"],
                            "message_value": row["message_value"],
                        },
                    )

            def insert_rows(table: str, rows: list[dict[str, Any]], cols: list[str], force_user: bool = False) -> None:
                if not rows:
                    return
                col_csv = ", ".join(cols)
                val_csv = ", ".join(f":{c}" for c in cols)
                stmt = text(f"insert into {table} ({col_csv}) values ({val_csv})")
                for r in rows:
                    params = {c: r.get(c) for c in cols}
                    if force_user:
                        params["user_id"] = user_id
                    conn.execute(stmt, params)

            insert_rows("vehicles", data.get("vehicles", []), ["id", "user_id", "type", "label", "vin", "plate_number", "make", "model", "production_year", "purchased_at", "current_odometer_km", "notes"], True)
            insert_rows("accounts", data.get("accounts", []), ["id", "user_id", "name", "account_type", "currency", "initial_balance", "initial_balance_at", "current_balance"], True)
            insert_rows(
                "transactions",
                data.get("transactions", []),
                [
                    "id",
                    "user_id",
                    "account_id",
                    "amount",
                    "currency",
                    "transaction_at",
                    "direction",
                    "category",
                    "note",
                    "transfer_group_id",
                    "recurring_group_id",
                    "recurring_frequency",
                    "recurring_index",
                    "recurring_day_of_month",
                    "recurring_weekend_policy",
                ],
                True,
            )
            rate_watch = [str(s).strip().upper() for s in data.get("rateWatchlist", []) if str(s).strip()]
            for sym in rate_watch:
                conn.execute(
                    text(
                        """
                        insert into rate_assets (id, user_id, symbol, created_at, updated_at)
                        values (:id, :user_id, :symbol, now(), now())
                        on conflict (user_id, symbol)
                        do update set updated_at = now()
                        """
                    ),
                    {"id": str(uuid4()), "user_id": user_id, "symbol": sym},
                )
            for row in data.get("rateSnapshots", []):
                if not isinstance(row, dict):
                    continue
                sym = str(row.get("symbol", "")).strip().upper()
                if not sym:
                    continue
                conn.execute(
                    text(
                        """
                        insert into rate_assets (id, user_id, symbol, created_at, updated_at)
                        values (:id, :user_id, :symbol, now(), now())
                        on conflict (user_id, symbol)
                        do update set updated_at = now()
                        """
                    ),
                    {"id": str(uuid4()), "user_id": user_id, "symbol": sym},
                )
                conn.execute(
                    text(
                        """
                        insert into rate_snapshots (id, user_id, symbol, price, currency, source, last_updated_at, created_at, updated_at)
                        values (:id, :user_id, :symbol, :price, :currency, :source, :last_updated_at, now(), now())
                        on conflict (user_id, symbol)
                        do update set price = excluded.price, currency = excluded.currency, source = excluded.source, last_updated_at = excluded.last_updated_at, updated_at = now()
                        """
                    ),
                    {
                        "id": str(uuid4()),
                        "user_id": user_id,
                        "symbol": sym,
                        "price": row.get("price"),
                        "currency": str(row.get("currency", "USD")).strip().upper(),
                        "source": str(row.get("source", "manual")).strip().lower(),
                        "last_updated_at": row.get("updatedAt") or row.get("updated_at") or datetime.utcnow(),
                    },
                )
            insert_rows("vehicle_services", data.get("vehicleServices", []), ["id", "vehicle_id", "service_type", "service_at", "odometer_km", "total_cost", "currency", "vendor", "description", "receipt_url"])
            insert_rows("vehicle_service_rules", data.get("vehicleServiceRules", []), ["id", "vehicle_id", "service_type", "interval_value", "interval_unit", "lead_days", "last_service_id", "next_due_date", "next_due_odometer_km", "is_active"])
            insert_rows("properties", data.get("properties", []), ["id", "user_id", "type", "name", "address_line1", "city", "postal_code", "country_code", "acquired_at", "purchase_price", "purchase_currency", "estimated_value", "estimated_value_currency", "estimated_value_updated_at", "floor_area_m2", "land_area_m2", "notes"], True)
            insert_rows("property_costs", data.get("propertyCosts", []), ["id", "property_id", "cost_type", "period_start", "period_end", "amount", "currency", "provider", "meter_value", "meter_unit", "is_recurring", "recurring_template_id"])
            insert_rows("insurances", data.get("insurances", []), ["id", "user_id", "insurance_type", "provider", "policy_number", "subject_vehicle_id", "subject_property_id", "coverage_amount", "coverage_currency", "deductible_amount", "deductible_currency", "valid_from", "valid_to", "payment_frequency", "is_active"], True)
            insert_rows("insurance_premiums", data.get("insurancePremiums", []), ["id", "insurance_id", "period_start", "period_end", "amount", "currency", "paid_at", "payment_transaction_id"])
            for row in data.get("calendarIntegrations", []):
                conn.execute(
                    text(
                        """
                        insert into calendar_integrations (id, user_id, provider, external_calendar_id, access_token_encrypted, refresh_token_encrypted, token_expires_at, sync_enabled)
                        values (:id, :user_id, :provider, :external_calendar_id, :access_token_encrypted, :refresh_token_encrypted, :token_expires_at, :sync_enabled)
                        """
                    ),
                    {
                        "id": row.get("id", str(uuid4())),
                        "user_id": user_id,
                        "provider": row.get("provider", "google"),
                        "external_calendar_id": row.get("external_calendar_id", row.get("externalCalendarId", "primary")),
                        "access_token_encrypted": row.get("access_token_encrypted", "imported-token"),
                        "refresh_token_encrypted": row.get("refresh_token_encrypted", "imported-token"),
                        "token_expires_at": row.get("token_expires_at"),
                        "sync_enabled": row.get("sync_enabled", row.get("syncEnabled", True)),
                    },
                )
            insert_rows("notification_rules", data.get("notificationRules", []), ["id", "user_id", "source", "source_entity_id", "title_template", "message_template", "due_at", "lead_days", "channel", "timezone", "is_active"], True)
            insert_rows("notification_deliveries", data.get("notificationDeliveries", []), ["id", "notification_rule_id", "scheduled_for", "delivered_at", "status", "attempts", "error_message", "provider_message_id"])
            insert_rows("calendar_events", data.get("calendarEvents", []), ["id", "notification_rule_id", "calendar_integration_id", "provider_event_id", "event_uid", "event_hash", "last_synced_at"])

        return self.debug_counts()

    def mark_auto_backup_run(self, user_id: UUID, when: datetime) -> None:
        self._run(
            "update app_settings set auto_backup_last_run_at = :when, updated_at = now() where user_id = :user_id",
            {"when": when, "user_id": user_id},
        )

    def register_user(self, email: str, password: str, full_name: str | None) -> dict[str, Any]:
        self._ensure_auth_columns()
        exists = self._run("select id from users where lower(email) = lower(:email) limit 1", {"email": email})
        if exists:
            raise HTTPException(status_code=409, detail="email already registered")
        user_id = uuid4()
        self._run(
            "insert into users (id, email, full_name) values (:id, :email, :full_name)",
            {"id": user_id, "email": email, "full_name": full_name},
        )
        self._run(
            "insert into user_credentials (user_id, password_hash) values (:user_id, :password_hash)",
            {"user_id": user_id, "password_hash": hash_password(password)},
        )
        return {"id": user_id, "email": email, "full_name": full_name}

    def authenticate_user(self, email: str, password: str) -> dict[str, Any] | None:
        self._ensure_auth_columns()
        rows = self._run(
            """
            select u.id, u.email, u.full_name, c.password_hash
            from users u
            join user_credentials c on c.user_id = u.id
            where lower(u.email) = lower(:email)
            limit 1
            """,
            {"email": email},
        )
        if not rows:
            return None
        row = rows[0]
        if not verify_password(password, row["password_hash"]):
            return None
        return {"id": row["id"], "email": row["email"], "full_name": row["full_name"]}

    def get_user_by_id(self, user_id: UUID) -> dict[str, Any] | None:
        rows = self._run("select id, email, full_name from users where id = :id limit 1", {"id": user_id})
        return rows[0] if rows else None

    def update_user_profile(self, user_id: UUID, email: str | None, full_name: str | None) -> dict[str, Any]:
        row = self.get_user_by_id(user_id)
        if row is None:
            raise HTTPException(status_code=404, detail="user not found")
        new_email = row["email"] if email is None else email
        new_full_name = row.get("full_name") if full_name is None else full_name
        if email is not None:
            exists = self._run(
                "select id from users where lower(email) = lower(:email) and id <> :id limit 1",
                {"email": email, "id": user_id},
            )
            if exists:
                raise HTTPException(status_code=409, detail="email already registered")
        updated = self._run(
            "update users set email = :email, full_name = :full_name, updated_at = now() where id = :id returning id, email, full_name",
            {"id": user_id, "email": new_email, "full_name": new_full_name},
        )
        return updated[0]

    def change_user_password(self, user_id: UUID, current_password: str, new_password: str) -> None:
        self._ensure_auth_columns()
        row = self._run("select password_hash from user_credentials where user_id = :id limit 1", {"id": user_id})
        if not row:
            raise HTTPException(status_code=404, detail="credentials not found")
        if not verify_password(current_password, row[0]["password_hash"]):
            raise HTTPException(status_code=401, detail="invalid current password")
        self._run(
            "update user_credentials set password_hash = :password_hash, updated_at = now() where user_id = :id",
            {"id": user_id, "password_hash": hash_password(new_password)},
        )

    def create_account(self, user_id: UUID, payload: AccountCreate) -> dict[str, Any]:
        self._ensure_auth_columns()
        initial_balance_at = payload.initialBalanceAt or datetime.utcnow()
        row = self._run(
            """
            insert into accounts (id, user_id, name, account_type, currency, initial_balance, initial_balance_at, current_balance)
            values (:id, :user_id, :name, :account_type, :currency, :initial_balance, :initial_balance_at, :current_balance)
            returning id, name, account_type, currency, initial_balance, initial_balance_at, current_balance, created_at
            """,
            {
                "id": str(uuid4()),
                "user_id": user_id,
                "name": payload.name,
                "account_type": payload.accountType,
                "currency": payload.currency,
                "initial_balance": _to_float(payload.initialBalance),
                "initial_balance_at": initial_balance_at,
                "current_balance": _to_float(payload.initialBalance),
            },
        )[0]
        return row

    def list_accounts(self, user_id: UUID) -> list[dict[str, Any]]:
        return self._run(
            """
            select id, name, account_type, currency, initial_balance, initial_balance_at, current_balance, created_at
            from accounts
            where user_id = :user_id
            order by created_at desc
            """,
            {"user_id": user_id},
        )

    def create_transaction(self, user_id: UUID, payload: TransactionCreate) -> dict[str, Any]:
        self._ensure_auth_columns()
        account = self._run("select id from accounts where id = :id and user_id = :user_id limit 1", {"id": payload.accountId, "user_id": user_id})
        if not account:
            raise HTTPException(status_code=404, detail=f"account not found: {payload.accountId}")
        recurring_group_id = str(uuid4()) if payload.recurringFrequency else None
        day_anchor = payload.recurringDayOfMonth or payload.occurredAt.day
        weekend_policy = payload.recurringWeekendPolicy or "exact"
        first: dict[str, Any] | None = None
        for idx in range(payload.recurringCount):
            tx_time = (
                _move_from_weekend(payload.occurredAt, weekend_policy)
                if not payload.recurringFrequency
                else _shift_recurring(payload.occurredAt, payload.recurringFrequency, idx, day_anchor, weekend_policy)
            )
            row = self._run(
                """
                insert into transactions (
                  id, user_id, account_id, amount, currency, transaction_at, direction, category, note,
                  transfer_group_id, recurring_group_id, recurring_frequency, recurring_index, recurring_day_of_month, recurring_weekend_policy
                )
                values (
                  :id, :user_id, :account_id, :amount, :currency, :transaction_at, :direction, :category, :note,
                  null, :recurring_group_id, :recurring_frequency, :recurring_index, :recurring_day_of_month, :recurring_weekend_policy
                )
                returning id, account_id, direction, amount, currency, transaction_at, category, note,
                          transfer_group_id, recurring_group_id, recurring_frequency, recurring_index, recurring_day_of_month, recurring_weekend_policy
                """,
                {
                    "id": str(uuid4()),
                    "user_id": user_id,
                    "account_id": payload.accountId,
                    "amount": _to_float(payload.amount),
                    "currency": payload.currency,
                    "transaction_at": tx_time,
                    "direction": payload.direction,
                    "category": payload.category,
                    "note": payload.note,
                    "recurring_group_id": recurring_group_id,
                    "recurring_frequency": payload.recurringFrequency,
                    "recurring_index": idx + 1 if payload.recurringFrequency else None,
                    "recurring_day_of_month": day_anchor if payload.recurringFrequency in {"monthly", "yearly"} else None,
                    "recurring_weekend_policy": weekend_policy if payload.recurringFrequency else None,
                },
            )[0]
            self._run(
                "update accounts set current_balance = current_balance + :delta, updated_at = now() where id = :id",
                {"delta": _to_float(payload.amount * _tx_sign(payload.direction)), "id": payload.accountId},
            )
            if first is None:
                first = row
        return first or {}

    def list_transactions(self, user_id: UUID) -> list[dict[str, Any]]:
        return self._run(
            """
            select id, account_id, direction, amount, currency, transaction_at, category, note,
                   transfer_group_id, recurring_group_id, recurring_frequency, recurring_index, recurring_day_of_month, recurring_weekend_policy
            from transactions
            where user_id = :user_id
            order by transaction_at desc
            """,
            {"user_id": user_id},
        )

    def update_account(self, user_id: UUID, account_id: UUID, payload: AccountUpdate) -> dict[str, Any]:
        current = self._run(
            "select id, name, account_type, currency, initial_balance, initial_balance_at, current_balance, created_at from accounts where id = :id and user_id = :user_id limit 1",
            {"id": account_id, "user_id": user_id},
        )
        if not current:
            raise HTTPException(status_code=404, detail=f"account not found: {account_id}")
        merged = current[0].copy()
        updates = payload.model_dump(exclude_none=True)
        if "name" in updates:
            merged["name"] = updates["name"]
        if "accountType" in updates:
            merged["account_type"] = updates["accountType"]
        if "currency" in updates:
            merged["currency"] = updates["currency"]
        if "initialBalanceAt" in updates:
            merged["initial_balance_at"] = updates["initialBalanceAt"]
        if "initialBalance" in updates:
            merged["initial_balance"] = _to_float(updates["initialBalance"])
            tx_total_rows = self._run(
                """
                select coalesce(sum(case when direction = 'income' then amount else -amount end), 0) as signed_total
                from transactions
                where user_id = :user_id and account_id = :account_id
                """,
                {"user_id": user_id, "account_id": account_id},
            )
            signed_total = tx_total_rows[0]["signed_total"] if tx_total_rows else 0
            merged["current_balance"] = Decimal(str(merged["initial_balance"])) + Decimal(str(signed_total))
        row = self._run(
            """
            update accounts
            set name = :name, account_type = :account_type, currency = :currency,
                initial_balance = :initial_balance, initial_balance_at = :initial_balance_at, current_balance = :current_balance, updated_at = now()
            where id = :id and user_id = :user_id
            returning id, name, account_type, currency, initial_balance, initial_balance_at, current_balance, created_at
            """,
            {
                "id": account_id,
                "user_id": user_id,
                "name": merged["name"],
                "account_type": merged["account_type"],
                "currency": merged["currency"],
                "initial_balance": merged["initial_balance"],
                "initial_balance_at": merged.get("initial_balance_at"),
                "current_balance": merged["current_balance"],
            },
        )[0]
        return row

    def delete_account(self, user_id: UUID, account_id: UUID, action: AccountDeleteAction, target_account_id: UUID | None = None) -> None:
        source_rows = self._run(
            "select id, current_balance from accounts where id = :id and user_id = :user_id limit 1",
            {"id": account_id, "user_id": user_id},
        )
        if not source_rows:
            raise HTTPException(status_code=404, detail=f"account not found: {account_id}")
        if action == AccountDeleteAction.transfer_balance:
            if target_account_id is None:
                raise HTTPException(status_code=400, detail="targetAccountId is required for transfer_balance")
            if target_account_id == account_id:
                raise HTTPException(status_code=400, detail="targetAccountId must be different from account_id")
            target = self._run(
                "select id from accounts where id = :id and user_id = :user_id limit 1",
                {"id": target_account_id, "user_id": user_id},
            )
            if not target:
                raise HTTPException(status_code=404, detail=f"account not found: {target_account_id}")
            self._run(
                "update accounts set current_balance = current_balance + :delta, updated_at = now() where id = :id and user_id = :user_id",
                {"delta": source_rows[0]["current_balance"], "id": target_account_id, "user_id": user_id},
            )
        self._run("delete from transactions where account_id = :account_id and user_id = :user_id", {"account_id": account_id, "user_id": user_id})
        self._run("delete from accounts where id = :id and user_id = :user_id", {"id": account_id, "user_id": user_id})

    def update_transaction(self, user_id: UUID, transaction_id: UUID, payload: TransactionUpdate) -> dict[str, Any]:
        current = self._run(
            """
            select id, account_id, direction, amount, currency, transaction_at, category, note,
                   transfer_group_id, recurring_group_id, recurring_frequency, recurring_index, recurring_day_of_month, recurring_weekend_policy
            from transactions
            where id = :id and user_id = :user_id
            limit 1
            """,
            {"id": transaction_id, "user_id": user_id},
        )
        if not current:
            raise HTTPException(status_code=404, detail=f"transaction not found: {transaction_id}")
        merged = current[0].copy()
        updates = payload.model_dump(exclude_none=True)
        original_account_id = row_account_id = merged["account_id"]
        if "accountId" in updates:
            target = self._run(
                "select id from accounts where id = :id and user_id = :user_id limit 1",
                {"id": updates["accountId"], "user_id": user_id},
            )
            if not target:
                raise HTTPException(status_code=404, detail=f"account not found: {updates['accountId']}")
            merged["account_id"] = updates["accountId"]
            row_account_id = updates["accountId"]
        if "direction" in updates:
            merged["direction"] = updates["direction"]
        if "amount" in updates:
            merged["amount"] = _to_float(updates["amount"])
        if "currency" in updates:
            merged["currency"] = updates["currency"]
        if "occurredAt" in updates:
            merged["transaction_at"] = updates["occurredAt"]
        if "category" in updates:
            merged["category"] = updates["category"]
        if "note" in updates:
            merged["note"] = updates["note"]
        old_delta = Decimal(str(current[0]["amount"])) * _tx_sign(current[0]["direction"])
        new_delta = Decimal(str(merged["amount"])) * _tx_sign(merged["direction"])
        row = self._run(
            """
            update transactions
            set account_id = :account_id, direction = :direction, amount = :amount, currency = :currency, transaction_at = :transaction_at, category = :category, note = :note, updated_at = now()
            where id = :id and user_id = :user_id
            returning id, account_id, direction, amount, currency, transaction_at, category, note,
                      transfer_group_id, recurring_group_id, recurring_frequency, recurring_index, recurring_day_of_month, recurring_weekend_policy
            """,
            {
                "id": transaction_id,
                "user_id": user_id,
                "account_id": row_account_id,
                "direction": merged["direction"],
                "amount": merged["amount"],
                "currency": merged["currency"],
                "transaction_at": merged["transaction_at"],
                "category": merged.get("category"),
                "note": merged.get("note"),
            },
        )[0]
        if original_account_id != row["account_id"]:
            self._run(
                "update accounts set current_balance = current_balance - :delta, updated_at = now() where id = :id and user_id = :user_id",
                {"delta": _to_float(old_delta), "id": original_account_id, "user_id": user_id},
            )
            self._run(
                "update accounts set current_balance = current_balance + :delta, updated_at = now() where id = :id and user_id = :user_id",
                {"delta": _to_float(new_delta), "id": row["account_id"], "user_id": user_id},
            )
            return row
        self._run(
            "update accounts set current_balance = current_balance + :delta, updated_at = now() where id = :id and user_id = :user_id",
            {"delta": _to_float(new_delta - old_delta), "id": row["account_id"], "user_id": user_id},
        )
        return row

    def delete_transaction(self, user_id: UUID, transaction_id: UUID) -> None:
        current = self._run(
            "select id, account_id, direction, amount from transactions where id = :id and user_id = :user_id limit 1",
            {"id": transaction_id, "user_id": user_id},
        )
        if not current:
            raise HTTPException(status_code=404, detail=f"transaction not found: {transaction_id}")
        row = current[0]
        delta = Decimal(str(row["amount"])) * _tx_sign(row["direction"])
        self._run("delete from transactions where id = :id and user_id = :user_id", {"id": transaction_id, "user_id": user_id})
        self._run(
            "update accounts set current_balance = current_balance - :delta, updated_at = now() where id = :id and user_id = :user_id",
            {"delta": _to_float(delta), "id": row["account_id"], "user_id": user_id},
        )

    def transfer_between_accounts(self, user_id: UUID, payload: TransactionTransferCreate) -> dict[str, Any]:
        self._ensure_auth_columns()
        from_account = self._run(
            "select id from accounts where id = :id and user_id = :user_id limit 1",
            {"id": payload.fromAccountId, "user_id": user_id},
        )
        to_account = self._run(
            "select id from accounts where id = :id and user_id = :user_id limit 1",
            {"id": payload.toAccountId, "user_id": user_id},
        )
        if not from_account:
            raise HTTPException(status_code=404, detail=f"account not found: {payload.fromAccountId}")
        if not to_account:
            raise HTTPException(status_code=404, detail=f"account not found: {payload.toAccountId}")
        transfer_group_id = str(uuid4())
        outgoing = self._run(
            """
            insert into transactions (
              id, user_id, account_id, amount, currency, transaction_at, direction, category, note,
              transfer_group_id, recurring_group_id, recurring_frequency, recurring_index, recurring_day_of_month, recurring_weekend_policy
            )
            values (
              :id, :user_id, :account_id, :amount, :currency, :transaction_at, 'expense', :category, :note,
              :transfer_group_id, null, null, null, null, null
            )
            returning id, account_id, direction, amount, currency, transaction_at, category, note,
                      transfer_group_id, recurring_group_id, recurring_frequency, recurring_index, recurring_day_of_month, recurring_weekend_policy
            """,
            {
                "id": str(uuid4()),
                "user_id": user_id,
                "account_id": payload.fromAccountId,
                "amount": _to_float(payload.amount),
                "currency": payload.currency,
                "transaction_at": payload.occurredAt,
                "category": payload.category,
                "note": payload.note,
                "transfer_group_id": transfer_group_id,
            },
        )[0]
        incoming = self._run(
            """
            insert into transactions (
              id, user_id, account_id, amount, currency, transaction_at, direction, category, note,
              transfer_group_id, recurring_group_id, recurring_frequency, recurring_index, recurring_day_of_month, recurring_weekend_policy
            )
            values (
              :id, :user_id, :account_id, :amount, :currency, :transaction_at, 'income', :category, :note,
              :transfer_group_id, null, null, null, null, null
            )
            returning id, account_id, direction, amount, currency, transaction_at, category, note,
                      transfer_group_id, recurring_group_id, recurring_frequency, recurring_index, recurring_day_of_month, recurring_weekend_policy
            """,
            {
                "id": str(uuid4()),
                "user_id": user_id,
                "account_id": payload.toAccountId,
                "amount": _to_float(payload.amount),
                "currency": payload.currency,
                "transaction_at": payload.occurredAt,
                "category": payload.category,
                "note": payload.note,
                "transfer_group_id": transfer_group_id,
            },
        )[0]
        self._run(
            "update accounts set current_balance = current_balance - :delta, updated_at = now() where id = :id and user_id = :user_id",
            {"delta": _to_float(payload.amount), "id": payload.fromAccountId, "user_id": user_id},
        )
        self._run(
            "update accounts set current_balance = current_balance + :delta, updated_at = now() where id = :id and user_id = :user_id",
            {"delta": _to_float(payload.amount), "id": payload.toAccountId, "user_id": user_id},
        )
        return {"transferGroupId": UUID(transfer_group_id), "outgoing": outgoing, "incoming": incoming}

    def list_transaction_category_stats(self, user_id: UUID) -> TransactionCategoryStatsResponse:
        rows = self._run(
            """
            select category, count(*)::integer as usage_count
            from transactions
            where user_id = :user_id and coalesce(trim(category), '') <> ''
            group by category
            order by usage_count desc, lower(category) asc
            """,
            {"user_id": user_id},
        )
        categories = [{"category": row["category"], "usageCount": row["usage_count"]} for row in rows]
        most_used = categories[0]["category"] if categories else None
        return TransactionCategoryStatsResponse(mostUsedCategory=most_used, categories=categories)

    def rename_transaction_category(self, user_id: UUID, category: str, payload: TransactionCategoryRename) -> TransactionCategoryStatsResponse:
        old_category = category.strip()
        if not old_category:
            raise HTTPException(status_code=400, detail="category must not be empty")
        updated = self._run(
            """
            update transactions
            set category = :new_category, updated_at = now()
            where user_id = :user_id and category = :old_category
            returning id
            """,
            {"new_category": payload.newCategory, "user_id": user_id, "old_category": old_category},
        )
        if not updated:
            raise HTTPException(status_code=404, detail=f"category not found: {category}")
        return self.list_transaction_category_stats(user_id)

    def delete_transaction_category(self, user_id: UUID, category: str, delete_transactions: bool) -> TransactionCategoryStatsResponse:
        name = category.strip()
        if not name:
            raise HTTPException(status_code=400, detail="category must not be empty")
        rows = self._run(
            """
            select id, account_id, direction, amount
            from transactions
            where user_id = :user_id and category = :category
            """,
            {"user_id": user_id, "category": name},
        )
        if not rows:
            raise HTTPException(status_code=404, detail=f"category not found: {category}")
        if delete_transactions:
            for row in rows:
                delta = Decimal(str(row["amount"])) * _tx_sign(row["direction"])
                self._run(
                    "update accounts set current_balance = current_balance - :delta, updated_at = now() where id = :id and user_id = :user_id",
                    {"delta": _to_float(delta), "id": row["account_id"], "user_id": user_id},
                )
            self._run("delete from transactions where user_id = :user_id and category = :category", {"user_id": user_id, "category": name})
        else:
            self._run(
                "update transactions set category = null, updated_at = now() where user_id = :user_id and category = :category",
                {"user_id": user_id, "category": name},
            )
        return self.list_transaction_category_stats(user_id)

    def delete_user(self, user_id: UUID) -> None:
        self._ensure_auth_columns()
        self._run("delete from users where id = :id", {"id": user_id})


def get_persistence() -> Persistence:
    if settings.storage_backend == "postgres":
        return PostgresPersistence(settings.database_url, settings.default_user_id)
    return InMemoryPersistence()
