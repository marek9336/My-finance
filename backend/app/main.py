import json
import asyncio
import secrets
from pathlib import Path
from datetime import date, datetime, timedelta, timezone
from typing import Any
from uuid import UUID

from fastapi import Cookie, FastAPI, File, Header, HTTPException, Request, Response, UploadFile, status
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.responses import FileResponse, RedirectResponse
from fastapi.responses import JSONResponse

from .schemas import (
    AppSettings,
    AppSettingsUpdate,
    ApiErrorDetail,
    ApiErrorPayload,
    ApiErrorResponse,
    AccountCreate,
    AccountUpdate,
    AccountResponse,
    AuthResponse,
    BackupImportResponse,
    BackupRunResponse,
    GoogleCalendarConnectRequest,
    GoogleCalendarConnectResponse,
    GoogleCalendarSyncRunRequest,
    GoogleCalendarSyncRunResponse,
    HealthResponse,
    InsuranceCreate,
    InsurancePremiumCreate,
    InsurancePremiumResponse,
    InsuranceResponse,
    LocaleBundleResponse,
    LocaleListResponse,
    LocalePublishResponse,
    LoginRequest,
    UserProfileResponse,
    UserProfileUpdate,
    UserPasswordChange,
    NotificationRuleCreate,
    NotificationRuleResponse,
    PropertyCostCreate,
    PropertyCostResponse,
    PropertyCreate,
    PropertyResponse,
    RegisterRequest,
    TransactionCreate,
    TransactionUpdate,
    TransactionResponse,
    VehicleCreate,
    VehicleResponse,
    VehicleServiceCreate,
    VehicleServiceResponse,
    VehicleServiceRuleCreate,
    VehicleServiceRuleResponse,
)
from .services.sync import SyncStats, compute_event_hash, compute_event_uid, make_provider_event_id
from .persistence import get_persistence
from .store import store

app = FastAPI(
    title="My-finance API",
    version="0.1.0",
    description="MVP API skeleton for vehicles, properties, insurance and notifications.",
)

_project_root_candidate = Path(__file__).resolve().parents[2]
if (_project_root_candidate / "backend" / "ui").exists():
    ROOT_DIR = _project_root_candidate
    UI_DIR = ROOT_DIR / "backend" / "ui"
    CUSTOM_LOCALES_DIR = ROOT_DIR / "i18n" / "custom"
    BACKUP_DIR = ROOT_DIR / "backups"
else:
    # Docker image layout: /app/app, /app/ui, /app/i18n, /app/backups
    ROOT_DIR = Path(__file__).resolve().parents[1]
    UI_DIR = ROOT_DIR / "ui"
    CUSTOM_LOCALES_DIR = ROOT_DIR / "i18n" / "custom"
    BACKUP_DIR = ROOT_DIR / "backups"
CUSTOM_LOCALES_DIR.mkdir(parents=True, exist_ok=True)
BACKUP_DIR.mkdir(parents=True, exist_ok=True)
persistence = get_persistence()
backup_scheduler_task: asyncio.Task | None = None
active_sessions: dict[str, dict[str, Any]] = {}
SESSION_COOKIE_NAME = "mf_session"


def _extract_token_from_request(request: Request) -> str | None:
    auth = request.headers.get("Authorization")
    if auth:
        parts = auth.split(" ", 1)
        if len(parts) == 2 and parts[0].lower() == "bearer":
            return parts[1].strip()
    return request.cookies.get(SESSION_COOKIE_NAME)


def _session_timeout_minutes(user_id: UUID) -> int | None:
    try:
        return persistence.get_app_settings(user_id).sessionTimeoutMinutes
    except Exception:
        return None


def _get_session_user_id(token: str | None) -> UUID | None:
    if not token:
        return None
    session = active_sessions.get(token)
    if session is None:
        return None
    now = datetime.now(timezone.utc)
    last_seen = session.get("last_seen", now)
    current_user_id = session.get("user_id")
    if current_user_id is None:
        del active_sessions[token]
        return None
    timeout_minutes = _session_timeout_minutes(current_user_id)
    if timeout_minutes and (now - last_seen) > timedelta(minutes=timeout_minutes):
        del active_sessions[token]
        return None
    session["last_seen"] = now
    active_sessions[token] = session
    return current_user_id


