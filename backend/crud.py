from sqlalchemy.orm import Session, joinedload
from passlib.context import CryptContext  # type: ignore[import]
from datetime import datetime

from . import models, schemas, exceptions

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# -----------------
# User utilities
# -----------------

def get_user(db: Session, user_id: int):
    return db.query(models.User).filter(models.User.id == user_id).first()


def get_user_by_email(db: Session, email: str):
    return db.query(models.User).filter(models.User.email == email).first()


def create_user(db: Session, user: schemas.UserCreate):
    hashed_password = pwd_context.hash(user.password)
    user_data = user.dict(exclude={"password"})
    db_user = models.User(**user_data, password=hashed_password)
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user


def update_user(db: Session, user_id: int, updates: dict):
    db_user = get_user(db, user_id)
    if not db_user:
        return None
    for key, value in updates.items():
        if hasattr(db_user, key):
            setattr(db_user, key, value)
    db.commit()
    db.refresh(db_user)
    return db_user


def authenticate_user(db: Session, email: str, password: str):
    user = get_user_by_email(db, email)
    if not user:
        return None
    if not pwd_context.verify(password, user.password):
        return None
    return user

# -----------------
# Event utilities
# -----------------

def get_event(db: Session, event_id: int):
    return db.query(models.Event).filter(models.Event.id == event_id).first()


def get_events(db: Session, skip: int = 0, limit: int = 100):
    return db.query(models.Event).offset(skip).limit(limit).all()


def create_event(db: Session, event: schemas.EventCreate):
    db_event = models.Event(**event.dict())
    db.add(db_event)
    db.commit()
    db.refresh(db_event)
    return db_event


def update_event(db: Session, event_id: int, updates: schemas.EventUpdate):
    db_event = get_event(db, event_id)
    if not db_event:
        return None
    for key, value in updates.dict(exclude_unset=True).items():
        setattr(db_event, key, value)
    db.commit()
    db.refresh(db_event)
    return db_event


def delete_event(db: Session, event_id: int):
    db_event = get_event(db, event_id)
    if not db_event:
        return None
    db.delete(db_event)
    db.commit()
    return db_event

# -----------------
# Campaign utilities
# -----------------

def get_campaign(db: Session, campaign_id: int):
    return db.query(models.Campaign).filter(models.Campaign.id == campaign_id).first()


def get_campaigns(db: Session, skip: int = 0, limit: int = 100):
    return db.query(models.Campaign).offset(skip).limit(limit).all()


def create_campaign(db: Session, campaign: schemas.CampaignCreate):
    db_campaign = models.Campaign(**campaign.dict())
    db.add(db_campaign)
    db.commit()
    db.refresh(db_campaign)
    return db_campaign


def update_campaign(db: Session, campaign_id: int, updates: schemas.CampaignUpdate):
    db_campaign = get_campaign(db, campaign_id)
    if not db_campaign:
        return None
    for key, value in updates.dict(exclude_unset=True).items():
        setattr(db_campaign, key, value)
    db.commit()
    db.refresh(db_campaign)
    return db_campaign


def delete_campaign(db: Session, campaign_id: int):
    db_campaign = get_campaign(db, campaign_id)
    if not db_campaign:
        return None
    db.delete(db_campaign)
    db.commit()
    return db_campaign

# -----------------
# Deal utilities
# -----------------

def get_deal(db: Session, deal_id: int):
    return db.query(models.Deal).options(
        joinedload(models.Deal.sponsor),
        joinedload(models.Deal.organizer),
        joinedload(models.Deal.influencer),
        joinedload(models.Deal.event),
        joinedload(models.Deal.campaign)
    ).filter(models.Deal.id == deal_id).first()


def get_deals(db: Session, skip: int = 0, limit: int = 100):
    return db.query(models.Deal).options(
        joinedload(models.Deal.sponsor),
        joinedload(models.Deal.organizer),
        joinedload(models.Deal.influencer),
        joinedload(models.Deal.event),
        joinedload(models.Deal.campaign)
    ).offset(skip).limit(limit).all()


