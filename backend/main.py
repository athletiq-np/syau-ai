import asyncio
import structlog
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

from core.config import settings
from api.routes import jobs, models, projects
from websocket.manager import manager
from websocket.pubsub import listen_for_job_events
from services.job_service import enrich_with_urls
from services.job_service import get_job, reconcile_stale_jobs
from core.database import SessionLocal
from storage.minio import ensure_bucket_exists


# --- Logging setup ---
structlog.configure(
    processors=[
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.JSONRenderer(),
    ],
    wrapper_class=structlog.make_filtering_bound_logger(
        getattr(logging, settings.log_level.upper(), logging.INFO)
    ),
    logger_factory=structlog.PrintLoggerFactory(),
)

log = structlog.get_logger()


@asynccontextmanager
async def lifespan(app: FastAPI):
    log.info("startup", environment=settings.environment)

    # Ensure MinIO bucket exists
    try:
        ensure_bucket_exists()
        log.info("minio_ready", bucket=settings.minio_bucket)
    except Exception as e:
        log.warning("minio_init_failed", error=str(e))

    # Reconcile jobs left hanging by previous crashes or worker startup issues.
    db = SessionLocal()
    try:
        reconciled = reconcile_stale_jobs(
            db,
            pending_timeout_seconds=settings.stale_pending_seconds,
            running_timeout_seconds=settings.stale_running_seconds,
        )
        if reconciled:
            log.warning("startup_stale_jobs_reconciled", count=reconciled)
    except Exception as e:
        log.warning("stale_job_reconcile_failed", error=str(e))
    finally:
        db.close()

    # Start Redis pub/sub listener
    pubsub_task = asyncio.create_task(listen_for_job_events())

    yield

    pubsub_task.cancel()
    try:
        await pubsub_task
    except asyncio.CancelledError:
        pass
    log.info("shutdown")


app = FastAPI(title="SYAUAI API", version="0.1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(jobs.router)
app.include_router(models.router)
app.include_router(projects.router, prefix="/api")


@app.get("/health")
def health():
    from core.database import engine
    from core.redis import get_redis
    from storage.minio import get_s3_client
    from core.config import settings as cfg

    services = {}

    # DB check
    try:
        with engine.connect() as conn:
            conn.execute(__import__("sqlalchemy").text("SELECT 1"))
        services["db"] = "ok"
    except Exception as e:
        services["db"] = f"error: {e}"

    # Redis check
    try:
        r = get_redis()
        r.ping()
        services["redis"] = "ok"
    except Exception as e:
        services["redis"] = f"error: {e}"

    # MinIO check
    try:
        client = get_s3_client()
        client.list_buckets()
        services["minio"] = "ok"
    except Exception as e:
        services["minio"] = f"error: {e}"

    all_ok = all(v == "ok" for v in services.values())
    return {"status": "ok" if all_ok else "degraded", "services": services}


@app.websocket("/ws/jobs/{job_id}")
async def ws_job(websocket: WebSocket, job_id: str):
    await manager.connect(job_id, websocket)
    try:
        # Send current job state immediately on connect
        db = SessionLocal()
        try:
            from uuid import UUID
            job = get_job(db, UUID(job_id))
            if job:
                await websocket.send_json(enrich_with_urls(job))
        finally:
            db.close()

        # Keep alive until client disconnects
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        pass
    finally:
        manager.disconnect(job_id, websocket)


@app.websocket("/ws/projects/{project_id}")
async def ws_project(websocket: WebSocket, project_id: str):
    """WebSocket for project-level events (generation progress, shot status, etc.)"""
    from core.redis import get_redis
    import json as json_module

    await websocket.accept()
    redis = get_redis()
    pubsub = redis.pubsub()
    channel = f"project_events:{project_id}"
    pubsub.subscribe(channel)

    try:
        # Send initial project state
        db = SessionLocal()
        try:
            from uuid import UUID
            from schemas.project import ProjectDetailResponse
            project = db.query(__import__("models.project", fromlist=["Project"]).Project).filter(
                __import__("models.project", fromlist=["Project"]).Project.id == UUID(project_id)
            ).first()
            if project:
                await websocket.send_json({
                    "type": "init",
                    "project_id": project_id,
                    "status": project.status,
                    "total_shots": project.total_shots,
                })
        finally:
            db.close()

        # Listen for project events from Redis pub/sub
        for message in pubsub.listen():
            if message["type"] == "message":
                try:
                    data = json_module.loads(message["data"])
                    await websocket.send_json(data)
                except Exception as e:
                    log.warning("ws_project_message_error", error=str(e))

    except WebSocketDisconnect:
        pass
    finally:
        pubsub.unsubscribe(channel)
        pubsub.close()
