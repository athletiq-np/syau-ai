from __future__ import annotations

import base64
import io
import time

from fastapi import Depends, FastAPI

from gpu_server.config import settings
from gpu_server.handlers.ltx_video import LTXVideoHandler
from gpu_server.handlers.wan_video import WANVideoHandler
from gpu_server.handlers.qwen_chat import QwenChatHandler
from gpu_server.handlers.qwen_image import QwenImageHandler
from gpu_server.handlers.qwen_image_edit import QwenImageEditHandler
from gpu_server.handlers.qwen_video import QwenVideoHandler
from gpu_server.model_cache import get_model
from gpu_server.schemas import (
    ChatResponse,
    HealthResponse,
    ImageArtifact,
    ImageResponse,
    InferRequest,
    ModelsResponse,
    VideoArtifact,
    VideoResponse,
)
from gpu_server.security import require_api_key

app = FastAPI(title="SYAUAI GPU Inference API", version="0.1.0")

MODEL_CATALOG = {
    "image": [
        {"name": "qwen-image-2512", "display_name": "Qwen Image 2512"},
        {"name": "qwen-image-layered", "display_name": "Qwen Image Layered"},
        {"name": "qwen-image-edit", "display_name": "Qwen Image Edit"},
    ],
    "chat": [
        {"name": "qwen3.5-7b-instruct", "display_name": "Qwen 3.5 7B Instruct"},
    ],
    "video": [
        {"name": "wan-2.2", "display_name": "WAN 2.2 (Primary)"},
        {"name": "ltx-2.3", "display_name": "LTX 2.3 (Requires 48GB GPU)"},
        {"name": "qwen-video-preview", "display_name": "Qwen Video Preview"},
    ],
}


@app.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    return HealthResponse(status="ok", mode=settings.inference_mode)


@app.get("/models", response_model=ModelsResponse, dependencies=[Depends(require_api_key)])
def list_models() -> ModelsResponse:
    return ModelsResponse(models=MODEL_CATALOG)


@app.post("/infer/image", response_model=ImageResponse, dependencies=[Depends(require_api_key)])
def infer_image(body: InferRequest) -> ImageResponse:
    handler = _image_handler_for_model(body.model)
    model = get_model(body.model, handler)
    result = handler.infer(
        model,
        {"prompt": body.prompt, "negative_prompt": body.negative_prompt},
        body.params.model_dump(exclude_none=True),
    )

    images = []
    for index, image in enumerate(result["images"]):
        img_bytes = io.BytesIO()
        image.save(img_bytes, format="PNG")
        images.append(
            ImageArtifact(
                filename=f"{body.model}_{index}.png",
                content_type="image/png",
                data_base64=base64.b64encode(img_bytes.getvalue()).decode("utf-8"),
            )
        )
    return ImageResponse(images=images, seed_used=result.get("seed_used"))


@app.post("/infer/chat", response_model=ChatResponse, dependencies=[Depends(require_api_key)])
def infer_chat(body: InferRequest) -> ChatResponse:
    handler = QwenChatHandler()
    model = get_model(body.model, handler)
    result = handler.infer(
        model,
        {"prompt": body.prompt, "negative_prompt": body.negative_prompt},
        body.params.model_dump(exclude_none=True),
    )
    return ChatResponse(text=result["text"], tokens_used=result["tokens_used"])


@app.post("/infer/video", response_model=VideoResponse, dependencies=[Depends(require_api_key)])
def infer_video(body: InferRequest) -> VideoResponse:
    handler = _video_handler_for_model(body.model)
    model = get_model(body.model, handler)
    result = handler.infer(
        model,
        {"prompt": body.prompt, "negative_prompt": body.negative_prompt},
        body.params.model_dump(exclude_none=True),
    )
    return VideoResponse(
        video=VideoArtifact(
            filename=f"{body.model}.gif",
            content_type="image/gif",
            data_base64=base64.b64encode(result["video_bytes"]).decode("utf-8"),
        ),
        frames=result["frames"],
    )


def _image_handler_for_model(model_name: str):
    if model_name == "qwen-image-edit":
        return QwenImageEditHandler()
    return QwenImageHandler()


def _video_handler_for_model(model_name: str):
    if model_name == "ltx-2.3":
        return LTXVideoHandler()
    elif model_name == "wan-2.2":
        return WANVideoHandler()
    return QwenVideoHandler()