def _create_session(user_id: UUID) -> str:
    token = secrets.token_urlsafe(32)
    active_sessions[token] = {"user_id": user_id, "last_seen": datetime.now(timezone.utc)}
    return token


def build_error_response(details: list[ApiErrorDetail], message: str = "Invalid request payload") -> JSONResponse:
    payload = ApiErrorResponse(
        error=ApiErrorPayload(code="VALIDATION_ERROR", message=message, details=details)
    )
    return JSONResponse(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, content=payload.model_dump())


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    details: list[ApiErrorDetail] = []
    for err in exc.errors():
        loc = ".".join(str(item) for item in err.get("loc", []) if item != "body")
        details.append(ApiErrorDetail(field=loc or "body", message=err.get("msg", "validation error")))
    return build_error_response(details)


@app.exception_handler(ValueError)
async def value_error_exception_handler(request: Request, exc: ValueError) -> JSONResponse:
    return build_error_response([ApiErrorDetail(field="body", message=str(exc))])


@app.middleware("http")
async def ui_auth_middleware(request: Request, call_next):
    path = request.url.path
    public_api = {
        "/api/v1/health",
        "/api/v1/auth/register",
        "/api/v1/auth/login",
        "/api/v1/bootstrap/restore",
        "/api/v1/public/i18n/locales",
    }
    if path.startswith("/api/v1/public/i18n/"):
        return await call_next(request)
    if path.startswith("/api/v1") and path not in public_api:
        token = _extract_token_from_request(request)
        if not _get_session_user_id(token):
            return JSONResponse(status_code=401, content={"detail": "authentication required"})
    if path.startswith("/ui") and path != "/ui/get-started":
        session_token = _extract_token_from_request(request)
        if not _get_session_user_id(session_token):
            return RedirectResponse(url="/ui/get-started", status_code=302)
    return await call_next(request)


@app.get("/")
async def root(request: Request) -> RedirectResponse:
    token = _extract_token_from_request(request)
    if _get_session_user_id(token):
        return RedirectResponse(url="/ui/dashboard", status_code=302)
    return RedirectResponse(url="/ui/get-started", status_code=302)


@app.get("/api/v1/health", response_model=HealthResponse)
async def health() -> HealthResponse:
    return HealthResponse(status="ok")


@app.get("/api/v1/settings/app", response_model=AppSettings)
async def get_app_settings(
    authorization: str | None = Header(default=None),
    session_token: str | None = Cookie(default=None, alias=SESSION_COOKIE_NAME),
) -> AppSettings:
    user_id = _require_user(authorization, session_token)
    return persistence.get_app_settings(user_id)


@app.put("/api/v1/settings/app", response_model=AppSettings)
async def update_app_settings(
    payload: AppSettingsUpdate,
    authorization: str | None = Header(default=None),
    session_token: str | None = Cookie(default=None, alias=SESSION_COOKIE_NAME),
) -> AppSettings:
    user_id = _require_user(authorization, session_token)
    return persistence.update_app_settings(user_id, payload)


@app.get("/api/v1/i18n/locales", response_model=LocaleListResponse)
async def get_locales(
    authorization: str | None = Header(default=None),
    session_token: str | None = Cookie(default=None, alias=SESSION_COOKIE_NAME),
) -> LocaleListResponse:
    user_id = _require_user(authorization, session_token)
    locales = persistence.list_locales(user_id)
    return LocaleListResponse(locales=locales)


@app.get("/api/v1/public/i18n/locales", response_model=LocaleListResponse)
async def get_public_locales() -> LocaleListResponse:
    return LocaleListResponse(locales=sorted(store.base_locales.keys()))


