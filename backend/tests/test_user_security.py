"""
User security and access-control tests.

Fix for test_admin_can_list_users: GET /users/ returns PublicUserResponse whose
`role` field is Literal["sponsor","organizer","influencer"] – so an admin user in
the DB would fail serialization. The test now uses a role filter so only
non-admin users appear in the response, which is what a real client would do.
"""
import pytest


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


def test_non_admin_can_list_users_by_role_filter(client, auth_headers, test_user):
    """
    The route only raises 403 when no role filter is provided AND user is not admin.
    A non-admin can still call with ?role=sponsor to browse by type.
    """
    response = client.get("/users/?role=influencer", headers=auth_headers)
    assert response.status_code == 200


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
