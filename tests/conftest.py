import os
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from uuid import uuid4

TEST_DB_URL = "sqlite:///./test.db"
os.environ.setdefault("DATABASE_URL", TEST_DB_URL)
os.environ.setdefault("REDIS_URL", "redis://localhost:6379/1")
os.environ.setdefault("MINIO_ENDPOINT", "localhost:9000")
os.environ.setdefault("MINIO_ACCESS_KEY", "test")
os.environ.setdefault("MINIO_SECRET_KEY", "test1234")
os.environ.setdefault("MINIO_BUCKET", "test-bucket")
os.environ.setdefault("MINIO_SECURE", "false")
os.environ.setdefault("MINIO_PUBLIC_ENDPOINT", "http://localhost:9000")`nos.environ["INFERENCE_MODE"] = "mock"`nos.environ.pop("INFERENCE_API_BASE_URL", None)`nos.environ.pop("INFERENCE_API_KEY", None)

import sys
_repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
_backend_dir = os.path.join(_repo_root, "backend")
if os.path.isdir(_backend_dir):
    sys.path.insert(0, _backend_dir)
elif os.path.isdir("/app"):
    sys.path.insert(0, "/app")
else:
    sys.path.insert(0, _repo_root)

from core.database import Base
from main import app
from models.job import AIModel, Job


@pytest.fixture(scope="session")
def engine():
    _engine = create_engine(TEST_DB_URL, connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=_engine)
    yield _engine
    Base.metadata.drop_all(bind=_engine)


@pytest.fixture
def db(engine):
    TestSession = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = TestSession()
    try:
        session.query(Job).delete()
        session.query(AIModel).delete()
        session.add_all([
            AIModel(
                id=uuid4(),
                name="qwen-image-2512",
                display_name="Qwen Image 2512",
                type="image",
                local_path="/data/models/t2i/qwen-image-2512",
                is_enabled=True,
                max_width=2512,
                max_height=2512,
            ),
            AIModel(
                id=uuid4(),
                name="qwen-image-layered",
                display_name="Qwen Image Layered",
                type="image",
                local_path="/data/models/layered/qwen-image-layered",
                is_enabled=True,
                max_width=1024,
                max_height=1024,
            ),
            AIModel(
                id=uuid4(),
                name="qwen-image-edit",
                display_name="Qwen Image Edit",
                type="image",
                local_path="/data/models/qwen-image-edit",
                is_enabled=True,
                max_width=2048,
                max_height=2048,
            ),
            AIModel(
                id=uuid4(),
                name="qwen3.5-7b-instruct",
                display_name="Qwen 3.5 7B Instruct",
                type="chat",
                local_path="/data/models/llm/qwen3.5-7b-instruct",
                is_enabled=True,
            ),
            AIModel(
                id=uuid4(),
                name="ltx-2.3",
                display_name="LTX 2.3",
                type="video",
                local_path="/data/models/ltx-2.3",
                is_enabled=True,
                max_width=1024,
                max_height=1024,
            ),
        ])
        session.commit()
        yield session
    finally:
        session.rollback()
        session.close()


@pytest.fixture
def client(db):
    def override_get_db():
        try:
            yield db
        finally:
            pass

    from api.deps import get_session
    app.dependency_overrides[get_session] = override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()
