from __future__ import annotations

import base64
from typing import Any

import httpx
import structlog

from core.config import settings

log = structlog.get_logger()


class RemoteInferenceError(RuntimeError):
    pass


def _headers() -> dict[str, str]:
    headers = {"Content-Type": "application/json"}
    if settings.inference_api_key:
        headers["Authorization"] = f"Bearer {settings.inference_api_key}"
    return headers


def _base_url() -> str:
    if not settings.inference_api_base_url:
        raise RemoteInferenceError("INFERENCE_API_BASE_URL is required when INFERENCE_MODE=remote")
    return settings.inference_api_base_url.rstrip("/")


def _post(path: str, payload: dict[str, Any]) -> dict[str, Any]:
    url = f"{_base_url()}{path}"
    try:
        with httpx.Client(timeout=settings.inference_timeout_seconds) as client:
            response = client.post(url, headers=_headers(), json=payload)
            response.raise_for_status()
            return response.json()
    except httpx.HTTPStatusError as exc:
        body = exc.response.text[:500]
        log.error("remote_inference_http_error", url=url, status_code=exc.response.status_code, body=body)
        raise RemoteInferenceError(f"Remote inference error {exc.response.status_code}: {body}") from exc
    except httpx.HTTPError as exc:
        log.error("remote_inference_network_error", url=url, error=str(exc))
        raise RemoteInferenceError(str(exc)) from exc


def infer_image(*, model: str, prompt: str, negative_prompt: str, params: dict[str, Any]) -> dict[str, Any]:
    payload = {
        "model": model,
        "prompt": prompt,
        "negative_prompt": negative_prompt,
        "params": params,
    }
    data = _post("/infer/image", payload)
    images = []
    for index, item in enumerate(data.get("images", [])):
        encoded = item["data_base64"]
        images.append({
            "filename": item.get("filename", f"image_{index}.png"),
            "content_type": item.get("content_type", "image/png"),
            "bytes": base64.b64decode(encoded),
        })
    return {"images": images, "seed_used": data.get("seed_used")}


def infer_chat(*, model: str, prompt: str, negative_prompt: str, params: dict[str, Any]) -> dict[str, Any]:
    payload = {
        "model": model,
        "prompt": prompt,
        "negative_prompt": negative_prompt,
        "params": params,
    }
    data = _post("/infer/chat", payload)
    return {
        "text": data["text"],
        "tokens_used": data.get("tokens_used", 0),
    }


def infer_video(*, model: str, prompt: str, negative_prompt: str, params: dict[str, Any]) -> dict[str, Any]:
    payload = {
        "model": model,
        "prompt": prompt,
        "negative_prompt": negative_prompt,
        "params": params,
    }
    data = _post("/infer/video", payload)
    video = data["video"]
    return {
        "filename": video.get("filename", "video.gif"),
        "content_type": video.get("content_type", "image/gif"),
        "bytes": base64.b64decode(video["data_base64"]),
        "frames": data.get("frames"),
    }
