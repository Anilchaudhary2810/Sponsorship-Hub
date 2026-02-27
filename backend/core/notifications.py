from fastapi import WebSocket, WebSocketDisconnect
from typing import Dict, List, Set, Optional
import json
from sqlalchemy.orm import Session
from .. import models, database

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

    async def notify_user(self, user_id: int, message: dict):
        if user_id in self.active_connections:
            dead_connections = []
            for connection in self.active_connections[user_id]:
                try:
                    await connection.send_text(json.dumps(message))
                except Exception:
                    dead_connections.append(connection)
            
            for dead in dead_connections:
                self.disconnect(dead, user_id)

    async def broadcast_all(self, message: dict):
        for user_id in list(self.active_connections.keys()):
            await self.notify_user(user_id, message)

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
        await self.notify_user(user_id, ws_msg)
        return notif

notification_manager = NotificationManager()
