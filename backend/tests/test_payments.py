"""
Payment tests – covers /payments endpoints with Razorpay (Mocked).
"""
import pytest
from unittest.mock import MagicMock
from datetime import datetime
import hashlib
import hmac

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def payment_deal(db):
    """Create a deal in 'payment_pending' state for payment testing."""
    from backend.models import User, Deal
    from backend.crud import pwd_context

    sponsor = User(
        full_name="Pay Sponsor",
        email="pay_sponsor@example.com",
        password=pwd_context.hash("Password123"),
        role="sponsor",
        is_verified=True,
    )
    organizer = User(
        full_name="Pay Organizer",
        email="pay_org@example.com",
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
        status="payment_pending",
        payment_amount=1500,
        currency="INR",
        sponsor_accepted=True,
        organizer_accepted=True,
    )
    db.add(deal)
    db.commit()
    db.refresh(deal)
    return deal, sponsor, organizer


@pytest.fixture
def sponsor_pay_headers(payment_deal):
    from backend.auth import create_access_token
    deal, sponsor, _ = payment_deal
    token = create_access_token({"sub": str(sponsor.id)})
    return {"Authorization": f"Bearer {token}"}

@pytest.fixture
def organizer_pay_headers(payment_deal):
    from backend.auth import create_access_token
    deal, _, organizer = payment_deal
    token = create_access_token({"sub": str(organizer.id)})
    return {"Authorization": f"Bearer {token}"}


# ---------------------------------------------------------------------------
# Create Razorpay Order
# ---------------------------------------------------------------------------

def test_create_razorpay_order_success(client, payment_deal, sponsor_pay_headers):
    deal, _, _ = payment_deal
    response = client.post(
        f"/payments/create-order?deal_id={deal.id}",
        headers=sponsor_pay_headers
    )
    assert response.status_code == 200
    data = response.json()
    assert "order_" in data["razorpay_payment_id"]
    assert data["payment_status"] == "created"


def test_create_order_does_not_settle_without_webhook(client, payment_deal, sponsor_pay_headers, db):
    deal, _, _ = payment_deal
    response = client.post(
        f"/payments/create-order?deal_id={deal.id}",
        headers=sponsor_pay_headers
    )
    assert response.status_code == 200

    db.refresh(deal)
    assert deal.payment_done is False
    assert deal.status == "payment_pending"


def test_create_razorpay_order_not_sponsor(client, payment_deal, organizer_pay_headers):
    """Only the sponsor of the deal can initiate payment order."""
    deal, _, _ = payment_deal
    response = client.post(
        f"/payments/create-order?deal_id={deal.id}",
        headers=organizer_pay_headers
    )
    assert response.status_code == 403


def test_create_razorpay_order_already_paid(client, payment_deal, sponsor_pay_headers, db):
    """If the deal is already paid, a second order attempt is rejected."""
    deal, _, _ = payment_deal
    deal.payment_done = True
    db.commit()

    response = client.post(
        f"/payments/create-order?deal_id={deal.id}",
        headers=sponsor_pay_headers
    )
    assert response.status_code == 400
    assert "already paid" in response.json()["message"].lower()


def test_checkout_config_returns_public_key(client, sponsor_pay_headers, monkeypatch):
    from backend.config import settings

    monkeypatch.setattr(settings, "RAZORPAY_KEY_ID", "rzp_test_public_123")
    response = client.get("/payments/checkout-config", headers=sponsor_pay_headers)

    assert response.status_code == 200
    body = response.json()
    assert body["provider"] == "razorpay"
    assert body["key_id"] == "rzp_test_public_123"
    assert "secret" not in "".join(body.keys()).lower()


# ---------------------------------------------------------------------------
# Razorpay Webhook
# ---------------------------------------------------------------------------

def test_razorpay_webhook_paid(client, payment_deal, db):
    deal, _, _ = payment_deal
    
    # Mocking order.paid event from Razorpay
    webhook_data = {
        "event": "order.paid",
        "payload": {
            "order": {
                "entity": {
                    "id": "order_test_123",
                    "status": "paid",
                    "notes": {"deal_id": str(deal.id)}
                }
            }
        }
    }
    
    response = client.post(
        "/payments/webhook",
        headers={"X-Razorpay-Signature": "mocked"},
        json=webhook_data
    )
    assert response.status_code == 200
    assert response.json()["status"] == "success"

    db.refresh(deal)
    assert deal.status == "signing_pending"
    assert deal.payment_done is True


