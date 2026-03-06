"""
core/config.py — Variables d'environnement et configuration globale.

Utilise pydantic-settings pour valider et typer toutes les variables d'env
au démarrage. Une erreur de validation lève une exception immédiatement.

Supporte OpenAI direct ou OpenRouter (alternative économique).
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic import Field, HttpUrl
from pydantic_settings import BaseSettings, SettingsConfigDict


ENV_FILE_PATH = Path(__file__).resolve().parent.parent / ".env"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(ENV_FILE_PATH),
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # --- LLM Provider ---
    # Supporte OpenAI direct OU OpenRouter (plus économique)
    # Priorité : OPENROUTER_API_KEY > OPENAI_API_KEY
    openrouter_api_key: str | None = Field(
        None, description="Clé API OpenRouter (alternative économique)"
    )
    openai_api_key: str | None = Field(
        None, description="Clé API OpenAI directe (fallback si pas d'OpenRouter)"
    )
    openai_api_base: str = Field(
        "https://api.openai.com/v1",
        description="Base URL de l'API (OpenRouter: https://openrouter.ai/api/v1)"
    )

    # --- Modèle LLM ---
    openai_model: str = Field(
        "gpt-4o-mini",
        description="Modèle LLM principal (gpt-4o-mini recommandé pour coût/qualité)"
    )
    llm_temperature: float = Field(0.3, ge=0.0, le=2.0)
    llm_max_retries: int = Field(3, ge=1, le=10)
    llm_timeout_seconds: int = Field(60, ge=10, le=300)

    # --- LangSmith (Tracing) ---
    langchain_tracing_v2: bool = Field(False, description="Activer le tracing LangSmith")
    langchain_endpoint: str = Field("https://api.smith.langchain.com")
    langchain_api_key: str | None = Field(None, description="Clé API LangSmith")
    langchain_project: str = Field("SEO-Factory-Dev", description="Nom du projet LangSmith")

    # --- Crawl4AI ---
    crawl4ai_headless: bool = Field(True, description="Mode headless du navigateur")
    crawl4ai_timeout: int = Field(30, ge=5, le=120)
    crawl4ai_wait_time: int = Field(2, ge=0, le=10)

    # --- FastAPI ---
    environment: str = Field("development")
    api_host: str = Field("0.0.0.0")
    api_port: int = Field(8000, ge=1, le=65535)
    api_debug: bool = Field(False)

    # --- Sécurité ---
    api_rate_limit: int = Field(100, ge=1, le=1000)
    api_key_required: bool = Field(False)

    # --- Pipeline ---
    max_arbitre_retries: int = Field(3, ge=1, le=10)

    @property
    def effective_api_key(self) -> str:
        """Retourne la clé API à utiliser (OpenRouter prioritaire, sinon OpenAI)."""
        if self.openrouter_api_key:
            return self.openrouter_api_key
        if self.openai_api_key:
            return self.openai_api_key
        raise ValueError(
            "Aucune clé API LLM configurée. "
            "Définissez OPENROUTER_API_KEY ou OPENAI_API_KEY dans .env"
        )

    @property
    def is_openrouter(self) -> bool:
        """True si on utilise OpenRouter comme provider."""
        return self.openrouter_api_key is not None


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Retourne l'instance singleton des settings (chargée une seule fois)."""
    return Settings()
