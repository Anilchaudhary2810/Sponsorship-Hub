import asyncio
import importlib
import json
from types import ModuleType
from typing import Any, Awaitable, Callable, Dict, Optional

from ..config import settings
from ..logger import logger

Handler = Callable[[dict], Awaitable[None]]


class RealtimeBus:
    """
    Optional cross-instance realtime fanout.
    - If REDIS_URL is configured and redis client is available, pub/sub is enabled.
    - Otherwise, all methods no-op and app keeps local in-memory behavior.
    """

    def __init__(self) -> None:
        self.redis_url: Optional[str] = settings.REDIS_URL
        self.handlers: Dict[str, Handler] = {}
        self.redis: Any = None
        self.pubsub: Any = None
        self.listener_task: Optional[asyncio.Task] = None
        self.enabled = bool(self.redis_url)

    def register_handler(self, channel: str, handler: Handler) -> None:
        self.handlers[channel] = handler

    @staticmethod
    def _load_redis_module() -> ModuleType | None:
        try:
            module = importlib.import_module("redis.asyncio")
            return module if isinstance(module, ModuleType) else None
        except Exception:
            return None

    async def start(self) -> None:
        if not self.enabled or not self.handlers:
            return

        redis_module = self._load_redis_module()
        if redis_module is None:
            logger.warning("Realtime bus disabled: redis.asyncio is not installed")
            self.enabled = False
            return

        try:
            redis_client = redis_module.Redis.from_url(self.redis_url, decode_responses=True)
            pubsub = redis_client.pubsub()
            await pubsub.subscribe(*self.handlers.keys())
            self.redis = redis_client
            self.pubsub = pubsub
            self.listener_task = asyncio.create_task(self._listen(), name="realtime-bus-listener")
            logger.info(f"Realtime bus enabled on {self.redis_url}")
        except Exception as exc:
            logger.warning(f"Realtime bus disabled (startup failed): {exc}")
            self.enabled = False
            self.redis = None
            self.pubsub = None
            self.listener_task = None

    async def stop(self) -> None:
        if self.listener_task:
            self.listener_task.cancel()
            try:
                await self.listener_task
            except asyncio.CancelledError:
                pass
        self.listener_task = None

        if self.pubsub:
            await self.pubsub.close()
        self.pubsub = None

        if self.redis:
            await self.redis.close()
        self.redis = None

    async def publish(self, channel: str, payload: dict) -> None:
        if not self.enabled or not self.redis:
            return
        try:
            await asyncio.wait_for(
                self.redis.publish(channel, json.dumps(payload)),
                timeout=1.0,
            )
        except Exception as exc:
            logger.warning(f"Realtime publish failed on channel '{channel}': {exc}")

    async def _listen(self) -> None:
        if not self.pubsub:
            return

        while True:
            try:
                message = await self.pubsub.get_message(
                    ignore_subscribe_messages=True,
                    timeout=1.0,
                )
                if not message:
                    await asyncio.sleep(0.05)
                    continue

                channel = str(message.get("channel", ""))
                raw_data = message.get("data")
                if not isinstance(raw_data, str):
                    continue

                handler = self.handlers.get(channel)
                if not handler:
                    continue

                payload = json.loads(raw_data)
                if isinstance(payload, dict):
                    await handler(payload)
            except asyncio.CancelledError:
                break
            except Exception as exc:
                logger.warning(f"Realtime listener error: {exc}")
                await asyncio.sleep(0.2)


realtime_bus = RealtimeBus()
