# My-finance

My-finance is a self-hosted personal finance web app (FastAPI + PostgreSQL + Docker).
It focuses on:
- user accounts and authentication,
- account/transaction management,
- settings with localization (CZ/EN), timezone, appearance,
- backup/restore,
- reminder-ready architecture for future modules (garage, property, taxes, OCR, AI assistant).

## Current stack
- Backend: FastAPI
- DB: PostgreSQL (or in-memory for development)
- UI: server-hosted HTML/JS pages
- Runtime: Docker Compose

## Quick start (Docker)
1. Install Docker Desktop.
2. From repository root run:
```powershell
docker compose up --build
```
3. Open:
- `http://localhost:8000/`
- API docs: `http://localhost:8000/docs`

`/` automatically redirects:
- to `get-started` when not logged in,
- to `dashboard` when logged in.

## Non-Docker local start
Use:
- `install.ps1` for local setup,
- then run backend from project root.

## Main UI routes
- `GET /ui/get-started`
- `GET /ui/dashboard`
- `GET /ui/settings`

## Backups
- Download backup: `GET /api/v1/admin/backup/download`
- Restore backup file: `POST /api/v1/admin/backup/import-file`
- Run backup now: `POST /api/v1/admin/backup/run-now`

## Project planning
- All unfinished and planned work is tracked in `TODO.md` (local-only, ignored by git).
- Keep `README.md` and `TODO.md` updated together whenever scope changes.
