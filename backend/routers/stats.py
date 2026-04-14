from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session
from sqlalchemy import func
from ..database import get_db
from .. import models
from backend.core.limiter import limiter
from ..core.pagination import clamp_limit

router = APIRouter(prefix="/stats", tags=["stats"])

@router.get("/public")
@limiter.limit("120/minute")
def get_public_stats(request: Request, db: Session = Depends(get_db)):
    """Returns aggregated stats for the landing page"""
    verified_sponsors = db.query(models.User).filter(
        models.User.role == "sponsor",
        models.User.is_verified == True
    ).count()
    
    events_hosted = db.query(models.Event).count()
    
    closed_deals = db.query(models.Deal).filter(models.Deal.status == "closed").count()
    
    return {
        "sponsors": verified_sponsors,
        "events": events_hosted,
        "closed_deals": closed_deals,
    }


@router.get("/marketplace-snapshot")
@limiter.limit("120/minute")
def get_marketplace_snapshot(
    request: Request,
    limit: int = 6,
    db: Session = Depends(get_db),
):
    safe_limit = clamp_limit(limit, default=6, maximum=12)

    recent_events = (
        db.query(models.Event)
        .order_by(models.Event.created_at.desc())
        .limit(safe_limit)
        .all()
    )
    recent_campaigns = (
        db.query(models.Campaign)
        .order_by(models.Campaign.created_at.desc())
        .limit(safe_limit)
        .all()
    )

    return {
        "events": [
            {
                "id": int(getattr(e, "id", 0)),
                "title": str(getattr(e, "title", "")),
                "city": getattr(e, "city", None),
                "state": getattr(e, "state", None),
                "category": getattr(e, "category", None),
                "currency": str(getattr(e, "currency", "INR")),
                "date": str(getattr(e, "date", "")) if getattr(e, "date", None) else None,
            }
            for e in recent_events
        ],
        "campaigns": [
            {
                "id": int(getattr(c, "id", 0)),
                "title": str(getattr(c, "title", "")),
                "platform_required": getattr(c, "platform_required", None),
                "status": getattr(c, "status", None),
            }
            for c in recent_campaigns
        ],
    }
