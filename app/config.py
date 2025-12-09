from __future__ import annotations

from enum import Enum
from pathlib import Path
from typing import Optional

from pydantic import BaseSettings, Field


class ModelProvider(str, Enum):
    OPENAI = "OPENAI"
    ANTHROPIC = "ANTHROPIC"


class Settings(BaseSettings):
    search_url: str = Field(
        "https://www.zhipin.com/web/geek/job?query=Python&city=101010100",
        env="SEARCH_URL",
    )
    resume_profile: str = Field("", env="RESUME_PROFILE")
    openai_api_key: Optional[str] = Field(None, env="OPENAI_API_KEY")
    claude_api_key: Optional[str] = Field(None, env="CLAUDE_API_KEY")
    anthropic_api_url: Optional[str] = Field(None, env="ANTHROPIC_API_URL")
    model_provider: ModelProvider = Field(ModelProvider.OPENAI, env="MODEL_PROVIDER")
    database_url: str = Field("sqlite:///./data/jobs.db", env="DATABASE_URL")
    storage_state_path: Path = Field(Path("storage_state.json"), env="STORAGE_STATE_PATH")
    output_dir: Path = Field(Path("output"), env="OUTPUT_DIR")
    max_jobs: int = Field(20, env="MAX_JOBS")

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"

    def get_api_key(self) -> str:
        if self.model_provider == ModelProvider.ANTHROPIC:
            if not self.claude_api_key:
                raise ValueError("CLAUDE_API_KEY is not set")
            return self.claude_api_key
        if not self.openai_api_key:
            raise ValueError("OPENAI_API_KEY is not set")
        return self.openai_api_key


settings = Settings()
