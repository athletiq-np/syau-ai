from types import SimpleNamespace
from unittest.mock import MagicMock, call, patch

import pytest
from celery.exceptions import Retry

from models.job import JobStatus
from workers import chat_worker, image_worker, video_worker
from inference import model_cache
from workers import utils as worker_utils


def _job(**overrides):
    job = SimpleNamespace(
        id="job-123",
        model="qwen-image-2512",
        prompt="test prompt",
        negative_prompt="",
        params={"width": 128, "height": 128, "steps": 4, "cfg_scale": 7},
    )
    for key, value in overrides.items():
        setattr(job, key, value)
    return job


def _db_with_job(job):
    db = MagicMock()
    db.get.return_value = job
    return db


@patch("workers.image_worker.time.sleep", return_value=None)
@patch("workers.image_worker.random.randint", side_effect=[123456, 80, 100, 120])
@patch("workers.image_worker.upload_bytes")
@patch("workers.image_worker.publish_ws_event")
@patch("workers.image_worker.update_job")
@patch("workers.image_worker.SessionLocal")
def test_image_worker_success(session_local, update_job, publish_ws_event, upload_bytes, _randint, _sleep):
    session_local.return_value = _db_with_job(_job())

    result = image_worker.run_image_job.run("job-123")

    assert result == {"status": "done", "job_id": "job-123"}
    assert upload_bytes.call_args[0][0] == "outputs/job-123_0.png"
    assert upload_bytes.call_args.kwargs["content_type"] == "image/png"
    update_job.assert_any_call("job-123", JobStatus.running)
    done_call = update_job.call_args_list[-1]
    assert done_call.args[:2] == ("job-123", JobStatus.done)
    assert done_call.kwargs["output_keys"] == ["outputs/job-123_0.png"]
    assert done_call.kwargs["seed_used"] == 123456
    assert publish_ws_event.call_args_list[0] == call("job-123", status="running", message="Generating image...")
    assert session_local.return_value.close.called


@patch("workers.image_worker.update_job")
@patch("workers.image_worker.SessionLocal")
def test_image_worker_failure_marks_job_failed(session_local, update_job):
    session_local.return_value = _db_with_job(None)

    with patch("workers.image_worker.retry_or_fail_task", side_effect=ValueError("Job job-404 not found")) as retry_or_fail:
        with pytest.raises(ValueError, match="Job job-404 not found"):
            image_worker.run_image_job.run("job-404")

    retry_or_fail.assert_called_once()
    update_job.assert_not_called()
    assert session_local.return_value.close.called


@patch("workers.video_worker.os.remove")
@patch("workers.video_worker.upload_file")
@patch("workers.video_worker.get_model", return_value={"model": "cached"})
@patch("workers.video_worker.publish_ws_event")
@patch("workers.video_worker.update_job")
@patch("workers.video_worker.SessionLocal")
def test_video_worker_success(session_local, update_job, publish_ws_event, get_model, upload_file, remove_file):
    session_local.return_value = _db_with_job(_job(model="qwen-image-layered"))

    with patch("workers.video_worker.QwenVideoHandler") as handler_cls:
        handler = handler_cls.return_value
        handler.infer.return_value = {"video_path": "/tmp/video.gif", "frames": 12}

        result = video_worker.run_video_job.run("job-123")

    assert result == {"status": "done", "job_id": "job-123"}
    get_model.assert_called_once()
    upload_file.assert_called_once_with("outputs/job-123_0.gif", "/tmp/video.gif", content_type="image/gif")
    remove_file.assert_called_once_with("/tmp/video.gif")
    update_job.assert_any_call("job-123", JobStatus.running)
    assert update_job.call_args_list[-1].kwargs["output_keys"] == ["outputs/job-123_0.gif"]
    assert publish_ws_event.call_args_list[0] == call("job-123", status="running", message="Generating video preview...")


