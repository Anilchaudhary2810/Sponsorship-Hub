from fastapi import WebSocket
from typing import Dict, Set
import json
import asyncio
from sqlalchemy.orm import Session
from .. import models
from .realtime import realtime_bus

class NotificationManager:
    def __init__(self):
        # user_id -> set of WebSocket connections
        self.active_connections: Dict[int, Set[WebSocket]] = {}

    async def connect(self, websocket: WebSocket, user_id: int):
        if user_id not in self.active_connections:
            self.active_connections[user_id] = set()
        self.active_connections[user_id].add(websocket)

    def disconnect(self, websocket: WebSocket, user_id: int):
        if user_id in self.active_connections:
            if websocket in self.active_connections[user_id]:
                self.active_connections[user_id].remove(websocket)
            if not self.active_connections[user_id]:
                del self.active_connections[user_id]

    async def notify_user(self, user_id: int, message: dict, fanout: bool = True):
        if user_id in self.active_connections:
            dead_connections = []
            for connection in self.active_connections[user_id]:
                try:
                    await asyncio.wait_for(connection.send_text(json.dumps(message)), timeout=2.0)
                except Exception:
                    dead_connections.append(connection)
            
            for dead in dead_connections:
                self.disconnect(dead, user_id)

        if fanout:
            await realtime_bus.publish(
                "notifications.user",
                {"user_id": user_id, "message": message}
            )

    async def broadcast_all(self, message: dict, fanout: bool = True):
        for user_id in list(self.active_connections.keys()):
            await self.notify_user(user_id, message, fanout=False)

        if fanout:
            await realtime_bus.publish("notifications.broadcast", {"message": message})

    async def push_notification(self, db: Session, user_id: int, title: str, message: str, type: str):
        """Creates a DB notification and sends it via WebSocket"""
        notif = models.Notification(
            user_id=user_id,
            title=title,
            message=message,
            type=type
        )
        db.add(notif)
        db.commit()
        db.refresh(notif)
        
        # Pull latest stats to push via WebSocket too
        # Example type: "DEAL_UPDATE", "NEW_APPLICATION"
        ws_msg = {
            "title": title,
            "message": message,
            "type": type,
            "notif_id": notif.id,
            "created_at": notif.created_at.isoformat()
        }
        await self.notify_user(user_id, ws_msg, fanout=True)
        return notif

notification_manager = NotificationManager()


async def _handle_user_notification(payload: dict) -> None:
    user_id_raw = payload.get("user_id")
    message = payload.get("message")

    if user_id_raw is None or not isinstance(message, dict):
        return

    try:
        user_id = int(user_id_raw)
    except (TypeError, ValueError):
        return

    await notification_manager.notify_user(user_id, message, fanout=False)


async def _handle_broadcast_notification(payload: dict) -> None:
    message = payload.get("message")
    if not isinstance(message, dict):
        return
    await notification_manager.broadcast_all(message, fanout=False)


realtime_bus.register_handler("notifications.user", _handle_user_notification)
realtime_bus.register_handler("notifications.broadcast", _handle_broadcast_notification)
