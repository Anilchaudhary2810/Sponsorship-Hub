def test_plan_distribution_requires_admin(client, auth_headers):
    resp = client.get("/ops/plan-distribution", headers=auth_headers)
    assert resp.status_code == 403


def test_plan_distribution_admin(client, admin_auth_headers):
    resp = client.get("/ops/plan-distribution", headers=admin_auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert "distribution" in data
    assert "estimated_mrr_inr" in data
