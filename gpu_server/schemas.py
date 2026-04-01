from __future__ import annotations

from typing import Any, Optional

from pydantic import BaseModel, Field


class InferParams(BaseModel):
    width: Optional[int] = None
    height: Optional[int] = None
    steps: Optional[int] = None
    cfg_scale: Optional[float] = None
    seed: Optional[int] = None
    num_frames: Optional[int] = None
    input_image_base64: Optional[str] = None
    input_image_name: Optional[str] = None


class InferRequest(BaseModel):
    model: str = Field(..., min_length=1, max_length=64)
    prompt: str = Field(..., min_length=1, max_length=2000)
    negative_prompt: str = Field("", max_length=2000)
    params: InferParams = Field(default_factory=InferParams)


class ImageArtifact(BaseModel):
    filename: str
    content_type: str
    data_base64: str


class VideoArtifact(BaseModel):
    filename: str
    content_type: str
    data_base64: str


class ImageResponse(BaseModel):
    images: list[ImageArtifact]
    seed_used: Optional[int] = None


class ChatResponse(BaseModel):
    text: str
    tokens_used: int


class VideoResponse(BaseModel):
    video: VideoArtifact
    frames: int


class HealthResponse(BaseModel):
    status: str
    mode: str


class ModelsResponse(BaseModel):
    models: dict[str, list[dict[str, Any]]]
