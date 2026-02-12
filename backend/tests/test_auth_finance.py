from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_register_create_account_and_transaction() -> None:
    reg_res = client.post(
        "/api/v1/auth/register",
        json={
            "email": "tester@example.com",
            "password": "Secret123!",
            "fullName": "Test User",
        },
    )
    assert reg_res.status_code == 201
    token = reg_res.json()["token"]
    headers = {"Authorization": f"Bearer {token}"}

    acc_res = client.post(
        "/api/v1/accounts",
        json={
            "name": "Main",
            "accountType": "checking",
            "currency": "CZK",
            "initialBalance": 1000,
        },
        headers=headers,
    )
    assert acc_res.status_code == 201
    account_id = acc_res.json()["id"]

    tx_res = client.post(
        "/api/v1/transactions",
        json={
            "accountId": account_id,
            "direction": "expense",
            "amount": 100,
            "currency": "CZK",
            "occurredAt": "2026-02-12T18:00:00Z",
            "category": "food",
            "note": "test",
        },
        headers=headers,
    )
    assert tx_res.status_code == 201

    list_acc = client.get("/api/v1/accounts", headers=headers)
    assert list_acc.status_code == 200
    assert len(list_acc.json()) >= 1

    list_tx = client.get("/api/v1/transactions", headers=headers)
    assert list_tx.status_code == 200
    assert len(list_tx.json()) >= 1
