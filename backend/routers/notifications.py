from fastapi import APIRouter, Depends, HTTPException, status, WebSocket, WebSocketDisconnect, Request
from sqlalchemy.orm import Session
from typing import List
import json
import asyncio
from .. import models, schemas, auth, database
from ..core.notifications import notification_manager
from backend.core.limiter import limiter

router = APIRouter(
    prefix="/notifications",
    tags=['Notifications']
)

async def _safe_ws_close(websocket: WebSocket, code: int) -> None:
    try:
        await websocket.close(code=code)
    except RuntimeError:
        return

ws_router = APIRouter(
    prefix="/ws/notifications",
    tags=['WebSocket Notifications']
)

@router.get("/", response_model=List[schemas.NotificationResponse])
@limiter.limit("120/minute")
def get_my_notifications(
    request: Request,
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(auth.get_current_user)
):
    current_user_id = int(getattr(current_user, "id", 0))
    notifications = db.query(models.Notification).filter(
        models.Notification.user_id == current_user_id
    ).order_by(models.Notification.created_at.desc()).limit(20).all()
    return notifications

@router.put("/{id}/read")
@limiter.limit("120/minute")
def mark_notification_as_read(
    request: Request,
    id: int,
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(auth.get_current_user)
):
    current_user_id = int(getattr(current_user, "id", 0))
    notif = db.query(models.Notification).filter(
        models.Notification.id == id,
        models.Notification.user_id == current_user_id
    ).first()
    
    if not notif:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Notification not found")
    
    setattr(notif, "is_read", True)
    db.commit()
    return {"message": "Notification marked as read"}

@router.put("/read-all")
@limiter.limit("60/minute")
def mark_all_notifications_as_read(
    request: Request,
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(auth.get_current_user)
):
    current_user_id = int(getattr(current_user, "id", 0))
    db.query(models.Notification).filter(
        models.Notification.user_id == current_user_id,
        models.Notification.is_read == False
    ).update({"is_read": True}, synchronize_session=False)
    db.commit()
    return {"message": "All notifications marked as read"}

@ws_router.websocket("/{user_id}")
async def websocket_endpoint(websocket: WebSocket, user_id: int):
    from ..auth import decode_token_sub
    from jose import JWTError

    token = websocket.cookies.get("access_token")
    if not token:
        token = websocket.query_params.get("token")

    if not token:
        await _safe_ws_close(websocket, status.WS_1008_POLICY_VIOLATION)
        return
        
    try:
        token_user_id = decode_token_sub(token, expected_type="access")
        if int(token_user_id) != int(user_id):
            await _safe_ws_close(websocket, status.WS_1008_POLICY_VIOLATION)
            return
    except (JWTError, ValueError):
        await _safe_ws_close(websocket, status.WS_1008_POLICY_VIOLATION)
        return

    await websocket.accept()
    await notification_manager.connect(websocket, user_id)
    try:
        while True:
            try:
                raw = await asyncio.wait_for(websocket.receive_text(), timeout=30.0)
                if raw == "pong":
                    continue
            except asyncio.TimeoutError:
                try:
                    await websocket.send_text(json.dumps({"type": "ping"}))
                except Exception:
                    break
    except WebSocketDisconnect:
        notification_manager.disconnect(websocket, user_id)
    finally:
        notification_manager.disconnect(websocket, user_id)
