"""
Rate-limit tests.

The global conftest disables rate-limiting for all tests via an autouse fixture.
To test rate-limiting specifically, we must re-enable the limiter for these tests.
"""
import pytest


def test_login_rate_limiting(client, test_user):
    """After 5 failed attempts, the 6th should be rate-limited (HTTP 429)."""
    from backend.core.limiter import limiter

    # Re-enable the rate limiter for this specific test only
    limiter.enabled = True
    try:
        for _ in range(5):
            client.post(
                "/auth/login",
                json={"email": test_user.email, "password": "WrongPassword"}
            )

        # 6th attempt must be blocked
        response = client.post(
            "/auth/login",
            json={"email": test_user.email, "password": "WrongPassword"}
        )
        assert response.status_code == 429
    finally:
        limiter.enabled = False  # Always restore, even on failure