def create_deal(db: Session, deal: schemas.DealCreate):
    data = deal.dict()
    # Auto-accept for the initiator
    if data.get("deal_type") == "promotion":
        if data.get("influencer_id") and not data.get("organizer_id"):
            # Influencer applied
            data["influencer_accepted"] = True
        elif data.get("sponsor_id"):
            # Sponsor initiated (if we add sponsor-to-influencer flow)
            # Actually, if a sponsor initiates, they should be marked as accepted
            data["sponsor_accepted"] = True
    elif data.get("deal_type") == "sponsorship":
        if data.get("organizer_id"):
            # Organizer proposed to sponsor
            data["organizer_accepted"] = True
        elif data.get("sponsor_id"):
            # Sponsor proposed to organizer
            data["sponsor_accepted"] = True
            
    db_deal = models.Deal(**data)
    db.add(db_deal)
    db.commit()
    db.refresh(db_deal)
    return db_deal


def update_deal(db: Session, deal_id: int, updates: dict):
    db_deal = get_deal(db, deal_id)
    if not db_deal:
        return None
    
    # Strictly control what can be updated via generic update
    # prevents mass assignment of status/payment fields
    allowed_fields = {"proof_of_work"}
    for key, value in updates.items():
        if key in allowed_fields and hasattr(db_deal, key):
            setattr(db_deal, key, value)
            
    db.commit()
    db.refresh(db_deal)
    return db_deal


def delete_deal(db: Session, deal_id: int):
    db_deal = get_deal(db, deal_id)
    if not db_deal:
        return None
    db.delete(db_deal)
    db.commit()
    return db_deal

# specialized actions

def deal_accept(db: Session, deal_id: int, role: str, accept: bool):
    deal = get_deal(db, deal_id)
    if not deal:
        return None

    # Allow acceptance only in early states (proposed or payment_pending if partner hasn't accepted yet)
    early_states = {"proposed"}
    if deal.status not in early_states:
        raise exceptions.BusinessLogicError(f"Cannot accept deal in '{deal.status}' state")

    if not accept:
        # Can only reject in 'proposed' state
        if deal.status != "proposed":
            raise exceptions.BusinessLogicError(f"Cannot decline a deal that is already in '{deal.status}' state")
        deal.status = "rejected"
        db.commit()
        db.refresh(deal)
        return deal

    if role == "organizer":
        deal.organizer_accepted = True
    elif role == "sponsor":
        deal.sponsor_accepted = True
    elif role == "influencer":
        deal.influencer_accepted = True

    # Logic for auto-status update
    can_advance = False
    if deal.deal_type == "sponsorship":
        if deal.organizer_accepted and deal.sponsor_accepted:
            can_advance = True
    elif deal.deal_type == "promotion":
        if deal.sponsor_accepted and deal.influencer_accepted:
            can_advance = True

    # Only advance to payment_pending if not already there or further
    if can_advance and deal.status == "proposed":
        deal.status = "payment_pending"

    db.commit()
    db.refresh(deal)
    return deal


def deal_payment_webhook(db: Session, deal_id: int, payment_id: str, status: str):
    """Only called by Payment provider webhook for security"""
    deal = get_deal(db, deal_id)
    if not deal:
        return None
        
    # Prevent backward transitions or accidental reverts from late webhooks
    if deal.status not in ["payment_pending", "proposed"]: # proposed handling is a fallback for concurrent updates
        raise exceptions.BusinessLogicError(f"Payment received for deal in invalid state: {deal.status}")

    deal.razorpay_payment_id = payment_id
    deal.payment_status = status
    
    if status == "succeeded":
        deal.payment_done = True
        deal.payment_timestamp = datetime.utcnow()
        deal.status = "signing_pending"
    
    db.commit()
    db.refresh(deal)
    return deal


