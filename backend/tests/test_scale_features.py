from datetime import datetime

from backend.auth import create_access_token
from backend.crud import pwd_context
from backend.models import Deal, User


def _auth_headers(user_id: int) -> dict[str, str]:
    token = create_access_token({"sub": str(user_id)})
    return {"Authorization": f"Bearer {token}"}


def _seed_users(db):
    sponsor = User(
        full_name="Scale Sponsor",
        email="scale_sponsor@example.com",
        password=pwd_context.hash("Password123"),
        role="sponsor",
        is_verified=True,
    )
    organizer = User(
        full_name="Scale Organizer",
        email="scale_organizer@example.com",
        password=pwd_context.hash("Password123"),
        role="organizer",
        is_verified=True,
    )
    influencer = User(
        full_name="Scale Influencer",
        email="scale_influencer@example.com",
        password=pwd_context.hash("Password123"),
        role="influencer",
        is_verified=True,
    )
    manager = User(
        full_name="Scale Manager",
        email="scale_manager@example.com",
        password=pwd_context.hash("Password123"),
        role="sponsor",
        is_verified=True,
    )
    db.add_all([sponsor, organizer, influencer, manager])
    db.commit()
    for item in [sponsor, organizer, influencer, manager]:
        db.refresh(item)
    return sponsor, organizer, influencer, manager


def _create_deal(db, sponsor_id: int, organizer_id: int):
    deal = Deal(
        sponsor_id=sponsor_id,
        organizer_id=organizer_id,
        deal_type="sponsorship",
        status="proposed",
        sponsor_accepted=True,
        payment_amount=15000,
        currency="INR",
        created_at=datetime.utcnow(),
    )
    db.add(deal)
    db.commit()
    db.refresh(deal)
    return deal


def test_proposal_tools_flow(client, db):
    sponsor, organizer, _, _ = _seed_users(db)
    sponsor_id = int(getattr(sponsor, "id", 0))
    organizer_id = int(getattr(organizer, "id", 0))
    sponsor_headers = _auth_headers(sponsor_id)
    organizer_headers = _auth_headers(organizer_id)
    deal = _create_deal(db, sponsor_id, organizer_id)

    tpl_resp = client.post(
        "/proposal/templates",
        headers=sponsor_headers,
        json={"name": "Fast Sponsorship", "description": "Standard terms", "deal_type": "sponsorship"},
    )
    assert tpl_resp.status_code == 200

    list_tpl = client.get("/proposal/templates", headers=sponsor_headers)
    assert list_tpl.status_code == 200
    assert len(list_tpl.json()) >= 1

    approval_resp = client.post(
        f"/proposal/deals/{deal.id}/approvals",
        headers=sponsor_headers,
        json={"approver_role": "manager", "approver_user_id": organizer_id},
    )
    assert approval_resp.status_code == 200
    approval_id = approval_resp.json()["id"]

    decision_resp = client.put(
        f"/proposal/approvals/{approval_id}/decision",
        headers=organizer_headers,
        json={"decision": "approved"},
    )
    assert decision_resp.status_code == 200
    assert decision_resp.json()["status"] == "approved"

    nego_resp = client.post(
        f"/proposal/deals/{deal.id}/negotiations",
        headers=sponsor_headers,
        json={"change_type": "counter_offer", "message": "Adjust payment to 14k"},
    )
    assert nego_resp.status_code == 200

    nego_list = client.get(f"/proposal/deals/{deal.id}/negotiations", headers=organizer_headers)
    assert nego_list.status_code == 200
    assert len(nego_list.json()) >= 1


def test_revenue_confidence_flow(client, db):
    sponsor, organizer, _, _ = _seed_users(db)
    sponsor_id = int(getattr(sponsor, "id", 0))
    organizer_id = int(getattr(organizer, "id", 0))
    sponsor_headers = _auth_headers(sponsor_id)
    organizer_headers = _auth_headers(organizer_id)
    deal = _create_deal(db, sponsor_id, organizer_id)

    milestone_resp = client.post(
        f"/revenue/deals/{deal.id}/milestones",
        headers=sponsor_headers,
        json={"title": "Kickoff", "amount": 5000},
    )
    assert milestone_resp.status_code == 200
    milestone_id = milestone_resp.json()["id"]

    fund_resp = client.put(
        f"/revenue/milestones/{milestone_id}/action",
        headers=sponsor_headers,
        json={"action": "fund"},
    )
    assert fund_resp.status_code == 200
    assert fund_resp.json()["status"] == "funded"

    release_resp = client.put(
        f"/revenue/milestones/{milestone_id}/action",
        headers=sponsor_headers,
        json={"action": "release"},
    )
    assert release_resp.status_code == 200
    assert release_resp.json()["status"] == "released"

    dispute_open = client.post(
        f"/revenue/deals/{deal.id}/disputes",
        headers=organizer_headers,
        json={"reason": "Delivery mismatch", "details": "Need clarification"},
    )
    assert dispute_open.status_code == 200
    dispute_id = dispute_open.json()["id"]

    dispute_update = client.put(
        f"/revenue/disputes/{dispute_id}/resolve",
        headers=sponsor_headers,
        json={"decision": "under_review", "resolution_note": "Investigating"},
    )
    assert dispute_update.status_code == 200
    assert dispute_update.json()["status"] == "under_review"

    escrow_resp = client.get(f"/revenue/deals/{deal.id}/escrow", headers=organizer_headers)
    assert escrow_resp.status_code == 200
    assert "escrow_state" in escrow_resp.json()