@patch("workers.chat_worker.upload_bytes")
@patch("workers.chat_worker.get_model", return_value={"model": "cached"})
@patch("workers.chat_worker.publish_ws_event")
@patch("workers.chat_worker.update_job")
@patch("workers.chat_worker.SessionLocal")
def test_chat_worker_success(session_local, update_job, publish_ws_event, get_model, upload_bytes):
    session_local.return_value = _db_with_job(_job(model="qwen3.5-7b-instruct", params={"steps": 1}))

    with patch("workers.chat_worker.QwenChatHandler") as handler_cls:
        handler = handler_cls.return_value
        handler.infer.return_value = {"text": "hello world", "tokens_used": 32}

        result = chat_worker.run_chat_job.run("job-123")

    assert result == {"status": "done", "job_id": "job-123"}
    get_model.assert_called_once()
    upload_bytes.assert_called_once_with(
        "outputs/job-123_0.txt",
        b"hello world",
        content_type="text/plain; charset=utf-8",
    )
    update_job.assert_any_call("job-123", JobStatus.running)
    assert update_job.call_args_list[-1].kwargs["output_keys"] == ["outputs/job-123_0.txt"]
    assert publish_ws_event.call_args_list[0] == call("job-123", status="running", message="Generating chat response...")


@patch("workers.chat_worker.upload_bytes")
@patch("workers.chat_worker.publish_ws_event")
@patch("workers.chat_worker.update_job")
@patch("workers.chat_worker.SessionLocal")
def test_chat_worker_remote_success(session_local, update_job, publish_ws_event, upload_bytes):
    session_local.return_value = _db_with_job(_job(model="qwen3.5-7b-instruct", params={"steps": 1}))

    with patch("workers.chat_worker.settings.inference_mode", "remote"), \
         patch("workers.chat_worker.remote_client.infer_chat", return_value={"text": "remote hello", "tokens_used": 64}) as infer_chat:
        result = chat_worker.run_chat_job.run("job-123")

    assert result == {"status": "done", "job_id": "job-123"}
    infer_chat.assert_called_once()
    upload_bytes.assert_called_once_with(
        "outputs/job-123_0.txt",
        b"remote hello",
        content_type="text/plain; charset=utf-8",
    )
    update_job.assert_any_call("job-123", JobStatus.running)
    assert update_job.call_args_list[-1].kwargs["output_keys"] == ["outputs/job-123_0.txt"]


def test_model_cache_reuses_same_model():
    handler = MagicMock()
    handler.load.return_value = "model-a"

    with patch.object(model_cache, "_current_model", None), \
         patch.object(model_cache, "_current_model_name", None), \
         patch.object(model_cache, "_current_handler", None):
        first = model_cache.get_model("qwen-image-2512", handler)
        second = model_cache.get_model("qwen-image-2512", handler)

    assert first == "model-a"
    assert second == "model-a"
    handler.load.assert_called_once_with("qwen-image-2512")
    handler.unload.assert_not_called()


def test_model_cache_unloads_previous_model_when_switching():
    first_handler = MagicMock()
    second_handler = MagicMock()
    first_handler.load.return_value = "model-a"
    second_handler.load.return_value = "model-b"

    with patch.object(model_cache, "_current_model", None), \
         patch.object(model_cache, "_current_model_name", None), \
         patch.object(model_cache, "_current_handler", None):
        first = model_cache.get_model("qwen-image-2512", first_handler)
        second = model_cache.get_model("qwen-image-layered", second_handler)

    assert first == "model-a"
    assert second == "model-b"
    first_handler.unload.assert_called_once_with("model-a")
    second_handler.load.assert_called_once_with("qwen-image-layered")


@patch("workers.image_worker.upload_bytes", side_effect=ConnectionError("minio unavailable"))
@patch("workers.image_worker.publish_ws_event")
@patch("workers.image_worker.update_job")
@patch("workers.image_worker.time.sleep", return_value=None)
@patch("workers.image_worker.random.randint", side_effect=[123456, 80, 100, 120])
@patch("workers.image_worker.SessionLocal")
def test_image_worker_retries_transient_failure(session_local, _randint, _sleep, update_job, publish_ws_event, _upload_bytes):
    session_local.return_value = _db_with_job(_job())

    with patch("workers.image_worker.retry_or_fail_task", side_effect=Retry()) as retry_or_fail:
        with pytest.raises(Retry):
            image_worker.run_image_job.run("job-123")

    update_job.assert_any_call("job-123", JobStatus.running)
    retry_or_fail.assert_called_once()
    publish_ws_event.assert_any_call("job-123", status="running", message="Generating image...")


