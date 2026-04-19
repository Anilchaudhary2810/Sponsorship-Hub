from __future__ import annotations

from datetime import datetime
from typing import Any

from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from .. import exceptions, models, schemas
from ..core.limiter import limiter
from ..core.notifications import notification_manager
from ..database import get_db
from .auth_router import get_current_user

router = APIRouter(prefix="/proposal", tags=["Proposal Tools"])


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
        raise exceptions.AuthorizationError("You are not a participant in this deal")


def _has_required_workspace_role_for_deal(
    db: Session,
    deal_id: int,
    user_id: int,
    required_role: str,
) -> bool:
    membership = db.query(models.WorkspaceMember).join(
        models.WorkspaceResource,
        models.WorkspaceResource.workspace_id == models.WorkspaceMember.workspace_id,
    ).filter(
        models.WorkspaceResource.resource_type == "deal",
        models.WorkspaceResource.resource_id == deal_id,
        models.WorkspaceMember.user_id == user_id,
        models.WorkspaceMember.status == "active",
        models.WorkspaceMember.role == required_role,
    ).first()
    return membership is not None


@router.get("/templates", response_model=list[schemas.DealTemplateResponse])
@limiter.limit("90/minute")
def list_templates(
    request: Request,
    deal_type: schemas.DealType | None = None,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    del request
    user_id = _as_int(getattr(current_user, "id", 0))
    query = db.query(models.DealTemplate).filter(models.DealTemplate.owner_user_id == user_id)
    if deal_type:
        query = query.filter(models.DealTemplate.deal_type == deal_type)
    return query.order_by(models.DealTemplate.updated_at.desc()).all()


@router.post("/templates", response_model=schemas.DealTemplateResponse)
@limiter.limit("40/minute")
def create_template(
    request: Request,
    payload: schemas.DealTemplateCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    del request
    user_id = _as_int(getattr(current_user, "id", 0))
    new_template = models.DealTemplate(
        owner_user_id=user_id,
        name=payload.name.strip(),
        description=payload.description,
        deal_type=payload.deal_type,
        terms_json=payload.terms_json or {},
        is_default=bool(payload.is_default),
    )
    if bool(payload.is_default):
        db.query(models.DealTemplate).filter(
            models.DealTemplate.owner_user_id == user_id,
            models.DealTemplate.deal_type == payload.deal_type,
            models.DealTemplate.is_default == True,
        ).update({"is_default": False})
    db.add(new_template)
    db.commit()
    db.refresh(new_template)
    return new_template


@router.put("/templates/{template_id}", response_model=schemas.DealTemplateResponse)
@limiter.limit("40/minute")
def update_template(
    request: Request,
    template_id: int,
    payload: schemas.DealTemplateUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    del request
    user_id = _as_int(getattr(current_user, "id", 0))
    template = db.query(models.DealTemplate).filter(models.DealTemplate.id == template_id).first()
    if not template:
        raise exceptions.ValidationError("Template not found")
    if _as_int(getattr(template, "owner_user_id", 0)) != user_id:
        raise exceptions.AuthorizationError("You can only update your own templates")

    updates = payload.model_dump(exclude_unset=True)
    if updates.get("name") is not None:
        updates["name"] = str(updates["name"]).strip()

    if updates.get("is_default") is True:
        db.query(models.DealTemplate).filter(
            models.DealTemplate.owner_user_id == user_id,
            models.DealTemplate.deal_type == template.deal_type,
            models.DealTemplate.is_default == True,
            models.DealTemplate.id != template_id,
        ).update({"is_default": False})

    for key, value in updates.items():
        setattr(template, key, value)
    db.commit()
    db.refresh(template)
    return template


@router.delete("/templates/{template_id}")
@limiter.limit("30/minute")
def delete_template(
    request: Request,
    template_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    del request
    user_id = _as_int(getattr(current_user, "id", 0))
    template = db.query(models.DealTemplate).filter(models.DealTemplate.id == template_id).first()
    if not template:
        raise exceptions.ValidationError("Template not found")
    if _as_int(getattr(template, "owner_user_id", 0)) != user_id:
        raise exceptions.AuthorizationError("You can only delete your own templates")
    db.delete(template)
    db.commit()
    return {"ok": True}


@router.get("/deals/{deal_id}/approvals", response_model=list[schemas.DealApprovalResponse])
@limiter.limit("80/minute")
def list_deal_approvals(
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
    return db.query(models.DealApproval).filter(models.DealApproval.deal_id == deal_id).order_by(
        models.DealApproval.created_at.asc()
    ).all()


@router.post("/deals/{deal_id}/approvals", response_model=schemas.DealApprovalResponse)
@limiter.limit("40/minute")
async def request_deal_approval(
    request: Request,
    deal_id: int,
    payload: schemas.DealApprovalCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    del request
    deal = db.query(models.Deal).filter(models.Deal.id == deal_id).first()
    if not deal:
        raise exceptions.ValidationError("Deal not found")
    _require_deal_access(deal, current_user)

    approval = models.DealApproval(
        deal_id=deal_id,
        requested_by_user_id=_as_int(getattr(current_user, "id", 0)),
        approver_user_id=payload.approver_user_id,
        approver_role=payload.approver_role,
        status="pending",
        note=payload.note,
    )
    db.add(approval)
    deal_status = _as_str(getattr(deal, "status", ""))
    if deal_status == "proposed":
        setattr(deal, "status", "approval_pending")
        db.add(deal)
    db.commit()
    db.refresh(approval)

    for uid in _deal_participant_ids(deal):
        if uid == _as_int(getattr(current_user, "id", 0)):
            continue
        await notification_manager.push_notification(
            db,
            user_id=uid,
            title="Approval requested",
            message=f"Deal #{deal_id} requires approval before acceptance.",
            type="approval",
        )
    return approval


@router.put("/approvals/{approval_id}/decision", response_model=schemas.DealApprovalResponse)
@limiter.limit("50/minute")
async def decide_approval(
    request: Request,
    approval_id: int,
    payload: schemas.DealApprovalDecision,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    del request
    approval = db.query(models.DealApproval).filter(models.DealApproval.id == approval_id).first()
    if not approval:
        raise exceptions.ValidationError("Approval request not found")
    deal = db.query(models.Deal).filter(models.Deal.id == approval.deal_id).first()
    if not deal:
        raise exceptions.ValidationError("Deal not found")

    _require_deal_access(deal, current_user)
    current_user_id = _as_int(getattr(current_user, "id", 0))
    current_user_role = _as_str(getattr(current_user, "role", ""))

    designated_user = _as_int(getattr(approval, "approver_user_id", 0), default=0)
    if designated_user:
        if designated_user != current_user_id and current_user_role != "admin":
            raise exceptions.AuthorizationError("Only designated approver can decide this request")
    else:
        required_role = _as_str(getattr(approval, "approver_role", ""))
        if current_user_role != "admin":
            if not _has_required_workspace_role_for_deal(
                db=db,
                deal_id=_as_int(getattr(deal, "id", 0)),
                user_id=current_user_id,
                required_role=required_role,
            ):
                raise exceptions.AuthorizationError("Only approved workspace role can decide this request")

    approval_status = _as_str(getattr(approval, "status", ""))
    if approval_status != "pending":
        raise exceptions.BusinessLogicError("Approval request already decided")

    new_approval_status = "approved" if payload.decision == "approved" else "rejected"
    setattr(approval, "status", new_approval_status)
    setattr(approval, "note", payload.note or _as_str(getattr(approval, "note", ""), default=""))
    setattr(approval, "decided_at", datetime.utcnow())
    db.add(approval)

    if new_approval_status == "rejected":
        setattr(deal, "status", "rejected")
    else:
        pending = db.query(models.DealApproval).filter(
            models.DealApproval.deal_id == approval.deal_id,
            models.DealApproval.status == "pending",
        ).count()
        rejected = db.query(models.DealApproval).filter(
            models.DealApproval.deal_id == approval.deal_id,
            models.DealApproval.status == "rejected",
        ).count()
        deal_status = _as_str(getattr(deal, "status", ""))
        if pending == 0 and rejected == 0 and deal_status == "approval_pending":
            setattr(deal, "status", "proposed")
    db.add(deal)
    db.commit()
    db.refresh(approval)

    for uid in _deal_participant_ids(deal):
        await notification_manager.notify_user(uid, {"type": "DEAL_UPDATE", "deal_id": _as_int(getattr(deal, "id", 0))})

    return approval


@router.get("/deals/{deal_id}/negotiations", response_model=list[schemas.NegotiationEntryResponse])
@limiter.limit("100/minute")
def list_negotiations(
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
    return db.query(models.NegotiationEntry).filter(
        models.NegotiationEntry.deal_id == deal_id
    ).order_by(models.NegotiationEntry.created_at.asc()).all()


@router.post("/deals/{deal_id}/negotiations", response_model=schemas.NegotiationEntryResponse)
@limiter.limit("80/minute")
async def add_negotiation_entry(
    request: Request,
    deal_id: int,
    payload: schemas.NegotiationEntryCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    del request
    deal = db.query(models.Deal).filter(models.Deal.id == deal_id).first()
    if not deal:
        raise exceptions.ValidationError("Deal not found")
    _require_deal_access(deal, current_user)
    if _as_str(getattr(deal, "status", "")) in {"closed", "rejected"}:
        raise exceptions.BusinessLogicError("Negotiation is locked for this deal state")

    entry = models.NegotiationEntry(
        deal_id=deal_id,
        actor_user_id=_as_int(getattr(current_user, "id", 0)),
        change_type=payload.change_type,
        message=payload.message,
        payload=payload.payload or {},
    )
    db.add(entry)
    db.commit()
    db.refresh(entry)

    for uid in _deal_participant_ids(deal):
        if uid == _as_int(getattr(current_user, "id", 0)):
            continue
        await notification_manager.push_notification(
            db,
            user_id=uid,
            title="Negotiation update",
            message=f"Deal #{deal_id} has a new negotiation entry.",
            type="negotiation",
        )
    return entry
