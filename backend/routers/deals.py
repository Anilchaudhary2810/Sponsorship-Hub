from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session, joinedload
from typing import List

from ..database import get_db
from .. import schemas, crud, exceptions, models
from ..core.notifications import notification_manager

from backend.core.limiter import limiter
from fastapi import Request

from .auth_router import get_current_user
from ..models import User

router = APIRouter(prefix="/deals", tags=["deals"])

@router.post("/", response_model=schemas.DealResponse, status_code=status.HTTP_201_CREATED)
@limiter.limit("5/minute")
async def create_deal(
    request: Request, 
    deal: schemas.DealCreate, 
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # Verify current user is part of the deal they are creating
    if current_user.id not in [deal.sponsor_id, deal.organizer_id, deal.influencer_id]:
         raise exceptions.AuthorizationError("You must be a participant in the deal you create")
    
    result = crud.create_deal(db, deal)
    
    # Notify participants (excluding current user to avoid self-notifying)
    for uid in [result.sponsor_id, result.organizer_id, result.influencer_id]:
        if uid and int(uid) != int(current_user.id):
            await notification_manager.push_notification(
                db, uid, 
                "New Deal Proposed", 
                f"{current_user.full_name} has proposed a new partnership deal.",
                "deal_new"
            )
            
    return result


@router.get("/", response_model=List[schemas.DealResponse])
def list_deals(
    skip: int = 0, limit: int = 100, 
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # Security: Filter deals so users only see their own
    return db.query(models.Deal).filter(
        (models.Deal.sponsor_id == current_user.id) | 
        (models.Deal.organizer_id == current_user.id) | 
        (models.Deal.influencer_id == current_user.id)
    ).options(
        joinedload(models.Deal.sponsor),
        joinedload(models.Deal.organizer),
        joinedload(models.Deal.influencer),
        joinedload(models.Deal.event),
        joinedload(models.Deal.campaign)
    ).offset(skip).limit(limit).all()


@router.get("/{deal_id}", response_model=schemas.DealResponse)
def get_deal(
    deal_id: int, 
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    db_deal = crud.get_deal(db, deal_id)
    if not db_deal:
        raise exceptions.ValidationError("Deal not found")
        
    if current_user.id not in [db_deal.sponsor_id, db_deal.organizer_id, db_deal.influencer_id] and current_user.role != "admin":
        raise exceptions.AuthorizationError()
        
    return db_deal


@router.put("/{deal_id}", response_model=schemas.DealResponse)
async def update_deal(
    deal_id: int, 
    deal_updates: schemas.DealUpdate, 
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    db_deal = crud.get_deal(db, deal_id)
    if not db_deal:
        raise exceptions.ValidationError("Deal not found")
        
    if current_user.id not in [db_deal.sponsor_id, db_deal.organizer_id, db_deal.influencer_id] and current_user.role != "admin":
        raise exceptions.AuthorizationError()

    updated = crud.update_deal(db, deal_id, deal_updates.dict(exclude_unset=True))
    
    # Notify participants
    for uid in [updated.sponsor_id, updated.organizer_id, updated.influencer_id]:
        if uid:
            await notification_manager.notify_user(uid, {"type": "DEAL_UPDATE", "deal_id": updated.id})
            
    return updated


@router.delete("/{deal_id}", response_model=schemas.DealResponse)
async def delete_deal(
    deal_id: int, 
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    db_deal = crud.get_deal(db, deal_id)
    if not db_deal:
        raise exceptions.ValidationError("Deal not found")
    
    # Only initiator or admin should delete proposed deals
    if current_user.id not in [db_deal.sponsor_id, db_deal.organizer_id, db_deal.influencer_id] and current_user.role != "admin":
        raise exceptions.AuthorizationError()
        
    result = crud.delete_deal(db, deal_id)
    
    # Notify participants before returning
    for uid in [db_deal.sponsor_id, db_deal.organizer_id, db_deal.influencer_id]:
        if uid:
            await notification_manager.notify_user(uid, {"type": "DEAL_UPDATE", "deal_id": deal_id})
            
    return result


# actions
@router.put("/{deal_id}/accept", response_model=schemas.DealResponse)
async def accept_deal(
    deal_id: int, 
    action: schemas.DealAccept, 
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    db_deal = crud.get_deal(db, deal_id)
    if not db_deal:
         raise exceptions.ValidationError("Deal not found")
         
    # Verify the role in the request matches the user's actual role and they are part of the deal
    if current_user.role != action.role:
        raise exceptions.AuthorizationError(f"Role mismatch: User is {current_user.role}, action requires {action.role}")
    
    if current_user.id not in [db_deal.sponsor_id, db_deal.organizer_id, db_deal.influencer_id]:
        raise exceptions.AuthorizationError(f"User ID {current_user.id} is not a participant in deal {deal_id}")

    result = crud.deal_accept(db, deal_id, action.role, action.accept)
    if not result:
        raise exceptions.BusinessLogicError("Action invalid for current state")

    word = "accepted" if action.accept else "rejected"
    # Notify participants
    for uid in [db_deal.sponsor_id, db_deal.organizer_id, db_deal.influencer_id]:
        if uid and int(uid) != int(current_user.id):
            await notification_manager.push_notification(
                db, uid,
                f"Deal {word.capitalize()}",
                f"{current_user.full_name} has {word} the partnership proposal.",
                "deal_update"
            )
            
    return result


@router.put("/{deal_id}/payment", response_model=schemas.DealResponse)
async def mark_payment_done(
    deal_id: int, 
    payment: schemas.DealPayment, 
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    db_deal = crud.get_deal(db, deal_id)
    if not db_deal:
         raise exceptions.ValidationError("Deal not found")
         
    if current_user.id != db_deal.sponsor_id:
        raise exceptions.AuthorizationError(f"Only sponsors can pay for this deal. User ID {current_user.id} != Sponsor ID {db_deal.sponsor_id}")
        
    result = crud.deal_payment(db, deal_id, payment)
    if not result:
        raise exceptions.BusinessLogicError("Payment update failed")

    for uid in [db_deal.sponsor_id, db_deal.organizer_id, db_deal.influencer_id]:
        if uid and int(uid) != int(current_user.id):
            await notification_manager.push_notification(
                db, uid,
                "Payment Received!",
                f"A payment of {payment.amount} {payment.currency} has been recorded for your deal.",
                "payment"
            )

    return result


# NO MANUAL PAYMENT ENDPOINT ALLOWED


@router.put("/{deal_id}/sign", response_model=schemas.DealResponse)
async def sign_deal(
    deal_id: int, 
    sign: schemas.DealSign, 
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    db_deal = crud.get_deal(db, deal_id)
    if not db_deal:
        raise exceptions.ValidationError("Deal not found")
        
    # Check role alignment (unless admin)
    if current_user.role != sign.role and current_user.role != "admin":
        raise exceptions.AuthorizationError(f"Role mismatch: You are logged in as {current_user.role}, but trying to sign as {sign.role}")

    # Check participation (unless admin)
    participants = [
        int(db_deal.sponsor_id) if db_deal.sponsor_id is not None else -1,
        int(db_deal.organizer_id) if db_deal.organizer_id is not None else -1,
        int(db_deal.influencer_id) if db_deal.influencer_id is not None else -1
    ]
    
    if int(current_user.id) not in participants and current_user.role != "admin":
        raise exceptions.AuthorizationError(f"Authorization failed: User ID {current_user.id} is not a valid participant in this deal.")

    result = crud.deal_sign(db, deal_id, sign)
    if not result:
        raise exceptions.BusinessLogicError(f"Cannot sign deal: Current status is '{db_deal.status}', but it must be 'signing_pending'")

    for uid in [db_deal.sponsor_id, db_deal.organizer_id, db_deal.influencer_id]:
        if uid and int(uid) != int(current_user.id):
            await notification_manager.push_notification(
                db, uid,
                "Contract Signed",
                f"{current_user.full_name} has signed the partnership agreement.",
                "sign"
            )

    return result
