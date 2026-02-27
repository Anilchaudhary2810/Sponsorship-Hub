"""
Reviews route tests – covers /reviews endpoints.
Note: reviews router has no auth guard; tests reflect actual behaviour.
"""
import pytest


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def review_deal(db):
    """Create a minimal deal + two users to hang reviews from."""
    from backend.models import User, Deal
    from backend.crud import pwd_context

    sponsor = User(
        full_name="Review Sponsor",
        email="rev_sponsor@example.com",
        password=pwd_context.hash("Password123"),
        role="sponsor",
        is_verified=True,
    )
    organizer = User(
        full_name="Review Organizer",
        email="rev_org@example.com",
        password=pwd_context.hash("Password123"),
        role="organizer",
        is_verified=True,
    )
    db.add_all([sponsor, organizer])
    db.commit()
    db.refresh(sponsor)
    db.refresh(organizer)

    deal = Deal(
        sponsor_id=sponsor.id,
        organizer_id=organizer.id,
        deal_type="sponsorship",
        status="closed",
        payment_amount=500,
        currency="INR",
        payment_done=True,
    )
    db.add(deal)
    db.commit()
    db.refresh(deal)
    return deal, sponsor, organizer


# ---------------------------------------------------------------------------
# Create Review
# ---------------------------------------------------------------------------

def test_create_review_success(client, review_deal):
    deal, sponsor, organizer = review_deal
    response = client.post(
        "/reviews/",
        json={
            "deal_id": deal.id,
            "reviewer_id": sponsor.id,
            "reviewer_role": "sponsor",
            "target_role": "organizer",
            "rating": 5,
            "comment": "Great partnership!"
        }
    )
    assert response.status_code == 201
    data = response.json()
    assert data["rating"] == 5
    assert data["deal_id"] == deal.id


def test_create_review_duplicate_rejected(client, review_deal):
    """Same reviewer cannot post two reviews for the same deal (unique constraint)."""
    deal, sponsor, organizer = review_deal
    payload = {
        "deal_id": deal.id,
        "reviewer_id": sponsor.id,
        "reviewer_role": "sponsor",
        "target_role": "organizer",
        "rating": 4
    }
    client.post("/reviews/", json=payload)  # first review
    response = client.post("/reviews/", json=payload)  # duplicate
    assert response.status_code == 400


def test_create_review_invalid_rating_type(client, review_deal):
    """Rating must be an integer; string should be rejected."""
    deal, sponsor, _ = review_deal
    response = client.post(
        "/reviews/",
        json={
            "deal_id": deal.id,
            "reviewer_id": sponsor.id,
            "reviewer_role": "sponsor",
            "target_role": "organizer",
            "rating": "five"  # invalid
        }
    )
    assert response.status_code == 422


def test_create_review_missing_required_field(client, review_deal):
    """Omitting rating should return 422."""
    deal, sponsor, _ = review_deal
    response = client.post(
        "/reviews/",
        json={
            "deal_id": deal.id,
            "reviewer_id": sponsor.id,
            "reviewer_role": "sponsor",
            "target_role": "organizer"
            # rating missing
        }
    )
    assert response.status_code == 422


# ---------------------------------------------------------------------------
# List Reviews
# ---------------------------------------------------------------------------

def test_list_all_reviews(client, review_deal):
    deal, sponsor, _ = review_deal
    # Create one review first
    client.post(
        "/reviews/",
        json={
            "deal_id": deal.id,
            "reviewer_id": sponsor.id,
            "reviewer_role": "sponsor",
            "target_role": "organizer",
            "rating": 3
        }
    )
    response = client.get("/reviews/")
    assert response.status_code == 200
    assert isinstance(response.json(), list)
    assert len(response.json()) >= 1


def test_get_reviews_by_deal(client, review_deal):
    deal, sponsor, _ = review_deal
    client.post(
        "/reviews/",
        json={
            "deal_id": deal.id,
            "reviewer_id": sponsor.id,
            "reviewer_role": "sponsor",
            "target_role": "organizer",
            "rating": 4
        }
    )
    response = client.get(f"/reviews/{deal.id}")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert all(r["deal_id"] == deal.id for r in data)


def test_get_reviews_for_nonexistent_deal(client):
    """A deal with no reviews returns an empty list (not 404)."""
    response = client.get("/reviews/999999")
    assert response.status_code == 200
    assert response.json() == []
