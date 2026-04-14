from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session, joinedload
from typing import List

from ..database import get_db
from .. import schemas, crud, exceptions, models
from ..core.notifications import notification_manager
from ..core.pagination import clamp_limit
from ..core.audit import log_audit_event

from backend.core.limiter import limiter
from fastapi import Request

from .auth_router import get_current_user
from ..models import User

router = APIRouter(prefix="/deals", tags=["deals"])


def _to_int(value: object, default: int = 0) -> int:
    try:
        return int(value)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return default


def _to_optional_int(value: object) -> int | None:
    if value is None:
        return None
    try:
        return int(value)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return None


def _to_str(value: object, default: str = "") -> str:
    if isinstance(value, str):
        return value
    return default


def _participant_ids_from_deal(deal_obj: object) -> list[int]:
    participants: list[int] = []
    for raw in (
        getattr(deal_obj, "sponsor_id", None),
        getattr(deal_obj, "organizer_id", None),
        getattr(deal_obj, "influencer_id", None),
    ):
        parsed = _to_optional_int(raw)
        if parsed is not None:
            participants.append(parsed)
    return participants


async def _notify_participants(
    db: Session,
    deal_obj: object,
    actor_user_id: int | None,
    title: str,
    message: str,
    notification_type: str,
) -> None:
    actor_id = actor_user_id if actor_user_id is not None else -1
    for uid in _participant_ids_from_deal(deal_obj):
        if uid == actor_id:
            continue
        await notification_manager.push_notification(db, uid, title, message, notification_type)


async def _signal_participants_refresh(deal_obj: object, deal_id: int) -> None:
    for uid in _participant_ids_from_deal(deal_obj):
        await notification_manager.notify_user(uid, {"type": "DEAL_UPDATE", "deal_id": deal_id})


def _audit(db: Session, request: Request, action: str, actor_user_id: int | None, target_id: int | None, meta: dict | None = None) -> None:
    forwarded = request.headers.get("x-forwarded-for")
    ip_address = forwarded.split(",")[0].strip() if forwarded else (request.client.host if request.client else "unknown")
    user_agent = request.headers.get("user-agent", "")
    log_audit_event(
        db,
        action=action,
        actor_user_id=actor_user_id,
        target_type="deal",
        target_id=target_id,
        ip_address=ip_address,
        user_agent=user_agent,
        metadata=meta or {},
    )

