from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", case_sensitive=False)

    database_url: str
    redis_url: str = "redis://redis:6379/0"

    minio_endpoint: str = "minio:9000"
    minio_public_endpoint: str = "http://localhost:9000"
    minio_access_key: str = "changeme"
    minio_secret_key: str = "changeme_also"
    minio_bucket: str = "syau-outputs"
    minio_secure: bool = False

    models_dir: str = "/data/models"
    log_level: str = "INFO"
    environment: str = "development"
    inference_mode: str = "mock"
    inference_api_base_url: Optional[str] = None
    inference_api_key: Optional[str] = None
    inference_timeout_seconds: int = 180
    chat_max_new_tokens: int = 512
    chat_temperature: float = 0.7
    llm_default_model: str = "qwen3.5-7b-instruct"
    llm_default_path: str = "/data/models/llm/qwen3.5-7b-instruct"
    llm_planner_model: str = "/data/models/qwen2.5-awq"
    llm_planner_path: str = "/data/models/qwen2.5-awq"
    comfyui_url: Optional[str] = None
    stale_pending_seconds: int = 300
    stale_running_seconds: int = 3600


settings = Settings()
