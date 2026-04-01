import uuid
from datetime import datetime, timezone
from sqlalchemy import (
    Column, String, Text, Integer, Float, Boolean,
    DateTime, Enum as SAEnum, JSON
)
from sqlalchemy.dialects.postgresql import UUID
import enum

from core.database import Base


class JobStatus(str, enum.Enum):
    pending = "pending"
    running = "running"
    done = "done"
    failed = "failed"
    cancelled = "cancelled"


class Job(Base):
    __tablename__ = "jobs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    status = Column(SAEnum(JobStatus), nullable=False, default=JobStatus.pending, index=True)
    type = Column(String(32), nullable=False, index=True)
    model = Column(String(64), nullable=False)
    prompt = Column(Text, nullable=False)
    negative_prompt = Column(Text, nullable=False, default="")
    params = Column(JSON, nullable=False, default=dict)
    output_keys = Column(JSON, nullable=True)
    seed_used = Column(Integer, nullable=True)
    duration_seconds = Column(Float, nullable=True)
    error = Column(Text, nullable=True)
    celery_task_id = Column(String(255), nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))
    started_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)


class AIModel(Base):
    __tablename__ = "models"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(64), unique=True, nullable=False, index=True)
    display_name = Column(String(128), nullable=False)
    type = Column(String(32), nullable=False, index=True)
    local_path = Column(String(512), nullable=False)
    is_enabled = Column(Boolean, nullable=False, default=True)
    max_width = Column(Integer, nullable=True)
    max_height = Column(Integer, nullable=True)
    credit_cost = Column(Integer, nullable=False, default=1)
    created_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))
