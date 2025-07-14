"""Configuration settings for the Azerbaijan Legal RAG API"""

import os
from typing import Optional
from pydantic_settings import BaseSettings
from pydantic import Field

# Disable tokenizers parallelism to prevent fork warnings
os.environ["TOKENIZERS_PARALLELISM"] = "false"


class Settings(BaseSettings):
    """Application settings with environment variable support"""

    # API Settings
    app_name: str = "Azerbaijan Legal RAG API"
    app_version: str = "1.0.0"
    api_prefix: str = "/api/v1"
    debug: bool = Field(default=False, env="DEBUG")

    # Docs Settings
    openapi_url: str | None = Field(default="/openapi.json", env="OPENAPI_URL")

    # CORS Settings
    cors_origins: list[str] = Field(default=["*"], env="CORS_ORIGINS")

    # OpenAI Settings
    openai_api_key: str = Field(..., env="OPENAI_API_KEY")
    llm_model: str = Field(default="gpt-4-turbo", env="LLM_MODEL")
    llm_temperature: float = Field(default=0.1, env="LLM_TEMPERATURE")

    # Chroma Settings
    chroma_api_key: str = Field(..., env="CHROMA_API_KEY")
    chroma_tenant_id: str = Field(
        default="9dbcf5dd-fab5-4e65-a402-75a6830743c5", env="CHROMA_TENANT_ID"
    )
    chroma_database: str = Field(default="LegalRAG", env="CHROMA_DATABASE")
    chroma_collection: str = Field(default="LegalRAG", env="CHROMA_COLLECTION")

    # Redis Settings
    redis_url: str = Field(default="redis://localhost:6379", env="REDIS_URL")
    redis_password: Optional[str] = Field(default=None, env="REDIS_PASSWORD")
    redis_db: int = Field(default=0, env="REDIS_DB")
    session_ttl: int = Field(default=3600, env="SESSION_TTL")  # 1 hour

    # RAG Settings
    embedding_model: str = Field(
        default="intfloat/multilingual-e5-large", env="EMBEDDING_MODEL"
    )
    retrieval_k: int = Field(default=5, env="RETRIEVAL_K")
    chunk_size: int = Field(default=800, env="CHUNK_SIZE")
    chunk_overlap: int = Field(default=100, env="CHUNK_OVERLAP")

    class Config:
        env_file = ".env"
        case_sensitive = False


# Create global settings instance
settings = Settings()
