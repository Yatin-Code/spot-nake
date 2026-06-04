"""
SpotNake Configuration — Pydantic Settings
Loads all provider keys from .env with validation.
"""

from __future__ import annotations

import os
from pathlib import Path

from pydantic_settings import BaseSettings
from pydantic import Field


class Settings(BaseSettings):
    """All configuration from environment variables."""

    # ── Telegram ──
    telegram_bot_token: str
    telegram_owner_id: int

    # ── AI Providers (V1 Active) ──
    gemini_api_key: str          # Primary: intent parsing + embeddings
    groq_api_key: str            # Fallback #1: fast Llama 3.1 70B
    cerebras_api_key: str        # Fallback #2: ultra-fast Llama 3.1 8B
    openrouter_api_key: str      # Fallback #3: free Llama 3.1 8B
    
    # ── AI Providers (V2 Reserved) ──
    together_api_key: str = ""
    huggingface_api_key: str = ""
    replicate_api_token: str = ""
    cloudflare_api_key: str = ""
    nvidia_api_key: str = ""

    # ── Database ──
    mongodb_uri: str
    db_name: str = "spotnake"

    # ── App Settings ──
    port: int = 7860
    download_dir: str = "/data/downloads"
    max_recommendations: int = 10
    audio_format: str = "mp3"
    audio_quality: str = "320"
    log_level: str = "INFO"

    # ── Gemini Models ──
    gemini_model: str = "gemini-2.0-flash"
    embedding_model: str = "gemini-embedding-001"

    model_config = {
        "env_file": str(Path(__file__).resolve().parent.parent / ".env"),
        "env_file_encoding": "utf-8",
        "extra": "ignore",
    }


def get_settings() -> Settings:
    """Singleton-style settings loader."""
    return Settings()
