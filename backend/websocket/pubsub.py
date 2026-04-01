import asyncio
import json
import structlog
from core.redis import get_redis
from .manager import manager

log = structlog.get_logger()

CHANNEL_PREFIX = "job_events"


def job_channel(job_id: str) -> str:
    return f"{CHANNEL_PREFIX}:{job_id}"


async def listen_for_job_events() -> None:
    """Background task: subscribe to Redis pub/sub and forward to WebSockets."""
    r = get_redis()
    pubsub = r.pubsub()
    pubsub.psubscribe(f"{CHANNEL_PREFIX}:*")
    log.info("pubsub_listening", pattern=f"{CHANNEL_PREFIX}:*")

    loop = asyncio.get_event_loop()

    while True:
        try:
            message = await loop.run_in_executor(None, _get_message, pubsub)
            if message is None:
                await asyncio.sleep(0.05)
                continue
            if message["type"] != "pmessage":
                continue

            channel: str = message["channel"]
            job_id = channel.split(":", 1)[1]
            data = json.loads(message["data"])
            await manager.broadcast(job_id, data)
        except Exception as e:
            log.error("pubsub_error", error=str(e))
            await asyncio.sleep(1)


def _get_message(pubsub):
    return pubsub.get_message(ignore_subscribe_messages=True, timeout=0.05)


def publish_job_event(job_id: str, payload: dict) -> None:
    """Publish a job event from a synchronous context (Celery worker or FastAPI)."""
    r = get_redis()
    r.publish(job_channel(job_id), json.dumps(payload))
