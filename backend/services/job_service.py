from __future__ import annotations
from datetime import datetime, timedelta, timezone
from typing import Optional
from uuid import UUID

from sqlalchemy.orm import Session
from sqlalchemy import select, func, or_

from models.job import Job, JobStatus, AIModel
from schemas.job import JobCreate
from storage.minio import download_text, get_presigned_url
import structlog

log = structlog.get_logger()


def create_job(db: Session, data: JobCreate, user_id: str = "anonymous") -> Job:
    model = db.scalar(
        select(AIModel).where(
            AIModel.name == data.model,
            AIModel.type == data.type,
            AIModel.is_enabled == True,  # noqa: E712
        )
    )
    if model is None:
        raise ValueError(f"Model '{data.model}' is not enabled for job type '{data.type}'")

    job = Job(
        user_id=user_id,
        type=data.type,
        model=data.model,
        prompt=data.prompt,
        negative_prompt=data.negative_prompt,
        params=data.params.model_dump(),
        status=JobStatus.pending,
    )
    db.add(job)
    db.commit()
    db.refresh(job)
    log.info("job_created", job_id=str(job.id), user_id=user_id, type=job.type, model=job.model)
    return job


def get_job(db: Session, job_id: UUID) -> Optional[Job]:
    return db.get(Job, job_id)


def list_jobs(
    db: Session,
    page: int = 1,
    page_size: int = 20,
    type: Optional[str] = None,
    status: Optional[str] = None,
    user_id: Optional[str] = None,
) -> tuple[list[Job], int]:
    stmt = select(Job)
    count_stmt = select(func.count()).select_from(Job)

    # Filter by user_id if provided (own jobs only)
    if user_id:
        stmt = stmt.where(Job.user_id == user_id)
        count_stmt = count_stmt.where(Job.user_id == user_id)

    if type:
        stmt = stmt.where(Job.type == type)
        count_stmt = count_stmt.where(Job.type == type)
    if status:
        stmt = stmt.where(Job.status == status)
        count_stmt = count_stmt.where(Job.status == status)

    total = db.scalar(count_stmt) or 0
    stmt = stmt.order_by(Job.created_at.desc()).offset((page - 1) * page_size).limit(page_size)
    items = list(db.scalars(stmt))
    return items, total


def cancel_job(db: Session, job_id: UUID) -> Optional[Job]:
    job = db.get(Job, job_id)
    if job is None:
        return None
    if job.status in (JobStatus.pending, JobStatus.running):
        if job.celery_task_id:
            try:
                from workers.celery_app import celery_app
                celery_app.control.revoke(job.celery_task_id, terminate=True)
            except Exception as e:
                log.warning("celery_revoke_failed", job_id=str(job_id), error=str(e))
        job.status = JobStatus.cancelled
        job.completed_at = datetime.now(timezone.utc)
        db.commit()
        db.refresh(job)
        log.info("job_cancelled", job_id=str(job_id))
    return job


def enrich_with_urls(job: Job) -> dict:
    """Return job as dict with presigned output_urls added."""
    d = {
        "id": str(job.id),
        "status": job.status,
        "type": job.type,
        "model": job.model,
        "prompt": job.prompt,
        "negative_prompt": job.negative_prompt,
        "params": job.params,
        "output_keys": job.output_keys,
        "output_urls": [],
        "output_text": None,
        "seed_used": job.seed_used,
        "duration_seconds": job.duration_seconds,
        "error": job.error,
        "created_at": job.created_at.isoformat() if job.created_at else None,
        "started_at": job.started_at.isoformat() if job.started_at else None,
        "completed_at": job.completed_at.isoformat() if job.completed_at else None,
    }
    if job.output_keys:
        d["output_urls"] = [get_presigned_url(k) for k in job.output_keys]
        if job.type == "chat":
            text_key = next((k for k in job.output_keys if k.endswith(".txt")), None)
            if text_key:
                try:
                    d["output_text"] = download_text(text_key)
                except Exception as exc:
                    log.warning("chat_output_text_unavailable", job_id=str(job.id), key=text_key, error=str(exc))
    return d


def get_enabled_models(db: Session) -> list[AIModel]:
    stmt = select(AIModel).where(AIModel.is_enabled == True).order_by(AIModel.type, AIModel.name)  # noqa: E712
    return list(db.scalars(stmt))


def reconcile_stale_jobs(
    db: Session,
    *,
    pending_timeout_seconds: int,
    running_timeout_seconds: int,
) -> int:
    now = datetime.now(timezone.utc)
    stale_pending_before = now - timedelta(seconds=pending_timeout_seconds)
    stale_running_before = now - timedelta(seconds=running_timeout_seconds)

    stmt = select(Job).where(
        or_(
            (Job.status == JobStatus.pending) & (Job.created_at < stale_pending_before),
            (Job.status == JobStatus.running) & (Job.started_at.is_not(None)) & (Job.started_at < stale_running_before),
        )
    )
    jobs = list(db.scalars(stmt))
    if not jobs:
        return 0

    from websocket.pubsub import publish_job_event

    for job in jobs:
        previous_status = job.status.value
        job.status = JobStatus.failed
        job.completed_at = now
        job.error = (
            "Job was marked failed during startup reconciliation after exceeding "
            f"the {previous_status} timeout."
        )
        publish_job_event(
            str(job.id),
            {
                "job_id": str(job.id),
                "status": JobStatus.failed.value,
                "error": job.error,
                "message": "Recovered stale job during startup reconciliation.",
            },
        )

    db.commit()
    log.warning("stale_jobs_reconciled", count=len(jobs))
    return len(jobs)
