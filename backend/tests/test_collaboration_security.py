from backend.auth import create_access_token
from backend.crud import pwd_context
from backend.models import AuditEvent, User


def _auth_headers(user_id: int) -> dict[str, str]:
    token = create_access_token({"sub": str(user_id)})
    return {"Authorization": f"Bearer {token}"}


def _seed_users(db):
    owner = User(
        full_name="Collab Owner",
        email="collab_owner@example.com",
        password=pwd_context.hash("Password123"),
        role="sponsor",
        is_verified=True,
    )
    manager = User(
        full_name="Collab Manager",
        email="collab_manager@example.com",
        password=pwd_context.hash("Password123"),
        role="organizer",
        is_verified=True,
    )
    member = User(
        full_name="Collab Member",
        email="collab_member@example.com",
        password=pwd_context.hash("Password123"),
        role="influencer",
        is_verified=True,
    )
    db.add_all([owner, manager, member])
    db.commit()
    for row in [owner, manager, member]:
        db.refresh(row)
    return owner, manager, member


def test_manager_cannot_promote_member_to_owner(client, db):
    owner, manager, member = _seed_users(db)
    owner_headers = _auth_headers(int(getattr(owner, "id", 0)))
    manager_headers = _auth_headers(int(getattr(manager, "id", 0)))

    workspace = client.post(
        "/collaboration/workspaces",
        headers=owner_headers,
        json={"name": "Security Workspace"},
    )
    assert workspace.status_code == 200
    workspace_id = workspace.json()["id"]

    manager_row = client.post(
        f"/collaboration/workspaces/{workspace_id}/members",
        headers=owner_headers,
        json={"user_id": int(getattr(manager, "id", 0)), "role": "manager"},
    )
    assert manager_row.status_code == 200

    member_row = client.post(
        f"/collaboration/workspaces/{workspace_id}/members",
        headers=owner_headers,
        json={"user_id": int(getattr(member, "id", 0)), "role": "viewer"},
    )
    assert member_row.status_code == 200
    member_id = member_row.json()["id"]

    promote = client.put(
        f"/collaboration/workspaces/{workspace_id}/members/{member_id}",
        headers=manager_headers,
        json={"role": "owner"},
    )
    assert promote.status_code == 403


def test_collaboration_role_changes_are_audited(client, db):
    owner, manager, member = _seed_users(db)
    owner_headers = _auth_headers(int(getattr(owner, "id", 0)))

    workspace = client.post(
        "/collaboration/workspaces",
        headers=owner_headers,
        json={"name": "Audit Workspace"},
    )
    assert workspace.status_code == 200
    workspace_id = workspace.json()["id"]

    invited = client.post(
        f"/collaboration/workspaces/{workspace_id}/members",
        headers=owner_headers,
        json={"user_id": int(getattr(manager, "id", 0)), "role": "manager"},
    )
    assert invited.status_code == 200
    manager_member_id = invited.json()["id"]

    promote_finance = client.put(
        f"/collaboration/workspaces/{workspace_id}/members/{manager_member_id}",
        headers=owner_headers,
        json={"role": "finance"},
    )
    assert promote_finance.status_code == 200

    owner_assignment = client.post(
        f"/collaboration/workspaces/{workspace_id}/members",
        headers=owner_headers,
        json={"user_id": int(getattr(member, "id", 0)), "role": "owner"},
    )
    assert owner_assignment.status_code == 200

    events = db.query(AuditEvent).filter(AuditEvent.action == "collaboration.member_role_changed").all()
    assert len(events) >= 3

    # Ensure at least one event tracks role mutation with before/after.
    assert any(
        isinstance(evt.event_meta, dict)
        and evt.event_meta.get("workspace_id") == workspace_id
        and evt.event_meta.get("from_role") is not None
        and evt.event_meta.get("to_role") is not None
        for evt in events
    )
