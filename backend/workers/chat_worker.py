"""Chat inference worker using the shared handler/model-cache flow."""
import time
import structlog

from core.config import settings
from workers.celery_app import celery_app
from workers.utils import publish_ws_event, retry_or_fail_task, update_job
from models.job import JobStatus
from inference.handlers.qwen_chat import QwenChatHandler
from inference.model_cache import get_model
from inference import remote_client
from storage.minio import upload_bytes
from core.database import SessionLocal
from models.job import Job

log = structlog.get_logger()


@celery_app.task(name="workers.chat_worker.run_chat_job", bind=True, max_retries=3)
def run_chat_job(self, job_id: str) -> dict:
    log.info("job_received", job_id=job_id, worker="chat")
    try:
        db = SessionLocal()
        try:
            job = db.get(Job, job_id)
            if not job:
                raise ValueError(f"Job {job_id} not found")
        finally:
            db.close()

        update_job(job_id, JobStatus.running)
        publish_ws_event(job_id, status="running", message="Generating chat response...")
        start = time.time()

        if settings.inference_mode.lower() == "remote":
            result = remote_client.infer_chat(
                model=job.model,
                prompt=job.prompt,
                negative_prompt=job.negative_prompt,
                params=job.params or {},
            )
        else:
            handler = QwenChatHandler()
            model = get_model(job.model, handler)
            result = handler.infer(
                model,
                {"prompt": job.prompt, "negative_prompt": job.negative_prompt},
                job.params or {},
            )

        publish_ws_event(job_id, status="running", progress=90, message="Saving chat transcript...")
        key = f"outputs/{job_id}_0.txt"
        upload_bytes(key, result["text"].encode("utf-8"), content_type="text/plain; charset=utf-8")

        duration = time.time() - start
        update_job(job_id, JobStatus.done, output_keys=[key], duration_seconds=duration)
        log.info("job_done", job_id=job_id, duration_seconds=round(duration, 2), tokens_used=result["tokens_used"])
        return {"status": "done", "job_id": job_id}
    except Exception as exc:
        log.error("job_failed", job_id=job_id, error=str(exc))
        retry_or_fail_task(self, job_id, exc, message="Transient worker issue detected, retrying chat job...")
