from __future__ import annotations

from datetime import date as date_cls
from datetime import datetime, timedelta
from typing import Any

from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from .. import exceptions, models, schemas
from ..core.limiter import limiter
from ..database import get_db
from .auth_router import get_current_user

router = APIRouter(prefix="/retention", tags=["Retention Engine"])


def _as_int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _as_str(value: Any, default: str = "") -> str:
    if isinstance(value, str):
        return value
    return default


def _upsert_nudge(
    db: Session,
    user_id: int,
    nudge_type: str,
    title: str,
    message: str,
    payload: dict[str, Any],
    due_at: datetime | None = None,
) -> None:
    dedupe_key = str(payload.get("dedupe_key", ""))
    existing = db.query(models.LifecycleNudge).filter(
        models.LifecycleNudge.user_id == user_id,
        models.LifecycleNudge.nudge_type == nudge_type,
        models.LifecycleNudge.state.in_(["pending", "sent"]),
    ).all()
    for row in existing:
        row_payload = getattr(row, "payload", {}) or {}
        if str(row_payload.get("dedupe_key", "")) == dedupe_key:
            return

    nudge = models.LifecycleNudge(
        user_id=user_id,
        nudge_type=nudge_type,
        title=title,
        message=message,
        state="pending",
        due_at=due_at,
        payload=payload,
    )
    db.add(nudge)


def _generate_for_user(db: Session, user: models.User) -> dict[str, int]:
    user_id = _as_int(getattr(user, "id", 0))
    role = _as_str(getattr(user, "role", "")).lower()
    now = datetime.utcnow()
    created = 0

    # Pending signatures
    if role == "sponsor":
        pending_signature_deals = db.query(models.Deal).filter(
            models.Deal.sponsor_id == user_id,
            models.Deal.payment_done == True,
            models.Deal.sponsor_signed == False,
            models.Deal.status.in_(["signing_pending", "payment_pending"]),
        ).all()
    elif role == "organizer":
        pending_signature_deals = db.query(models.Deal).filter(
            models.Deal.organizer_id == user_id,
            models.Deal.payment_done == True,
            models.Deal.organizer_signed == False,
            models.Deal.status.in_(["signing_pending", "payment_pending"]),
        ).all()
    else:
        pending_signature_deals = db.query(models.Deal).filter(
            models.Deal.influencer_id == user_id,
            models.Deal.payment_done == True,
            models.Deal.influencer_signed == False,
            models.Deal.status.in_(["signing_pending", "payment_pending"]),
        ).all()

    for deal in pending_signature_deals:
        _upsert_nudge(
            db,
            user_id=user_id,
            nudge_type="pending_signature",
            title="Signature pending",
            message=f"Deal #{deal.id} is paid and waiting for your signature.",
            payload={"deal_id": deal.id, "dedupe_key": f"pending_signature:{deal.id}"},
            due_at=now + timedelta(days=1),
        )
        created += 1

    # Expiring deals (events within 7 days, not closed)
    soon = now.date() + timedelta(days=7)
    deal_query = db.query(models.Deal).filter(models.Deal.status.notin_(["closed", "rejected"]))
    if role == "sponsor":
        deal_query = deal_query.filter(models.Deal.sponsor_id == user_id)
    elif role == "organizer":
        deal_query = deal_query.filter(models.Deal.organizer_id == user_id)
    else:
        deal_query = deal_query.filter(models.Deal.influencer_id == user_id)
    deals = deal_query.all()
    for deal in deals:
        deal_event_id = _as_int(getattr(deal, "event_id", 0), default=0)
        event = db.query(models.Event).filter(models.Event.id == deal_event_id).first() if deal_event_id > 0 else None
        event_date = getattr(event, "date", None) if event is not None else None
        if event is not None and isinstance(event_date, date_cls) and event_date <= soon:
            deal_id = _as_int(getattr(deal, "id", 0))
            event_id = _as_int(getattr(event, "id", 0))
            _upsert_nudge(
                db,
                user_id=user_id,
                nudge_type="expiring_deal",
                title="Upcoming deadline",
                message=f"Deal #{deal_id} links to event '{_as_str(getattr(event, 'title', ''), default='Event')}' happening soon.",
                payload={"deal_id": deal_id, "event_id": event_id, "dedupe_key": f"expiring:{deal_id}:{event_id}"},
                due_at=datetime.combine(event_date, datetime.min.time()),
            )
            created += 1

    # Inactive opportunities (no new deals in 14 days)
    lookback = now - timedelta(days=14)
    if role == "sponsor":
        recent_deals = db.query(models.Deal).filter(models.Deal.sponsor_id == user_id, models.Deal.created_at >= lookback).count()
    elif role == "organizer":
        recent_deals = db.query(models.Deal).filter(models.Deal.organizer_id == user_id, models.Deal.created_at >= lookback).count()
    else:
        recent_deals = db.query(models.Deal).filter(models.Deal.influencer_id == user_id, models.Deal.created_at >= lookback).count()
    if recent_deals == 0:
        _upsert_nudge(
            db,
            user_id=user_id,
            nudge_type="inactive_opportunity",
            title="Activity is slowing down",
            message="No new deals in the last 14 days. Launch a new proposal to keep momentum.",
            payload={"dedupe_key": f"inactive:{user_id}:{now.strftime('%Y-%m-%d')}"},
            due_at=now + timedelta(days=1),
        )
        created += 1

    return {"nudges_created": created}


@router.post("/generate")
@limiter.limit("20/minute")
def generate_my_nudges(
    request: Request,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    del request
    summary = _generate_for_user(db, current_user)
    db.commit()
    return summary


@router.post("/generate-all")
@limiter.limit("10/minute")
def generate_all_nudges(
    request: Request,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    del request
    if _as_str(getattr(current_user, "role", "")).lower() != "admin":
        raise exceptions.AuthorizationError("Admin access required")

    users = db.query(models.User).all()
    total = 0
    for user in users:
        summary = _generate_for_user(db, user)
        total += summary["nudges_created"]
    db.commit()
    return {"users_processed": len(users), "nudges_created": total}


@router.get("/me", response_model=list[schemas.LifecycleNudgeResponse])
@limiter.limit("100/minute")
def list_my_nudges(
    request: Request,
    state: str | None = None,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    del request
    user_id = _as_int(getattr(current_user, "id", 0))
    query = db.query(models.LifecycleNudge).filter(models.LifecycleNudge.user_id == user_id)
    if state:
        query = query.filter(models.LifecycleNudge.state == state)
    return query.order_by(models.LifecycleNudge.created_at.desc()).limit(200).all()


@router.put("/{nudge_id}", response_model=schemas.LifecycleNudgeResponse)
@limiter.limit("80/minute")
def update_nudge_state(
    request: Request,
    nudge_id: int,
    payload: schemas.NudgeStateUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    del request
    user_id = _as_int(getattr(current_user, "id", 0))
    nudge = db.query(models.LifecycleNudge).filter(models.LifecycleNudge.id == nudge_id).first()
    if not nudge:
        raise exceptions.ValidationError("Nudge not found")
    if _as_int(getattr(nudge, "user_id", 0)) != user_id:
        raise exceptions.AuthorizationError("You can update only your own nudges")
    setattr(nudge, "state", payload.state)
    db.add(nudge)
    db.commit()
    db.refresh(nudge)
    return nudge
