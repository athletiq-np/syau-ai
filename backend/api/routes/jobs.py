from uuid import UUID
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from api.deps import get_session
from core.security import get_current_user
from schemas.job import JobCreate, JobCreatedResponse, JobListResponse, JobResponse
from services.job_service import create_job, get_job, list_jobs, cancel_job, enrich_with_urls
import structlog

log = structlog.get_logger()
router = APIRouter(prefix="/api/jobs", tags=["jobs"])


@router.post("", response_model=JobCreatedResponse, status_code=202)
def submit_job(
    body: JobCreate,
    db: Session = Depends(get_session),
    user_id: str = Depends(get_current_user),
):
    try:
        job = create_job(db, body, user_id=user_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    # Dispatch Celery task based on job type
    task_id = _dispatch(job)
    if task_id:
        job.celery_task_id = task_id
        db.commit()

    return JobCreatedResponse(job_id=job.id, status=job.status)


def _dispatch(job) -> Optional[str]:
    try:
        if job.type == "image":
            from workers.image_worker import run_image_job
            result = run_image_job.apply_async(args=[str(job.id)], queue="image")
            return result.id
        elif job.type == "video":
            from workers.video_worker import run_video_job
            result = run_video_job.apply_async(args=[str(job.id)], queue="video")
            return result.id
        elif job.type == "chat":
            from workers.chat_worker import run_chat_job
            result = run_chat_job.apply_async(args=[str(job.id)], queue="chat")
            return result.id
    except Exception as e:
        log.error("dispatch_failed", job_id=str(job.id), error=str(e))
    return None


@router.get("", response_model=JobListResponse)
def list_jobs_endpoint(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    type: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    db: Session = Depends(get_session),
    user_id: str = Depends(get_current_user),
):
    items, total = list_jobs(db, page=page, page_size=page_size, type=type, status=status, user_id=user_id)
    enriched = [enrich_with_urls(j) for j in items]
    return {"items": enriched, "total": total, "page": page, "page_size": page_size}


@router.get("/{job_id}")
def get_job_endpoint(
    job_id: UUID,
    db: Session = Depends(get_session),
    user_id: str = Depends(get_current_user),
):
    job = get_job(db, job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")

    # Ensure user can only view their own jobs
    if job.user_id != user_id:
        raise HTTPException(status_code=403, detail="Unauthorized: job belongs to another user")

    return enrich_with_urls(job)


@router.delete("/{job_id}", status_code=204)
def cancel_job_endpoint(
    job_id: UUID,
    db: Session = Depends(get_session),
    user_id: str = Depends(get_current_user),
):
    job = cancel_job(db, job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")

    # Ensure user can only cancel their own jobs
    if job.user_id != user_id:
        raise HTTPException(status_code=403, detail="Unauthorized: job belongs to another user")
