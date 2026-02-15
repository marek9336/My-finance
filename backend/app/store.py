from datetime import datetime
import json
from pathlib import Path
from uuid import UUID, uuid4


class InMemoryStore:
    def __init__(self) -> None:
        self.users: dict[UUID, dict] = {}
        self.user_credentials: dict[UUID, str] = {}
        self.accounts: dict[UUID, dict] = {}
        self.transactions: dict[UUID, dict] = {}
        self.vehicles: dict[UUID, dict] = {}
        self.vehicle_services: dict[UUID, dict] = {}
        self.vehicle_service_rules: dict[UUID, dict] = {}
        self.properties: dict[UUID, dict] = {}
        self.property_costs: dict[UUID, dict] = {}
        self.insurances: dict[UUID, dict] = {}
        self.insurance_premiums: dict[UUID, dict] = {}
        self.calendar_integrations: dict[UUID, dict] = {}
        self.notification_rules: dict[UUID, dict] = {}
        self.notification_deliveries: dict[UUID, dict] = {}
        self.calendar_events: dict[str, dict] = {}
        self.rate_watchlists: dict[UUID, list[str]] = {}
        self.rate_snapshots: dict[UUID, dict[str, dict]] = {}
        self.settings: dict[str, object] = {
            "defaultLocale": "en",
            "defaultTimezone": "Europe/Prague",
            "defaultDisplayCurrency": "CZK",
            "secondaryDisplayCurrency": "USD",
            "calendarProvider": "google",
            "calendarSyncEnabled": True,
            "selfRegistrationEnabled": True,
            "smtpEnabled": False,
            "autoBackupEnabled": False,
            "autoBackupIntervalMinutes": 1440,
            "autoBackupRetentionDays": 30,
            "autoBackupLastRunAt": None,
            "sessionTimeoutMinutes": None,
        }
        self.base_locales: dict[str, dict[str, str]] = self._load_locales_from_files()
        self.custom_locales: dict[str, dict[str, str]] = {}

    @staticmethod
    def _fallback_locales() -> dict[str, dict[str, str]]:
        return {
            "en": {
                "app.title": "My Finance",
                "common.dashboard": "Dashboard",
                "common.settings": "Settings",
                "common.logout": "Logout",
                "common.language": "Language",
                "common.timezone": "Timezone",
                "common.appearance": "Appearance",
                "common.detect_timezone": "Detect Timezone",
                "common.save": "Save",
                "theme.system": "System",
                "theme.light": "Light",
                "theme.dark": "Dark",
                "onboarding.title": "Get Started",
                "onboarding.subtitle": "Choose app language, timezone, appearance and create your account.",
                "onboarding.initial_setup": "Initial Setup",
                "onboarding.restore_database": "Restore Database",
                "onboarding.already_logged_in": "You are already signed in.",
                "onboarding.go_dashboard": "Open Dashboard",
                "onboarding.logout_first": "Logout First",
                "auth.register": "Register",
                "auth.login": "Login",
                "auth.email": "Email",
                "auth.password": "Password",
                "auth.full_name": "Full name",
                "dashboard.title": "Dashboard",
                "dashboard.subtitle": "Accounts and transactions.",
                "dashboard.create_account": "Create Account",
                "dashboard.create_transaction": "Create Transaction",
                "dashboard.refresh": "Refresh Data",
                "dashboard.advanced_json": "Advanced JSON",
                "settings.title": "Settings",
                "settings.subtitle": "Language, timezone, appearance, backup and translations.",
                "settings.general": "General",
                "settings.calendar_provider": "Calendar provider",
                "settings.sync": "Calendar sync enabled",
                "settings.registration_enabled": "Self registration enabled",
                "settings.smtp": "SMTP enabled",
                "settings.backup": "Backup",
                "settings.translations": "Translations",
                "error.auth_required": "Authentication required.",
                "error.fill_email_password": "Fill email and password.",
                "error.invalid_email": "Invalid email format.",
                "error.password_min_8": "Password must have at least 8 characters.",
                "feedback.settings_saved": "Settings saved.",
            },
            "cs": {
                "app.title": "Moje finance",
                "common.dashboard": "Přehled",
                "common.settings": "Nastavení",
                "common.logout": "Odhlásit",
                "common.language": "Jazyk",
                "common.timezone": "Časové pásmo",
                "common.appearance": "Vzhled",
                "common.detect_timezone": "Zjistit časové pásmo",
                "common.save": "Uložit",
                "theme.system": "Systém",
                "theme.light": "Světlý",
                "theme.dark": "Tmavý",
                "onboarding.title": "Začínáme",
                "onboarding.subtitle": "Nastav jazyk, časové pásmo, vzhled a vytvoř účet.",
                "onboarding.initial_setup": "První nastavení",
                "onboarding.restore_database": "Obnovit databázi",
                "onboarding.already_logged_in": "Už jsi přihlášen.",
                "onboarding.go_dashboard": "Otevřít přehled",
                "onboarding.logout_first": "Nejdříve odhlásit",
                "auth.register": "Registrace",
                "auth.login": "Přihlášení",
                "auth.email": "E-mail",
                "auth.password": "Heslo",
                "auth.full_name": "Celé jméno",
                "dashboard.title": "Přehled",
                "dashboard.subtitle": "Účty a transakce.",
                "dashboard.create_account": "Vytvořit účet",
                "dashboard.create_transaction": "Vytvořit transakci",
                "dashboard.refresh": "Obnovit data",
                "dashboard.advanced_json": "Pokročilý JSON",
                "settings.title": "Nastavení",
                "settings.subtitle": "Jazyk, časové pásmo, vzhled, záloha a překlady.",
                "settings.general": "Obecné",
                "settings.calendar_provider": "Poskytovatel kalendáře",
                "settings.sync": "Synchronizace kalendáře zapnuta",
                "settings.registration_enabled": "Samoobslužná registrace povolena",
                "settings.smtp": "SMTP zapnuto",
                "settings.backup": "Záloha",
                "settings.translations": "Překlady",
                "error.auth_required": "Je vyžadováno přihlášení.",
                "error.fill_email_password": "Vyplň e-mail a heslo.",
                "error.invalid_email": "Neplatný formát e-mailu.",
                "error.password_min_8": "Heslo musí mít alespoň 8 znaků.",
                "feedback.settings_saved": "Nastavení uloženo.",
            },
        }

    def _load_locales_from_files(self) -> dict[str, dict[str, str]]:
        fallback = self._fallback_locales()
        # Support both local repo layout and Docker runtime layout.
        current = Path(__file__).resolve()
        candidates = [
            current.parents[2] / "i18n" / "locales",  # repo root
            current.parents[1] / "i18n" / "locales",  # /app/i18n/locales
            Path("/app/i18n/locales"),                # explicit docker path
        ]
        locales_dir = next((p for p in candidates if p.exists()), candidates[0])
        loaded: dict[str, dict[str, str]] = {}
        for locale in fallback.keys():
            file_path = locales_dir / f"{locale}.json"
            if not file_path.exists():
                loaded[locale] = fallback[locale]
                continue
            try:
                data = json.loads(file_path.read_text(encoding="utf-8"))
                if isinstance(data, dict):
                    normalized = {str(k): str(v) for k, v in data.items()}
                    loaded[locale] = {**fallback[locale], **normalized}
                else:
                    loaded[locale] = fallback[locale]
            except (OSError, json.JSONDecodeError, UnicodeDecodeError):
                loaded[locale] = fallback[locale]
        return loaded

    @staticmethod
    def make_id() -> UUID:
        return uuid4()

    @staticmethod
    def now() -> datetime:
        return datetime.utcnow()


store = InMemoryStore()
