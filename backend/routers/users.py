from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from ..database import get_db
from .. import schemas, crud, exceptions, models
from ..core.notifications import notification_manager
from ..auth import create_access_token, ACCESS_TOKEN_EXPIRE_MINUTES

from .auth_router import get_current_user
from ..models import User

router = APIRouter(prefix="/users", tags=["Users"])

@router.get("/", response_model=list[schemas.PublicUserResponse])
def list_users(
    role: str = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    query = db.query(crud.models.User)
    
    if role:
        query = query.filter(crud.models.User.role == role)
    elif current_user.role != "admin":
        raise exceptions.AuthorizationError("Only admins can list all users. Please specify a role filter.")
        
    return query.all()


# ---- PUBLIC PROFILE — must be BEFORE /{user_id} --------------------------------
@router.get("/{user_id}/profile")
def get_public_profile(user_id: int, db: Session = Depends(get_db)):
    user = crud.get_user(db, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Gather role-based stats
    if user.role == "organizer":
        active_items = db.query(models.Event).filter(models.Event.organizer_id == user_id).count()
        total_deals = db.query(models.Deal).filter(models.Deal.organizer_id == user_id).count()
        success_deals = db.query(models.Deal).filter(
            models.Deal.organizer_id == user_id, models.Deal.status == "closed"
        ).count()
        total_earned = db.query(models.Deal).filter(
            models.Deal.organizer_id == user_id, models.Deal.payment_done == True
        ).with_entities(models.Deal.payment_amount).all()
    elif user.role == "sponsor":
        active_items = db.query(models.Campaign).filter(models.Campaign.creator_id == user_id).count()
        total_deals = db.query(models.Deal).filter(models.Deal.sponsor_id == user_id).count()
        success_deals = db.query(models.Deal).filter(
            models.Deal.sponsor_id == user_id, models.Deal.status == "closed"
        ).count()
        total_earned = db.query(models.Deal).filter(
            models.Deal.sponsor_id == user_id, models.Deal.payment_done == True
        ).with_entities(models.Deal.payment_amount).all()
    else:  # influencer
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

    # Get reviews targeting this user
    reviews = (
        db.query(models.DealReview)
        .filter(models.DealReview.target_user_id == user_id)
        .order_by(models.DealReview.created_at.desc())
        .limit(20)
        .all()
    )

    return {
        "user": {
            "id": user.id,
            "full_name": user.full_name,
            "email": user.email,
            "role": user.role,
            "city": user.city,
            "state": user.state,
            "website": user.website,
            "about": user.about,
            "company_name": getattr(user, "company_name", None),
            "organization_name": getattr(user, "organization_name", None),
            "trust_score": float(user.trust_score) if user.trust_score else 5.0,
            "verification_badge": user.verification_badge,
            "created_at": user.created_at,
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
            "joined_date": user.created_at.strftime("%B %Y") if user.created_at else "—"
        },
        "reviews": [
            {
                "id": r.id,
                "rating": r.rating,
                "comment": r.comment,
                "created_at": str(r.created_at),
                "reviewer_name": r.reviewer.full_name if r.reviewer else "Anonymous",
                "reviewer_role": r.reviewer_role
            }
            for r in reviews
        ]
    }


@router.get("/{user_id}", response_model=schemas.UserResponse)
def read_user(
    user_id: int, 
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    if current_user.id != user_id and current_user.role != "admin":
         raise exceptions.AuthorizationError("You can only view your own full profile")

    db_user = crud.get_user(db, user_id)
    if not db_user:
        raise exceptions.ValidationError("User not found")
    return db_user


@router.put("/{user_id}", response_model=schemas.UserResponse)
async def update_user(
    user_id: int, 
    user_updates: schemas.PublicUserUpdate, 
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    if current_user.id != user_id and current_user.role != "admin":
        raise exceptions.AuthorizationError()

    db_user = crud.update_user(db, user_id, user_updates.dict(exclude_unset=True))
    if not db_user:
        raise exceptions.ValidationError("User not found")
        
    # Notify marketplace to refresh if identity parameters changed
    await notification_manager.broadcast_all({"type": "MARKETPLACE_REFRESH"})
    
    return db_user
