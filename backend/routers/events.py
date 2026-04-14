from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.orm import Session
from typing import List

from ..database import get_db
from .. import schemas, crud, exceptions
from ..core.notifications import notification_manager
from backend.core.limiter import limiter
from ..core.pagination import clamp_limit
from .auth_router import get_current_user
from ..models import User

router = APIRouter(prefix="/events", tags=["events"])

@router.post("/", response_model=schemas.EventResponse, status_code=status.HTTP_201_CREATED)
@limiter.limit("20/minute")
async def create_event(
    request: Request,
    event: schemas.EventCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    user_role = str(getattr(current_user, "role", ""))
    user_id = int(getattr(current_user, "id", 0))
    organizer_id = int(getattr(event, "organizer_id", 0))

    if user_role not in {"organizer", "admin"}:
        raise exceptions.AuthorizationError("Only organizers can create events")
    if user_role != "admin" and organizer_id != user_id:
        raise exceptions.AuthorizationError("You can only create events for your own account")

    result = crud.create_event(db, event)
    await notification_manager.broadcast_all({"type": "MARKETPLACE_REFRESH", "message": "New event added!"})
    return result


@router.get("/", response_model=List[schemas.EventResponse])
@limiter.limit("90/minute")
def list_events(request: Request, skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    safe_limit = clamp_limit(limit, default=20, maximum=100)
    safe_skip = max(0, int(skip))
    return crud.get_events(db, skip=safe_skip, limit=safe_limit)


@router.get("/{event_id}", response_model=schemas.EventResponse)
def get_event(event_id: int, db: Session = Depends(get_db)):
    db_event = crud.get_event(db, event_id)
    if not db_event:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Event not found")
    return db_event


@router.put("/{event_id}", response_model=schemas.EventResponse)
@limiter.limit("30/minute")
async def update_event(
    request: Request,
    event_id: int,
    event_updates: schemas.EventUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    existing = crud.get_event(db, event_id)
    if not existing:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Event not found")

    user_role = str(getattr(current_user, "role", ""))
    user_id = int(getattr(current_user, "id", 0))
    existing_organizer_id = int(getattr(existing, "organizer_id", 0))
    if user_role != "admin" and existing_organizer_id != user_id:
        raise exceptions.AuthorizationError("You can only update your own events")

    db_event = crud.update_event(db, event_id, event_updates)
    if not db_event:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Event not found")
    await notification_manager.broadcast_all({"type": "MARKETPLACE_REFRESH"})
    return db_event


@router.delete("/{event_id}", response_model=schemas.EventResponse)
@limiter.limit("20/minute")
async def delete_event(
    request: Request,
    event_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    existing = crud.get_event(db, event_id)
    if not existing:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Event not found")

    user_role = str(getattr(current_user, "role", ""))
    user_id = int(getattr(current_user, "id", 0))
    existing_organizer_id = int(getattr(existing, "organizer_id", 0))
    if user_role != "admin" and existing_organizer_id != user_id:
        raise exceptions.AuthorizationError("You can only delete your own events")

    db_event = crud.delete_event(db, event_id)
    if not db_event:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Event not found")
    await notification_manager.broadcast_all({"type": "MARKETPLACE_REFRESH"})
    return db_event
