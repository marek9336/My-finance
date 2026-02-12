from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_backup_export_and_restore_roundtrip() -> None:
    first = client.post("/api/v1/vehicles", json={"type": "car", "label": "Primary car", "currentOdometerKm": 1000})
    assert first.status_code == 201

    exported = client.get("/api/v1/admin/backup/export")
    assert exported.status_code == 200
    backup_payload = exported.json()
    assert "data" in backup_payload
    assert "vehicles" in backup_payload["data"]

    second = client.post("/api/v1/vehicles", json={"type": "car", "label": "Second car", "currentOdometerKm": 2000})
    assert second.status_code == 201

    before_restore = client.get("/api/v1/debug/state").json()
    assert before_restore["vehicles"] >= 2

    restored = client.post("/api/v1/admin/backup/import", json=backup_payload)
    assert restored.status_code == 200
    assert restored.json()["replaced"] is True

    after_restore = client.get("/api/v1/debug/state").json()
    assert after_restore["vehicles"] == len(backup_payload["data"]["vehicles"])


def test_backup_ui_available() -> None:
    ui_res = client.get("/ui/backup")
    assert ui_res.status_code == 200


def test_run_backup_now_creates_file() -> None:
    res = client.post("/api/v1/admin/backup/run-now")
    assert res.status_code == 200
    body = res.json()
    assert body["created"] is True
    assert body["file"].startswith("backups/")
