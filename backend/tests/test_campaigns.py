"""
Campaign route tests – covers CRUD for /campaigns.
Note: campaigns router has no auth guard; tests reflect actual behaviour.
"""
import pytest


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def sponsor_user(db):
    from backend.models import User
    from backend.crud import pwd_context
    user = User(
        full_name="Sponsor For Campaigns",
        email="sponsor_camp@example.com",
        password=pwd_context.hash("Password123"),
        role="sponsor",
        is_verified=True
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@pytest.fixture
def sample_campaign(db, sponsor_user):
    from backend.models import Campaign
    camp = Campaign(
        title="Summer Campaign",
        description="Promote summer event",
        creator_id=sponsor_user.id,
        status="open"
    )
    db.add(camp)
    db.commit()
    db.refresh(camp)
    return camp


# ---------------------------------------------------------------------------
# Create
# ---------------------------------------------------------------------------

def test_create_campaign_success(client, sponsor_user):
    response = client.post(
        "/campaigns/",
        json={
            "title": "Winter Promo",
            "description": "Cold season campaign",
            "creator_id": sponsor_user.id,
            "status": "open"
        }
    )
    assert response.status_code == 201
    data = response.json()
    assert data["title"] == "Winter Promo"
    assert data["creator_id"] == sponsor_user.id


def test_create_campaign_missing_title(client, sponsor_user):
    """title is required; omitting it must return 422."""
    response = client.post(
        "/campaigns/",
        json={"creator_id": sponsor_user.id}
    )
    assert response.status_code == 422


def test_create_campaign_missing_creator(client):
    """creator_id is required; omitting it must return 422."""
    response = client.post(
        "/campaigns/",
        json={"title": "No Creator Camp"}
    )
    assert response.status_code == 422


# ---------------------------------------------------------------------------
# Read / List
# ---------------------------------------------------------------------------

def test_list_campaigns(client, sample_campaign):
    response = client.get("/campaigns/")
    assert response.status_code == 200
    assert isinstance(response.json(), list)
    assert len(response.json()) >= 1


def test_get_campaign_by_id(client, sample_campaign):
    response = client.get(f"/campaigns/{sample_campaign.id}")
    assert response.status_code == 200
    assert response.json()["id"] == sample_campaign.id
    assert response.json()["title"] == "Summer Campaign"


def test_get_campaign_not_found(client):
    response = client.get("/campaigns/999999")
    assert response.status_code == 404


# ---------------------------------------------------------------------------
# Update
# ---------------------------------------------------------------------------

def test_update_campaign_success(client, sample_campaign):
    response = client.put(
        f"/campaigns/{sample_campaign.id}",
        json={"title": "Autumn Campaign", "status": "closed"}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["title"] == "Autumn Campaign"
    assert data["status"] == "closed"


def test_update_campaign_partial(client, sample_campaign):
    """Partial update: only description changes; other fields intact."""
    response = client.put(
        f"/campaigns/{sample_campaign.id}",
        json={"description": "Updated description"}
    )
    assert response.status_code == 200
    assert response.json()["description"] == "Updated description"
    assert response.json()["title"] == "Summer Campaign"


def test_update_campaign_not_found(client):
    response = client.put("/campaigns/999999", json={"title": "Ghost"})
    assert response.status_code == 404


# ---------------------------------------------------------------------------
# Delete
# ---------------------------------------------------------------------------

def test_delete_campaign_success(client, sample_campaign):
    response = client.delete(f"/campaigns/{sample_campaign.id}")
    assert response.status_code == 200
    assert response.json()["message"] == "Campaign deleted successfully"

    # Confirm it's gone
    get_response = client.get(f"/campaigns/{sample_campaign.id}")
    assert get_response.status_code == 404


def test_delete_campaign_not_found(client):
    response = client.delete("/campaigns/999999")
    assert response.status_code == 404
