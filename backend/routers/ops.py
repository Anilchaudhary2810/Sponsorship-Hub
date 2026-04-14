from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from ..database import get_db
from .. import models, exceptions
from ..core.metrics import get_metrics_snapshot
from ..core.pagination import clamp_limit
from ..core.billing import PLAN_DEFINITIONS, normalize_plan_tier
from ..auth import get_current_user
from backend.core.limiter import limiter

router = APIRouter(prefix="/ops", tags=["ops"])


def _require_admin(user: models.User) -> None:
    role = str(getattr(user, "role", ""))
    if role != "admin":
        raise exceptions.AuthorizationError("Admin access required")


@router.get("/metrics")
@limiter.limit("30/minute")
def read_metrics(
    request: Request,
    current_user: models.User = Depends(get_current_user),
):
    _require_admin(current_user)
    return get_metrics_snapshot()


@router.get("/audit-events")
@limiter.limit("30/minute")
def list_audit_events(
    request: Request,
    skip: int = 0,
    limit: int = 100,
    action: str | None = None,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    _require_admin(current_user)

    safe_skip = max(0, int(skip))
    safe_limit = clamp_limit(limit, default=20, maximum=200)

    query = db.query(models.AuditEvent)
    if action:
        query = query.filter(models.AuditEvent.action == action)

    events = (
        query.order_by(models.AuditEvent.created_at.desc())
        .offset(safe_skip)
        .limit(safe_limit)
        .all()
    )

    return [
        {
            "id": int(getattr(e, "id", 0)),
            "action": str(getattr(e, "action", "")),
            "actor_user_id": getattr(e, "actor_user_id", None),
            "target_type": getattr(e, "target_type", None),
            "target_id": getattr(e, "target_id", None),
            "ip_address": getattr(e, "ip_address", None),
            "user_agent": getattr(e, "user_agent", None),
            "event_meta": getattr(e, "event_meta", None),
            "created_at": str(getattr(e, "created_at", "")),
        }
        for e in events
    ]


@router.get("/plan-distribution")
@limiter.limit("30/minute")
def get_plan_distribution(
    request: Request,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    _require_admin(current_user)
    del request

    users = db.query(models.User).all()
    distribution = {key: 0 for key in PLAN_DEFINITIONS.keys()}
    estimated_mrr_inr = 0

    for user in users:
        tier = normalize_plan_tier(getattr(user, "plan_tier", None))
        distribution[tier] += 1
        if tier != "free":
            estimated_mrr_inr += PLAN_DEFINITIONS[tier].monthly_price_inr

    paid_users = sum(v for k, v in distribution.items() if k != "free")
    return {
        "total_users": len(users),
        "paid_users": paid_users,
        "estimated_mrr_inr": estimated_mrr_inr,
        "distribution": distribution,
    }
