"""
Deal CRUD tests – covers /deals endpoints (create, list, get, update, delete).
Deal lifecycle (accept/sign) is covered in test_deal_lifecycle.py.
"""
import pytest
from backend.crud import pwd_context


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def deal_users(db):
    """Returns (sponsor, organizer, influencer) Users."""
    from backend.models import User
    sponsor = User(
        full_name="Deal Sponsor",
        email="deal_sponsor@example.com",
        password=pwd_context.hash("Password123"),
        role="sponsor",
        is_verified=True
    )
    organizer = User(
        full_name="Deal Organizer",
        email="deal_org@example.com",
        password=pwd_context.hash("Password123"),
        role="organizer",
        is_verified=True
    )
    influencer = User(
        full_name="Deal Influencer",
        email="deal_inf@example.com",
        password=pwd_context.hash("Password123"),
        role="influencer",
        is_verified=True
    )
    db.add_all([sponsor, organizer, influencer])
    db.commit()
    for u in [sponsor, organizer, influencer]:
        db.refresh(u)
    return sponsor, organizer, influencer


@pytest.fixture
def sponsor_headers(deal_users):
    from backend.auth import create_access_token
    sponsor, _, _ = deal_users
    token = create_access_token({"sub": str(sponsor.id)})
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def organizer_headers(deal_users):
    from backend.auth import create_access_token
    _, organizer, _ = deal_users
    token = create_access_token({"sub": str(organizer.id)})
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def influencer_headers(deal_users):
    from backend.auth import create_access_token
    _, _, influencer = deal_users
    token = create_access_token({"sub": str(influencer.id)})
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def created_deal(client, deal_users, sponsor_headers):
    """POST a deal and return the response JSON."""
    sponsor, organizer, _ = deal_users
    resp = client.post(
        "/deals/",
        json={
            "sponsor_id": sponsor.id,
            "organizer_id": organizer.id,
            "deal_type": "sponsorship"
        },
        headers=sponsor_headers
    )
    assert resp.status_code == 201
    return resp.json()


# ---------------------------------------------------------------------------
# Create Deal
# ---------------------------------------------------------------------------

def test_create_deal_sponsorship(client, deal_users, sponsor_headers):
    """Sponsor can create a sponsorship deal with an organizer."""
    sponsor, organizer, _ = deal_users
    response = client.post(
        "/deals/",
        json={
            "sponsor_id": sponsor.id,
            "organizer_id": organizer.id,
            "deal_type": "sponsorship"
        },
        headers=sponsor_headers
    )
    assert response.status_code == 201
    data = response.json()
    assert data["deal_type"] == "sponsorship"
    assert data["sponsor_id"] == sponsor.id
    assert data["status"] == "proposed"


def test_create_deal_promotion(client, deal_users, influencer_headers):
    """Influencer can create a promotion deal."""
    sponsor, _, influencer = deal_users
    response = client.post(
        "/deals/",
        json={
            "sponsor_id": sponsor.id,
            "influencer_id": influencer.id,
            "deal_type": "promotion"
        },
        headers=influencer_headers
    )
    assert response.status_code == 201
    assert response.json()["deal_type"] == "promotion"


def test_create_deal_unauthenticated(client, deal_users):
    """No auth token → 401."""
    sponsor, organizer, _ = deal_users
    response = client.post(
        "/deals/",
        json={
            "sponsor_id": sponsor.id,
            "organizer_id": organizer.id,
            "deal_type": "sponsorship"
        }
    )
    assert response.status_code == 401


def test_create_deal_not_participant(client, deal_users, influencer_headers):
    """
    Influencer trying to create a sponsor↔organizer deal (they are not a participant)
    must be rejected with 403.
    """
    sponsor, organizer, _ = deal_users
    response = client.post(
        "/deals/",
        json={
            "sponsor_id": sponsor.id,
            "organizer_id": organizer.id,
            "deal_type": "sponsorship"
        },
        headers=influencer_headers
    )
    assert response.status_code == 403


def test_create_deal_missing_deal_type(client, deal_users, sponsor_headers):
    """deal_type is required; omitting it returns 422."""
    sponsor, organizer, _ = deal_users
    response = client.post(
        "/deals/",
        json={"sponsor_id": sponsor.id, "organizer_id": organizer.id},
        headers=sponsor_headers
    )
    assert response.status_code == 422


