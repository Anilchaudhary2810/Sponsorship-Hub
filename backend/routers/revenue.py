from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Any

from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from .. import exceptions, models, schemas
from ..core.limiter import limiter
from ..core.notifications import notification_manager
from ..database import get_db
from .auth_router import get_current_user

router = APIRouter(prefix="/revenue", tags=["Revenue Confidence"])


def _as_int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _as_str(value: Any, default: str = "") -> str:
    if isinstance(value, str):
        return value
    return default


def _deal_participant_ids(deal: models.Deal) -> set[int]:
    ids: set[int] = set()
    for field_name in ("sponsor_id", "organizer_id", "influencer_id"):
        value = _as_int(getattr(deal, field_name, 0), default=0)
        if value > 0:
            ids.add(value)
    return ids


def _require_deal_access(deal: models.Deal, current_user: models.User) -> None:
    current_user_id = _as_int(getattr(current_user, "id", 0))
    current_user_role = _as_str(getattr(current_user, "role", ""))
    if current_user_role == "admin":
        return
    if current_user_id not in _deal_participant_ids(deal):
        raise exceptions.AuthorizationError("You are not allowed to access this deal")


def _require_sponsor_or_admin(deal: models.Deal, current_user: models.User) -> None:
    current_user_id = _as_int(getattr(current_user, "id", 0))
    current_user_role = _as_str(getattr(current_user, "role", ""))
    sponsor_id = _as_int(getattr(deal, "sponsor_id", 0))
    if current_user_role == "admin":
        return
    if current_user_id != sponsor_id:
        raise exceptions.AuthorizationError("Only sponsor (or admin) can perform this action")


def _derive_escrow_state(deal: models.Deal, milestones: list[models.DealMilestone]) -> dict[str, Any]:
    planned_total = Decimal("0")
    funded_total = Decimal("0")
    released_total = Decimal("0")
    disputed_total = Decimal("0")

    for milestone in milestones:
        amount = Decimal(str(getattr(milestone, "amount", 0) or 0))
        planned_total += amount
        status = _as_str(getattr(milestone, "status", "planned"))
        if status in {"funded", "released", "disputed"}:
            funded_total += amount
        if status == "released":
            released_total += amount
        if status == "disputed":
            disputed_total += amount

    if milestones:
        if disputed_total > 0:
            state = "disputed"
        elif released_total == planned_total and planned_total > 0:
            state = "fully_released"
        elif funded_total > released_total:
            state = "escrow_funded"
        else:
            state = "planned"
    else:
        if bool(getattr(deal, "payment_done", False)):
            state = "escrow_funded"
        else:
            state = _as_str(getattr(deal, "payment_status", "pending")) or "pending"

    return {
        "escrow_state": state,
        "planned_total": planned_total,
        "funded_total": funded_total,
        "released_total": released_total,
        "disputed_total": disputed_total,
        "currency": _as_str(getattr(deal, "currency", "INR"), default="INR"),
        "milestones_count": len(milestones),
    }


