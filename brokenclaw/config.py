from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    host: str = "127.0.0.1"
    port: int = 9000
    token_file: Path = Path("tokens.json")
    client_secret_file: Path = Path("client_secret.json")
    log_level: str = "INFO"
    google_maps_api_key: str = ""
    news_api_key: str = ""
    github_token: str = ""
    wolfram_app_id: str = ""
    canvas_feed_url: str = ""

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


@lru_cache
def get_settings() -> Settings:
    return Settings()
