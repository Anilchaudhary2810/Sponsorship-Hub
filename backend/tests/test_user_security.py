"""
User security and access-control tests.
"""
import pytest
from backend.auth import create_access_token
from backend.models import User

def test_user_cannot_update_role(client, test_user, auth_headers):
    """PublicUserUpdate schema has no 'role' field; role must remain unchanged."""
    response = client.put(
        f"/users/{test_user.id}",
        json={"role": "admin"},
        headers=auth_headers
    )
    assert response.status_code == 200
    assert response.json()["role"] == "sponsor"   # still sponsor


def test_user_cannot_verify_self(client, test_user, auth_headers, db):
    """is_verified is not part of PublicUserUpdate; must remain unchanged."""
    test_user.is_verified = False
    db.commit()

    response = client.put(
        f"/users/{test_user.id}",
        json={"is_verified": True},
        headers=auth_headers
    )
    assert response.status_code == 200
    assert response.json()["is_verified"] is False


def test_user_cannot_update_other_user(client, test_user, auth_headers, db):
    """A regular user cannot mutate another user's profile."""
    from backend.models import User
    other_user = User(
        full_name="Other User",
        email="other_sec@example.com",
        password="hashed",
        role="influencer",
        is_verified=True
    )
    db.add(other_user)
    db.commit()
    db.refresh(other_user)

    response = client.put(
        f"/users/{other_user.id}",
        json={"full_name": "I am a hacker"},
        headers=auth_headers
    )
    assert response.status_code == 403


def test_non_admin_cannot_list_all_users(client, auth_headers):
    """GET /users/ without a role filter requires admin; sponsors get 403."""
    response = client.get("/users/", headers=auth_headers)
    assert response.status_code == 403


def test_admin_can_list_users_with_role_filter(client, admin_auth_headers, test_user):
    """
    Admin lists users filtered by a non-admin role so every returned object
    satisfies PublicUserResponse.role Literal constraint.
    test_user has role='sponsor', so ?role=sponsor returns at least one result.
    """
    response = client.get("/users/?role=sponsor", headers=admin_auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert len(data) >= 1
    # Every returned record must have role=sponsor (matches the filter)
    for item in data:
        assert item["role"] == "sponsor"


def test_non_admin_can_list_users_by_allowed_role_filter(client, auth_headers, db):
    """
    Sponsor users can browse allowed counterparty roles (influencers).
    """
    influencer = User(
        full_name="Influencer Listing User",
        email="list_influencer@example.com",
        password="hashed",
        role="influencer",
        is_verified=True,
    )
    db.add(influencer)
    db.commit()

    response = client.get("/users/?role=influencer", headers=auth_headers)
    assert response.status_code == 200
    for item in response.json():
        assert item["role"] == "influencer"


def test_non_admin_cannot_list_disallowed_role_filter(client, auth_headers):
    """Sponsor users cannot browse same-role user listings."""
    response = client.get("/users/?role=sponsor", headers=auth_headers)
    assert response.status_code == 403


def test_non_admin_cannot_list_admin_role_filter(client, auth_headers):
    response = client.get("/users/?role=admin", headers=auth_headers)
    assert response.status_code == 403


def test_admin_invalid_role_filter_returns_400(client, admin_auth_headers):
    response = client.get("/users/?role=unknown-role", headers=admin_auth_headers)
    assert response.status_code == 400


def test_organizer_can_list_sponsors_but_not_influencers(client, db):
    organizer = User(
        full_name="Org Viewer",
        email="org_viewer@example.com",
        password="hashed",
        role="organizer",
        is_verified=True,
    )
    db.add(organizer)
    db.commit()
    db.refresh(organizer)

    organizer_headers = {"Authorization": f"Bearer {create_access_token(data={'sub': str(organizer.id)})}"}

    allowed_resp = client.get("/users/?role=sponsor", headers=organizer_headers)
    assert allowed_resp.status_code == 200

    blocked_resp = client.get("/users/?role=influencer", headers=organizer_headers)
    assert blocked_resp.status_code == 403


def test_user_can_read_own_profile(client, test_user, auth_headers):
    response = client.get(f"/users/{test_user.id}", headers=auth_headers)
    assert response.status_code == 200
    assert response.json()["email"] == test_user.email


def test_user_cannot_read_other_full_profile(client, test_user, auth_headers, test_admin):
    """Regular user cannot view another user's full profile."""
    response = client.get(f"/users/{test_admin.id}", headers=auth_headers)
    assert response.status_code == 403


def test_read_nonexistent_user(client, admin_auth_headers):
    """Requesting a user that doesn't exist returns 400 (ValidationError)."""
    response = client.get("/users/999999", headers=admin_auth_headers)
    assert response.status_code == 400


def test_update_nonexistent_user(client, admin_auth_headers):
    """Updating a user that doesn't exist returns an error."""
    response = client.put(
        "/users/999999",
        json={"full_name": "ghost"},
        headers=admin_auth_headers
    )
    # Either 400 (ValidationError from CRUD) or 403 (AuthorizationError from role check)
    assert response.status_code in (400, 403)


def test_access_protected_endpoint_without_token(client):
    """Any protected endpoint without Authorization header returns 401."""
    response = client.get("/users/1")
    assert response.status_code == 401


def test_access_protected_endpoint_with_garbage_token(client):
    """Malformed JWT returns 401."""
    response = client.get("/users/1", headers={"Authorization": "Bearer garbage.token.here"})
    assert response.status_code == 401
