from fastapi import WebSocket
from typing import Dict, Set, Optional, Literal
import json
import asyncio
from sqlalchemy.orm import Session

from .. import models
from ..logger import logger
from .realtime import realtime_bus

DeliveryKind = Literal["user", "broadcast"]


class NotificationManager:
    def __init__(
        self,
        queue_maxsize: int = 5000,
        worker_count: int = 2,
        send_timeout_seconds: float = 2.0,
        enqueue_timeout_seconds: float = 0.05,
    ):
        # user_id -> set of WebSocket connections
        self.active_connections: Dict[int, Set[WebSocket]] = {}
        self._queue: asyncio.Queue[tuple[DeliveryKind, Optional[int], dict]] = asyncio.Queue(
            maxsize=max(1, queue_maxsize)
        )
        self._worker_count = max(0, worker_count)
        self._workers: list[asyncio.Task] = []
        self._send_timeout_seconds = max(0.05, send_timeout_seconds)
        self._enqueue_timeout_seconds = max(0.001, enqueue_timeout_seconds)
        self.dropped_jobs = 0

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

    def _ensure_workers(self) -> None:
        if self._workers or self._worker_count <= 0:
            return

        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            return

        for idx in range(self._worker_count):
            task = loop.create_task(self._delivery_worker(), name=f"notification-delivery-worker-{idx}")
            self._workers.append(task)

    async def shutdown(self) -> None:
        for task in self._workers:
            task.cancel()
        for task in self._workers:
            try:
                await task
            except asyncio.CancelledError:
                pass
            except Exception:
                pass
        self._workers = []

    async def _enqueue_job(self, kind: DeliveryKind, user_id: Optional[int], message: dict) -> None:
        self._ensure_workers()
        try:
            await asyncio.wait_for(
                self._queue.put((kind, user_id, message)),
                timeout=self._enqueue_timeout_seconds,
            )
        except asyncio.TimeoutError:
            self.dropped_jobs += 1
            logger.warning(
                f"Notification queue backpressure: dropped {kind} job (user_id={user_id}, qsize={self._queue.qsize()})"
            )

    async def _delivery_worker(self) -> None:
        while True:
            kind, user_id, message = await self._queue.get()
            try:
                if kind == "user" and user_id is not None:
                    await self._deliver_to_user(user_id, message)
                elif kind == "broadcast":
                    await self._deliver_broadcast(message)
            except asyncio.CancelledError:
                raise
            except Exception as exc:
                logger.warning(f"Notification delivery worker error: {exc}")
            finally:
                self._queue.task_done()

    async def _deliver_to_user(self, user_id: int, message: dict) -> None:
        if user_id not in self.active_connections:
            return

        dead_connections = []
        payload = json.dumps(message)
        for connection in list(self.active_connections[user_id]):
            try:
                await asyncio.wait_for(connection.send_text(payload), timeout=self._send_timeout_seconds)
            except Exception:
                dead_connections.append(connection)

        for dead in dead_connections:
            self.disconnect(dead, user_id)

    async def _deliver_broadcast(self, message: dict) -> None:
        # Runs in worker context, not request path.
        for user_id in list(self.active_connections.keys()):
            await self._deliver_to_user(user_id, message)

    async def notify_user(self, user_id: int, message: dict, fanout: bool = True):
        broker_ready = bool(realtime_bus.enabled and getattr(realtime_bus, "redis", None))
        if fanout and broker_ready:
            await realtime_bus.publish(
                "notifications.user",
                {"user_id": user_id, "message": message}
            )
            return

        await self._enqueue_job("user", user_id, message)

        if fanout:
            # Best-effort cross-instance fanout while broker starts up.
            await realtime_bus.publish("notifications.user", {"user_id": user_id, "message": message})

    async def broadcast_all(self, message: dict, fanout: bool = True):
        broker_ready = bool(realtime_bus.enabled and getattr(realtime_bus, "redis", None))
        if fanout and broker_ready:
            await realtime_bus.publish("notifications.broadcast", {"message": message})
            return

        # Request-path work is O(1): enqueue one job for background fanout.
        await self._enqueue_job("broadcast", None, message)

        if fanout:
            # Best-effort cross-instance fanout while broker starts up.
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