def test_collaboration_retention_reporting_integrations(client, db):
    sponsor, organizer, _, manager = _seed_users(db)
    sponsor_id = int(getattr(sponsor, "id", 0))
    organizer_id = int(getattr(organizer, "id", 0))
    manager_id = int(getattr(manager, "id", 0))
    sponsor_headers = _auth_headers(sponsor_id)
    organizer_headers = _auth_headers(organizer_id)

    workspace_resp = client.post("/collaboration/workspaces", headers=sponsor_headers, json={"name": "Scale Team"})
    assert workspace_resp.status_code == 200
    workspace_id = workspace_resp.json()["id"]

    invite_resp = client.post(
        f"/collaboration/workspaces/{workspace_id}/members",
        headers=sponsor_headers,
        json={"user_id": organizer_id, "role": "manager"},
    )
    assert invite_resp.status_code == 200

    resource_resp = client.post(
        f"/collaboration/workspaces/{workspace_id}/resources",
        headers=sponsor_headers,
        json={"resource_type": "deal", "resource_id": 101},
    )
    assert resource_resp.status_code == 200

    workspace_view = client.get(f"/collaboration/workspaces/{workspace_id}", headers=organizer_headers)
    assert workspace_view.status_code == 200
    assert len(workspace_view.json().get("members", [])) >= 2

    deal = _create_deal(db, sponsor_id, organizer_id)
    setattr(deal, "payment_done", True)
    setattr(deal, "status", "signing_pending")
    db.add(deal)
    db.commit()

    generate_nudges = client.post("/retention/generate", headers=sponsor_headers)
    assert generate_nudges.status_code == 200
    nudge_list = client.get("/retention/me", headers=sponsor_headers)
    assert nudge_list.status_code == 200
    assert isinstance(nudge_list.json(), list)
    if nudge_list.json():
        nudge_id = nudge_list.json()[0]["id"]
        mark_done = client.put(f"/retention/{nudge_id}", headers=sponsor_headers, json={"state": "done"})
        assert mark_done.status_code == 200

    roi_resp = client.get("/reports/roi", headers=sponsor_headers)
    assert roi_resp.status_code == 200
    assert "conversion_rate" in roi_resp.json()

    outcome_resp = client.get("/reports/campaign-outcomes", headers=sponsor_headers)
    assert outcome_resp.status_code == 200
    assert isinstance(outcome_resp.json(), list)

    monthly_resp = client.get("/reports/monthly-executive", headers=sponsor_headers)
    assert monthly_resp.status_code == 200
    assert "kpis" in monthly_resp.json()

    snapshot_resp = client.get("/reports/snapshots", headers=sponsor_headers)
    assert snapshot_resp.status_code == 200
    assert isinstance(snapshot_resp.json(), list)

    connect_resp = client.post("/integrations/connect", headers=sponsor_headers, json={"provider": "slack", "config_json": {}})
    assert connect_resp.status_code == 200

    sync_resp = client.post(
        "/integrations/slack/sync",
        headers=sponsor_headers,
        json={"event_type": "manual_sync", "payload": {"channel": "#ops"}},
    )
    assert sync_resp.status_code == 200

    events_resp = client.get("/integrations/slack/events", headers=sponsor_headers)
    assert events_resp.status_code == 200
    assert len(events_resp.json()) >= 1

    alert_resp = client.post(
        "/integrations/slack/test-alert",
        headers=sponsor_headers,
        json={"event_type": "slack_test", "payload": {"message": "hello"}},
    )
    assert alert_resp.status_code == 200

    export_csv = client.get("/integrations/sheets/export.csv", headers=sponsor_headers)
    assert export_csv.status_code == 200
    assert "text/csv" in export_csv.headers.get("content-type", "")

    export_ics = client.get("/integrations/calendar/export.ics", headers=sponsor_headers)
    assert export_ics.status_code == 200
    assert "text/calendar" in export_ics.headers.get("content-type", "")

    # Permission guard check: organizer should not manage sponsor-owned workspace owner role
    unauthorized_invite = client.post(
        f"/collaboration/workspaces/{workspace_id}/members",
        headers=_auth_headers(manager_id),
        json={"user_id": sponsor_id, "role": "viewer"},
    )
    # manager user is not a member in this workspace
    assert unauthorized_invite.status_code == 403
