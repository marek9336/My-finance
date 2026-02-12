from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_property_cost_invalid_period_returns_422() -> None:
    property_payload = {"type": "house", "name": "Test house"}
    property_res = client.post("/api/v1/properties", json=property_payload)
    assert property_res.status_code == 201
    property_id = property_res.json()["id"]

    cost_payload = {
        "costType": "electricity",
        "periodStart": "2026-02-10",
        "periodEnd": "2026-02-01",
        "amount": 1000,
        "currency": "CZK",
    }
    res = client.post(f"/api/v1/properties/{property_id}/costs", json=cost_payload)
    assert res.status_code == 422
    assert res.json()["error"]["code"] == "VALIDATION_ERROR"


def test_insurance_vehicle_requires_subject_vehicle_id() -> None:
    payload = {"insuranceType": "vehicle", "provider": "Allianz"}
    res = client.post("/api/v1/insurances", json=payload)
    assert res.status_code == 422
    assert res.json()["error"]["code"] == "VALIDATION_ERROR"


def test_invalid_currency_returns_422() -> None:
    payload = {"type": "car", "label": "Car", "currentOdometerKm": 10}
    vehicle_res = client.post("/api/v1/vehicles", json=payload)
    assert vehicle_res.status_code == 201
    vehicle_id = vehicle_res.json()["id"]

    service_payload = {
        "serviceType": "oil_change",
        "serviceAt": "2026-02-12",
        "totalCost": 1200,
        "currency": "CZ",
    }
    res = client.post(f"/api/v1/vehicles/{vehicle_id}/services", json=service_payload)
    assert res.status_code == 422
    assert res.json()["error"]["code"] == "VALIDATION_ERROR"