def test_razorpay_webhook_failed(client, payment_deal, db):
    deal, _, _ = payment_deal
    
    webhook_data = {
        "event": "order.failed",
        "payload": {
            "order": {
                "entity": {
                    "id": "order_fail_123",
                    "status": "failed",
                    "notes": {"deal_id": str(deal.id)}
                }
            }
        }
    }
    
    response = client.post(
        "/payments/webhook",
        headers={"X-Razorpay-Signature": "mocked"},
        json=webhook_data
    )
    assert response.status_code == 200
    db.refresh(deal)
    assert deal.payment_done is False


def test_razorpay_webhook_ignores_payload_amount_tampering(client, payment_deal, db):
    deal, _, _ = payment_deal
    original_amount = float(deal.payment_amount)

    webhook_data = {
        "event": "order.paid",
        "payload": {
            "order": {
                "entity": {
                    "id": "order_tampered_amount",
                    "status": "paid",
                    "amount": 1,
                    "notes": {"deal_id": str(deal.id)},
                }
            }
        }
    }

    response = client.post(
        "/payments/webhook",
        headers={"X-Razorpay-Signature": "mocked"},
        json=webhook_data
    )
    assert response.status_code == 200
    db.refresh(deal)
    assert float(deal.payment_amount) == original_amount
    assert deal.payment_done is True


def test_payment_captured_webhook_maps_deal_by_order_id(client, payment_deal, sponsor_pay_headers, db):
    deal, _, _ = payment_deal
    create_response = client.post(
        f"/payments/create-order?deal_id={deal.id}",
        headers=sponsor_pay_headers
    )
    assert create_response.status_code == 200
    order_id = create_response.json()["razorpay_payment_id"]

    webhook_data = {
        "event": "payment.captured",
        "payload": {
            "payment": {
                "entity": {
                    "id": "pay_test_captured_001",
                    "order_id": order_id,
                    "status": "captured",
                }
            }
        }
    }

    response = client.post(
        "/payments/webhook",
        headers={"X-Razorpay-Signature": "mocked"},
        json=webhook_data
    )
    assert response.status_code == 200

    db.refresh(deal)
    assert deal.payment_done is True
    assert deal.status == "signing_pending"
    assert deal.razorpay_payment_id == order_id


def test_verify_payment_updates_deal_state(client, payment_deal, sponsor_pay_headers, monkeypatch, db):
    from backend.config import settings

    deal, _, _ = payment_deal
    # Force mocked local order path for deterministic tests (no live Razorpay auth).
    monkeypatch.setattr(settings, "RAZORPAY_KEY_ID", None)
    monkeypatch.setattr(settings, "RAZORPAY_KEY_SECRET", None)

    create_response = client.post(
        f"/payments/create-order?deal_id={deal.id}",
        headers=sponsor_pay_headers
    )
    assert create_response.status_code == 200
    order_id = create_response.json()["razorpay_payment_id"]

    payment_id = "pay_test_001"
    monkeypatch.setattr(settings, "RAZORPAY_KEY_SECRET", "test_secret_123")
    signature = hmac.new(
        b"test_secret_123",
        f"{order_id}|{payment_id}".encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()

    verify_response = client.post(
        "/payments/verify",
        headers=sponsor_pay_headers,
        json={
            "deal_id": deal.id,
            "razorpay_order_id": order_id,
            "razorpay_payment_id": payment_id,
            "razorpay_signature": signature,
        },
    )
    assert verify_response.status_code == 200

    db.refresh(deal)
    assert deal.payment_done is True
    assert deal.status == "signing_pending"


def test_verify_payment_rejects_invalid_signature(client, payment_deal, sponsor_pay_headers, monkeypatch):
    from backend.config import settings

    deal, _, _ = payment_deal
    # Force mocked local order path for deterministic tests (no live Razorpay auth).
    monkeypatch.setattr(settings, "RAZORPAY_KEY_ID", None)
    monkeypatch.setattr(settings, "RAZORPAY_KEY_SECRET", None)

    create_response = client.post(
        f"/payments/create-order?deal_id={deal.id}",
        headers=sponsor_pay_headers
    )
    assert create_response.status_code == 200
    order_id = create_response.json()["razorpay_payment_id"]

    monkeypatch.setattr(settings, "RAZORPAY_KEY_SECRET", "test_secret_123")
    verify_response = client.post(
        "/payments/verify",
        headers=sponsor_pay_headers,
        json={
            "deal_id": deal.id,
            "razorpay_order_id": order_id,
            "razorpay_payment_id": "pay_test_001",
            "razorpay_signature": "invalid",
        },
    )
    assert verify_response.status_code == 400
