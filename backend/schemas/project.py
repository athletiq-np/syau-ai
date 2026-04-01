from __future__ import annotations
from datetime import datetime
from typing import Any, Optional
from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field

from models.project import ProjectStatus, ShotStatus, ShotType


class CharacterCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=128)
    description: str = Field("", max_length=1000)


class CharacterResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    project_id: UUID
    name: str
    description: str
    reference_url: Optional[str] = None
    created_at: datetime


class ShotResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    scene_id: UUID
    project_id: UUID
    order_index: int
    shot_type: ShotType
    status: ShotStatus
    prompt: str
    negative_prompt: str
    duration_frames: int
    width: int
    height: int
    seed: Optional[int] = None
    character_ids: list[str]
    output_url: Optional[str] = None
    created_at: datetime
    completed_at: Optional[datetime] = None
    error: Optional[str] = None


class SceneResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    project_id: UUID
    order_index: int
    title: str
    description: str
    shots: list[ShotResponse] = []
    created_at: datetime


class ProjectResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    title: str
    description: str
    status: ProjectStatus
    total_shots: int
    output_url: Optional[str] = None
    created_at: datetime
    updated_at: datetime


class ProjectDetailResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    title: str
    description: str
    status: ProjectStatus
    script: str
    total_shots: int
    output_url: Optional[str] = None
    characters: list[CharacterResponse] = []
    scenes: list[SceneResponse] = []
    created_at: datetime
    updated_at: datetime


class ProjectCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=255)
    description: str = Field("", max_length=2000)
    script: str = Field(..., min_length=1)


class ScriptAnalysisResponse(BaseModel):
    """Response from Qwen script analysis"""
    scenes: list[dict[str, Any]]  # Raw scene/shot data from LLM


class ProjectListResponse(BaseModel):
    items: list[ProjectResponse]
    total: int
    page: int
    page_size: int
