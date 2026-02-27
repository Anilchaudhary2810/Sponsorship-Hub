from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Dict
import json
from jose import jwt, JWTError

from ..database import get_db
from .. import models, schemas, crud
from ..auth import SECRET_KEY, ALGORITHM
from ..crud import get_user

router = APIRouter(prefix="/chat", tags=["chat"])

async def get_current_user_ws(token: str, db: Session):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id: str = payload.get("sub")
        if user_id is None:
            return None
        return get_user(db, int(user_id))
    except (JWTError, ValueError):
        return None

class ConnectionManager:
    def __init__(self):
        # deal_id -> List[WebSocket]
        self.active_connections: Dict[int, List[WebSocket]] = {}

    async def connect(self, websocket: WebSocket, deal_id: int):
        if deal_id not in self.active_connections:
            self.active_connections[deal_id] = []
        self.active_connections[deal_id].append(websocket)

    def disconnect(self, websocket: WebSocket, deal_id: int):
        if deal_id in self.active_connections:
            self.active_connections[deal_id].remove(websocket)
            if not self.active_connections[deal_id]:
                del self.active_connections[deal_id]

    async def broadcast(self, message: str, deal_id: int):
        if deal_id in self.active_connections:
            for connection in self.active_connections[deal_id]:
                await connection.send_text(message)

manager = ConnectionManager()

@router.get("/history/{deal_id}")
def fetch_chat_history(deal_id: int, db: Session = Depends(get_db)):
    messages = crud.get_chat_history(db, deal_id)
    result = []
    for msg in messages:
        result.append({
            "id": msg.id,
            "deal_id": msg.deal_id,
            "content": msg.content,
            "sender_id": msg.sender_id,
            "sender_role": msg.sender_role,
            "sender_name": msg.sender.full_name if msg.sender else msg.sender_role,
            "timestamp": msg.timestamp
        })
    return result

@router.websocket("/ws/{deal_id}")
async def websocket_endpoint(websocket: WebSocket, deal_id: int, token: str = Query(None), db: Session = Depends(get_db)):
    await websocket.accept()
    if not token:
        await websocket.close(code=1008)
        return
        
    user = await get_current_user_ws(token, db)
    if not user:
        await websocket.close(code=1008)
        return

    # Verify user is part of the deal
    deal = crud.get_deal(db, deal_id)
    if not deal or user.id not in [deal.sponsor_id, deal.organizer_id, deal.influencer_id]:
        await websocket.close(code=1008)
        return
    await manager.connect(websocket, deal_id)
    try:
        while True:
            data = await websocket.receive_text()
            payload = json.loads(data)
            
            # Save message to DB
            msg_create = schemas.ChatMessageCreate(
                deal_id=deal_id,
                sender_id=user.id,
                sender_role=user.role,
                content=payload["text"]
            )
            saved_msg = crud.create_chat_message(db, msg_create)
            
            # Broadcast to all participants in this deal room
            response_data = {
                "id": saved_msg.id,
                "deal_id": saved_msg.deal_id,
                "sender_id": saved_msg.sender_id,
                "sender_role": saved_msg.sender_role,
                "sender_name": user.full_name,
                "text": saved_msg.content,
                "timestamp": str(saved_msg.timestamp)
            }
            await manager.broadcast(json.dumps(response_data), deal_id)
    except WebSocketDisconnect:
        manager.disconnect(websocket, deal_id)
    except Exception:
        manager.disconnect(websocket, deal_id)
