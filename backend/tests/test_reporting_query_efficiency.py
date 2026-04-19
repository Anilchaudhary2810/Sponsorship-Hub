from sqlalchemy import event

from backend.models import Campaign, Deal, Event, User
from backend.crud import pwd_context
from backend.routers.reporting import _campaign_outcome_rows


def _count_select_queries(db, call):
    connection = db.connection()
    select_count = 0

    def _before_cursor_execute(conn, cursor, statement, parameters, context, executemany):
        del conn, cursor, parameters, context, executemany
        normalized = statement.lstrip().upper()
        if normalized.startswith("SELECT") or normalized.startswith("WITH"):
            nonlocal select_count
            select_count += 1

    event.listen(connection, "before_cursor_execute", _before_cursor_execute)
    try:
        call()
    finally:
        event.remove(connection, "before_cursor_execute", _before_cursor_execute)
    return select_count


def _create_user(db, *, email: str, role: str, name: str):
    user = User(
        full_name=name,
        email=email,
        password=pwd_context.hash("Password123"),
        role=role,
        is_verified=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def _seed_sponsor_campaigns(db, sponsor_id: int, organizer_id: int, count: int, offset: int = 0) -> None:
    for i in range(offset, offset + count):
        campaign = Campaign(
            creator_id=sponsor_id,
            title=f"Campaign {i}",
            status="open",
            budget=1000 + i,
            platform_required="Instagram",
            deliverables="1 Reel",
        )
        db.add(campaign)
        db.flush()

        db.add(
            Deal(
                sponsor_id=sponsor_id,
                organizer_id=organizer_id,
                campaign_id=campaign.id,
                deal_type="promotion",
                status="closed",
                payment_amount=1000 + i,
                payment_done=True,
            )
        )
        db.add(
            Deal(
                sponsor_id=sponsor_id,
                organizer_id=organizer_id,
                campaign_id=campaign.id,
                deal_type="promotion",
                status="proposed",
                payment_amount=900 + i,
                payment_done=False,
            )
        )
    db.commit()


def _seed_organizer_events(db, organizer_id: int, sponsor_id: int, count: int, offset: int = 0) -> None:
    for i in range(offset, offset + count):
        event_row = Event(
            organizer_id=organizer_id,
            title=f"Event {i}",
            city="surat",
            state="Gujarat",
            raw_budget=5000 + i,
            currency="INR",
        )
        db.add(event_row)
        db.flush()

        db.add(
            Deal(
                sponsor_id=sponsor_id,
                organizer_id=organizer_id,
                event_id=event_row.id,
                deal_type="sponsorship",
                status="closed",
                payment_amount=5000 + i,
                payment_done=True,
            )
        )
        db.add(
            Deal(
                sponsor_id=sponsor_id,
                organizer_id=organizer_id,
                event_id=event_row.id,
                deal_type="sponsorship",
                status="proposed",
                payment_amount=4500 + i,
                payment_done=False,
            )
        )
    db.commit()


def test_campaign_outcome_query_count_constant_for_sponsor(db):
    sponsor = _create_user(db, email="report_sponsor@example.com", role="sponsor", name="Report Sponsor")
    organizer = _create_user(db, email="report_org@example.com", role="organizer", name="Report Organizer")

    _seed_sponsor_campaigns(db, sponsor_id=sponsor.id, organizer_id=organizer.id, count=3)
    sponsor_ctx = db.query(User).filter(User.id == sponsor.id).first()
    assert sponsor_ctx is not None

    small_count = _count_select_queries(db, lambda: _campaign_outcome_rows(db, sponsor_ctx))
    small_rows = _campaign_outcome_rows(db, sponsor_ctx)
    assert len(small_rows) == 3

    _seed_sponsor_campaigns(db, sponsor_id=sponsor.id, organizer_id=organizer.id, count=60, offset=3)
    sponsor_ctx = db.query(User).filter(User.id == sponsor.id).first()
    assert sponsor_ctx is not None

    large_count = _count_select_queries(db, lambda: _campaign_outcome_rows(db, sponsor_ctx))
    large_rows = _campaign_outcome_rows(db, sponsor_ctx)
    assert len(large_rows) == 63

    assert small_count == large_count
    assert large_count <= 1


def test_campaign_outcome_query_count_constant_for_organizer(db):
    sponsor = _create_user(db, email="event_sponsor@example.com", role="sponsor", name="Event Sponsor")
    organizer = _create_user(db, email="event_org@example.com", role="organizer", name="Event Organizer")

    _seed_organizer_events(db, organizer_id=organizer.id, sponsor_id=sponsor.id, count=4)
    organizer_ctx = db.query(User).filter(User.id == organizer.id).first()
    assert organizer_ctx is not None

    small_count = _count_select_queries(db, lambda: _campaign_outcome_rows(db, organizer_ctx))
    small_rows = _campaign_outcome_rows(db, organizer_ctx)
    assert len(small_rows) == 4

    _seed_organizer_events(db, organizer_id=organizer.id, sponsor_id=sponsor.id, count=70, offset=4)
    organizer_ctx = db.query(User).filter(User.id == organizer.id).first()
    assert organizer_ctx is not None

    large_count = _count_select_queries(db, lambda: _campaign_outcome_rows(db, organizer_ctx))
    large_rows = _campaign_outcome_rows(db, organizer_ctx)
    assert len(large_rows) == 74

    assert small_count == large_count
    assert large_count <= 1
