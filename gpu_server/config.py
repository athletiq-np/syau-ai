from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", case_sensitive=False)

    host: str = "0.0.0.0"
    port: int = 8100
    api_key: str = "change-me"
    models_dir: str = "/data/models"
    inference_mode: str = "real"
    chat_max_new_tokens: int = 512
    chat_temperature: float = 0.7


settings = Settings()
