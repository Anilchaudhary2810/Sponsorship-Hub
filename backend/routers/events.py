from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List

from ..database import get_db
from .. import schemas, crud
from ..core.notifications import notification_manager

router = APIRouter(prefix="/events", tags=["events"])

@router.post("/", response_model=schemas.EventResponse, status_code=status.HTTP_201_CREATED)
async def create_event(event: schemas.EventCreate, db: Session = Depends(get_db)):
    result = crud.create_event(db, event)
    await notification_manager.broadcast_all({"type": "MARKETPLACE_REFRESH", "message": "New event added!"})
    return result


@router.get("/", response_model=List[schemas.EventResponse])
def list_events(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    return crud.get_events(db, skip=skip, limit=limit)


@router.get("/{event_id}", response_model=schemas.EventResponse)
def get_event(event_id: int, db: Session = Depends(get_db)):
    db_event = crud.get_event(db, event_id)
    if not db_event:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Event not found")
    return db_event


@router.put("/{event_id}", response_model=schemas.EventResponse)
async def update_event(event_id: int, event_updates: schemas.EventUpdate, db: Session = Depends(get_db)):
    db_event = crud.update_event(db, event_id, event_updates)
    if not db_event:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Event not found")
    await notification_manager.broadcast_all({"type": "MARKETPLACE_REFRESH"})
    return db_event


@router.delete("/{event_id}", response_model=schemas.EventResponse)
async def delete_event(event_id: int, db: Session = Depends(get_db)):
    db_event = crud.delete_event(db, event_id)
    if not db_event:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Event not found")
    await notification_manager.broadcast_all({"type": "MARKETPLACE_REFRESH"})
    return db_event
