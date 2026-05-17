from functools import lru_cache
from pathlib import Path

import yaml
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # GCP
    gcp_project: str = ""
    gcp_region: str = "us-central1"
    vertex_ai_location: str = "global"

    # Database
    database_url: str = "postgresql://social:social@localhost:5432/social_assistant"

    # GitHub
    github_token: str = ""

    # Telegram
    telegram_bot_token: str = ""
    telegram_chat_id: str = ""

    # Bluesky
    bluesky_handle: str = ""
    bluesky_password: str = ""

    # Pipeline (overridable via env, defaults come from config.yaml)
    model_default: str = "gemini-3.1-pro-preview"
    model_fast: str = "gemini-3.1-flash-lite"
    max_qa_retries: int = 2
    dedup_lookback_days: int = 90


class AppConfig:
    """Non-secret config loaded from config.yaml."""

    def __init__(self, path: Path = Path("config.yaml")) -> None:
        with open(path) as f:
            raw = yaml.safe_load(f)
        self.github = raw.get("github", {})
        self.pipeline = raw.get("pipeline", {})
        self.platforms = raw.get("platforms", {})
        self.gcp = raw.get("gcp", {})

        # Expose commonly used values
        self.tracked_users: list[str] = self.github.get("tracked_users", [])
        self.tracked_repos: list[str] = self.github.get("tracked_repos", [])
        self.star_jump_pct_7d: int = self.github.get("star_jump_pct_7d", 50)
        self.star_jump_abs_24h: int = self.github.get("star_jump_abs_24h", 100)
        self.star_cooldown_days: int = self.github.get("star_cooldown_days", 30)


@lru_cache
def get_settings() -> Settings:
    return Settings()


@lru_cache
def get_config() -> AppConfig:
    return AppConfig()
