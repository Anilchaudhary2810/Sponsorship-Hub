from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.orm import Session
from typing import List

from ..database import get_db
from .. import schemas, crud, models, exceptions
from ..core.notifications import notification_manager
from backend.core.limiter import limiter
from ..core.pagination import clamp_limit
from .auth_router import get_current_user

router = APIRouter(prefix="/reviews", tags=["reviews"])


def _opt_int(value: object) -> int | None:
    if value is None:
        return None
    try:
        return int(value)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return None

@router.post("/", response_model=schemas.ReviewResponse, status_code=status.HTTP_201_CREATED)
@limiter.limit("30/minute")
async def create_review(
    request: Request,
    review: schemas.ReviewCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    from sqlalchemy.exc import IntegrityError
    try:
        deal = crud.get_deal(db, review.deal_id)
        if not deal:
            raise exceptions.ValidationError("Deal not found")

        sponsor_id = int(getattr(deal, "sponsor_id", 0)) if getattr(deal, "sponsor_id", None) is not None else 0
        organizer_id = int(getattr(deal, "organizer_id", 0)) if getattr(deal, "organizer_id", None) is not None else 0
        influencer_id = int(getattr(deal, "influencer_id", 0)) if getattr(deal, "influencer_id", None) is not None else 0
        current_user_id = int(getattr(current_user, "id", 0))
        current_user_role = str(getattr(current_user, "role", ""))

        participants = {sponsor_id, organizer_id, influencer_id}
        if current_user_id not in participants:
            raise exceptions.AuthorizationError("Only deal participants can submit reviews")

        if review.reviewer_id != current_user_id:
            raise exceptions.AuthorizationError("Reviewer identity must match the authenticated user")

        if review.reviewer_role != current_user_role:
            raise exceptions.AuthorizationError("Reviewer role must match the authenticated user role")

        deal_status = str(getattr(deal, "status", ""))
        if deal_status != "closed":
            raise exceptions.BusinessLogicError("Reviews are allowed only after a deal is closed")

        result = crud.create_review(db, review)
        
        db_deal = deal
        if db_deal:
            deal_id_val = int(getattr(db_deal, "id", 0))
            for raw_uid in [
                getattr(db_deal, "sponsor_id", None),
                getattr(db_deal, "organizer_id", None),
                getattr(db_deal, "influencer_id", None),
            ]:
                uid = _opt_int(raw_uid)
                if uid is not None:
                    await notification_manager.notify_user(uid, {"type": "DEAL_UPDATE", "deal_id": deal_id_val})

        return result
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You have already submitted a review for this deal."
        )


@router.get("/my")
@limiter.limit("60/minute")
def get_my_reviews(
    request: Request,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """Return all reviews submitted BY the current user as {deal_id: rating} map."""
    current_user_id = int(getattr(current_user, "id", 0))
    reviews = crud.get_reviews_by_reviewer(db, current_user_id)
    return {str(r.deal_id): r.rating for r in reviews}


@router.get("/", response_model=List[schemas.ReviewResponse])
@limiter.limit("30/minute")
def list_reviews(
    request: Request,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    current_user_role = str(getattr(current_user, "role", ""))
    if current_user_role != "admin":
        raise exceptions.AuthorizationError("Only admins can list all reviews")
    safe_limit = clamp_limit(limit, default=20, maximum=100)
    safe_skip = max(0, int(skip))
    return db.query(models.DealReview).offset(safe_skip).limit(safe_limit).all()


@router.get("/{deal_id}", response_model=List[schemas.ReviewResponse])
@limiter.limit("80/minute")
def get_reviews(request: Request, deal_id: int, db: Session = Depends(get_db)):
    reviews = crud.get_reviews_by_deal(db, deal_id)
    return reviews
