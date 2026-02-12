# Backend Skeleton (FastAPI)

Minimal API skeleton for:
- vehicles and maintenance,
- properties and utility costs,
- insurance,
- notifications and Google Calendar sync,
- app settings for GUI configuration.

## Run locally

```bash
cd backend
python -m venv .venv
. .venv/Scripts/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

Swagger:
- `http://localhost:8000/docs`
- GUI settings:
  - `http://localhost:8000/ui/settings`
  - `http://localhost:8000/ui/translations`
  - `http://localhost:8000/ui/backup`
  - `http://localhost:8000/ui/get-started`
  - `http://localhost:8000/ui/dashboard`

## Tests

```bash
cd backend
pytest -q
```

## Key GUI settings endpoints

- `GET /api/v1/settings/app`
- `PUT /api/v1/settings/app`
- `POST /api/v1/auth/register`
- `POST /api/v1/auth/login`
- `GET /api/v1/auth/me`
- `POST /api/v1/accounts`
- `GET /api/v1/accounts`
- `POST /api/v1/transactions`
- `GET /api/v1/transactions`
- `GET /api/v1/i18n/locales`
- `GET /api/v1/i18n/{locale}`
- `PUT /api/v1/i18n/{locale}/custom`
- `POST /api/v1/i18n/{locale}/custom/publish` (writes `i18n/custom/<locale>.json` for Git commit)
- `GET /api/v1/admin/backup/export`
- `GET /api/v1/admin/backup/download`
- `POST /api/v1/admin/backup/import`
- `POST /api/v1/admin/backup/import-file`
- `POST /api/v1/admin/backup/run-now`
- `POST /api/v1/bootstrap/restore` (initial restore before login)

Automatic backups:
- Configure in GUI Settings (`/ui/settings`)
- Fields:
  - `autoBackupEnabled`
  - `autoBackupIntervalMinutes`
  - `autoBackupRetentionDays`
- Scheduler runs inside API process and writes files to `backups/`

Authentication flow:
- Only `Get Started` is public in UI.
- Other UI pages require login session.
- Most `/api/v1/*` endpoints require authentication except health/register/login/bootstrap restore.

## Note

Current implementation uses in-memory storage (`app/store.py`) as a development skeleton.
Next step is PostgreSQL integration using migrations in `db/migrations/`.

## PostgreSQL mode

1. Set env vars:
```bash
set STORAGE_BACKEND=postgres
set DATABASE_URL=postgresql+psycopg://postgres:postgres@localhost:5432/my_finance
set APP_DEFAULT_USER_ID=00000000-0000-0000-0000-000000000001
```
2. Run migrations:
```bash
cd backend
python scripts/run_migrations.py
```
3. Start API:
```bash
uvicorn app.main:app --reload --port 8000
```
