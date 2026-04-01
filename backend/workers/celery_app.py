from celery import Celery
from core.config import settings

celery_app = Celery(
    "syauai",
    broker=settings.redis_url,
    backend=settings.redis_url,
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    broker_connection_retry_on_startup=True,
    task_acks_late=True,
    worker_prefetch_multiplier=1,
    task_track_started=True,
    task_soft_time_limit=900,
    task_time_limit=960,
    task_routes={
        "workers.image_worker.*": {"queue": "image"},
        "workers.video_worker.*": {"queue": "video"},
        "workers.chat_worker.*": {"queue": "chat"},
    },
)

# Auto-discover tasks
celery_app.autodiscover_tasks(["workers"])

# Explicitly import task modules
from workers import image_worker, video_worker, chat_worker  # noqa: F401, E402
