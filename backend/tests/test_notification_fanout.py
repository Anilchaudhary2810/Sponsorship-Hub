import asyncio
import time

from backend.core.notifications import NotificationManager
from backend.core.realtime import realtime_bus


class _SlowWebSocket:
    async def send_text(self, payload: str) -> None:
        del payload
        await asyncio.sleep(0.1)


class _HangingWebSocket:
    async def send_text(self, payload: str) -> None:
        del payload
        await asyncio.sleep(0.2)


def test_broadcast_request_path_latency_stays_flat_with_many_connections():
    async def scenario() -> float:
        manager = NotificationManager(worker_count=1, queue_maxsize=32, enqueue_timeout_seconds=0.02)
        for uid in range(1, 801):
            manager.active_connections[uid] = {_SlowWebSocket()}

        started = time.perf_counter()
        await manager.broadcast_all({"type": "MARKETPLACE_REFRESH"}, fanout=False)
        elapsed = time.perf_counter() - started

        await manager.shutdown()
        return elapsed

    elapsed = asyncio.run(scenario())
    assert elapsed < 0.08


def test_notification_queue_backpressure_drops_when_full():
    async def scenario() -> int:
        manager = NotificationManager(worker_count=0, queue_maxsize=1, enqueue_timeout_seconds=0.01)
        await manager.notify_user(1, {"type": "A"}, fanout=False)
        await manager.notify_user(2, {"type": "B"}, fanout=False)
        dropped = manager.dropped_jobs
        await manager.shutdown()
        return dropped

    dropped_jobs = asyncio.run(scenario())
    assert dropped_jobs >= 1


def test_user_send_timeout_disconnects_stale_socket():
    async def scenario() -> bool:
        manager = NotificationManager(worker_count=1, send_timeout_seconds=0.01, enqueue_timeout_seconds=0.02)
        manager.active_connections[7] = {_HangingWebSocket()}
        await manager.notify_user(7, {"type": "PING"}, fanout=False)
        await asyncio.wait_for(manager._queue.join(), timeout=0.4)
        remaining = 7 in manager.active_connections
        await manager.shutdown()
        return remaining

    still_connected = asyncio.run(scenario())
    assert still_connected is False


def test_broadcast_prefers_pubsub_channel_over_local_iteration(monkeypatch):
    async def scenario() -> tuple[list[str], int]:
        channels: list[str] = []

        async def fake_publish(channel: str, payload: dict) -> None:
            del payload
            channels.append(channel)

        monkeypatch.setattr(realtime_bus, "enabled", True)
        monkeypatch.setattr(realtime_bus, "redis", object())
        monkeypatch.setattr(realtime_bus, "publish", fake_publish)

        manager = NotificationManager(worker_count=1)
        for uid in range(1, 50):
            manager.active_connections[uid] = {_SlowWebSocket()}

        await manager.broadcast_all({"type": "MARKETPLACE_REFRESH"}, fanout=True)
        qsize = manager._queue.qsize()
        await manager.shutdown()
        return channels, qsize

    published_channels, queue_size = asyncio.run(scenario())
    assert "notifications.broadcast" in published_channels
    assert queue_size == 0