def deal_payment(db: Session, deal_id: int, payment: schemas.DealPayment):
    deal = get_deal(db, deal_id)
    if not deal:
        return None
        
    if deal.status != "payment_pending":
        raise exceptions.BusinessLogicError(f"Cannot process payment for deal in {deal.status} state")

    deal.payment_done = True
    deal.payment_amount = payment.amount
    deal.currency = payment.currency
    deal.payment_timestamp = datetime.utcnow()
    deal.status = "signing_pending"
    
    db.commit()
    db.refresh(deal)
    return deal


def deal_sign(db: Session, deal_id: int, sign: schemas.DealSign):
    deal = get_deal(db, deal_id)
    if not deal:
        return None

    # Allow signing in signing_pending OR if payment is done and deal isn't closed yet
    signable_states = {"signing_pending", "payment_pending"}
    if deal.status not in signable_states and not (deal.payment_done and deal.status != "closed"):
        raise exceptions.BusinessLogicError(f"Cannot sign deal in '{deal.status}' state")

    if sign.role == "organizer":
        deal.organizer_signed = True
    elif sign.role == "sponsor":
        deal.sponsor_signed = True
    elif sign.role == "influencer":
        deal.influencer_signed = True

    # Ensure status is at least signing_pending when payment is done
    if deal.payment_done and deal.status == "payment_pending":
        deal.status = "signing_pending"

    # Check for closure
    is_closed = False
    if deal.deal_type == "sponsorship":
        if deal.organizer_signed and deal.sponsor_signed and deal.payment_done:
            is_closed = True
    elif deal.deal_type == "promotion":
        if deal.sponsor_signed and deal.influencer_signed and deal.payment_done:
            is_closed = True

    if is_closed:
        deal.status = "closed"

    db.commit()
    db.refresh(deal)
    return deal

# -----------------
# Review utilities
# -----------------

def create_review(db: Session, review: schemas.ReviewCreate):
    # Find the target user ID from the deal before creating review
    deal = get_deal(db, review.deal_id)
    if not deal:
        raise exceptions.ValidationError("Deal not found")
        
    target_user_id = None
    if review.target_role == "sponsor":
        target_user_id = deal.sponsor_id
    elif review.target_role == "organizer":
        target_user_id = deal.organizer_id
    elif review.target_role == "influencer":
        target_user_id = deal.influencer_id

    if not target_user_id:
        raise exceptions.ValidationError("Target user not found in deal")
        
    db_review = models.DealReview(
        **review.dict(),
        target_user_id=target_user_id
    )
    db.add(db_review)
    db.commit()
    db.refresh(db_review)
    
    # Recalculate target user's trust score
    from sqlalchemy import func
    avg_rating = db.query(func.avg(models.DealReview.rating)).filter(
        models.DealReview.target_user_id == target_user_id
    ).scalar()
    
    if avg_rating:
        update_user(db, target_user_id, {"trust_score": float(avg_rating)})
            
    return db_review


def get_reviews_by_deal(db: Session, deal_id: int):
    return db.query(models.DealReview).filter(models.DealReview.deal_id == deal_id).all()


def get_reviews_by_reviewer(db: Session, reviewer_id: int):
    """Return all reviews submitted BY a specific user (keyed by deal_id)."""
    return db.query(models.DealReview).filter(
        models.DealReview.reviewer_id == reviewer_id
    ).all()


# -----------------
# Chat messages
# -----------------
def create_chat_message(db: Session, message: schemas.ChatMessageCreate):
    db_msg = models.ChatMessage(**message.dict())
    db.add(db_msg)
    db.commit()
    db.refresh(db_msg)
    return db_msg


def get_chat_history(db: Session, deal_id: int, limit: int = 50):
    return db.query(models.ChatMessage).filter(
        models.ChatMessage.deal_id == deal_id
    ).order_by(models.ChatMessage.timestamp.asc()).limit(limit).all()
