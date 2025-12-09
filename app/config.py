from __future__ import annotations

from enum import Enum
from pathlib import Path
from typing import Optional

import httpx
from pydantic import BaseSettings, Field


class ModelProvider(str, Enum):
    OPENAI = "OPENAI"
    ANTHROPIC = "ANTHROPIC"


class Settings(BaseSettings):
    search_url: str = Field(
        "https://www.zhipin.com/web/geek/jobs?city=101200100&jobType=1901&salary=406&experience=107&degree=203&scale=303&query=java",
        env="SEARCH_URL",
    )
    resume_profile: str = Field("", env="RESUME_PROFILE")
    resume_profile_url: Optional[str] = Field(
        "https://blog.242500.xyz", env="RESUME_PROFILE_URL"
    )
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

    _cached_resume: Optional[str] = None

    def get_api_key(self) -> str:
        if self.model_provider == ModelProvider.ANTHROPIC:
            if not self.claude_api_key:
                raise ValueError("CLAUDE_API_KEY is not set")
            return self.claude_api_key
        if not self.openai_api_key:
            raise ValueError("OPENAI_API_KEY is not set")
        return self.openai_api_key

    def load_resume_profile(self) -> str:
        if self._cached_resume:
            return self._cached_resume

        if self.resume_profile.strip():
            self._cached_resume = self.resume_profile.strip()
            return self._cached_resume

        resume_text = ""
        if self.resume_profile_url:
            try:
                response = httpx.get(self.resume_profile_url, timeout=10)
                response.raise_for_status()
                resume_text = response.text
            except Exception:
                resume_text = ""

        self._cached_resume = resume_text.strip()
        return self._cached_resume


settings = Settings()