@app.get("/api/v1/i18n/{locale}", response_model=LocaleBundleResponse)
async def get_locale_bundle(
    locale: str,
    authorization: str | None = Header(default=None),
    session_token: str | None = Cookie(default=None, alias=SESSION_COOKIE_NAME),
) -> LocaleBundleResponse:
    user_id = _require_user(authorization, session_token)
    messages = persistence.get_locale_bundle(user_id, locale)
    if not messages:
        raise HTTPException(status_code=404, detail=f"locale not found: {locale}")
    return LocaleBundleResponse(locale=locale, messages=messages)


@app.get("/api/v1/public/i18n/{locale}", response_model=LocaleBundleResponse)
async def get_public_locale_bundle(locale: str) -> LocaleBundleResponse:
    messages = store.base_locales.get(locale, {})
    if not messages:
        raise HTTPException(status_code=404, detail=f"locale not found: {locale}")
    return LocaleBundleResponse(locale=locale, messages=messages)


@app.put("/api/v1/i18n/{locale}/custom", response_model=LocaleBundleResponse)
async def upsert_custom_locale(
    locale: str,
    payload: dict[str, str],
    authorization: str | None = Header(default=None),
    session_token: str | None = Cookie(default=None, alias=SESSION_COOKIE_NAME),
) -> LocaleBundleResponse:
    user_id = _require_user(authorization, session_token)
    merged = persistence.upsert_custom_locale(user_id, locale, payload)
    return LocaleBundleResponse(locale=locale, messages=merged)


@app.post("/api/v1/i18n/{locale}/custom/publish", response_model=LocalePublishResponse)
async def publish_custom_locale(
    locale: str,
    authorization: str | None = Header(default=None),
    session_token: str | None = Cookie(default=None, alias=SESSION_COOKIE_NAME),
) -> LocalePublishResponse:
    user_id = _require_user(authorization, session_token)
    custom = persistence.get_custom_locale(user_id, locale)
    if not custom:
        raise HTTPException(status_code=404, detail=f"custom locale not found: {locale}")
    file_path = CUSTOM_LOCALES_DIR / f"{locale}.json"
    file_path.write_text(json.dumps(custom, ensure_ascii=False, indent=2), encoding="utf-8")
    return LocalePublishResponse(locale=locale, path=str(file_path.relative_to(ROOT_DIR)), keys=len(custom))


@app.get("/ui/settings")
async def ui_settings() -> FileResponse:
    return FileResponse(UI_DIR / "settings.html")


@app.get("/ui/translations")
async def ui_translations() -> RedirectResponse:
    return RedirectResponse(url="/ui/settings", status_code=302)


@app.get("/ui/backup")
async def ui_backup() -> RedirectResponse:
    return RedirectResponse(url="/ui/settings", status_code=302)


@app.get("/ui/get-started")
async def ui_get_started() -> FileResponse:
    return FileResponse(UI_DIR / "get-started.html")


@app.get("/ui/dashboard")
async def ui_dashboard() -> FileResponse:
    return FileResponse(UI_DIR / "dashboard.html")


def _token_from_header(authorization: str | None) -> str:
    if not authorization:
        raise HTTPException(status_code=401, detail="missing Authorization header")
    parts = authorization.split(" ", 1)
    if len(parts) != 2 or parts[0].lower() != "bearer":
        raise HTTPException(status_code=401, detail="invalid Authorization header")
    return parts[1].strip()


def _require_user(authorization: str | None = None, session_token: str | None = None) -> UUID:
    token = session_token
    if authorization:
        token = _token_from_header(authorization)
    if not token:
        raise HTTPException(status_code=401, detail="missing session token")
    user_id = _get_session_user_id(token)
    if user_id is None:
        raise HTTPException(status_code=401, detail="invalid or expired token")
    return user_id


@app.post("/api/v1/auth/register", response_model=AuthResponse, status_code=201)
async def auth_register(payload: RegisterRequest, response: Response) -> AuthResponse:
    user = persistence.register_user(payload.email, payload.password, payload.fullName)
    token = _create_session(user["id"])
    response.set_cookie(SESSION_COOKIE_NAME, token, httponly=True, samesite="lax", secure=False)
    return AuthResponse(token=token, userId=user["id"], email=user["email"], fullName=user.get("full_name"))


