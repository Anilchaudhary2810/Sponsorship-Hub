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

router = APIRouter(prefix="/campaigns", tags=["campaigns"])

@router.post("/", response_model=schemas.CampaignResponse, status_code=status.HTTP_201_CREATED)
@limiter.limit("20/minute")
async def create_campaign(
    request: Request,
    campaign: schemas.CampaignCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    user_role = str(getattr(current_user, "role", ""))
    user_id = int(getattr(current_user, "id", 0))
    creator_id = int(getattr(campaign, "creator_id", 0))

    if user_role not in {"sponsor", "admin"}:
        raise exceptions.AuthorizationError("Only sponsors can create campaigns")
    if user_role != "admin" and creator_id != user_id:
        raise exceptions.AuthorizationError("You can only create campaigns for your own account")

    result = crud.create_campaign(db, campaign)
    await notification_manager.broadcast_all({"type": "MARKETPLACE_REFRESH", "message": "Brand campaign published!"})
    return result


@router.get("/", response_model=List[schemas.CampaignResponse])
@limiter.limit("90/minute")
def list_campaigns(request: Request, skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    safe_limit = clamp_limit(limit, default=20, maximum=100)
    safe_skip = max(0, int(skip))
    return crud.get_campaigns(db, skip=safe_skip, limit=safe_limit)


@router.get("/{campaign_id}", response_model=schemas.CampaignResponse)
def get_campaign(campaign_id: int, db: Session = Depends(get_db)):
    db_campaign = crud.get_campaign(db, campaign_id)
    if not db_campaign:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Campaign not found")
    return db_campaign


@router.put("/{campaign_id}", response_model=schemas.CampaignResponse)
@limiter.limit("30/minute")
async def update_campaign(
    request: Request,
    campaign_id: int,
    updates: schemas.CampaignUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    existing = crud.get_campaign(db, campaign_id)
    if not existing:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Campaign not found")

    user_role = str(getattr(current_user, "role", ""))
    user_id = int(getattr(current_user, "id", 0))
    existing_creator_id = int(getattr(existing, "creator_id", 0))
    if user_role != "admin" and existing_creator_id != user_id:
        raise exceptions.AuthorizationError("You can only update your own campaigns")

    db_campaign = crud.update_campaign(db, campaign_id, updates)
    if not db_campaign:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Campaign not found")
    await notification_manager.broadcast_all({"type": "MARKETPLACE_REFRESH"})
    return db_campaign


@router.delete("/{campaign_id}")
@limiter.limit("20/minute")
async def delete_campaign(
    request: Request,
    campaign_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    existing = crud.get_campaign(db, campaign_id)
    if not existing:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Campaign not found")

    user_role = str(getattr(current_user, "role", ""))
    user_id = int(getattr(current_user, "id", 0))
    existing_creator_id = int(getattr(existing, "creator_id", 0))
    if user_role != "admin" and existing_creator_id != user_id:
        raise exceptions.AuthorizationError("You can only delete your own campaigns")

    db_campaign = crud.delete_campaign(db, campaign_id)
    if not db_campaign:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Campaign not found")
    await notification_manager.broadcast_all({"type": "MARKETPLACE_REFRESH"})
    return {"message": "Campaign deleted successfully"}
