"""All configuration lives here. Nothing else in the app reads os.environ directly."""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "postgresql+psycopg://nibble:nibble@localhost:5432/nibble"

    llm_provider: str = "openai"
    llm_api_key: str = ""
    llm_chat_model: str = "gpt-4o-mini"
    llm_embedding_model: str = "text-embedding-3-small"
    embedding_dim: int = 1536

    cors_origins: str = "http://localhost:5173"

    # Chunking knobs - tune these once retrieval quality matters.
    chunk_size: int = 900
    chunk_overlap: int = 150
    top_k: int = 5

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