@patch("workers.image_worker.upload_bytes")
@patch("workers.image_worker.publish_ws_event")
@patch("workers.image_worker.update_job")
@patch("workers.image_worker.SessionLocal")
def test_image_worker_remote_success(session_local, update_job, publish_ws_event, upload_bytes):
    session_local.return_value = _db_with_job(_job())

    remote_result = {
        "images": [
            {"bytes": b"image-a", "content_type": "image/png"},
            {"bytes": b"image-b", "content_type": "image/png"},
        ],
        "seed_used": 999,
    }
    with patch("workers.image_worker.settings.inference_mode", "remote"), \
         patch("workers.image_worker.remote_client.infer_image", return_value=remote_result) as infer_image:
        result = image_worker.run_image_job.run("job-123")

    assert result == {"status": "done", "job_id": "job-123"}
    infer_image.assert_called_once()
    assert upload_bytes.call_count == 2
    assert upload_bytes.call_args_list[0] == call("outputs/job-123_0.png", b"image-a", content_type="image/png")
    assert upload_bytes.call_args_list[1] == call("outputs/job-123_1.png", b"image-b", content_type="image/png")
    done_call = update_job.call_args_list[-1]
    assert done_call.kwargs["output_keys"] == ["outputs/job-123_0.png", "outputs/job-123_1.png"]
    assert done_call.kwargs["seed_used"] == 999


@patch("workers.video_worker.upload_bytes")
@patch("workers.video_worker.publish_ws_event")
@patch("workers.video_worker.update_job")
@patch("workers.video_worker.SessionLocal")
def test_video_worker_remote_success(session_local, update_job, publish_ws_event, upload_bytes):
    session_local.return_value = _db_with_job(_job(model="qwen-image-layered"))

    remote_result = {
        "bytes": b"gif-bytes",
        "content_type": "image/gif",
        "frames": 18,
    }
    with patch("workers.video_worker.settings.inference_mode", "remote"), \
         patch("workers.video_worker.remote_client.infer_video", return_value=remote_result) as infer_video:
        result = video_worker.run_video_job.run("job-123")

    assert result == {"status": "done", "job_id": "job-123"}
    infer_video.assert_called_once()
    upload_bytes.assert_called_once_with("outputs/job-123_0.gif", b"gif-bytes", content_type="image/gif")
    assert update_job.call_args_list[-1].kwargs["output_keys"] == ["outputs/job-123_0.gif"]


def test_retry_or_fail_task_retries_transient_errors():
    task = SimpleNamespace(
        request=SimpleNamespace(retries=0),
        max_retries=3,
        retry=MagicMock(side_effect=Retry()),
    )

    with patch("workers.utils.update_job") as update_job, patch("workers.utils.publish_ws_event") as publish_ws_event:
        with pytest.raises(Retry):
            worker_utils.retry_or_fail_task(
                task,
                "job-123",
                ConnectionError("minio unavailable"),
                message="retrying image",
            )

    update_job.assert_called_once_with("job-123", JobStatus.pending, error="Retrying after transient error: minio unavailable")
    publish_ws_event.assert_called_once_with("job-123", status="pending", message="retrying image")
    task.retry.assert_called_once()


def test_retry_or_fail_task_fails_non_retryable_errors():
    task = SimpleNamespace(
        request=SimpleNamespace(retries=0),
        max_retries=3,
        retry=MagicMock(),
    )

    with patch("workers.utils.update_job") as update_job:
        with pytest.raises(ValueError, match="bad input"):
            worker_utils.retry_or_fail_task(task, "job-123", ValueError("bad input"), message="ignored")

    update_job.assert_called_once_with("job-123", JobStatus.failed, error="bad input")
    task.retry.assert_not_called()
