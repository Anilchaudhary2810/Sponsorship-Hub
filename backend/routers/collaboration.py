from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session, joinedload

from .. import exceptions, models, schemas
from ..core.audit import log_audit_event
from ..core.limiter import limiter
from ..database import get_db
from .auth_router import get_current_user

router = APIRouter(prefix="/collaboration", tags=["Team Collaboration"])


def _as_int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _as_str(value: Any, default: str = "") -> str:
    if isinstance(value, str):
        return value
    return default


def _client_ip(request: Request) -> str:
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    if request.client and request.client.host:
        return request.client.host
    return "unknown"


def _user_agent(request: Request) -> str:
    return request.headers.get("user-agent", "")


def _is_admin(user: models.User) -> bool:
    return _as_str(getattr(user, "role", "")) == "admin"


def _enforce_role_transition(
    actor_workspace_role: str,
    actor_is_admin: bool,
    target_current_role: str | None,
    target_new_role: str,
) -> None:
    if actor_is_admin:
        return

    # High-privilege role assignment: only workspace owner (or admin) can grant owner.
    if target_new_role == "owner" and actor_workspace_role != "owner":
        raise exceptions.AuthorizationError("Only workspace owner/admin can assign owner role")

    if actor_workspace_role == "manager":
        # Managers cannot elevate above manager and cannot mutate an owner member.
        if target_new_role == "owner":
            raise exceptions.AuthorizationError("Managers cannot assign owner role")
        if target_current_role == "owner":
            raise exceptions.AuthorizationError("Managers cannot modify owner role")


def _log_role_change(
    db: Session,
    request: Request,
    actor_user: models.User,
    workspace_id: int,
    member: models.WorkspaceMember,
    previous_role: str | None,
    new_role: str,
    source: str,
) -> None:
    actor_user_id = _as_int(getattr(actor_user, "id", 0))
    member_id = _as_int(getattr(member, "id", 0))
    member_user_id = _as_int(getattr(member, "user_id", 0))
    log_audit_event(
        db,
        action="collaboration.member_role_changed",
        actor_user_id=actor_user_id,
        target_type="workspace_member",
        target_id=member_id,
        ip_address=_client_ip(request),
        user_agent=_user_agent(request),
        metadata={
            "workspace_id": workspace_id,
            "member_user_id": member_user_id,
            "from_role": previous_role,
            "to_role": new_role,
            "source": source,
        },
    )


def _workspace_member_record(db: Session, workspace_id: int, user_id: int) -> models.WorkspaceMember | None:
    return db.query(models.WorkspaceMember).filter(
        models.WorkspaceMember.workspace_id == workspace_id,
        models.WorkspaceMember.user_id == user_id,
        models.WorkspaceMember.status == "active",
    ).first()


def _require_workspace_access(db: Session, workspace_id: int, current_user: models.User) -> tuple[models.Workspace, str]:
    workspace = db.query(models.Workspace).filter(models.Workspace.id == workspace_id).first()
    if not workspace:
        raise exceptions.ValidationError("Workspace not found")

    user_id = _as_int(getattr(current_user, "id", 0))
    role = _as_str(getattr(current_user, "role", ""))
    if role == "admin":
        return workspace, "owner"

    member = _workspace_member_record(db, workspace_id, user_id)
    if not member:
        raise exceptions.AuthorizationError("You are not a member of this workspace")
    return workspace, _as_str(getattr(member, "role", "viewer"), default="viewer")


def _require_workspace_manage_permission(member_role: str) -> None:
    if member_role not in {"owner", "manager"}:
        raise exceptions.AuthorizationError("Owner/Manager permission required")