@router.get("/deals/{deal_id}/milestones", response_model=list[schemas.DealMilestoneResponse])
@limiter.limit("100/minute")
def list_milestones(
    request: Request,
    deal_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    del request
    deal = db.query(models.Deal).filter(models.Deal.id == deal_id).first()
    if not deal:
        raise exceptions.ValidationError("Deal not found")
    _require_deal_access(deal, current_user)
    return db.query(models.DealMilestone).filter(models.DealMilestone.deal_id == deal_id).order_by(
        models.DealMilestone.sequence_no.asc()
    ).all()


@router.post("/deals/{deal_id}/milestones", response_model=schemas.DealMilestoneResponse)
@limiter.limit("40/minute")
async def create_milestone(
    request: Request,
    deal_id: int,
    payload: schemas.DealMilestoneCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    del request
    deal = db.query(models.Deal).filter(models.Deal.id == deal_id).first()
    if not deal:
        raise exceptions.ValidationError("Deal not found")
    _require_deal_access(deal, current_user)

    sequence_no = payload.sequence_no
    if sequence_no is None:
        latest = db.query(models.DealMilestone).filter(models.DealMilestone.deal_id == deal_id).order_by(
            models.DealMilestone.sequence_no.desc()
        ).first()
        sequence_no = (_as_int(getattr(latest, "sequence_no", 0)) + 1) if latest else 1

    milestone = models.DealMilestone(
        deal_id=deal_id,
        sequence_no=int(sequence_no),
        title=payload.title.strip(),
        description=payload.description,
        amount=payload.amount,
        due_date=payload.due_date,
        status="planned",
    )
    db.add(milestone)
    db.commit()
    db.refresh(milestone)

    for uid in _deal_participant_ids(deal):
        if uid == _as_int(getattr(current_user, "id", 0)):
            continue
        await notification_manager.push_notification(
            db,
            user_id=uid,
            title="New milestone",
            message=f"Deal #{deal_id} has a new payout milestone: {milestone.title}",
            type="milestone",
        )
    return milestone


@router.put("/milestones/{milestone_id}/action", response_model=schemas.DealMilestoneResponse)
@limiter.limit("60/minute")
async def update_milestone_status(
    request: Request,
    milestone_id: int,
    payload: schemas.DealMilestoneAction,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    del request
    milestone = db.query(models.DealMilestone).filter(models.DealMilestone.id == milestone_id).first()
    if not milestone:
        raise exceptions.ValidationError("Milestone not found")
    deal = db.query(models.Deal).filter(models.Deal.id == milestone.deal_id).first()
    if not deal:
        raise exceptions.ValidationError("Deal not found")
    _require_deal_access(deal, current_user)

    action = payload.action
    if action in {"fund", "release"}:
        _require_sponsor_or_admin(deal, current_user)

    if action == "fund":
        milestone_status = _as_str(getattr(milestone, "status", ""))
        if milestone_status not in {"planned", "disputed"}:
            raise exceptions.BusinessLogicError("Only planned/disputed milestones can be funded")
        setattr(milestone, "status", "funded")
        setattr(milestone, "funded_at", datetime.utcnow())
    elif action == "release":
        milestone_status = _as_str(getattr(milestone, "status", ""))
        if milestone_status != "funded":
            raise exceptions.BusinessLogicError("Only funded milestones can be released")
        setattr(milestone, "status", "released")
        setattr(milestone, "released_at", datetime.utcnow())
    elif action == "mark_disputed":
        milestone_status = _as_str(getattr(milestone, "status", ""))
        if milestone_status == "released":
            raise exceptions.BusinessLogicError("Released milestone cannot be disputed")
        setattr(milestone, "status", "disputed")
    else:
        raise exceptions.ValidationError("Unsupported milestone action")

    db.add(milestone)
    db.commit()
    db.refresh(milestone)

    for uid in _deal_participant_ids(deal):
        await notification_manager.notify_user(
            uid,
            {
                "type": "MILESTONE_UPDATE",
                "deal_id": _as_int(getattr(deal, "id", 0)),
                "milestone_id": _as_int(getattr(milestone, "id", 0)),
                "status": _as_str(getattr(milestone, "status", ""), default=""),
            },
        )

    return milestone


@router.get("/deals/{deal_id}/escrow")
@limiter.limit("100/minute")
def get_escrow_state(
    request: Request,
    deal_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    del request
    deal = db.query(models.Deal).filter(models.Deal.id == deal_id).first()
    if not deal:
        raise exceptions.ValidationError("Deal not found")
    _require_deal_access(deal, current_user)
    milestones = db.query(models.DealMilestone).filter(models.DealMilestone.deal_id == deal_id).all()
    return _derive_escrow_state(deal, milestones)


@router.get("/deals/{deal_id}/disputes", response_model=list[schemas.DealDisputeResponse])
@limiter.limit("80/minute")
def list_disputes(
    request: Request,
    deal_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    del request
    deal = db.query(models.Deal).filter(models.Deal.id == deal_id).first()
    if not deal:
        raise exceptions.ValidationError("Deal not found")
    _require_deal_access(deal, current_user)
    return db.query(models.DealDispute).filter(models.DealDispute.deal_id == deal_id).order_by(
        models.DealDispute.opened_at.desc()
    ).all()


@router.post("/deals/{deal_id}/disputes", response_model=schemas.DealDisputeResponse)
@limiter.limit("30/minute")
async def open_dispute(
    request: Request,
    deal_id: int,
    payload: schemas.DealDisputeCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    del request
    deal = db.query(models.Deal).filter(models.Deal.id == deal_id).first()
    if not deal:
        raise exceptions.ValidationError("Deal not found")
    _require_deal_access(deal, current_user)

    dispute = models.DealDispute(
        deal_id=deal_id,
        opened_by_user_id=_as_int(getattr(current_user, "id", 0)),
        reason=payload.reason.strip(),
        details=payload.details,
        status="open",
    )
    db.add(dispute)

    # If there are active funded milestones, mark them disputed.
    milestones = db.query(models.DealMilestone).filter(
        models.DealMilestone.deal_id == deal_id,
        models.DealMilestone.status.in_(["planned", "funded"]),
    ).all()
    for milestone in milestones:
        setattr(milestone, "status", "disputed")
        db.add(milestone)

    db.commit()
    db.refresh(dispute)

    for uid in _deal_participant_ids(deal):
        if uid == _as_int(getattr(current_user, "id", 0)):
            continue
        await notification_manager.push_notification(
            db,
            user_id=uid,
            title="Dispute opened",
            message=f"A dispute was opened for deal #{deal_id}: {dispute.reason}",
            type="dispute",
        )
    return dispute


@router.put("/disputes/{dispute_id}/resolve", response_model=schemas.DealDisputeResponse)
@limiter.limit("40/minute")
async def resolve_dispute(
    request: Request,
    dispute_id: int,
    payload: schemas.DealDisputeResolve,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    del request
    dispute = db.query(models.DealDispute).filter(models.DealDispute.id == dispute_id).first()
    if not dispute:
        raise exceptions.ValidationError("Dispute not found")
    deal = db.query(models.Deal).filter(models.Deal.id == dispute.deal_id).first()
    if not deal:
        raise exceptions.ValidationError("Deal not found")

    _require_sponsor_or_admin(deal, current_user)

    setattr(dispute, "status", payload.decision)
    setattr(dispute, "resolution_note", payload.resolution_note)
    setattr(dispute, "settlement_amount", payload.settlement_amount)
    if payload.decision in {"resolved", "rejected"}:
        setattr(dispute, "resolved_at", datetime.utcnow())

    db.add(dispute)
    db.commit()
    db.refresh(dispute)

    for uid in _deal_participant_ids(deal):
        await notification_manager.notify_user(
            uid,
            {
                "type": "DISPUTE_UPDATE",
                "deal_id": _as_int(getattr(deal, "id", 0)),
                "dispute_id": _as_int(getattr(dispute, "id", 0)),
                "status": _as_str(getattr(dispute, "status", ""), default=""),
            },
        )
    return dispute


@router.get("/deals/{deal_id}/payout-summary")
@limiter.limit("80/minute")
def payout_summary(
    request: Request,
    deal_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    del request
    deal = db.query(models.Deal).filter(models.Deal.id == deal_id).first()
    if not deal:
        raise exceptions.ValidationError("Deal not found")
    _require_deal_access(deal, current_user)
    milestones = db.query(models.DealMilestone).filter(models.DealMilestone.deal_id == deal_id).all()
    escrow = _derive_escrow_state(deal, milestones)

    milestone_rows = [
        {
            "id": int(getattr(m, "id", 0)),
            "sequence_no": int(getattr(m, "sequence_no", 0)),
            "title": _as_str(getattr(m, "title", ""), default=""),
            "amount": Decimal(str(getattr(m, "amount", 0) or 0)),
            "status": _as_str(getattr(m, "status", "planned"), default="planned"),
        }
        for m in sorted(milestones, key=lambda x: _as_int(getattr(x, "sequence_no", 0)))
    ]
    return {"deal_id": deal_id, "escrow": escrow, "milestones": milestone_rows}
