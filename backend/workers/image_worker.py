"""
Image generation worker — local mock for development.

Generates placeholder images using PIL instead of real models.
On GPU server, replace with real QwenImageHandler.
"""
import time
import io
import random
import structlog
from PIL import Image, ImageDraw

from core.config import settings
from workers.celery_app import celery_app
from workers.utils import publish_ws_event, retry_or_fail_task, update_job
from models.job import JobStatus
from storage.minio import upload_bytes
from core.database import SessionLocal
from models.job import Job
from inference import remote_client

log = structlog.get_logger()


@celery_app.task(name="workers.image_worker.run_image_job", bind=True, max_retries=3)
def run_image_job(self, job_id: str) -> dict:
    log.info("job_received", job_id=job_id, worker="image")

    try:
        db = SessionLocal()
        try:
            job = db.get(Job, job_id)
            if not job:
                raise ValueError(f"Job {job_id} not found")
        finally:
            db.close()

        update_job(job_id, JobStatus.running)
        publish_ws_event(job_id, status="running", message="Generating image...")

        start = time.time()

        if settings.inference_mode.lower() == "remote":
            publish_ws_event(job_id, status="running", progress=25, message="Requesting remote image inference...")
            remote_result = remote_client.infer_image(
                model=job.model,
                prompt=job.prompt,
                negative_prompt=job.negative_prompt,
                params=job.params or {},
            )
            output_keys = []
            for index, image in enumerate(remote_result["images"]):
                key = f"outputs/{job_id}_{index}.png"
                upload_bytes(key, image["bytes"], content_type=image["content_type"])
                output_keys.append(key)
            seed = remote_result.get("seed_used")
        else:
            # Generate mock image
            width = int(job.params.get("width", 1024))
            height = int(job.params.get("height", 1024))
            seed = job.params.get("seed") or random.randint(0, 2**31 - 1)

            # Simulate processing steps
            for i in range(3):
                time.sleep(1)
                publish_ws_event(job_id, status="running", progress=(i + 1) * 33,
                               message=f"Generating... {(i + 1) * 33}%")

            # Generate PIL image with prompt text
            img = Image.new("RGB", (width, height), color=(random.randint(50, 150), random.randint(50, 150), random.randint(50, 150)))
            draw = ImageDraw.Draw(img)

            # Add prompt text to image
            prompt_text = job.prompt[:100]  # Truncate long prompts
            text_y = 20
            for line in (prompt_text[i:i+50] for i in range(0, len(prompt_text), 50)):
                draw.text((20, text_y), line, fill=(255, 255, 255))
                text_y += 30

            # Add seed info
            draw.text((20, height - 40), f"Seed: {seed}", fill=(200, 200, 200))

            # Upload to MinIO
            img_bytes = io.BytesIO()
            img.save(img_bytes, format="PNG")
            img_bytes.seek(0)

            key = f"outputs/{job_id}_0.png"
            upload_bytes(key, img_bytes.getvalue(), content_type="image/png")
            output_keys = [key]

        duration = time.time() - start
        update_job(job_id, JobStatus.done, output_keys=output_keys, seed_used=seed, duration_seconds=duration)
        log.info("job_done", job_id=job_id, duration_seconds=round(duration, 2), seed=seed)
        return {"status": "done", "job_id": job_id}

    except Exception as exc:
        log.error("job_failed", job_id=job_id, error=str(exc))
        retry_or_fail_task(self, job_id, exc, message="Transient worker issue detected, retrying image job...")
