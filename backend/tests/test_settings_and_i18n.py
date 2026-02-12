from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_app_settings_update() -> None:
    get_res = client.get("/api/v1/settings/app")
    assert get_res.status_code == 200
    assert get_res.json()["calendarProvider"] == "google"

    put_res = client.put(
        "/api/v1/settings/app",
        json={
            "selfRegistrationEnabled": False,
            "defaultTimezone": "UTC",
            "autoBackupEnabled": True,
            "autoBackupIntervalMinutes": 60,
            "autoBackupRetentionDays": 14
        },
    )
    assert put_res.status_code == 200
    body = put_res.json()
    assert body["selfRegistrationEnabled"] is False
    assert body["defaultTimezone"] == "UTC"
    assert body["autoBackupEnabled"] is True
    assert body["autoBackupIntervalMinutes"] == 60
    assert body["autoBackupRetentionDays"] == 14


def test_custom_locale_overlay() -> None:
    locales_res = client.get("/api/v1/i18n/locales")
    assert locales_res.status_code == 200
    assert "en" in locales_res.json()["locales"]

    put_res = client.put(
        "/api/v1/i18n/en/custom",
        json={"settings.calendar": "Calendar", "custom.key": "Custom message"},
    )
    assert put_res.status_code == 200
    merged = put_res.json()["messages"]
    assert merged["settings.calendar"] == "Calendar"
    assert merged["custom.key"] == "Custom message"


def test_publish_custom_locale_to_file() -> None:
    client.put("/api/v1/i18n/en/custom", json={"custom.export.key": "Value"})
    publish_res = client.post("/api/v1/i18n/en/custom/publish")
    assert publish_res.status_code == 200
    body = publish_res.json()
    assert body["locale"] == "en"
    assert body["keys"] >= 1
    assert body["path"].startswith("i18n/custom/")


def test_ui_pages_available() -> None:
    settings_res = client.get("/ui/settings")
    translations_res = client.get("/ui/translations")
    assert settings_res.status_code == 200
    assert translations_res.status_code == 200
