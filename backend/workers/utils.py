"""Utilities shared by all Celery workers."""
from __future__ import annotations
from datetime import datetime, timezone
from typing import Optional
import json
import structlog
from celery.exceptions import Retry
from botocore.exceptions import BotoCoreError
from redis.exceptions import RedisError

from core.database import SessionLocal
from core.redis import get_redis
from models.job import Job, JobStatus

log = structlog.get_logger()

WS_CHANNEL_PREFIX = "job_events"
RETRYABLE_EXCEPTIONS = (OSError, ConnectionError, TimeoutError, BotoCoreError, RedisError)


def update_job(
    job_id: str,
    status: JobStatus,
    *,
    output_keys: Optional[list] = None,
    seed_used: Optional[int] = None,
    duration_seconds: Optional[float] = None,
    error: Optional[str] = None,
) -> None:
    """Update job record in DB and publish WebSocket event."""
    db = SessionLocal()
    try:
        job = db.get(Job, job_id)
        if job is None:
            log.error("job_not_found", job_id=job_id)
            return

        job.status = status
        now = datetime.now(timezone.utc)

        if status == JobStatus.running and job.started_at is None:
            job.started_at = now
        if status in (JobStatus.done, JobStatus.failed, JobStatus.cancelled):
            job.completed_at = now

        if output_keys is not None:
            job.output_keys = output_keys
        if seed_used is not None:
            job.seed_used = seed_used
        if duration_seconds is not None:
            job.duration_seconds = duration_seconds
        if error is not None:
            job.error = error

        db.commit()
        log.info("job_updated", job_id=job_id, status=status.value)
    finally:
        db.close()

    publish_ws_event(job_id, status=status.value, output_keys=output_keys, error=error)


def publish_ws_event(
    job_id: str,
    *,
    status: str,
    output_keys: Optional[list] = None,
    error: Optional[str] = None,
    progress: Optional[int] = None,
    message: Optional[str] = None,
) -> None:
    payload: dict = {"job_id": job_id, "status": status}
    if output_keys is not None:
        payload["output_keys"] = output_keys
    if error is not None:
        payload["error"] = error
    if progress is not None:
        payload["progress"] = progress
    if message is not None:
        payload["message"] = message

    r = get_redis()
    channel = f"{WS_CHANNEL_PREFIX}:{job_id}"
    r.publish(channel, json.dumps(payload))


def is_retryable_error(exc: Exception) -> bool:
    return isinstance(exc, RETRYABLE_EXCEPTIONS)


def retry_or_fail_task(task, job_id: str, exc: Exception, *, message: str) -> None:
    retries = getattr(task.request, "retries", 0)
    max_retries = getattr(task, "max_retries", 0) or 0

    if is_retryable_error(exc) and retries < max_retries:
        countdown = min(30, 2 ** retries)
        update_job(job_id, JobStatus.pending, error=f"Retrying after transient error: {exc}")
        publish_ws_event(job_id, status="pending", message=message)
        raise task.retry(exc=exc, countdown=countdown)

    update_job(job_id, JobStatus.failed, error=str(exc))
    raise exc
