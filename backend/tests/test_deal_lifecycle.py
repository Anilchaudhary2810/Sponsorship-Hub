"""
Deal lifecycle tests – covers the deal state machine:
proposed → payment_pending → signing_pending → closed

Also covers rejection and invalid state transitions.
"""
import pytest
from backend.models import Deal
from backend.auth import create_access_token


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def lifecycle_users(db):
    """Create sponsor + organizer for lifecycle tests."""
    from backend.models import User
    from backend.crud import pwd_context

    sponsor = User(
        full_name="LC Sponsor",
        email="lc_sponsor@example.com",
        password=pwd_context.hash("Password123"),
        role="sponsor",
        is_verified=True
    )
    organizer = User(
        full_name="LC Organizer",
        email="lc_org@example.com",
        password=pwd_context.hash("Password123"),
        role="organizer",
        is_verified=True
    )
    db.add_all([sponsor, organizer])
    db.commit()
    db.refresh(sponsor)
    db.refresh(organizer)
    return sponsor, organizer


@pytest.fixture
def lc_sponsor_headers(lifecycle_users):
    sponsor, _ = lifecycle_users
    token = create_access_token({"sub": str(sponsor.id)})
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def lc_organizer_headers(lifecycle_users):
    _, organizer = lifecycle_users
    token = create_access_token({"sub": str(organizer.id)})
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def proposed_deal(db, lifecycle_users):
    """Manually insert a proposed deal (sponsor_accepted=True) for lifecycle tests."""
    sponsor, organizer = lifecycle_users
    deal = Deal(
        sponsor_id=sponsor.id,
        organizer_id=organizer.id,
        deal_type="sponsorship",
        status="proposed",
        payment_amount=1000,
        currency="INR",
        sponsor_accepted=True   # sponsor initiated → auto-accepted
    )
    db.add(deal)
    db.commit()
    db.refresh(deal)
    return deal


@pytest.fixture
def payment_pending_deal(db, lifecycle_users):
    """A deal both parties have accepted (in payment_pending state)."""
    sponsor, organizer = lifecycle_users
    deal = Deal(
        sponsor_id=sponsor.id,
        organizer_id=organizer.id,
        deal_type="sponsorship",
        status="payment_pending",
        payment_amount=1000,
        currency="INR",
        sponsor_accepted=True,
        organizer_accepted=True,
    )
    db.add(deal)
    db.commit()
    db.refresh(deal)
    return deal


@pytest.fixture
def signing_pending_deal(db, lifecycle_users):
    """A deal that has been paid and is awaiting signatures."""
    from datetime import datetime
    sponsor, organizer = lifecycle_users
    deal = Deal(
        sponsor_id=sponsor.id,
        organizer_id=organizer.id,
        deal_type="sponsorship",
        status="signing_pending",
        payment_amount=1000,
        currency="INR",
        sponsor_accepted=True,
        organizer_accepted=True,
        payment_done=True,
        payment_timestamp=datetime.utcnow(),
        razorpay_payment_id="pi_sign_test",
    )
    db.add(deal)
    db.commit()
    db.refresh(deal)
    return deal


# ---------------------------------------------------------------------------
# Accept
# ---------------------------------------------------------------------------

def test_organizer_accepts_moves_to_payment_pending(client, proposed_deal, lc_organizer_headers):
    """When both sides accept, deal transitions to payment_pending."""
    res = client.put(
        f"/deals/{proposed_deal.id}/accept",
        json={"role": "organizer", "accept": True},
        headers=lc_organizer_headers
    )
    assert res.status_code == 200
    assert res.json()["status"] == "payment_pending"
    assert res.json()["organizer_accepted"] is True


def test_deal_rejection_moves_to_rejected(client, proposed_deal, lc_organizer_headers):
    """Organizer rejecting a deal moves it to 'rejected'."""
    res = client.put(
        f"/deals/{proposed_deal.id}/accept",
        json={"role": "organizer", "accept": False},
        headers=lc_organizer_headers
    )
    assert res.status_code == 200
    assert res.json()["status"] == "rejected"


def test_accept_role_mismatch_rejected(client, proposed_deal, lc_organizer_headers):
    """Organizer cannot accept as sponsor (role mismatch)."""
    res = client.put(
        f"/deals/{proposed_deal.id}/accept",
        json={"role": "sponsor", "accept": True},
        headers=lc_organizer_headers
    )
    assert res.status_code == 403
    assert "Role mismatch" in res.json()["message"]


def test_accept_not_participant(client, proposed_deal, db):
    """A user not part of the deal cannot accept it."""
    from backend.models import User
    from backend.crud import pwd_context
    outsider = User(
        full_name="Outsider",
        email="outsider_lc@example.com",
        password=pwd_context.hash("Password123"),
        role="organizer",
        is_verified=True
    )
    db.add(outsider)
    db.commit()
    db.refresh(outsider)
    token = create_access_token({"sub": str(outsider.id)})
    headers = {"Authorization": f"Bearer {token}"}

    res = client.put(
        f"/deals/{proposed_deal.id}/accept",
        json={"role": "organizer", "accept": True},
        headers=headers
    )
    assert res.status_code == 403