@app.post("/api/v1/auth/login", response_model=AuthResponse)
async def auth_login(payload: LoginRequest, response: Response) -> AuthResponse:
    user = persistence.authenticate_user(payload.email, payload.password)
    if user is None:
        raise HTTPException(status_code=401, detail="invalid email or password")
    token = _create_session(user["id"])
    if payload.rememberMe:
        response.set_cookie(SESSION_COOKIE_NAME, token, httponly=True, samesite="lax", secure=False, max_age=60 * 60 * 24 * 30)
    else:
        response.set_cookie(SESSION_COOKIE_NAME, token, httponly=True, samesite="lax", secure=False)
    return AuthResponse(token=token, userId=user["id"], email=user["email"], fullName=user.get("full_name"))


@app.get("/api/v1/auth/me", response_model=AuthResponse)
async def auth_me(authorization: str | None = Header(default=None), session_token: str | None = Cookie(default=None, alias=SESSION_COOKIE_NAME)) -> AuthResponse:
    user_id = _require_user(authorization, session_token)
    user = persistence.get_user_by_id(user_id)
    if user is None:
        raise HTTPException(status_code=401, detail="user not found")
    token = _token_from_header(authorization) if authorization else session_token
    return AuthResponse(token=token, userId=user["id"], email=user["email"], fullName=user.get("full_name"))


@app.get("/api/v1/users/me", response_model=UserProfileResponse)
async def get_user_profile(
    authorization: str | None = Header(default=None),
    session_token: str | None = Cookie(default=None, alias=SESSION_COOKIE_NAME),
) -> UserProfileResponse:
    user_id = _require_user(authorization, session_token)
    user = persistence.get_user_by_id(user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="user not found")
    return UserProfileResponse(userId=user["id"], email=user["email"], fullName=user.get("full_name"))


@app.put("/api/v1/users/me", response_model=UserProfileResponse)
async def update_user_profile(
    payload: UserProfileUpdate,
    authorization: str | None = Header(default=None),
    session_token: str | None = Cookie(default=None, alias=SESSION_COOKIE_NAME),
) -> UserProfileResponse:
    user_id = _require_user(authorization, session_token)
    user = persistence.update_user_profile(user_id, payload.email, payload.fullName)
    return UserProfileResponse(userId=user["id"], email=user["email"], fullName=user.get("full_name"))


@app.post("/api/v1/users/me/change-password")
async def change_user_password(
    payload: UserPasswordChange,
    authorization: str | None = Header(default=None),
    session_token: str | None = Cookie(default=None, alias=SESSION_COOKIE_NAME),
) -> dict[str, bool]:
    user_id = _require_user(authorization, session_token)
    persistence.change_user_password(user_id, payload.currentPassword, payload.newPassword)
    return {"updated": True}


@app.post("/api/v1/auth/logout")
async def auth_logout(
    response: Response,
    authorization: str | None = Header(default=None),
    session_token: str | None = Cookie(default=None, alias=SESSION_COOKIE_NAME),
) -> dict[str, bool]:
    token = _token_from_header(authorization) if authorization else session_token
    if token and token in active_sessions:
        del active_sessions[token]
    response.delete_cookie(SESSION_COOKIE_NAME)
    return {"ok": True}


@app.delete("/api/v1/auth/me")
async def delete_my_account(
    response: Response,
    authorization: str | None = Header(default=None),
    session_token: str | None = Cookie(default=None, alias=SESSION_COOKIE_NAME),
) -> dict[str, bool]:
    user_id = _require_user(authorization, session_token)
    persistence.delete_user(user_id)
    tokens_to_remove = [token for token, data in active_sessions.items() if data.get("user_id") == user_id]
    for token in tokens_to_remove:
        del active_sessions[token]
    response.delete_cookie(SESSION_COOKIE_NAME)
    return {"deleted": True}


