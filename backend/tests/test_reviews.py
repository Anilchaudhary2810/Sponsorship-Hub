"""
Reviews route tests - covers /reviews endpoints.
"""
import pytest
from backend.auth import create_access_token


@pytest.fixture
def review_deal(db):
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


def _headers_for(user_id: int):
    token = create_access_token({"sub": str(user_id)})
    return {"Authorization": f"Bearer {token}"}


def test_create_review_success(client, review_deal):
    deal, sponsor, _ = review_deal
    response = client.post(
        "/reviews/",
        headers=_headers_for(sponsor.id),
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


def test_create_review_reviewer_impersonation_blocked(client, review_deal):
    deal, sponsor, organizer = review_deal
    response = client.post(
        "/reviews/",
        headers=_headers_for(sponsor.id),
        json={
            "deal_id": deal.id,
            "reviewer_id": organizer.id,
            "reviewer_role": "organizer",
            "target_role": "sponsor",
            "rating": 4
        }
    )
    assert response.status_code == 403


def test_create_review_duplicate_rejected(client, review_deal):
    deal, sponsor, _ = review_deal
    payload = {
        "deal_id": deal.id,
        "reviewer_id": sponsor.id,
        "reviewer_role": "sponsor",
        "target_role": "organizer",
        "rating": 4
    }
    client.post("/reviews/", headers=_headers_for(sponsor.id), json=payload)
    response = client.post("/reviews/", headers=_headers_for(sponsor.id), json=payload)
    assert response.status_code == 400


def test_create_review_invalid_rating_type(client, review_deal):
    deal, sponsor, _ = review_deal
    response = client.post(
        "/reviews/",
        headers=_headers_for(sponsor.id),
        json={
            "deal_id": deal.id,
            "reviewer_id": sponsor.id,
            "reviewer_role": "sponsor",
            "target_role": "organizer",
            "rating": "five"
        }
    )
    assert response.status_code == 422


def test_create_review_missing_required_field(client, review_deal):
    deal, sponsor, _ = review_deal
    response = client.post(
        "/reviews/",
        headers=_headers_for(sponsor.id),
        json={
            "deal_id": deal.id,
            "reviewer_id": sponsor.id,
            "reviewer_role": "sponsor",
            "target_role": "organizer"
        }
    )
    assert response.status_code == 422


def test_list_all_reviews_admin_only(client, review_deal, test_admin):
    deal, sponsor, _ = review_deal
    client.post(
        "/reviews/",
        headers=_headers_for(sponsor.id),
        json={
            "deal_id": deal.id,
            "reviewer_id": sponsor.id,
            "reviewer_role": "sponsor",
            "target_role": "organizer",
            "rating": 3
        }
    )

    non_admin_response = client.get("/reviews/", headers=_headers_for(sponsor.id))
    assert non_admin_response.status_code == 403

    admin_response = client.get("/reviews/", headers=_headers_for(test_admin.id))
    assert admin_response.status_code == 200
    assert isinstance(admin_response.json(), list)
    assert len(admin_response.json()) >= 1


def test_get_reviews_by_deal(client, review_deal):
    deal, sponsor, _ = review_deal
    client.post(
        "/reviews/",
        headers=_headers_for(sponsor.id),
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
    response = client.get("/reviews/999999")
    assert response.status_code == 200
    assert response.json() == []