def test_accept_deal_not_found(client, lc_sponsor_headers):
    res = client.put(
        "/deals/999999/accept",
        json={"role": "sponsor", "accept": True},
        headers=lc_sponsor_headers
    )
    assert res.status_code == 400


def test_accept_deal_wrong_state(client, payment_pending_deal, lc_organizer_headers):
    """Cannot accept a deal that's already in payment_pending."""
    res = client.put(
        f"/deals/{payment_pending_deal.id}/accept",
        json={"role": "organizer", "accept": True},
        headers=lc_organizer_headers
    )
    assert res.status_code == 400


def test_accept_unauthenticated(client, proposed_deal):
    res = client.put(
        f"/deals/{proposed_deal.id}/accept",
        json={"role": "organizer", "accept": True}
    )
    assert res.status_code == 401


# ---------------------------------------------------------------------------
# Sign
# ---------------------------------------------------------------------------

def test_sponsor_sign(client, signing_pending_deal, lc_sponsor_headers):
    """Sponsor can sign a deal in signing_pending state."""
    res = client.put(
        f"/deals/{signing_pending_deal.id}/sign",
        json={"role": "sponsor", "signature": "SponsorSig"},
        headers=lc_sponsor_headers
    )
    assert res.status_code == 200
    assert res.json()["sponsor_signed"] is True


def test_both_sign_closes_deal(client, signing_pending_deal, lc_sponsor_headers, lc_organizer_headers):
    """When both sponsor and organizer sign, deal closes."""
    # Sponsor signs
    client.put(
        f"/deals/{signing_pending_deal.id}/sign",
        json={"role": "sponsor", "signature": "SpSig"},
        headers=lc_sponsor_headers
    )
    # Organizer signs  
    res = client.put(
        f"/deals/{signing_pending_deal.id}/sign",
        json={"role": "organizer", "signature": "OrgSig"},
        headers=lc_organizer_headers
    )
    assert res.status_code == 200
    assert res.json()["status"] == "closed"


def test_skip_acceptance_sign_fails(client, proposed_deal, lc_sponsor_headers):
    """Cannot sign a deal that's still in proposed state."""
    res = client.put(
        f"/deals/{proposed_deal.id}/sign",
        json={"role": "sponsor", "signature": "early_sig"},
        headers=lc_sponsor_headers
    )
    assert res.status_code == 400
    msg = res.json()["message"].lower()
    assert "invalid" in msg or "proposed" in msg


def test_sign_role_mismatch(client, signing_pending_deal, lc_organizer_headers):
    """Organizer cannot sign as sponsor."""
    res = client.put(
        f"/deals/{signing_pending_deal.id}/sign",
        json={"role": "sponsor", "signature": "OrgFakeSig"},
        headers=lc_organizer_headers
    )
    assert res.status_code == 403


def test_sign_not_participant(client, signing_pending_deal, db):
    """A user not in the deal cannot sign."""
    from backend.models import User
    from backend.crud import pwd_context
    outsider = User(
        full_name="Outsider Signer",
        email="outsider_sign@example.com",
        password=pwd_context.hash("Password123"),
        role="sponsor",
        is_verified=True
    )
    db.add(outsider)
    db.commit()
    db.refresh(outsider)
    token = create_access_token({"sub": str(outsider.id)})
    headers = {"Authorization": f"Bearer {token}"}

    res = client.put(
        f"/deals/{signing_pending_deal.id}/sign",
        json={"role": "sponsor", "signature": "outsider"},
        headers=headers
    )
    assert res.status_code == 403


def test_sign_deal_not_found(client, lc_sponsor_headers):
    res = client.put(
        "/deals/999999/sign",
        json={"role": "sponsor", "signature": "ghost"},
        headers=lc_sponsor_headers
    )
    assert res.status_code == 400


def test_sign_unauthenticated(client, signing_pending_deal):
    res = client.put(
        f"/deals/{signing_pending_deal.id}/sign",
        json={"role": "sponsor", "signature": "unsigned"}
    )
    assert res.status_code == 401


# ---------------------------------------------------------------------------
# Mass-assignment guard
# ---------------------------------------------------------------------------

def test_invalid_status_injection(client, proposed_deal, lc_sponsor_headers):
    """PUT /deals/{id} cannot change status (only proof_of_work is allowed)."""
    response = client.put(
        f"/deals/{proposed_deal.id}",
        json={"status": "closed"},
        headers=lc_sponsor_headers
    )
    assert response.status_code == 200
    assert response.json()["status"] == "proposed"   # unchanged
