from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends, Request
from sqlalchemy.orm import Session
from typing import List, Dict, Optional
import json
import asyncio
from jose import JWTError

from ..database import get_db
from .. import models, schemas, crud, exceptions
from ..auth import decode_token_sub, get_current_user
from ..crud import get_user
from ..core.realtime import realtime_bus
from backend.core.limiter import limiter

router = APIRouter(prefix="/chat", tags=["chat"])


async def get_current_user_ws(token: str, db: Session):
    try:
        user_id = decode_token_sub(token, expected_type="access")
        return get_user(db, int(user_id))
    except (JWTError, exceptions.AuthenticationError, ValueError):
        return None


class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[int, List[WebSocket]] = {}

    async def connect(self, websocket: WebSocket, deal_id: int):
        if deal_id not in self.active_connections:
            self.active_connections[deal_id] = []
        self.active_connections[deal_id].append(websocket)

    def disconnect(self, websocket: WebSocket, deal_id: int):
        if deal_id in self.active_connections:
            if websocket in self.active_connections[deal_id]:
                self.active_connections[deal_id].remove(websocket)
            if not self.active_connections[deal_id]:
                del self.active_connections[deal_id]

    async def broadcast(self, message: str, deal_id: int, fanout: bool = True):
        if deal_id in self.active_connections:
            dead_connections: List[WebSocket] = []
            for connection in self.active_connections[deal_id]:
                try:
                    await asyncio.wait_for(connection.send_text(message), timeout=2.0)
                except Exception:
                    dead_connections.append(connection)

            for dead in dead_connections:
                self.disconnect(dead, deal_id)

        if fanout:
            await realtime_bus.publish("chat.deal", {"deal_id": deal_id, "message": message})


manager = ConnectionManager()


async def _handle_chat_fanout(payload: dict) -> None:
    deal_id = payload.get("deal_id")
    message = payload.get("message")

    if deal_id is None or not isinstance(message, str):
        return

    try:
        resolved_deal_id = int(deal_id)
    except (TypeError, ValueError):
        return

    await manager.broadcast(message, resolved_deal_id, fanout=False)


realtime_bus.register_handler("chat.deal", _handle_chat_fanout)


@router.get("/history/{deal_id}")
@limiter.limit("60/minute")
def fetch_chat_history(
    request: Request,
    deal_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    deal = crud.get_deal(db, deal_id)
    if not deal:
        raise exceptions.ValidationError("Deal not found")

    current_user_id = int(getattr(current_user, "id", 0))
    current_user_role = str(getattr(current_user, "role", ""))
    sponsor_id = getattr(deal, "sponsor_id", None)
    organizer_id = getattr(deal, "organizer_id", None)
    influencer_id = getattr(deal, "influencer_id", None)

    participant_ids = {
        int(sponsor_id) if sponsor_id is not None else -1,
        int(organizer_id) if organizer_id is not None else -1,
        int(influencer_id) if influencer_id is not None else -1,
    }

    if current_user_id not in participant_ids and current_user_role != "admin":
        raise exceptions.AuthorizationError("You are not allowed to access this chat history")

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
async def websocket_endpoint(websocket: WebSocket, deal_id: int, db: Session = Depends(get_db)):
    async def _safe_ws_close(code: int) -> None:
        try:
            await websocket.close(code=code)
        except RuntimeError:
            return

    await websocket.accept()

    token = websocket.cookies.get("access_token")

    # Backward-compatible fallback: first message can be auth envelope {"type":"auth","token":"..."}
    if not token:
        try:
            initial_message = await websocket.receive_text()
            payload = json.loads(initial_message)
            if isinstance(payload, dict) and payload.get("type") == "auth" and isinstance(payload.get("token"), str):
                token = payload["token"]
        except Exception:
            token = None

    if not token:
        await _safe_ws_close(code=1008)
        return

    user = await get_current_user_ws(token, db)
    if not user:
        await _safe_ws_close(code=1008)
        return

    deal = crud.get_deal(db, deal_id)
    if not deal:
        await _safe_ws_close(code=1008)
        return

    user_id = int(getattr(user, "id", 0))
    sponsor_id = getattr(deal, "sponsor_id", None)
    organizer_id = getattr(deal, "organizer_id", None)
    influencer_id = getattr(deal, "influencer_id", None)
    participant_ids = {
        int(sponsor_id) if sponsor_id is not None else -1,
        int(organizer_id) if organizer_id is not None else -1,
        int(influencer_id) if influencer_id is not None else -1,
    }
    if user_id not in participant_ids:
        await _safe_ws_close(code=1008)
        return

    await manager.connect(websocket, deal_id)
    try:
        while True:
            try:
                data = await asyncio.wait_for(websocket.receive_text(), timeout=30.0)
            except asyncio.TimeoutError:
                try:
                    await websocket.send_text(json.dumps({"type": "ping"}))
                except Exception:
                    break
                continue
            payload = json.loads(data)
            text = payload.get("text") if isinstance(payload, dict) else None
            if not isinstance(text, str) or not text.strip():
                continue
            if len(text) > 4000:
                continue

            msg_create = schemas.ChatMessageCreate(
                deal_id=deal_id,
                sender_id=user_id,
                sender_role=str(getattr(user, "role", "")),
                content=text,
            )
            saved_msg = crud.create_chat_message(db, msg_create)

            response_data = {
                "id": saved_msg.id,
                "deal_id": saved_msg.deal_id,
                "sender_id": saved_msg.sender_id,
                "sender_role": saved_msg.sender_role,
                "sender_name": str(getattr(user, "full_name", "User")),
                "text": saved_msg.content,
                "timestamp": str(saved_msg.timestamp)
            }
            await manager.broadcast(json.dumps(response_data), deal_id, fanout=True)
    except WebSocketDisconnect:
        manager.disconnect(websocket, deal_id)
    except Exception:
        manager.disconnect(websocket, deal_id)
    finally:
        manager.disconnect(websocket, deal_id)