@router.post("/workspaces", response_model=schemas.WorkspaceResponse)
@limiter.limit("20/minute")
def create_workspace(
    request: Request,
    payload: schemas.WorkspaceCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    user_id = _as_int(getattr(current_user, "id", 0))
    workspace = models.Workspace(name=payload.name.strip(), owner_user_id=user_id, is_active=True)
    db.add(workspace)
    db.commit()
    db.refresh(workspace)

    owner_member = models.WorkspaceMember(
        workspace_id=workspace.id,
        user_id=user_id,
        role="owner",
        status="active",
        invited_by_user_id=user_id,
    )
    db.add(owner_member)
    db.commit()

    workspace = db.query(models.Workspace).options(joinedload(models.Workspace.members)).filter(
        models.Workspace.id == workspace.id
    ).first()
    if workspace is None:
        raise exceptions.ValidationError("Workspace creation failed")
    return workspace


@router.get("/workspaces", response_model=list[schemas.WorkspaceResponse])
@limiter.limit("100/minute")
def list_workspaces(
    request: Request,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    del request
    user_id = _as_int(getattr(current_user, "id", 0))
    current_role = _as_str(getattr(current_user, "role", ""))

    if current_role == "admin":
        return db.query(models.Workspace).options(joinedload(models.Workspace.members)).order_by(
            models.Workspace.updated_at.desc()
        ).limit(200).all()

    workspace_ids = db.query(models.WorkspaceMember.workspace_id).filter(
        models.WorkspaceMember.user_id == user_id,
        models.WorkspaceMember.status == "active",
    ).all()
    ids = [wid for (wid,) in workspace_ids]
    if not ids:
        return []
    return db.query(models.Workspace).options(joinedload(models.Workspace.members)).filter(
        models.Workspace.id.in_(ids)
    ).order_by(models.Workspace.updated_at.desc()).all()


@router.get("/workspaces/{workspace_id}", response_model=schemas.WorkspaceResponse)
@limiter.limit("100/minute")
def get_workspace(
    request: Request,
    workspace_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    del request
    workspace, _ = _require_workspace_access(db, workspace_id, current_user)
    full_workspace = db.query(models.Workspace).options(joinedload(models.Workspace.members)).filter(
        models.Workspace.id == workspace.id
    ).first()
    if full_workspace is None:
        raise exceptions.ValidationError("Workspace not found")
    return full_workspace


@router.post("/workspaces/{workspace_id}/members", response_model=schemas.WorkspaceMemberResponse)
@limiter.limit("40/minute")
def invite_member(
    request: Request,
    workspace_id: int,
    payload: schemas.WorkspaceMemberInvite,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    _, member_role = _require_workspace_access(db, workspace_id, current_user)
    _require_workspace_manage_permission(member_role)
    actor_is_admin = _is_admin(current_user)

    existing = db.query(models.WorkspaceMember).filter(
        models.WorkspaceMember.workspace_id == workspace_id,
        models.WorkspaceMember.user_id == payload.user_id,
    ).first()
    if existing:
        previous_role = _as_str(getattr(existing, "role", ""), default="")
        new_role = payload.role
        _enforce_role_transition(
            actor_workspace_role=member_role,
            actor_is_admin=actor_is_admin,
            target_current_role=previous_role,
            target_new_role=new_role,
        )
        setattr(existing, "role", payload.role)
        setattr(existing, "status", "active")
        setattr(existing, "invited_by_user_id", _as_int(getattr(current_user, "id", 0)))
        db.add(existing)
        db.commit()
        db.refresh(existing)
        if previous_role != new_role:
            _log_role_change(
                db=db,
                request=request,
                actor_user=current_user,
                workspace_id=workspace_id,
                member=existing,
                previous_role=previous_role,
                new_role=new_role,
                source="invite_existing",
            )
        return existing

    _enforce_role_transition(
        actor_workspace_role=member_role,
        actor_is_admin=actor_is_admin,
        target_current_role=None,
        target_new_role=payload.role,
    )
    invited = models.WorkspaceMember(
        workspace_id=workspace_id,
        user_id=payload.user_id,
        role=payload.role,
        status="active",
        invited_by_user_id=_as_int(getattr(current_user, "id", 0)),
    )
    db.add(invited)
    db.commit()
    db.refresh(invited)
    _log_role_change(
        db=db,
        request=request,
        actor_user=current_user,
        workspace_id=workspace_id,
        member=invited,
        previous_role=None,
        new_role=_as_str(getattr(invited, "role", "")),
        source="invite_new",
    )
    return invited


@router.put("/workspaces/{workspace_id}/members/{member_id}", response_model=schemas.WorkspaceMemberResponse)
@limiter.limit("40/minute")
def update_member(
    request: Request,
    workspace_id: int,
    member_id: int,
    payload: schemas.WorkspaceMemberUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    _, member_role = _require_workspace_access(db, workspace_id, current_user)
    _require_workspace_manage_permission(member_role)
    actor_is_admin = _is_admin(current_user)

    member = db.query(models.WorkspaceMember).filter(
        models.WorkspaceMember.workspace_id == workspace_id,
        models.WorkspaceMember.id == member_id,
    ).first()
    if not member:
        raise exceptions.ValidationError("Workspace member not found")

    previous_role = _as_str(getattr(member, "role", ""), default="")
    if member_role == "manager" and not actor_is_admin and previous_role == "owner":
        raise exceptions.AuthorizationError("Managers cannot modify owner membership")

    if payload.role is not None:
        _enforce_role_transition(
            actor_workspace_role=member_role,
            actor_is_admin=actor_is_admin,
            target_current_role=previous_role,
            target_new_role=payload.role,
        )
        setattr(member, "role", payload.role)
    if payload.status is not None:
        setattr(member, "status", payload.status)
    db.add(member)
    db.commit()
    db.refresh(member)
    current_role = _as_str(getattr(member, "role", ""), default="")
    if payload.role is not None and previous_role != current_role:
        _log_role_change(
            db=db,
            request=request,
            actor_user=current_user,
            workspace_id=workspace_id,
            member=member,
            previous_role=previous_role,
            new_role=current_role,
            source="update_member",
        )
    return member


@router.delete("/workspaces/{workspace_id}/members/{member_id}")
@limiter.limit("30/minute")
def remove_member(
    request: Request,
    workspace_id: int,
    member_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    del request
    workspace, member_role = _require_workspace_access(db, workspace_id, current_user)
    _require_workspace_manage_permission(member_role)

    member = db.query(models.WorkspaceMember).filter(
        models.WorkspaceMember.workspace_id == workspace_id,
        models.WorkspaceMember.id == member_id,
    ).first()
    if not member:
        raise exceptions.ValidationError("Workspace member not found")

    if _as_int(getattr(member, "user_id", 0)) == _as_int(getattr(workspace, "owner_user_id", 0)):
        raise exceptions.BusinessLogicError("Workspace owner cannot be removed")

    setattr(member, "status", "removed")
    db.add(member)
    db.commit()
    return {"ok": True}


@router.get("/workspaces/{workspace_id}/resources", response_model=list[schemas.WorkspaceResourceResponse])
@limiter.limit("80/minute")
def list_workspace_resources(
    request: Request,
    workspace_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    del request
    _require_workspace_access(db, workspace_id, current_user)
    return db.query(models.WorkspaceResource).filter(
        models.WorkspaceResource.workspace_id == workspace_id
    ).order_by(models.WorkspaceResource.created_at.desc()).all()


@router.post("/workspaces/{workspace_id}/resources", response_model=schemas.WorkspaceResourceResponse)
@limiter.limit("50/minute")
def add_workspace_resource(
    request: Request,
    workspace_id: int,
    payload: schemas.WorkspaceResourceAdd,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    del request
    _, member_role = _require_workspace_access(db, workspace_id, current_user)
    _require_workspace_manage_permission(member_role)

    existing = db.query(models.WorkspaceResource).filter(
        models.WorkspaceResource.workspace_id == workspace_id,
        models.WorkspaceResource.resource_type == payload.resource_type,
        models.WorkspaceResource.resource_id == payload.resource_id,
    ).first()
    if existing:
        return existing

    resource = models.WorkspaceResource(
        workspace_id=workspace_id,
        resource_type=payload.resource_type,
        resource_id=payload.resource_id,
        added_by_user_id=_as_int(getattr(current_user, "id", 0)),
    )
    db.add(resource)
    db.commit()
    db.refresh(resource)
    return resource


@router.delete("/workspaces/{workspace_id}/resources/{resource_row_id}")
@limiter.limit("40/minute")
def delete_workspace_resource(
    request: Request,
    workspace_id: int,
    resource_row_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    del request
    _, member_role = _require_workspace_access(db, workspace_id, current_user)
    _require_workspace_manage_permission(member_role)

    resource = db.query(models.WorkspaceResource).filter(
        models.WorkspaceResource.workspace_id == workspace_id,
        models.WorkspaceResource.id == resource_row_id,
    ).first()
    if not resource:
        raise exceptions.ValidationError("Workspace resource not found")
    db.delete(resource)
    db.commit()
    return {"ok": True}
