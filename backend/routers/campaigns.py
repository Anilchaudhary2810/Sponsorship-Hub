from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List

from ..database import get_db
from .. import schemas, crud
from ..core.notifications import notification_manager

router = APIRouter(prefix="/campaigns", tags=["campaigns"])

@router.post("/", response_model=schemas.CampaignResponse, status_code=status.HTTP_201_CREATED)
async def create_campaign(campaign: schemas.CampaignCreate, db: Session = Depends(get_db)):
    result = crud.create_campaign(db, campaign)
    await notification_manager.broadcast_all({"type": "MARKETPLACE_REFRESH", "message": "Brand campaign published!"})
    return result


@router.get("/", response_model=List[schemas.CampaignResponse])
def list_campaigns(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    return crud.get_campaigns(db, skip=skip, limit=limit)


@router.get("/{campaign_id}", response_model=schemas.CampaignResponse)
def get_campaign(campaign_id: int, db: Session = Depends(get_db)):
    db_campaign = crud.get_campaign(db, campaign_id)
    if not db_campaign:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Campaign not found")
    return db_campaign


@router.put("/{campaign_id}", response_model=schemas.CampaignResponse)
async def update_campaign(campaign_id: int, updates: schemas.CampaignUpdate, db: Session = Depends(get_db)):
    db_campaign = crud.update_campaign(db, campaign_id, updates)
    if not db_campaign:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Campaign not found")
    await notification_manager.broadcast_all({"type": "MARKETPLACE_REFRESH"})
    return db_campaign


@router.delete("/{campaign_id}")
async def delete_campaign(campaign_id: int, db: Session = Depends(get_db)):
    db_campaign = crud.delete_campaign(db, campaign_id)
    if not db_campaign:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Campaign not found")
    await notification_manager.broadcast_all({"type": "MARKETPLACE_REFRESH"})
    return {"message": "Campaign deleted successfully"}
