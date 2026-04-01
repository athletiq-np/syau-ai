import uuid
import enum
from datetime import datetime, timezone
from sqlalchemy import (
    Column, String, Text, Integer,
    DateTime, Enum as SAEnum, JSON, ForeignKey
)
from sqlalchemy.dialects.postgresql import UUID

from core.database import Base


class ProjectStatus(str, enum.Enum):
    draft = "draft"
    processing = "processing"
    done = "done"
    failed = "failed"


class ShotType(str, enum.Enum):
    t2v = "t2v"
    i2v = "i2v"


class ShotStatus(str, enum.Enum):
    pending = "pending"
    running = "running"
    done = "done"
    failed = "failed"


class Project(Base):
    __tablename__ = "projects"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=False, default="")
    status = Column(SAEnum(ProjectStatus), nullable=False, default=ProjectStatus.draft, index=True)
    script = Column(Text, nullable=False)
    total_shots = Column(Integer, nullable=False, default=0)
    output_key = Column(String(512), nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc), index=True)
    updated_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))


class Character(Base):
    __tablename__ = "characters"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id = Column(UUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True)
    name = Column(String(128), nullable=False)
    description = Column(Text, nullable=False, default="")
    reference_key = Column(String(512), nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))


class Scene(Base):
    __tablename__ = "scenes"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id = Column(UUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True)
    order_index = Column(Integer, nullable=False)
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=False, default="")
    created_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))


class Shot(Base):
    __tablename__ = "shots"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    scene_id = Column(UUID(as_uuid=True), ForeignKey("scenes.id", ondelete="CASCADE"), nullable=False, index=True)
    project_id = Column(UUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True)
    order_index = Column(Integer, nullable=False)
    shot_type = Column(SAEnum(ShotType), nullable=False, default=ShotType.t2v)
    status = Column(SAEnum(ShotStatus), nullable=False, default=ShotStatus.pending, index=True)
    prompt = Column(Text, nullable=False)
    negative_prompt = Column(Text, nullable=False, default="")
    duration_frames = Column(Integer, nullable=False, default=81)
    width = Column(Integer, nullable=False, default=640)
    height = Column(Integer, nullable=False, default=640)
    seed = Column(Integer, nullable=True)
    character_ids = Column(JSON, nullable=False, default=list)
    reference_key = Column(String(512), nullable=True)
    output_key = Column(String(512), nullable=True)
    job_id = Column(UUID(as_uuid=True), ForeignKey("jobs.id", ondelete="SET NULL"), nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))
    completed_at = Column(DateTime(timezone=True), nullable=True)
    error = Column(Text, nullable=True)
