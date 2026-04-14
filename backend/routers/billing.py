from __future__ import annotations

from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from .. import models, schemas
from ..auth import get_current_user
from ..core.billing import PLAN_DEFINITIONS, month_window_utc, normalize_plan_tier
from ..database import get_db
from backend.core.limiter import limiter

router = APIRouter(prefix="/billing", tags=["billing"])


def _get_monthly_usage(db: Session, user_id: int) -> tuple[str, dict[str, int]]:
    month_start, month_end = month_window_utc()
    start_naive = month_start.replace(tzinfo=None)
    end_naive = month_end.replace(tzinfo=None)

    events_created = (
        db.query(models.Event)
        .filter(
            models.Event.organizer_id == user_id,
            models.Event.created_at >= start_naive,
            models.Event.created_at < end_naive,
        )
        .count()
    )
    campaigns_created = (
        db.query(models.Campaign)
        .filter(
            models.Campaign.creator_id == user_id,
            models.Campaign.created_at >= start_naive,
            models.Campaign.created_at < end_naive,
        )
        .count()
    )
    deals_created = (
        db.query(models.Deal)
        .filter(
            models.Deal.created_at >= start_naive,
            models.Deal.created_at < end_naive,
        )
        .filter(
            (models.Deal.sponsor_id == user_id)
            | (models.Deal.organizer_id == user_id)
            | (models.Deal.influencer_id == user_id)
        )
        .count()
    )
    chat_messages_sent = (
        db.query(models.ChatMessage)
        .filter(
            models.ChatMessage.sender_id == user_id,
            models.ChatMessage.timestamp >= start_naive,
            models.ChatMessage.timestamp < end_naive,
        )
        .count()
    )
    notifications_received = (
        db.query(models.Notification)
        .filter(
            models.Notification.user_id == user_id,
            models.Notification.created_at >= start_naive,
            models.Notification.created_at < end_naive,
        )
        .count()
    )

    return month_start.date().isoformat(), {
        "events_created": int(events_created),
        "campaigns_created": int(campaigns_created),
        "deals_created": int(deals_created),
        "chat_messages_sent": int(chat_messages_sent),
        "notifications_received": int(notifications_received),
    }


@router.get("/plans", response_model=list[schemas.BillingPlanResponse])
@limiter.limit("120/minute")
def list_plans(request: Request):
    del request
    return [
        schemas.BillingPlanResponse(
            code=plan.code,
            name=plan.name,
            monthly_price_inr=plan.monthly_price_inr,
            limits=plan.limits,
            features=plan.features,
        )
        for plan in PLAN_DEFINITIONS.values()
    ]


@router.get("/me", response_model=schemas.BillingOverviewResponse)
@limiter.limit("90/minute")
def get_my_billing(
    request: Request,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    del request
    user_id = int(getattr(current_user, "id", 0))
    tier = normalize_plan_tier(getattr(current_user, "plan_tier", None))
    status = str(getattr(current_user, "plan_status", "active") or "active")
    month_start, usage_data = _get_monthly_usage(db, user_id)
    return schemas.BillingOverviewResponse(
        plan_tier=tier,
        plan_status=status,
        plan_renewal_at=getattr(current_user, "plan_renewal_at", None),
        limits=PLAN_DEFINITIONS[tier].limits,
        usage=schemas.BillingUsageResponse(month_start=month_start, **usage_data),
    )


@router.post("/me/change-plan", response_model=schemas.BillingOverviewResponse)
@limiter.limit("30/minute")
def change_my_plan(
    payload: schemas.ChangePlanRequest,
    request: Request,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    del request
    tier = normalize_plan_tier(payload.target_plan)
    prior_plan = normalize_plan_tier(getattr(current_user, "plan_tier", None))
    plan = PLAN_DEFINITIONS[tier]

    current_user.plan_tier = tier
    current_user.plan_status = "active"
    current_user.plan_renewal_at = datetime.now(timezone.utc).replace(tzinfo=None) + timedelta(days=30)
    db.add(current_user)

    db.add(
        models.BillingEvent(
            user_id=int(getattr(current_user, "id", 0)),
            from_plan=prior_plan,
            to_plan=tier,
            amount=plan.monthly_price_inr,
            currency="INR",
            status="simulated",
            note=payload.note,
        )
    )
    db.commit()
    db.refresh(current_user)

    month_start, usage_data = _get_monthly_usage(db, int(getattr(current_user, "id", 0)))
    return schemas.BillingOverviewResponse(
        plan_tier=tier,
        plan_status="active",
        plan_renewal_at=getattr(current_user, "plan_renewal_at", None),
        limits=plan.limits,
        usage=schemas.BillingUsageResponse(month_start=month_start, **usage_data),
    )


@router.get("/me/history", response_model=list[schemas.BillingEventResponse])
@limiter.limit("60/minute")
def get_my_billing_history(
    request: Request,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    del request
    user_id = int(getattr(current_user, "id", 0))
    return (
        db.query(models.BillingEvent)
        .filter(models.BillingEvent.user_id == user_id)
        .order_by(models.BillingEvent.created_at.desc())
        .limit(50)
        .all()
    )
