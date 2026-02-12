# API kontrakty (v1): garaz, nemovitosti, notifikace

Zakladni REST navrh pro backend (NestJS/FastAPI). JSON, UTF-8, casy v ISO 8601 (`timestamptz`).

## 1) Vehicles

### POST `/api/v1/vehicles`

Request:
```json
{
  "type": "car",
  "label": "Skoda Octavia 2.0 TDI",
  "vin": "TMB...",
  "plateNumber": "1AB2345",
  "make": "Skoda",
  "model": "Octavia",
  "productionYear": 2019,
  "purchasedAt": "2023-04-15",
  "currentOdometerKm": 125000,
  "notes": "Firemni auto"
}
```

Response `201`:
```json
{
  "id": "uuid",
  "type": "car",
  "label": "Skoda Octavia 2.0 TDI",
  "currentOdometerKm": 125000,
  "createdAt": "2026-02-12T17:40:00Z"
}
```

### POST `/api/v1/vehicles/{vehicleId}/services`

Request:
```json
{
  "serviceType": "oil_change",
  "serviceAt": "2026-02-12",
  "odometerKm": 126000,
  "totalCost": 3200.0,
  "currency": "CZK",
  "vendor": "Autoservis Novak",
  "description": "olej + filtr"
}
```

Response `201`:
```json
{
  "id": "uuid",
  "vehicleId": "uuid",
  "serviceType": "oil_change",
  "serviceAt": "2026-02-12",
  "odometerKm": 126000
}
```

### POST `/api/v1/vehicles/{vehicleId}/service-rules`

Request:
```json
{
  "serviceType": "oil_change",
  "intervalValue": 12,
  "intervalUnit": "months",
  "leadDays": 30
}
```

Response `201`:
```json
{
  "id": "uuid",
  "vehicleId": "uuid",
  "serviceType": "oil_change",
  "nextDueDate": "2027-02-12",
  "isActive": true
}
```

## 2) Properties

### POST `/api/v1/properties`

Request:
```json
{
  "type": "house",
  "name": "Rodinny dum Brno",
  "addressLine1": "Kvetna 12",
  "city": "Brno",
  "postalCode": "60200",
  "countryCode": "CZ",
  "acquiredAt": "2022-08-01",
  "purchasePrice": 7800000,
  "purchaseCurrency": "CZK",
  "estimatedValue": 9200000,
  "estimatedValueCurrency": "CZK",
  "estimatedValueUpdatedAt": "2026-02-01"
}
```

Response `201`:
```json
{
  "id": "uuid",
  "type": "house",
  "name": "Rodinny dum Brno",
  "estimatedValue": 9200000
}
```

### POST `/api/v1/properties/{propertyId}/costs`

Request:
```json
{
  "costType": "electricity",
  "periodStart": "2026-01-01",
  "periodEnd": "2026-01-31",
  "amount": 2800.5,
  "currency": "CZK",
  "provider": "CEZ",
  "meterValue": 312.6,
  "meterUnit": "kWh",
  "isRecurring": true
}
```

Response `201`:
```json
{
  "id": "uuid",
  "propertyId": "uuid",
  "costType": "electricity",
  "amount": 2800.5,
  "currency": "CZK"
}
```

## 3) Insurance

### POST `/api/v1/insurances`

Request:
```json
{
  "insuranceType": "vehicle",
  "provider": "Allianz",
  "policyNumber": "POL-2026-1234",
  "subjectVehicleId": "uuid",
  "coverageAmount": 1200000,
  "coverageCurrency": "CZK",
  "deductibleAmount": 5000,
  "deductibleCurrency": "CZK",
  "validFrom": "2026-01-01",
  "validTo": "2026-12-31",
  "paymentFrequency": "yearly"
}
```

Response `201`:
```json
{
  "id": "uuid",
  "insuranceType": "vehicle",
  "provider": "Allianz",
  "validTo": "2026-12-31",
  "isActive": true
}
```

### POST `/api/v1/insurances/{insuranceId}/premiums`

Request:
```json
{
  "periodStart": "2026-01-01",
  "periodEnd": "2026-12-31",
  "amount": 9600,
  "currency": "CZK",
  "paidAt": "2026-01-03",
  "paymentTransactionId": "uuid"
}
```

Response `201`:
```json
{
  "id": "uuid",
  "insuranceId": "uuid",
  "amount": 9600,
  "currency": "CZK"
}
```

## 4) Google Calendar integration + notifications

### POST `/api/v1/integrations/google-calendar/connect`

Request:
```json
{
  "authorizationCode": "oauth-code",
  "externalCalendarId": "primary"
}
```

Response `200`:
```json
{
  "integrationId": "uuid",
  "provider": "google",
  "externalCalendarId": "primary",
  "syncEnabled": true
}
```

### POST `/api/v1/notification-rules`

