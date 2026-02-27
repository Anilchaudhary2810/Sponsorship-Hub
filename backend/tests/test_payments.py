"""
Payment tests – covers /payments endpoints with Razorpay (Mocked).
"""
import pytest
from unittest.mock import MagicMock
from datetime import datetime

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