@app.post("/api/v1/accounts", response_model=AccountResponse, status_code=201)
async def create_account(
    payload: AccountCreate,
    authorization: str | None = Header(default=None),
    session_token: str | None = Cookie(default=None, alias=SESSION_COOKIE_NAME),
) -> AccountResponse:
    user_id = _require_user(authorization, session_token)
    row = persistence.create_account(user_id, payload)
    return AccountResponse(
        id=row["id"],
        name=row["name"],
        accountType=row["account_type"],
        currency=row["currency"],
        currentBalance=row["current_balance"],
        createdAt=row["created_at"],
    )


@app.get("/api/v1/accounts", response_model=list[AccountResponse])
async def list_accounts(
    authorization: str | None = Header(default=None),
    session_token: str | None = Cookie(default=None, alias=SESSION_COOKIE_NAME),
) -> list[AccountResponse]:
    user_id = _require_user(authorization, session_token)
    rows = persistence.list_accounts(user_id)
    return [
        AccountResponse(
            id=row["id"],
            name=row["name"],
            accountType=row["account_type"],
            currency=row["currency"],
            currentBalance=row["current_balance"],
            createdAt=row["created_at"],
        )
        for row in rows
    ]


@app.put("/api/v1/accounts/{account_id}", response_model=AccountResponse)
async def update_account(
    account_id: UUID,
    payload: AccountUpdate,
    authorization: str | None = Header(default=None),
    session_token: str | None = Cookie(default=None, alias=SESSION_COOKIE_NAME),
) -> AccountResponse:
    user_id = _require_user(authorization, session_token)
    row = persistence.update_account(user_id, account_id, payload)
    return AccountResponse(
        id=row["id"],
        name=row["name"],
        accountType=row["account_type"],
        currency=row["currency"],
        currentBalance=row["current_balance"],
        createdAt=row["created_at"],
    )


@app.post("/api/v1/transactions", response_model=TransactionResponse, status_code=201)
async def create_transaction(
    payload: TransactionCreate,
    authorization: str | None = Header(default=None),
    session_token: str | None = Cookie(default=None, alias=SESSION_COOKIE_NAME),
) -> TransactionResponse:
    user_id = _require_user(authorization, session_token)
    row = persistence.create_transaction(user_id, payload)
    return TransactionResponse(
        id=row["id"],
        accountId=row["account_id"],
        direction=row["direction"],
        amount=row["amount"],
        currency=row["currency"],
        occurredAt=row["transaction_at"],
        category=row.get("category"),
        note=row.get("note"),
    )


@app.get("/api/v1/transactions", response_model=list[TransactionResponse])
async def list_transactions(
    authorization: str | None = Header(default=None),
    session_token: str | None = Cookie(default=None, alias=SESSION_COOKIE_NAME),
) -> list[TransactionResponse]:
    user_id = _require_user(authorization, session_token)
    rows = persistence.list_transactions(user_id)
    return [
        TransactionResponse(
            id=row["id"],
            accountId=row["account_id"],
            direction=row["direction"],
            amount=row["amount"],
            currency=row["currency"],
            occurredAt=row["transaction_at"],
            category=row.get("category"),
            note=row.get("note"),
        )
        for row in rows
    ]


@app.put("/api/v1/transactions/{transaction_id}", response_model=TransactionResponse)
async def update_transaction(
    transaction_id: UUID,
    payload: TransactionUpdate,
    authorization: str | None = Header(default=None),
    session_token: str | None = Cookie(default=None, alias=SESSION_COOKIE_NAME),
) -> TransactionResponse:
    user_id = _require_user(authorization, session_token)
    row = persistence.update_transaction(user_id, transaction_id, payload)
    return TransactionResponse(
        id=row["id"],
        accountId=row["account_id"],
        direction=row["direction"],
        amount=row["amount"],
        currency=row["currency"],
        occurredAt=row["transaction_at"],
        category=row.get("category"),
        note=row.get("note"),
    )


@app.get("/api/v1/admin/backup/export")
async def export_backup(
    authorization: str | None = Header(default=None),
    session_token: str | None = Cookie(default=None, alias=SESSION_COOKIE_NAME),
) -> dict[str, Any]:
    user_id = _require_user(authorization, session_token)
    return persistence.export_backup(user_id)


