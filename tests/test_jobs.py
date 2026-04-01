"""Basic integration tests for the jobs API."""
from datetime import datetime, timedelta, timezone
import pytest
from unittest.mock import patch
from uuid import UUID
from models.job import Job, JobStatus
from services.job_service import reconcile_stale_jobs


def test_health(client):
    res = client.get("/health")
    # Services may not be available in test env — just check schema
    assert res.status_code == 200
    data = res.json()
    assert "status" in data
    assert "services" in data


def test_create_job(client):
    with patch("api.routes.jobs._dispatch", return_value="mock-task-id"):
        res = client.post("/api/jobs", json={
            "type": "image",
            "model": "qwen-image-2512",
            "prompt": "a red apple on a wooden table",
            "params": {"width": 512, "height": 512, "steps": 10},
        })
    assert res.status_code == 202
    data = res.json()
    assert "job_id" in data
    assert data["status"] == "pending"


def test_get_job(client):
    with patch("api.routes.jobs._dispatch", return_value=None):
        create_res = client.post("/api/jobs", json={
            "type": "image",
            "model": "qwen-image-2512",
            "prompt": "test prompt",
        })
    assert create_res.status_code == 202
    job_id = create_res.json()["job_id"]

    with patch("storage.minio.get_presigned_url", return_value="http://minio/test.png"):
        get_res = client.get(f"/api/jobs/{job_id}")
    assert get_res.status_code == 200
    data = get_res.json()
    assert data["id"] == job_id
    assert data["status"] == "pending"
    assert data["prompt"] == "test prompt"


def test_list_jobs(client):
    with patch("api.routes.jobs._dispatch", return_value=None):
        for i in range(3):
            client.post("/api/jobs", json={
                "type": "image",
                "model": "qwen-image-2512",
                "prompt": f"test prompt {i}",
            })

    with patch("storage.minio.get_presigned_url", return_value="http://minio/test.png"):
        res = client.get("/api/jobs?page=1&page_size=10")
    assert res.status_code == 200
    data = res.json()
    assert "items" in data
    assert "total" in data
    assert data["total"] >= 3


def test_cancel_job(client):
    with patch("api.routes.jobs._dispatch", return_value=None):
        create_res = client.post("/api/jobs", json={
            "type": "image",
            "model": "qwen-image-2512",
            "prompt": "cancel me",
        })
    job_id = create_res.json()["job_id"]

    res = client.delete(f"/api/jobs/{job_id}")
    assert res.status_code == 204

    with patch("storage.minio.get_presigned_url", return_value="http://minio/test.png"):
        get_res = client.get(f"/api/jobs/{job_id}")
    assert get_res.json()["status"] == "cancelled"


def test_get_missing_job(client):
    res = client.get("/api/jobs/00000000-0000-0000-0000-000000000000")
    assert res.status_code == 404


def test_prompt_too_long(client):
    res = client.post("/api/jobs", json={
        "type": "image",
        "model": "qwen-image-2512",
        "prompt": "x" * 2001,
    })
    assert res.status_code == 422


def test_rejects_model_type_mismatch(client):
    res = client.post("/api/jobs", json={
        "type": "image",
        "model": "qwen3.5-7b-instruct",
        "prompt": "wrong model type",
    })
    assert res.status_code == 400
    assert "not enabled for job type" in res.json()["detail"]


def test_chat_job_hydrates_output_text(client, db):
    with patch("api.routes.jobs._dispatch", return_value=None):
        create_res = client.post("/api/jobs", json={
            "type": "chat",
            "model": "qwen3.5-7b-instruct",
            "prompt": "write a tagline",
        })
    assert create_res.status_code == 202
    job_id = create_res.json()["job_id"]

    job = db.get(Job, UUID(job_id))
    job.status = JobStatus.done
    job.output_keys = ["outputs/chat-result.txt"]
    db.commit()

    with patch("services.job_service.get_presigned_url", return_value="http://minio/chat.txt"), \
         patch("services.job_service.download_text", return_value="Mock chat output"):
        get_res = client.get(f"/api/jobs/{job_id}")

    assert get_res.status_code == 200
    data = get_res.json()
    assert data["output_text"] == "Mock chat output"
    assert data["output_urls"] == ["http://minio/chat.txt"]


def test_list_models_groups_enabled_models(client):
    res = client.get("/api/models")
    assert res.status_code == 200
    data = res.json()["models"]
    assert "image" in data
    assert "chat" in data
    assert any(model["name"] == "qwen-image-2512" for model in data["image"])


def test_reconcile_stale_jobs_marks_old_pending_and_running_failed(db):
    now = datetime.now(timezone.utc)
    pending_job = Job(
        type="image",
        model="qwen-image-2512",
        prompt="stale pending",
        negative_prompt="",
        params={},
        status=JobStatus.pending,
        created_at=now - timedelta(seconds=1000),
    )
    running_job = Job(
        type="chat",
        model="qwen3.5-7b-instruct",
        prompt="stale running",
        negative_prompt="",
        params={},
        status=JobStatus.running,
        created_at=now - timedelta(seconds=1000),
        started_at=now - timedelta(seconds=1000),
    )
    fresh_job = Job(
        type="image",
        model="qwen-image-2512",
        prompt="fresh pending",
        negative_prompt="",
        params={},
        status=JobStatus.pending,
        created_at=now,
    )
    db.add_all([pending_job, running_job, fresh_job])
    db.commit()

    with patch("websocket.pubsub.publish_job_event") as publish_job_event:
        count = reconcile_stale_jobs(db, pending_timeout_seconds=300, running_timeout_seconds=300)

    assert count == 2
    db.refresh(pending_job)
    db.refresh(running_job)
    db.refresh(fresh_job)
    assert pending_job.status == JobStatus.failed
    assert running_job.status == JobStatus.failed
    assert fresh_job.status == JobStatus.pending
    assert publish_job_event.call_count == 2
