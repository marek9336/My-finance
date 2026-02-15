# My-finance

My-finance is a self-hosted web app for personal finance management.
It helps you track account balances, transactions, transfers, recurring payments, and basic investment/rates overview in one place.

## What is currently included
- User registration, login, logout and profile basics
- Dashboard with account summaries, statistics and charts
- Transactions & Accounts page for account management, transfers and transaction history
- Savings & Investments page scaffold
- Rates page with watchlist, manual snapshots and automatic refresh
- Services page scaffold
- Settings for language, timezone, appearance, layout width, and translation editing
- Backup/restore endpoints and startup onboarding page

## Run with Docker
1. Install Docker Desktop.
2. In repository root run:
```powershell
docker compose up --build
```
3. Open `http://localhost:8000/`.

Notes:
- If not signed in, app opens `Get Started`.
- If signed in, app opens `Dashboard`.

## Run locally (without Docker)
1. Use `install.ps1` from repository root.
2. Start the backend according to project scripts.
3. Open `http://localhost:8000/`.

## Main pages
- `/ui/get-started`
- `/ui/dashboard`
- `/ui/transactions`
- `/ui/savings-investments`
- `/ui/rates`
- `/ui/services`
- `/ui/settings`

## Disclaimer
This app is experimental software. Always verify financial data and recommendations before acting.