def test_create_deal_invalid_deal_type(client, deal_users, sponsor_headers):
    """Invalid deal_type literal returns 422."""
    sponsor, organizer, _ = deal_users
    response = client.post(
        "/deals/",
        json={
            "sponsor_id": sponsor.id,
            "organizer_id": organizer.id,
            "deal_type": "fraud"
        },
        headers=sponsor_headers
    )
    assert response.status_code == 422


# ---------------------------------------------------------------------------
# List Deals
# ---------------------------------------------------------------------------

def test_list_deals_authenticated(client, created_deal, sponsor_headers):
    response = client.get("/deals/", headers=sponsor_headers)
    assert response.status_code == 200
    assert isinstance(response.json(), list)
    assert len(response.json()) >= 1


def test_list_deals_unauthenticated(client):
    response = client.get("/deals/")
    assert response.status_code == 401


# ---------------------------------------------------------------------------
# Get Deal by ID
# ---------------------------------------------------------------------------

def test_get_deal_by_id(client, created_deal, sponsor_headers):
    deal_id = created_deal["id"]
    response = client.get(f"/deals/{deal_id}", headers=sponsor_headers)
    assert response.status_code == 200
    assert response.json()["id"] == deal_id


def test_get_deal_not_found(client, sponsor_headers):
    response = client.get("/deals/999999", headers=sponsor_headers)
    assert response.status_code == 400  # ValidationError → 400


def test_get_deal_not_participant(client, created_deal, influencer_headers):
    """
    Influencer (not part of a sponsor↔organizer deal) cannot view the deal.
    """
    deal_id = created_deal["id"]
    response = client.get(f"/deals/{deal_id}", headers=influencer_headers)
    assert response.status_code == 403


# ---------------------------------------------------------------------------
# Update Deal (proof_of_work only)
# ---------------------------------------------------------------------------

def test_update_deal_proof_of_work(client, created_deal, sponsor_headers):
    deal_id = created_deal["id"]
    response = client.put(
        f"/deals/{deal_id}",
        json={"proof_of_work": "https://link-to-proof.com"},
        headers=sponsor_headers
    )
    assert response.status_code == 200
    assert response.json()["proof_of_work"] == "https://link-to-proof.com"


def test_update_deal_status_injection_blocked(client, created_deal, sponsor_headers):
    """Attempts to inject status via PUT are silently ignored (mass-assignment guard)."""
    deal_id = created_deal["id"]
    response = client.put(
        f"/deals/{deal_id}",
        json={"status": "closed"},
        headers=sponsor_headers
    )
    assert response.status_code == 200
    assert response.json()["status"] == "proposed"  # unchanged


def test_update_deal_not_found(client, sponsor_headers):
    response = client.put(
        "/deals/999999",
        json={"proof_of_work": "test"},
        headers=sponsor_headers
    )
    assert response.status_code == 400


def test_update_deal_not_participant(client, created_deal, influencer_headers):
    deal_id = created_deal["id"]
    response = client.put(
        f"/deals/{deal_id}",
        json={"proof_of_work": "hack"},
        headers=influencer_headers
    )
    assert response.status_code == 403


def test_update_deal_unauthenticated(client, created_deal):
    deal_id = created_deal["id"]
    response = client.put(f"/deals/{deal_id}", json={"proof_of_work": "test"})
    assert response.status_code == 401


# ---------------------------------------------------------------------------
# Delete Deal
# ---------------------------------------------------------------------------

def test_delete_deal_success(client, created_deal, sponsor_headers):
    deal_id = created_deal["id"]
    response = client.delete(f"/deals/{deal_id}", headers=sponsor_headers)
    assert response.status_code == 200

    # Confirm it's gone
    get_resp = client.get(f"/deals/{deal_id}", headers=sponsor_headers)
    assert get_resp.status_code == 400


def test_delete_deal_not_found(client, sponsor_headers):
    response = client.delete("/deals/999999", headers=sponsor_headers)
    assert response.status_code == 400


def test_delete_deal_not_participant(client, created_deal, influencer_headers):
    deal_id = created_deal["id"]
    response = client.delete(f"/deals/{deal_id}", headers=influencer_headers)
    assert response.status_code == 403


def test_delete_deal_unauthenticated(client, created_deal):
    deal_id = created_deal["id"]
    response = client.delete(f"/deals/{deal_id}")
    assert response.status_code == 401