@app.post("/api/v1/bootstrap/restore", response_model=BackupImportResponse)
async def bootstrap_restore(file: UploadFile = File(...)) -> BackupImportResponse:
    if not file.filename.lower().endswith(".json"):
        raise HTTPException(status_code=400, detail="backup file must be JSON")
    content = await file.read()
    try:
        payload = json.loads(content.decode("utf-8"))
    except json.JSONDecodeError as exc:
        raise HTTPException(status_code=400, detail=f"invalid JSON: {exc}") from exc
    user_id: UUID | None = None
    default_user_id = getattr(persistence, "default_user_id", None)
    if default_user_id:
        user_id = UUID(str(default_user_id))
    elif store.users:
        user_id = next(iter(store.users.keys()))
    if user_id is None:
        user = persistence.register_user("bootstrap@local", "ChangeMe123!", "Bootstrap User")
        user_id = user["id"]
    counts = persistence.import_backup(user_id, payload)
    return BackupImportResponse(replaced=True, counts=counts)


@app.get("/api/v1/admin/backup/download")
async def download_backup(
    authorization: str | None = Header(default=None),
    session_token: str | None = Cookie(default=None, alias=SESSION_COOKIE_NAME),
) -> Response:
    user_id = _require_user(authorization, session_token)
    file_path, ts = _create_backup_file(user_id)
    persistence.mark_auto_backup_run(user_id, ts)
    backup = json.loads(file_path.read_text(encoding="utf-8"))
    content = json.dumps(jsonable_encoder(backup), ensure_ascii=False, indent=2).encode("utf-8")
    return Response(
        content=content,
        media_type="application/json",
        headers={"Content-Disposition": "attachment; filename=my-finance-backup.json"},
    )


def _backup_file_path(ts: datetime | None = None) -> Path:
    current = ts or datetime.now(timezone.utc)
    stamp = current.strftime("%Y%m%d_%H%M%S")
    return BACKUP_DIR / f"my-finance-backup-{stamp}.json"


def _create_backup_file(user_id: UUID) -> tuple[Path, datetime]:
    ts = datetime.now(timezone.utc)
    file_path = _backup_file_path(ts)
    payload = persistence.export_backup(user_id)
    file_path.write_text(json.dumps(jsonable_encoder(payload), ensure_ascii=False, indent=2), encoding="utf-8")
    return file_path, ts


def _cleanup_old_backups(retention_days: int) -> None:
    cutoff = datetime.now(timezone.utc) - timedelta(days=retention_days)
    for file_path in BACKUP_DIR.glob("my-finance-backup-*.json"):
        mtime = datetime.fromtimestamp(file_path.stat().st_mtime, tz=timezone.utc)
        if mtime < cutoff:
            file_path.unlink(missing_ok=True)


@app.post("/api/v1/admin/backup/run-now", response_model=BackupRunResponse)
async def run_backup_now(
    authorization: str | None = Header(default=None),
    session_token: str | None = Cookie(default=None, alias=SESSION_COOKIE_NAME),
) -> BackupRunResponse:
    user_id = _require_user(authorization, session_token)
    settings = persistence.get_app_settings(user_id)
    file_path, ts = _create_backup_file(user_id)
    persistence.mark_auto_backup_run(user_id, ts)
    _cleanup_old_backups(settings.autoBackupRetentionDays)
    return BackupRunResponse(created=True, file=str(file_path.relative_to(ROOT_DIR)), timestamp=ts)


@app.post("/api/v1/admin/backup/import", response_model=BackupImportResponse)
async def import_backup(
    payload: dict[str, Any],
    authorization: str | None = Header(default=None),
    session_token: str | None = Cookie(default=None, alias=SESSION_COOKIE_NAME),
) -> BackupImportResponse:
    user_id = _require_user(authorization, session_token)
    counts = persistence.import_backup(user_id, payload)
    return BackupImportResponse(replaced=True, counts=counts)


