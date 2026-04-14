from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from typing import Optional

from ..database import get_db
from .. import schemas, crud, exceptions, models
from ..core.notifications import notification_manager
from backend.core.limiter import limiter
from ..core.pagination import clamp_limit

from .auth_router import get_current_user
from ..models import User

router = APIRouter(prefix="/users", tags=["Users"])


@router.get("/", response_model=list[schemas.PublicUserResponse])
@limiter.limit("40/minute")
def list_users(
    request: Request,
    role: Optional[str] = None,
    skip: int = 0,
    limit: int = 50,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    query = db.query(crud.models.User)
    current_user_role = str(getattr(current_user, "role", ""))
    safe_limit = clamp_limit(limit, default=20, maximum=100)
    safe_skip = max(0, int(skip))

    if role:
        query = query.filter(crud.models.User.role == role)
    elif current_user_role != "admin":
        raise exceptions.AuthorizationError("Only admins can list all users. Please specify a role filter.")

    return query.offset(safe_skip).limit(safe_limit).all()


@router.get("/{user_id}/profile")
@limiter.limit("80/minute")
def get_public_profile(request: Request, user_id: int, db: Session = Depends(get_db)):
    user = crud.get_user(db, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    user_role = str(getattr(user, "role", ""))

    if user_role == "organizer":
        active_items = db.query(models.Event).filter(models.Event.organizer_id == user_id).count()
        total_deals = db.query(models.Deal).filter(models.Deal.organizer_id == user_id).count()
        success_deals = db.query(models.Deal).filter(
            models.Deal.organizer_id == user_id, models.Deal.status == "closed"
        ).count()
        total_earned = db.query(models.Deal).filter(
            models.Deal.organizer_id == user_id, models.Deal.payment_done == True
        ).with_entities(models.Deal.payment_amount).all()
    elif user_role == "sponsor":
        active_items = db.query(models.Campaign).filter(models.Campaign.creator_id == user_id).count()
        total_deals = db.query(models.Deal).filter(models.Deal.sponsor_id == user_id).count()
        success_deals = db.query(models.Deal).filter(
            models.Deal.sponsor_id == user_id, models.Deal.status == "closed"
        ).count()
        total_earned = db.query(models.Deal).filter(
            models.Deal.sponsor_id == user_id, models.Deal.payment_done == True
        ).with_entities(models.Deal.payment_amount).all()
    else:
        active_items = db.query(models.Deal).filter(
            models.Deal.influencer_id == user_id, models.Deal.status.notin_(["closed", "rejected"])
        ).count()
        total_deals = db.query(models.Deal).filter(models.Deal.influencer_id == user_id).count()
        success_deals = db.query(models.Deal).filter(
            models.Deal.influencer_id == user_id, models.Deal.status == "closed"
        ).count()
        total_earned = db.query(models.Deal).filter(
            models.Deal.influencer_id == user_id, models.Deal.payment_done == True
        ).with_entities(models.Deal.payment_amount).all()

    total_amount = sum(r[0] or 0 for r in total_earned) if total_earned else 0
    trust_score_raw = getattr(user, "trust_score", None)
    trust_score = float(trust_score_raw) if trust_score_raw is not None else 5.0

    created_at_raw = getattr(user, "created_at", None)
    created_at: Optional[datetime] = created_at_raw if isinstance(created_at_raw, datetime) else None
    joined_date = created_at.strftime("%B %Y") if created_at else "-"

    reviews = (
        db.query(models.DealReview)
        .filter(models.DealReview.target_user_id == user_id)
        .order_by(models.DealReview.created_at.desc())
        .limit(20)
        .all()
    )

    return {
        "user": {
            "id": int(getattr(user, "id", 0)),
            "full_name": str(getattr(user, "full_name", "")),
            "role": user_role,
            "city": getattr(user, "city", None),
            "state": getattr(user, "state", None),
            "website": getattr(user, "website", None),
            "about": getattr(user, "about", None),
            "company_name": getattr(user, "company_name", None),
            "organization_name": getattr(user, "organization_name", None),
            "trust_score": trust_score,
            "verification_badge": bool(getattr(user, "verification_badge", False)),
            "created_at": created_at,
            "instagram_handle": getattr(user, "instagram_handle", None),
            "youtube_channel": getattr(user, "youtube_channel", None),
            "audience_size": getattr(user, "audience_size", None),
            "niche": getattr(user, "niche", None),
            "platforms": getattr(user, "platforms", None),
        },
        "stats": {
            "active_listings": active_items,
            "total_deals": total_deals,
            "closed_deals": success_deals,
            "success_rate": f"{int((success_deals / total_deals * 100) if total_deals > 0 else 0)}%",
            "total_amount": total_amount,
            "joined_date": joined_date,
        },
        "reviews": [
            {
                "id": int(getattr(r, "id", 0)),
                "rating": int(getattr(r, "rating", 0)),
                "comment": getattr(r, "comment", None),
                "created_at": str(getattr(r, "created_at", "")),
                "reviewer_name": getattr(getattr(r, "reviewer", None), "full_name", "Anonymous"),
                "reviewer_role": getattr(r, "reviewer_role", None),
            }
            for r in reviews
        ],
    }


@router.get("/{user_id}", response_model=schemas.UserResponse)
def read_user(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    current_user_id = int(getattr(current_user, "id", 0))
    current_user_role = str(getattr(current_user, "role", ""))
    if current_user_id != user_id and current_user_role != "admin":
        raise exceptions.AuthorizationError("You can only view your own full profile")

    db_user = crud.get_user(db, user_id)
    if not db_user:
        raise exceptions.ValidationError("User not found")
    return db_user


@router.put("/{user_id}", response_model=schemas.UserResponse)
@limiter.limit("30/minute")
async def update_user(
    request: Request,
    user_id: int,
    user_updates: schemas.PublicUserUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    current_user_id = int(getattr(current_user, "id", 0))
    current_user_role = str(getattr(current_user, "role", ""))
    if current_user_id != user_id and current_user_role != "admin":
        raise exceptions.AuthorizationError()

    db_user = crud.update_user(db, user_id, user_updates.dict(exclude_unset=True))
    if not db_user:
        raise exceptions.ValidationError("User not found")

    await notification_manager.broadcast_all({"type": "MARKETPLACE_REFRESH"})
    return db_user
