from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List

from ..database import get_db
from .. import schemas, crud, models
from ..core.notifications import notification_manager
from .auth_router import get_current_user

router = APIRouter(prefix="/reviews", tags=["reviews"])

@router.post("/", response_model=schemas.ReviewResponse, status_code=status.HTTP_201_CREATED)
async def create_review(review: schemas.ReviewCreate, db: Session = Depends(get_db)):
    from sqlalchemy.exc import IntegrityError
    try:
        result = crud.create_review(db, review)
        
        db_deal = crud.get_deal(db, review.deal_id)
        if db_deal:
            for uid in [db_deal.sponsor_id, db_deal.organizer_id, db_deal.influencer_id]:
                if uid:
                    await notification_manager.notify_user(uid, {"type": "DEAL_UPDATE", "deal_id": db_deal.id})

        return result
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You have already submitted a review for this deal."
        )


@router.get("/my")
def get_my_reviews(
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Return all reviews submitted BY the current user as {deal_id: rating} map."""
    reviews = crud.get_reviews_by_reviewer(db, current_user.id)
    return {str(r.deal_id): r.rating for r in reviews}


@router.get("/", response_model=List[schemas.ReviewResponse])
def list_reviews(db: Session = Depends(get_db)):
    return db.query(models.DealReview).all()


@router.get("/{deal_id}", response_model=List[schemas.ReviewResponse])
def get_reviews(deal_id: int, db: Session = Depends(get_db)):
    reviews = crud.get_reviews_by_deal(db, deal_id)
    return reviews
