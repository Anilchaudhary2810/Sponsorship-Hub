"""
Auth flow tests – covers email verification and password reset flows.
"""
import pytest
import secrets
from datetime import datetime, timedelta


# ---------------------------------------------------------------------------
# Email Verification
# ---------------------------------------------------------------------------

def test_email_verification_success(client, db):
    from backend.models import User
    token = secrets.token_urlsafe(32)
    user = User(
        full_name="Verify Me",
        email="verify_flows@example.com",
        password="hashed",
        role="sponsor",
        is_verified=False,
        verification_token=token
    )
    db.add(user)
    db.commit()

    response = client.get(f"/auth/verify-email?token={token}")
    assert response.status_code == 200
    assert "verified successfully" in response.json()["message"]


def test_email_verification_invalid_token(client):
    response = client.get("/auth/verify-email?token=wrong_token_does_not_exist")
    assert response.status_code == 401


def test_email_verification_sets_is_verified(client, db):
    """After successful verification, is_verified must be True in the DB."""
    from backend.models import User
    token = secrets.token_urlsafe(32)
    user = User(
        full_name="Needs Verify",
        email="needsverify@example.com",
        password="hashed",
        role="organizer",
        is_verified=False,
        verification_token=token
    )
    db.add(user)
    db.commit()

    client.get(f"/auth/verify-email?token={token}")
    db.refresh(user)
    assert user.is_verified is True
    assert user.verification_token is None  # token should be cleared


# ---------------------------------------------------------------------------
# Password Reset
# ---------------------------------------------------------------------------

def test_password_reset_request_known_email(client, test_user):
    """Request for a valid email returns 200 (regardless of whether email was sent)."""
    res = client.post("/auth/request-password-reset", json={"email": test_user.email})
    assert res.status_code == 200
    assert "reset link" in res.json()["message"].lower() or "sent" in res.json()["message"].lower()


def test_password_reset_request_unknown_email(client):
    """Request for an unknown email still returns 200 (user enumeration prevention)."""
    res = client.post("/auth/request-password-reset", json={"email": "nobody@ghost.com"})
    assert res.status_code == 200


def test_password_reset_request_invalid_email_format(client):
    """Malformed email returns 422 from Pydantic."""
    res = client.post("/auth/request-password-reset", json={"email": "not-an-email"})
    assert res.status_code == 422


def test_password_reset_flow_success(client, db, test_user):
    """Full happy-path: request → reset → login with new password."""
    # 1. Request reset
    res = client.post("/auth/request-password-reset", json={"email": test_user.email})
    assert res.status_code == 200

    # Retrieve token from DB (simulating email receipt)
    db.refresh(test_user)
    token = test_user.reset_password_token
    assert token is not None

    # 2. Reset password
    res = client.post(
        "/auth/reset-password",
        json={"token": token, "new_password": "NewPassword456!"}
    )
    assert res.status_code == 200
    assert "successful" in res.json()["message"].lower()

    # 3. Login with new password
    res = client.post(
        "/auth/login",
        json={"email": test_user.email, "password": "NewPassword456!"}
    )
    assert res.status_code == 200


def test_password_reset_invalid_token(client):
    """Garbage reset token returns 400."""
    res = client.post(
        "/auth/reset-password",
        json={"token": "invalid_garbage_token", "new_password": "NewPass789!"}
    )
    assert res.status_code == 400
    assert "Invalid or expired" in res.json()["message"]


def test_expired_password_reset_token(client, db, test_user):
    """An expired reset token is rejected."""
    token = secrets.token_urlsafe(32)
    test_user.reset_password_token = token
    test_user.reset_password_expires_at = datetime.utcnow() - timedelta(minutes=1)
    db.commit()

    res = client.post(
        "/auth/reset-password",
        json={"token": token, "new_password": "NewPass789!"}
    )
    assert res.status_code == 400
    assert "Invalid or expired" in res.json()["message"]


def test_password_reset_clears_token(client, db, test_user):
    """After a successful reset, the reset token is cleared from the DB."""
    client.post("/auth/request-password-reset", json={"email": test_user.email})
    db.refresh(test_user)
    token = test_user.reset_password_token

    client.post(
        "/auth/reset-password",
        json={"token": token, "new_password": "Cleared123!"}
    )
    db.refresh(test_user)
    assert test_user.reset_password_token is None
    assert test_user.reset_password_expires_at is None


def test_password_reset_old_password_rejected_after_reset(client, db, test_user):
    """After a reset, the old password no longer works."""
    old_password = "Password123"
    client.post("/auth/request-password-reset", json={"email": test_user.email})
    db.refresh(test_user)
    token = test_user.reset_password_token

    client.post(
        "/auth/reset-password",
        json={"token": token, "new_password": "BrandNew987!"}
    )

    res = client.post(
        "/auth/login",
        json={"email": test_user.email, "password": old_password}
    )
    assert res.status_code == 401