@app.post("/api/v1/admin/backup/import-file", response_model=BackupImportResponse)
async def import_backup_file(
    file: UploadFile = File(...),
    authorization: str | None = Header(default=None),
    session_token: str | None = Cookie(default=None, alias=SESSION_COOKIE_NAME),
) -> BackupImportResponse:
    user_id = _require_user(authorization, session_token)
    if not file.filename.lower().endswith(".json"):
        raise HTTPException(status_code=400, detail="backup file must be JSON")
    content = await file.read()
    try:
        payload = json.loads(content.decode("utf-8"))
    except json.JSONDecodeError as exc:
        raise HTTPException(status_code=400, detail=f"invalid JSON: {exc}") from exc
    counts = persistence.import_backup(user_id, payload)
    return BackupImportResponse(replaced=True, counts=counts)


async def _auto_backup_loop() -> None:
    while True:
        await asyncio.sleep(60)
        try:
            default_user_id = getattr(persistence, "default_user_id", None)
            if default_user_id:
                scheduler_user_id = UUID(str(default_user_id))
            elif store.users:
                scheduler_user_id = next(iter(store.users.keys()))
            else:
                continue
            cfg = persistence.get_app_settings(scheduler_user_id)
            if not cfg.autoBackupEnabled:
                continue
            now = datetime.now(timezone.utc)
            last = cfg.autoBackupLastRunAt
            if last is None or (now - last).total_seconds() >= cfg.autoBackupIntervalMinutes * 60:
                _, ts = _create_backup_file(scheduler_user_id)
                persistence.mark_auto_backup_run(scheduler_user_id, ts)
                _cleanup_old_backups(cfg.autoBackupRetentionDays)
        except Exception:
            # Keep scheduler alive even if one run fails.
            continue


@app.on_event("startup")
async def on_startup() -> None:
    global backup_scheduler_task
    if backup_scheduler_task is None:
        backup_scheduler_task = asyncio.create_task(_auto_backup_loop())


@app.on_event("shutdown")
async def on_shutdown() -> None:
    global backup_scheduler_task
    if backup_scheduler_task is not None:
        backup_scheduler_task.cancel()
        backup_scheduler_task = None


@app.post("/api/v1/vehicles", response_model=VehicleResponse, status_code=201)
async def create_vehicle(payload: VehicleCreate) -> VehicleResponse:
    row = persistence.create_vehicle(payload)
    return VehicleResponse(
        id=row["id"],
        type=row["type"],
        label=row["label"],
        currentOdometerKm=row["current_odometer_km"],
        createdAt=row["created_at"],
    )


@app.post("/api/v1/vehicles/{vehicle_id}/services", response_model=VehicleServiceResponse, status_code=201)
async def create_vehicle_service(vehicle_id: UUID, payload: VehicleServiceCreate) -> VehicleServiceResponse:
    row = persistence.create_vehicle_service(vehicle_id, payload)
    return VehicleServiceResponse(
        id=row["id"],
        vehicleId=row["vehicle_id"],
        serviceType=row["service_type"],
        serviceAt=row["service_at"],
        odometerKm=row["odometer_km"],
    )


@app.post("/api/v1/vehicles/{vehicle_id}/service-rules", response_model=VehicleServiceRuleResponse, status_code=201)
async def create_vehicle_service_rule(vehicle_id: UUID, payload: VehicleServiceRuleCreate) -> VehicleServiceRuleResponse:
    next_due_date = None
    if payload.intervalUnit == "days":
        next_due_date = date.fromordinal(date.today().toordinal() + payload.intervalValue)
    elif payload.intervalUnit == "months":
        next_due_date = date.fromordinal(date.today().toordinal() + payload.intervalValue * 30)
    row = persistence.create_vehicle_service_rule(vehicle_id, payload, next_due_date)
    return VehicleServiceRuleResponse(
        id=row["id"],
        vehicleId=row["vehicle_id"],
        serviceType=row["service_type"],
        nextDueDate=row["next_due_date"],
        isActive=row["is_active"],
    )