Request:
```json
{
  "source": "service_rule",
  "sourceEntityId": "uuid",
  "titleTemplate": "STK: Skoda Octavia",
  "messageTemplate": "STK konci za mesic",
  "dueAt": "2026-05-01T08:00:00+02:00",
  "leadDays": 30,
  "channel": "google_calendar",
  "timezone": "Europe/Prague",
  "isActive": true
}
```

Response `201`:
```json
{
  "id": "uuid",
  "channel": "google_calendar",
  "dueAt": "2026-05-01T06:00:00Z",
  "isActive": true
}
```

### POST `/api/v1/sync/google-calendar/run`

Request:
```json
{
  "dryRun": false
}
```

Response `200`:
```json
{
  "created": 3,
  "updated": 1,
  "unchanged": 12,
  "canceled": 0,
  "failed": 0
}
```

## 5) GUI settings and i18n

### GET `/api/v1/settings/app`

Response `200`:
```json
{
  "defaultTimezone": "Europe/Prague",
  "calendarProvider": "google",
  "calendarSyncEnabled": true,
  "selfRegistrationEnabled": true,
  "smtpEnabled": false
}
```

### PUT `/api/v1/settings/app`

Request:
```json
{
  "selfRegistrationEnabled": false,
  "defaultTimezone": "UTC"
}
```

Response `200`:
```json
{
  "defaultTimezone": "UTC",
  "calendarProvider": "google",
  "calendarSyncEnabled": true,
  "selfRegistrationEnabled": false,
  "smtpEnabled": false,
  "autoBackupEnabled": true,
  "autoBackupIntervalMinutes": 60,
  "autoBackupRetentionDays": 14,
  "autoBackupLastRunAt": null
}
```

### PUT `/api/v1/i18n/{locale}/custom`

Request:
```json
{
  "settings.calendar": "Calendar",
  "custom.key": "Custom message"
}
```

Response `200`:
```json
{
  "locale": "en",
  "messages": {
    "settings.calendar": "Calendar",
    "custom.key": "Custom message"
  }
}
```

### POST `/api/v1/i18n/{locale}/custom/publish`

Response `200`:
```json
{
  "locale": "en",
  "path": "i18n/custom/en.json",
  "keys": 2
}
```

## 6) Authentication and first finance data

### POST `/api/v1/auth/register`

Request:
```json
{
  "email": "tester@example.com",
  "password": "Secret123!",
  "fullName": "Test User"
}
```

Response `201`:
```json
{
  "token": "session-token",
  "userId": "uuid",
  "email": "tester@example.com",
  "fullName": "Test User"
}
```

### POST `/api/v1/accounts`

Header:
- `Authorization: Bearer <token>`

Request:
```json
{
  "name": "Main account",
  "accountType": "checking",
  "currency": "CZK",
  "initialBalance": 1000
}
```

### POST `/api/v1/transactions`

Header:
- `Authorization: Bearer <token>`

Request:
```json
{
  "accountId": "uuid",
  "direction": "expense",
  "amount": 100,
  "currency": "CZK",
  "occurredAt": "2026-02-12T18:00:00Z",
  "category": "food",
  "note": "dinner"
}
```

## 7) Backup and restore (machine migration)

### GET `/api/v1/admin/backup/export`

Response `200`:
```json
{
  "meta": {
    "version": 1,
    "exportedAt": "2026-02-12T19:00:00Z",
    "storageBackend": "postgres"
  },
  "data": {
    "appSettings": {},
    "customLocales": [],
    "vehicles": []
  }
}
```

### GET `/api/v1/admin/backup/download`

- Downloads `my-finance-backup.json` as attachment.

### POST `/api/v1/admin/backup/import`

Request:
- same JSON structure as export

Response `200`:
```json
{
  "replaced": true,
  "counts": {
    "vehicles": 12,
    "properties": 1
  }
}
```

### POST `/api/v1/admin/backup/import-file`

- Multipart form upload (`file`) of exported JSON.
- Returns same response shape as `/import`.

### POST `/api/v1/admin/backup/run-now`

Response `200`:
```json
{
  "created": true,
  "file": "backups/my-finance-backup-20260212_193500.json",
  "timestamp": "2026-02-12T19:35:00Z"
}
```

## 8) Validation rules (minimum)

- `currency`: presne 3 znaky (`CZK`, `EUR`, ...).
- `periodEnd >= periodStart`.
- `odometerKm >= 0`.
- `leadDays >= 0`.
- `dueAt` musi byt validni datum/cas.
- `insuranceType=vehicle` vyzaduje `subjectVehicleId`.
- `insuranceType=property|household` vyzaduje `subjectPropertyId`.

## 9) Error format

```json
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Invalid request payload",
    "details": [
      {
        "field": "currency",
        "message": "must be 3-letter ISO code"
      }
    ]
  }
}
```
