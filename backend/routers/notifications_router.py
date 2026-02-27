from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends, Query
from sqlalchemy.orm import Session
from ..database import get_db
from ..core.notifications import notification_manager
from ..auth import SECRET_KEY, ALGORITHM
from ..crud import get_user
from jose import jwt, JWTError
import logging

logger = logging.getLogger("sponsorship.api")

router = APIRouter(prefix="/ws", tags=["notifications"])

async def get_current_user_ws(token: str, db: Session):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id: str = payload.get("sub")
        if user_id is None:
            return None
        return get_user(db, int(user_id))
    except (JWTError, ValueError):
        return None

@router.websocket("/notifications/{user_id}")
async def notifications_endpoint(websocket: WebSocket, user_id: int, token: str = Query(None), db: Session = Depends(get_db)):
    await websocket.accept()
    if not token:
        logger.warning(f"WS connection rejected: No token provided for user {user_id}")
        await websocket.close(code=1008)
        return
        
    user = await get_current_user_ws(token, db)
    if not user:
        logger.warning(f"WS connection rejected: Invalid token for user {user_id}")
        await websocket.close(code=1008)
        return
        
    if user.id != user_id:
        logger.warning(f"WS connection rejected: ID mismatch. Token user: {user.id}, URL user: {user_id}")
        await websocket.close(code=1008)
        return

    await notification_manager.connect(websocket, user_id)
    try:
        while True:
            # Keep connection alive; backend simply waits for closes
            await websocket.receive_text()
    except WebSocketDisconnect:
        notification_manager.disconnect(websocket, user_id)
    except Exception:
        notification_manager.disconnect(websocket, user_id)
