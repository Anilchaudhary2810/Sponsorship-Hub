"""
Auth flow tests – covers email verification and password reset flows.
"""
import secrets
from datetime import datetime, timedelta
import importlib
from urllib.parse import parse_qs, urlparse
from backend.auth import hash_token


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
    assert user.verification_token_expires_at is None


def test_email_verification_expired_token_rejected(client, db):
    """Expired verification tokens must be rejected."""
    from backend.models import User

    token = secrets.token_urlsafe(32)
    user = User(
        full_name="Expired Verify",
        email="expired_verify@example.com",
        password="hashed",
        role="organizer",
        is_verified=False,
        verification_token=token,
        verification_token_expires_at=datetime.utcnow() - timedelta(minutes=1),
    )
    db.add(user)
    db.commit()

    response = client.get(f"/auth/verify-email?token={token}")
    assert response.status_code == 401

    db.refresh(user)
    assert user.is_verified is False
    assert user.verification_token is None
    assert user.verification_token_expires_at is None


def test_resend_verification_rotates_token_and_expiry(client, db, monkeypatch):
    """Resending verification should issue a new token and fresh expiry for unverified users."""
    from backend.models import User

    auth_router_module = importlib.import_module("backend.routers.auth_router")
    monkeypatch.setattr(auth_router_module, "_should_send_verification_email", lambda: False)

    user = User(
        full_name="Need Resend",
        email="resend_verify@example.com",
        password="hashed",
        role="sponsor",
        is_verified=False,
        verification_token="old-token",
        verification_token_expires_at=datetime.utcnow() - timedelta(hours=1),
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    old_token = user.verification_token

    response = client.post("/auth/resend-verification", json={"email": user.email})
    assert response.status_code == 200
    assert "pending verification" in response.json()["message"].lower()

    db.refresh(user)
    assert user.verification_token is not None
    assert user.verification_token != old_token
    assert user.verification_token_expires_at is not None
    assert user.verification_token_expires_at > datetime.utcnow()


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


def test_password_reset_request_sends_email_with_raw_token_link(client, db, test_user, monkeypatch):
    """Known-email reset request should wire delivery using a link with raw token."""
    auth_router_module = importlib.import_module("backend.routers.auth_router")

    captured: dict[str, str] = {}

    def _fake_send_password_reset_email(*, to_email: str, reset_link: str, expires_minutes: int = 60):
        captured["to_email"] = to_email
        captured["reset_link"] = reset_link
        captured["expires_minutes"] = str(expires_minutes)

    monkeypatch.setattr(auth_router_module, "_should_send_password_reset_email", lambda: True)
    monkeypatch.setattr(auth_router_module, "send_password_reset_email", _fake_send_password_reset_email)

    res = client.post("/auth/request-password-reset", json={"email": test_user.email})
    assert res.status_code == 200
    assert captured.get("to_email") == test_user.email
    assert "reset-password?token=" in captured.get("reset_link", "")

    token_from_link = parse_qs(urlparse(captured["reset_link"]).query).get("token", [""])[0]
    assert token_from_link

    db.refresh(test_user)
    assert test_user.reset_password_token == hash_token(token_from_link)


def test_password_reset_flow_success(client, db, test_user):
    """Full happy-path: request → reset → login with new password."""
    # 1. Request reset
    res = client.post("/auth/request-password-reset", json={"email": test_user.email})
    assert res.status_code == 200

    # Simulate email-issued raw token while DB stores only its hash.
    token = secrets.token_urlsafe(32)
    test_user.reset_password_token = hash_token(token)
    test_user.reset_password_expires_at = datetime.utcnow() + timedelta(hours=1)
    db.commit()

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
    test_user.reset_password_token = hash_token(token)
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
    token = secrets.token_urlsafe(32)
    test_user.reset_password_token = hash_token(token)
    test_user.reset_password_expires_at = datetime.utcnow() + timedelta(hours=1)
    db.commit()

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
    token = secrets.token_urlsafe(32)
    test_user.reset_password_token = hash_token(token)
    test_user.reset_password_expires_at = datetime.utcnow() + timedelta(hours=1)
    db.commit()

    client.post(
        "/auth/reset-password",
        json={"token": token, "new_password": "BrandNew987!"}
    )

    res = client.post(
        "/auth/login",
        json={"email": test_user.email, "password": old_password}
    )
    assert res.status_code == 401


def test_password_reset_rejects_stored_hash_as_token(client, db, test_user):
    """Regression: stored hash value must not be usable as reset token input."""
    raw_token = secrets.token_urlsafe(32)
    stored_hash = hash_token(raw_token)
    test_user.reset_password_token = stored_hash
    test_user.reset_password_expires_at = datetime.utcnow() + timedelta(hours=1)
    db.commit()

    res = client.post(
        "/auth/reset-password",
        json={"token": stored_hash, "new_password": "NoBypass123!"}
    )
    assert res.status_code == 400
    assert "Invalid or expired" in res.json()["message"]


def test_password_reset_token_is_single_use(client, db, test_user):
    """A reset token can only be used once."""
    token = secrets.token_urlsafe(32)
    test_user.reset_password_token = hash_token(token)
    test_user.reset_password_expires_at = datetime.utcnow() + timedelta(hours=1)
    db.commit()

    first = client.post(
        "/auth/reset-password",
        json={"token": token, "new_password": "SingleUse123!"}
    )
    assert first.status_code == 200

    second = client.post(
        "/auth/reset-password",
        json={"token": token, "new_password": "SingleUse456!"}
    )
    assert second.status_code == 400
    assert "Invalid or expired" in second.json()["message"]
