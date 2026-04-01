from __future__ import annotations
from datetime import datetime
from typing import Any, Optional
from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field

from models.job import JobStatus


class JobParams(BaseModel):
    width: int = Field(1024, ge=64, le=2512)
    height: int = Field(1024, ge=64, le=2512)
    steps: int = Field(20, ge=1, le=100)
    cfg_scale: float = Field(7.0, ge=1.0, le=30.0)
    seed: Optional[int] = None
    num_frames: Optional[int] = Field(default=None, ge=8, le=161)
    input_image_base64: Optional[str] = Field(default=None, max_length=20_000_000)
    input_image_name: Optional[str] = Field(default=None, max_length=255)


class JobCreate(BaseModel):
    type: str = Field(..., pattern="^(image|video|chat)$")
    model: str = Field(..., min_length=1, max_length=64)
    prompt: str = Field(..., min_length=1, max_length=2000)
    negative_prompt: str = Field("", max_length=2000)
    params: JobParams = Field(default_factory=JobParams)


class JobResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    status: JobStatus
    type: str
    model: str
    prompt: str
    negative_prompt: str
    params: Any
    output_keys: Optional[list] = None
    output_urls: Optional[list[str]] = None
    output_text: Optional[str] = None
    seed_used: Optional[int] = None
    duration_seconds: Optional[float] = None
    error: Optional[str] = None
    created_at: datetime
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None


class JobListResponse(BaseModel):
    items: list[JobResponse]
    total: int
    page: int
    page_size: int


class JobCreatedResponse(BaseModel):
    job_id: UUID
    status: JobStatus


class ModelResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    display_name: str
    type: str
    is_enabled: bool
    max_width: Optional[int] = None
    max_height: Optional[int] = None
