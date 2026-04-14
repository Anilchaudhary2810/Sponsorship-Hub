def test_list_plans_public(client):
    resp = client.get("/billing/plans")
    assert resp.status_code == 200
    data = resp.json()
    codes = {item["code"] for item in data}
    assert {"free", "starter", "growth", "enterprise"}.issubset(codes)


def test_my_billing_default_plan(client, auth_headers):
    resp = client.get("/billing/me", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["plan_tier"] == "free"
    assert data["plan_status"] == "active"
    assert "limits" in data
    assert "usage" in data


def test_change_plan_creates_history_record(client, auth_headers):
    change_resp = client.post(
        "/billing/me/change-plan",
        headers=auth_headers,
        json={"target_plan": "growth", "note": "phase-4-check"},
    )
    assert change_resp.status_code == 200
    changed = change_resp.json()
    assert changed["plan_tier"] == "growth"
    assert changed["plan_status"] == "active"

    history_resp = client.get("/billing/me/history", headers=auth_headers)
    assert history_resp.status_code == 200
    history = history_resp.json()
    assert len(history) >= 1
    assert history[0]["to_plan"] == "growth"