@router.post("/", response_model=schemas.DealResponse, status_code=status.HTTP_201_CREATED)
@limiter.limit("5/minute")
async def create_deal(
    request: Request, 
    deal: schemas.DealCreate, 
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    current_user_id = _to_int(getattr(current_user, "id", 0))
    current_user_name = _to_str(getattr(current_user, "full_name", "A user"), default="A user")

    sponsor_id = _to_optional_int(deal.sponsor_id)
    organizer_id = _to_optional_int(deal.organizer_id)
    influencer_id = _to_optional_int(deal.influencer_id)
    participant_ids = {pid for pid in [sponsor_id, organizer_id, influencer_id] if pid is not None}

    # Verify current user is part of the deal they are creating
    if current_user_id not in participant_ids:
        raise exceptions.AuthorizationError("You must be a participant in the deal you create")
    
    result = crud.create_deal(db, deal)
    created_deal_id = _to_int(getattr(result, "id", 0))
    _audit(db, request, "deal.created", current_user_id, created_deal_id, {"deal_type": deal.deal_type})

    await _notify_participants(
        db=db,
        deal_obj=result,
        actor_user_id=current_user_id,
        title="New Deal Proposed",
        message=f"{current_user_name} has proposed a new partnership deal.",
        notification_type="deal_new",
    )
             
    return result


@router.get("/", response_model=List[schemas.DealResponse])
@limiter.limit("80/minute")
def list_deals(
    request: Request,
    skip: int = 0, limit: int = 100, 
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    current_user_id = _to_int(getattr(current_user, "id", 0))
    safe_limit = clamp_limit(limit, default=20, maximum=100)
    safe_skip = max(0, int(skip))
    # Security: Filter deals so users only see their own
    return db.query(models.Deal).filter(
        (models.Deal.sponsor_id == current_user_id) | 
        (models.Deal.organizer_id == current_user_id) | 
        (models.Deal.influencer_id == current_user_id)
    ).options(
        joinedload(models.Deal.sponsor),
        joinedload(models.Deal.organizer),
        joinedload(models.Deal.influencer),
        joinedload(models.Deal.event),
        joinedload(models.Deal.campaign)
    ).offset(safe_skip).limit(safe_limit).all()


@router.get("/{deal_id}", response_model=schemas.DealResponse)
@limiter.limit("100/minute")
def get_deal(
    request: Request,
    deal_id: int, 
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    db_deal = crud.get_deal(db, deal_id)
    if not db_deal:
        raise exceptions.ValidationError("Deal not found")

    current_user_id = _to_int(getattr(current_user, "id", 0))
    current_user_role = _to_str(getattr(current_user, "role", ""))
    participant_ids = set(_participant_ids_from_deal(db_deal))

    if current_user_id not in participant_ids and current_user_role != "admin":
        raise exceptions.AuthorizationError()
        
    return db_deal


@router.put("/{deal_id}", response_model=schemas.DealResponse)
@limiter.limit("40/minute")
async def update_deal(
    request: Request,
    deal_id: int, 
    deal_updates: schemas.DealUpdate, 
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    db_deal = crud.get_deal(db, deal_id)
    if not db_deal:
        raise exceptions.ValidationError("Deal not found")

    current_user_id = _to_int(getattr(current_user, "id", 0))
    current_user_role = _to_str(getattr(current_user, "role", ""))
    participant_ids = set(_participant_ids_from_deal(db_deal))

    if current_user_id not in participant_ids and current_user_role != "admin":
        raise exceptions.AuthorizationError()

    updated = crud.update_deal(db, deal_id, deal_updates.dict(exclude_unset=True))
    if not updated:
        raise exceptions.ValidationError("Deal not found")

    updated_id = _to_int(getattr(updated, "id", deal_id), default=deal_id)
    _audit(db, request, "deal.updated", current_user_id, updated_id)
    await _signal_participants_refresh(updated, updated_id)
             
    return updated


@router.delete("/{deal_id}", response_model=schemas.DealResponse)
@limiter.limit("20/minute")
async def delete_deal(
    request: Request,
    deal_id: int, 
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    db_deal = crud.get_deal(db, deal_id)
    if not db_deal:
        raise exceptions.ValidationError("Deal not found")

    current_user_id = _to_int(getattr(current_user, "id", 0))
    current_user_role = _to_str(getattr(current_user, "role", ""))
    participant_ids = set(_participant_ids_from_deal(db_deal))

    # Only initiator or admin should delete proposed deals
    if current_user_id not in participant_ids and current_user_role != "admin":
        raise exceptions.AuthorizationError()
         
    result = crud.delete_deal(db, deal_id)
    _audit(db, request, "deal.deleted", current_user_id, deal_id)

    await _signal_participants_refresh(db_deal, deal_id)
             
    return result


# actions
@router.put("/{deal_id}/accept", response_model=schemas.DealResponse)
@limiter.limit("40/minute")
async def accept_deal(
    request: Request,
    deal_id: int, 
    action: schemas.DealAccept, 
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    db_deal = crud.get_deal(db, deal_id)
    if not db_deal:
        raise exceptions.ValidationError("Deal not found")

    current_user_id = _to_int(getattr(current_user, "id", 0))
    current_user_role = _to_str(getattr(current_user, "role", ""))
    current_user_name = _to_str(getattr(current_user, "full_name", "A user"), default="A user")
    participant_ids = set(_participant_ids_from_deal(db_deal))

    # Verify the role in the request matches the user's actual role and they are part of the deal
    if current_user_role != action.role:
        raise exceptions.AuthorizationError(f"Role mismatch: User is {current_user_role}, action requires {action.role}")
    
    if current_user_id not in participant_ids:
        raise exceptions.AuthorizationError(f"User ID {current_user_id} is not a participant in deal {deal_id}")

    result = crud.deal_accept(db, deal_id, action.role, action.accept)
    if not result:
        raise exceptions.BusinessLogicError("Action invalid for current state")

    word = "accepted" if action.accept else "rejected"
    _audit(db, request, "deal.accept_action", current_user_id, deal_id, {"action": word, "role": action.role})
    await _notify_participants(
        db=db,
        deal_obj=db_deal,
        actor_user_id=current_user_id,
        title=f"Deal {word.capitalize()}",
        message=f"{current_user_name} has {word} the partnership proposal.",
        notification_type="deal_update",
    )
             
    return result


@router.put("/{deal_id}/payment", response_model=schemas.DealResponse)
@limiter.limit("20/minute")
async def mark_payment_done(
    request: Request,
    deal_id: int, 
    payment: schemas.DealPayment, 
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    db_deal = crud.get_deal(db, deal_id)
    if not db_deal:
        raise exceptions.ValidationError("Deal not found")

    current_user_id = _to_int(getattr(current_user, "id", 0))
    current_user_name = _to_str(getattr(current_user, "full_name", "A user"), default="A user")
    sponsor_id = _to_optional_int(getattr(db_deal, "sponsor_id", None))

    if sponsor_id is None or current_user_id != sponsor_id:
        raise exceptions.AuthorizationError(f"Only sponsors can pay for this deal. User ID {current_user_id} != Sponsor ID {sponsor_id}")
         
    result = crud.deal_payment(db, deal_id, payment)
    if not result:
        raise exceptions.BusinessLogicError("Payment update failed")

    _audit(db, request, "deal.payment_marked", current_user_id, deal_id, {"amount": str(payment.amount), "currency": payment.currency})
    await _notify_participants(
        db=db,
        deal_obj=db_deal,
        actor_user_id=current_user_id,
        title="Payment Received!",
        message=f"A payment of {payment.amount} {payment.currency} has been recorded for your deal.",
        notification_type="payment",
    )

    return result


# NO MANUAL PAYMENT ENDPOINT ALLOWED


@router.put("/{deal_id}/sign", response_model=schemas.DealResponse)
@limiter.limit("40/minute")
async def sign_deal(
    request: Request,
    deal_id: int, 
    sign: schemas.DealSign, 
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    db_deal = crud.get_deal(db, deal_id)
    if not db_deal:
        raise exceptions.ValidationError("Deal not found")

    current_user_id = _to_int(getattr(current_user, "id", 0))
    current_user_role = _to_str(getattr(current_user, "role", ""))
    current_user_name = _to_str(getattr(current_user, "full_name", "A user"), default="A user")

    # Check role alignment (unless admin)
    if current_user_role != sign.role and current_user_role != "admin":
        raise exceptions.AuthorizationError(f"Role mismatch: You are logged in as {current_user_role}, but trying to sign as {sign.role}")

    # Check participation (unless admin)
    participants = _participant_ids_from_deal(db_deal)
    
    if current_user_id not in participants and current_user_role != "admin":
        raise exceptions.AuthorizationError(f"Authorization failed: User ID {current_user_id} is not a valid participant in this deal.")

    result = crud.deal_sign(db, deal_id, sign)
    if not result:
        deal_status = _to_str(getattr(db_deal, "status", "unknown"), default="unknown")
        raise exceptions.BusinessLogicError(f"Cannot sign deal: Current status is '{deal_status}', but it must be 'signing_pending'")

    _audit(db, request, "deal.signed", current_user_id, deal_id, {"role": sign.role})
    await _notify_participants(
        db=db,
        deal_obj=db_deal,
        actor_user_id=current_user_id,
        title="Contract Signed",
        message=f"{current_user_name} has signed the partnership agreement.",
        notification_type="sign",
    )

    return result
