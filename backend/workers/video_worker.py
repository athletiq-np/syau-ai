"""Video generation worker — Wan 2.2 T2V/I2V via ComfyUI."""
import time
import base64
import structlog

from core.config import settings
from workers.celery_app import celery_app
from workers.utils import publish_ws_event, retry_or_fail_task, update_job
from models.job import JobStatus
from inference.comfyui_client import ComfyUIClient
from storage.minio import upload_bytes
from core.database import SessionLocal
from models.job import Job

log = structlog.get_logger()


@celery_app.task(name="workers.video_worker.run_video_job", bind=True, max_retries=2)
def run_video_job(self, job_id: str) -> dict:
    log.info("job_received", job_id=job_id, worker="video")
    try:
        db = SessionLocal()
        try:
            job = db.get(Job, job_id)
            if not job:
                raise ValueError(f"Job {job_id} not found")
        finally:
            db.close()

        update_job(job_id, JobStatus.running)
        publish_ws_event(job_id, status="running", progress=5, message="Submitting to ComfyUI...")

        params = job.params or {}
        comfyui_url = settings.comfyui_url or "http://host.docker.internal:8188"
        comfyui = ComfyUIClient(base_url=comfyui_url)

        start = time.time()

        # Check if this is I2V (image-to-video) or T2V (text-to-video)
        image_base64 = params.get("input_image_base64")
        image_name = params.get("input_image_name", "input.jpg")
        log.info("video_mode_check", job_id=job_id, has_image=bool(image_base64), image_name=image_name)

        if image_base64:
            # I2V mode: decode image and upload to ComfyUI
            publish_ws_event(job_id, status="running", progress=10, message="Uploading image to GPU...")
            image_bytes = base64.b64decode(image_base64)
            image_filename = comfyui.upload_image(image_bytes, filename=f"input_{job_id}.jpg")
            log.info("image_uploaded", job_id=job_id, filename=image_filename)

            result = comfyui.infer_wan_i2v(
                image_filename=image_filename,
                prompt=job.prompt,
                negative_prompt=job.negative_prompt or "",
                num_frames=int(params.get("num_frames") or 81),
                height=int(params.get("height") or 640),
                width=int(params.get("width") or 640),
                seed=int(params.get("seed") or 0),
                on_progress=lambda pct, msg: publish_ws_event(
                    job_id, status="running", progress=pct, message=msg
                ),
            )
        else:
            # T2V mode: text-to-video only
            result = comfyui.infer_wan_t2v(
                prompt=job.prompt,
                negative_prompt=job.negative_prompt or "",
                num_frames=int(params.get("num_frames") or 81),
                height=int(params.get("height") or 640),
                width=int(params.get("width") or 640),
                seed=int(params.get("seed") or 0),
                on_progress=lambda pct, msg: publish_ws_event(
                    job_id, status="running", progress=pct, message=msg
                ),
            )

        publish_ws_event(job_id, status="running", progress=90, message="Uploading video...")

        ext = result["filename"].rsplit(".", 1)[-1] if "." in result["filename"] else "mp4"
        key = f"outputs/{job_id}_0.{ext}"
        upload_bytes(key, result["video_bytes"], content_type=result["content_type"])

        duration = time.time() - start
        update_job(job_id, JobStatus.done, output_keys=[key], duration_seconds=duration)
        log.info("job_done", job_id=job_id, duration_seconds=round(duration, 2), filename=result["filename"])
        return {"status": "done", "job_id": job_id}

    except Exception as exc:
        log.error("job_failed", job_id=job_id, error=str(exc))
        retry_or_fail_task(self, job_id, exc, message="Video job failed, retrying...")
