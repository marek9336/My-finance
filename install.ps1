param(
  [switch]$RunApi,
  [switch]$UsePostgres,
  [string]$DatabaseUrl = "postgresql+psycopg://postgres:postgres@localhost:5432/my_finance"
)

$ErrorActionPreference = "Stop"

Write-Host "Setting up My-finance backend..."

if (-not (Test-Path ".\backend")) {
  throw "Missing backend directory."
}

if (-not (Get-Command python -ErrorAction SilentlyContinue)) {
  throw "Python is not installed. Install Python 3.11+ and run this script again."
}

Push-Location backend

if (-not (Test-Path ".venv")) {
  python -m venv .venv
}

$venvPython = ".\.venv\Scripts\python.exe"
if (-not (Test-Path $venvPython)) {
  throw "Virtual environment was not created correctly."
}

& $venvPython -m pip install --upgrade pip
& $venvPython -m pip install -r requirements.txt

Write-Host "Dependencies installed."

if ($UsePostgres) {
  Write-Host "Running SQL migrations..."
  $env:DATABASE_URL = $DatabaseUrl
  & $venvPython .\scripts\run_migrations.py
  Write-Host "Migrations finished."
  Write-Host "Use these env vars before starting API:"
  Write-Host '  $env:STORAGE_BACKEND="postgres"'
  Write-Host "  `$env:DATABASE_URL=`"$DatabaseUrl`""
}

Write-Host "Run API with:"
Write-Host "  .\backend\.venv\Scripts\python.exe -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload"

if ($RunApi) {
  & $venvPython -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
}

Pop-Location
