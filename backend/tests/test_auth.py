"""
Auth endpoint tests – covers register, login, logout, token refresh, and edge-cases.

Fix applied: test_register_success now checks the actual TokenResponse shape
(access_token + user.email) rather than a "message" key that was never returned.
"""
import pytest
from backend.crud import pwd_context


# ---------------------------------------------------------------------------
# Registration
# ---------------------------------------------------------------------------

def test_register_success(client):
    """Happy-path registration returns 201 + a bearer token and user object."""
    response = client.post(
        "/auth/register",
        json={
            "full_name": "New User",
            "email": "newuser_unique@example.com",
            "password": "Password123",
            "role": "influencer"
        }
    )
    assert response.status_code == 201
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"
    assert data["user"]["email"] == "newuser_unique@example.com"


def test_register_duplicate_email(client, test_user):
    """Registering with an already-used e-mail returns 400."""
    response = client.post(
        "/auth/register",
        json={
            "full_name": "New User",
            "email": test_user.email,
            "password": "Password123",
            "role": "influencer"
        }
    )
    assert response.status_code == 400
    assert "Email already registered" in response.json()["message"]


def test_register_weak_password_too_short(client):
    """Password shorter than 8 chars is rejected by Pydantic validator."""
    response = client.post(
        "/auth/register",
        json={
            "full_name": "Bad Pass User",
            "email": "badpass1@example.com",
            "password": "Ab1",
            "role": "sponsor"
        }
    )
    assert response.status_code == 422  # Pydantic validation error


def test_register_weak_password_no_digit(client):
    """Password without a digit is rejected."""
    response = client.post(
        "/auth/register",
        json={
            "full_name": "Bad Pass User",
            "email": "badpass2@example.com",
            "password": "NoDigitHere",
            "role": "sponsor"
        }
    )
    assert response.status_code == 422


def test_register_weak_password_no_uppercase(client):
    """Password without an uppercase letter is rejected."""
    response = client.post(
        "/auth/register",
        json={
            "full_name": "Bad Pass User",
            "email": "badpass3@example.com",
            "password": "nouppercase1",
            "role": "sponsor"
        }
    )
    assert response.status_code == 422


def test_register_invalid_role(client):
    """Unknown role value is rejected."""
    response = client.post(
        "/auth/register",
        json={
            "full_name": "Bad Role User",
            "email": "badrole@example.com",
            "password": "Password123",
            "role": "superadmin"   # not in Literal values
        }
    )
    assert response.status_code == 422


def test_register_missing_required_fields(client):
    """Omitting required fields (e.g. email) returns 422."""
    response = client.post(
        "/auth/register",
        json={
            "password": "Password123",
            "role": "sponsor"
            # full_name and email missing
        }
    )
    assert response.status_code == 422


def test_register_invalid_email_format(client):
    """Malformed e-mail address is rejected by Pydantic EmailStr."""
    response = client.post(
        "/auth/register",
        json={
            "full_name": "Bad Email",
            "email": "not-an-email",
            "password": "Password123",
            "role": "sponsor"
        }
    )
    assert response.status_code == 422


# ---------------------------------------------------------------------------
# Login
# ---------------------------------------------------------------------------

def test_login_success(client, test_user):
    response = client.post(
        "/auth/login",
        json={"email": test_user.email, "password": "Password123"}
    )
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert "refresh_token" in data
    assert data["user"]["email"] == test_user.email


def test_login_invalid_password(client, test_user):
    response = client.post(
        "/auth/login",
        json={"email": test_user.email, "password": "WrongPassword"}
    )
    assert response.status_code == 401
    assert "Invalid email or password" in response.json()["message"]


def test_login_nonexistent_email(client):
    """Login with an e-mail that was never registered returns 401."""
    response = client.post(
        "/auth/login",
        json={"email": "ghost@nowhere.com", "password": "Password123"}
    )
    assert response.status_code == 401


def test_login_unverified(client, db):
    """Unverified account is rejected on login."""
    from backend.models import User
    user = User(
        full_name="Unverified User",
        email="unverified_auth@example.com",
        password=pwd_context.hash("Password123"),
        role="sponsor",
        is_verified=False
    )
    db.add(user)
    db.commit()

    response = client.post(
        "/auth/login",
        json={"email": "unverified_auth@example.com", "password": "Password123"}
    )
    assert response.status_code == 401
    assert "verify your email" in response.json()["message"]


def test_login_missing_fields(client):
    """Login payload missing password returns 422."""
    response = client.post("/auth/login", json={"email": "test@example.com"})
    assert response.status_code == 422


# ---------------------------------------------------------------------------
# Token Refresh
# ---------------------------------------------------------------------------

def test_token_refresh(client, test_user):
    login_res = client.post(
        "/auth/login",
        json={"email": test_user.email, "password": "Password123"}
    )
    refresh_token = login_res.json()["refresh_token"]

    response = client.post("/auth/refresh", json={"refresh_token": refresh_token})
    assert response.status_code == 200
    assert "access_token" in response.json()


def test_token_refresh_invalid_token(client):
    """Garbage refresh token returns 401."""
    response = client.post("/auth/refresh", json={"refresh_token": "garbage.trash.junk"})
    assert response.status_code == 401


def test_token_refresh_missing_field(client):
    """Empty body for refresh returns 422."""
    response = client.post("/auth/refresh", json={})
    assert response.status_code == 422


# ---------------------------------------------------------------------------
# Logout
# ---------------------------------------------------------------------------

def test_logout(client, test_user, auth_headers):
    response = client.post("/auth/logout", headers=auth_headers)
    assert response.status_code == 200
    assert "logged out" in response.json()["message"].lower()


def test_logout_unauthenticated(client):
    """Calling logout without a token returns 401."""
    response = client.post("/auth/logout")
    assert response.status_code == 401


def test_logout_invalidates_refresh_token(client, test_user, db):
    """After logout, refresh token stored in DB should be cleared."""
    login_res = client.post(
        "/auth/login",
        json={"email": test_user.email, "password": "Password123"}
    )
    token_before = login_res.json()["access_token"]
    headers = {"Authorization": f"Bearer {token_before}"}

    client.post("/auth/logout", headers=headers)
    db.refresh(test_user)
    assert test_user.refresh_token is None