@app.post("/api/v1/properties", response_model=PropertyResponse, status_code=201)
async def create_property(payload: PropertyCreate) -> PropertyResponse:
    row = persistence.create_property(payload)
    return PropertyResponse(id=row["id"], type=row["type"], name=row["name"], estimatedValue=row["estimated_value"])


@app.post("/api/v1/properties/{property_id}/costs", response_model=PropertyCostResponse, status_code=201)
async def create_property_cost(property_id: UUID, payload: PropertyCostCreate) -> PropertyCostResponse:
    row = persistence.create_property_cost(property_id, payload)
    return PropertyCostResponse(id=row["id"], propertyId=row["property_id"], costType=row["cost_type"], amount=row["amount"], currency=row["currency"])


@app.post("/api/v1/insurances", response_model=InsuranceResponse, status_code=201)
async def create_insurance(payload: InsuranceCreate) -> InsuranceResponse:
    row = persistence.create_insurance(payload)
    return InsuranceResponse(id=row["id"], insuranceType=row["insurance_type"], provider=row["provider"], validTo=row["valid_to"], isActive=row["is_active"])


@app.post("/api/v1/insurances/{insurance_id}/premiums", response_model=InsurancePremiumResponse, status_code=201)
async def create_insurance_premium(insurance_id: UUID, payload: InsurancePremiumCreate) -> InsurancePremiumResponse:
    row = persistence.create_insurance_premium(insurance_id, payload)
    return InsurancePremiumResponse(id=row["id"], insuranceId=row["insurance_id"], amount=row["amount"], currency=row["currency"])


@app.post("/api/v1/integrations/google-calendar/connect", response_model=GoogleCalendarConnectResponse)
async def connect_google_calendar(payload: GoogleCalendarConnectRequest) -> GoogleCalendarConnectResponse:
    row = persistence.create_calendar_integration(payload)
    return GoogleCalendarConnectResponse(
        integrationId=row["id"],
        provider=row["provider"],
        externalCalendarId=row["external_calendar_id"],
        syncEnabled=row["sync_enabled"],
    )


@app.post("/api/v1/notification-rules", response_model=NotificationRuleResponse, status_code=201)
async def create_notification_rule(payload: NotificationRuleCreate) -> NotificationRuleResponse:
    row = persistence.create_notification_rule(payload)
    return NotificationRuleResponse(id=row["id"], channel=row["channel"], dueAt=row["due_at"], isActive=row["is_active"])


@app.post("/api/v1/sync/google-calendar/run", response_model=GoogleCalendarSyncRunResponse)
async def run_google_calendar_sync(payload: GoogleCalendarSyncRunRequest) -> GoogleCalendarSyncRunResponse:
    stats = SyncStats()
    active_rules = persistence.list_google_notification_rules()
    any_integration = persistence.any_calendar_integration_id()

    if not any_integration:
        return GoogleCalendarSyncRunResponse(created=0, updated=0, unchanged=0, canceled=0, failed=0)

    for rule in active_rules:
        event_uid = compute_event_uid(
            source=str(rule["source"]),
            source_entity_id=rule["source_entity_id"],
            due_at_iso=rule["due_at"].isoformat(),
        )
        event_hash = compute_event_hash(
            title=rule["title_template"],
            message=rule.get("message_template"),
            due_at_iso=rule["due_at"].isoformat(),
            timezone=rule["timezone"],
        )
        existing = persistence.get_calendar_event(any_integration, event_uid)
        if existing is None:
            if not payload.dryRun:
                persistence.create_calendar_event(any_integration, rule["id"], event_uid, event_hash, make_provider_event_id())
            stats.created += 1
            continue
        if existing["event_hash"] == event_hash:
            stats.unchanged += 1
            continue
        if not payload.dryRun:
            persistence.update_calendar_event_hash(existing["id"], event_hash)
        stats.updated += 1

    return GoogleCalendarSyncRunResponse(
        created=stats.created,
        updated=stats.updated,
        unchanged=stats.unchanged,
        canceled=stats.canceled,
        failed=stats.failed,
    )


@app.get("/api/v1/debug/state")
async def debug_state() -> dict[str, Any]:
    return persistence.debug_counts()
