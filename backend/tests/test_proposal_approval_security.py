from datetime import datetime

from backend.auth import create_access_token
from backend.crud import pwd_context
from backend.models import Deal, User, Workspace, WorkspaceMember, WorkspaceResource


def _auth_headers(user_id: int) -> dict[str, str]:
    token = create_access_token({"sub": str(user_id)})
    return {"Authorization": f"Bearer {token}"}


def _seed_users_and_deal(db):
    sponsor = User(
        full_name="Proposal Sponsor",
        email="proposal_sponsor@example.com",
        password=pwd_context.hash("Password123"),
        role="sponsor",
        is_verified=True,
    )
    organizer = User(
        full_name="Proposal Organizer",
        email="proposal_organizer@example.com",
        password=pwd_context.hash("Password123"),
        role="organizer",
        is_verified=True,
    )
    influencer = User(
        full_name="Proposal Influencer",
        email="proposal_influencer@example.com",
        password=pwd_context.hash("Password123"),
        role="influencer",
        is_verified=True,
    )
    db.add_all([sponsor, organizer, influencer])
    db.commit()
    for row in [sponsor, organizer, influencer]:
        db.refresh(row)

    deal = Deal(
        sponsor_id=int(getattr(sponsor, "id", 0)),
        organizer_id=int(getattr(organizer, "id", 0)),
        influencer_id=int(getattr(influencer, "id", 0)),
        deal_type="promotion",
        status="proposed",
        sponsor_accepted=True,
        payment_amount=12000,
        currency="INR",
        created_at=datetime.utcnow(),
    )
    db.add(deal)
    db.commit()
    db.refresh(deal)
    return sponsor, organizer, influencer, deal


def _attach_workspace_roles(db, sponsor, organizer, influencer, deal):
    sponsor_id = int(getattr(sponsor, "id", 0))
    organizer_id = int(getattr(organizer, "id", 0))
    influencer_id = int(getattr(influencer, "id", 0))
    deal_id = int(getattr(deal, "id", 0))
    workspace = Workspace(name="Proposal Workspace", owner_user_id=sponsor_id, is_active=True)
    db.add(workspace)
    db.commit()
    db.refresh(workspace)
    workspace_id = int(getattr(workspace, "id", 0))

    db.add_all(
        [
            WorkspaceMember(
                workspace_id=workspace_id,
                user_id=sponsor_id,
                role="owner",
                status="active",
                invited_by_user_id=sponsor_id,
            ),
            WorkspaceMember(
                workspace_id=workspace_id,
                user_id=organizer_id,
                role="viewer",
                status="active",
                invited_by_user_id=sponsor_id,
            ),
            WorkspaceMember(
                workspace_id=workspace_id,
                user_id=influencer_id,
                role="manager",
                status="active",
                invited_by_user_id=sponsor_id,
            ),
            WorkspaceResource(
                workspace_id=workspace_id,
                resource_type="deal",
                resource_id=deal_id,
                added_by_user_id=sponsor_id,
            ),
        ]
    )
    db.commit()


def test_unset_approver_user_rejects_unauthorized_participant(client, db):
    sponsor, organizer, influencer, deal = _seed_users_and_deal(db)
    _attach_workspace_roles(db, sponsor, organizer, influencer, deal)

    create_resp = client.post(
        f"/proposal/deals/{int(getattr(deal, 'id', 0))}/approvals",
        headers=_auth_headers(int(getattr(sponsor, "id", 0))),
        json={"approver_role": "manager"},
    )
    assert create_resp.status_code == 200
    approval_id = create_resp.json()["id"]

    unauthorized_decision = client.put(
        f"/proposal/approvals/{approval_id}/decision",
        headers=_auth_headers(int(getattr(organizer, "id", 0))),
        json={"decision": "approved"},
    )
    assert unauthorized_decision.status_code == 403


def test_unset_approver_user_allows_matching_workspace_role(client, db):
    sponsor, organizer, influencer, deal = _seed_users_and_deal(db)
    _attach_workspace_roles(db, sponsor, organizer, influencer, deal)

    create_resp = client.post(
        f"/proposal/deals/{int(getattr(deal, 'id', 0))}/approvals",
        headers=_auth_headers(int(getattr(sponsor, "id", 0))),
        json={"approver_role": "manager"},
    )
    assert create_resp.status_code == 200
    approval_id = create_resp.json()["id"]

    authorized_decision = client.put(
        f"/proposal/approvals/{approval_id}/decision",
        headers=_auth_headers(int(getattr(influencer, "id", 0))),
        json={"decision": "approved"},
    )
    assert authorized_decision.status_code == 200
    assert authorized_decision.json()["status"] == "approved"
