import asyncio
import json
import structlog
import logging
from contextlib import asynccontextmanager
from uuid import UUID

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

from core.config import settings
from core.redis import get_redis
from api.routes import jobs, models, projects, planning
from websocket.manager import manager
from websocket.pubsub import listen_for_job_events
from services.job_service import enrich_with_urls
from services.job_service import get_job, reconcile_stale_jobs
from core.database import SessionLocal
from storage.minio import ensure_bucket_exists, get_presigned_url
from models.project import Project
from tasks.tunnel_monitor import start_tunnel_monitor, stop_tunnel_monitor


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

    # Start tunnel health monitor
    tunnel_monitor_task = await start_tunnel_monitor()

    yield

    # Shutdown
    if tunnel_monitor_task:
        tunnel_monitor_task.cancel()
        try:
            await tunnel_monitor_task
        except asyncio.CancelledError:
            pass

    pubsub_task.cancel()
    try:
        await pubsub_task
    except asyncio.CancelledError:
        pass
    stop_tunnel_monitor()
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
app.include_router(planning.router)


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
    await websocket.accept()
    pubsub = None
    loop = asyncio.get_running_loop()

    try:
        # Send initial project state
        db = SessionLocal()
        try:
            project = db.query(Project).filter(Project.id == UUID(project_id)).first()
            if project:
                await websocket.send_json({
                    "type": "init",
                    "project_id": project_id,
                    "status": project.status,
                    "total_shots": project.total_shots,
                    "output_url": get_presigned_url(project.output_key) if project.output_key else None,
                })
        finally:
            db.close()

        redis = get_redis()
        pubsub = redis.pubsub()
        await loop.run_in_executor(None, pubsub.subscribe, f"project_events:{project_id}")

        async def recv_client():
            while True:
                await websocket.receive_text()

        async def forward_project_events():
            while True:
                message = await loop.run_in_executor(
                    None,
                    lambda: pubsub.get_message(ignore_subscribe_messages=True, timeout=0.5),
                )
                if message is None:
                    await asyncio.sleep(0.05)
                    continue
                if message["type"] != "message":
                    continue

                payload = json.loads(message["data"])
                output_key = payload.get("output_key")
                if output_key:
                    payload["output_url"] = get_presigned_url(output_key)
                await websocket.send_json(payload)

        client_task = asyncio.create_task(recv_client())
        forward_task = asyncio.create_task(forward_project_events())
        done, pending = await asyncio.wait(
            {client_task, forward_task},
            return_when=asyncio.FIRST_COMPLETED,
        )
        for task in pending:
            task.cancel()
        for task in done:
            task.result()

    except WebSocketDisconnect:
        pass
    finally:
        if pubsub is not None:
            try:
                await loop.run_in_executor(None, pubsub.close)
            except Exception:
                pass
