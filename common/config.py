from functools import lru_cache
from typing import Literal, Optional

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "sap-rag"
    log_level: str = "INFO"

    database_url: str = Field(default="postgresql+asyncpg://postgres:postgres@localhost:5432/sap_rag")
    source_schema: str = "public"
    source_table: str = "tickets_source"
    source_ticket_id_column: str = "ticket_id"
    source_question_column: str = "user_question"
    source_answer_column: str = "support_answer"
    source_functional_area_column: str = "functional_area"
    embedding_dimension: int = 384
    embedding_model: str = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
    chunk_size: int = 700
    chunk_overlap: int = 120

    enable_vector_search: bool = True
    enable_reranking: bool = True
    enable_fuzzy_search: bool = True
    enable_llm: bool = True

    vector_top_k: int = 20
    rerank_top_k: int = 5
    reranker_model: str = "cross-encoder/ms-marco-MiniLM-L-6-v2"
    fuzzy_top_k: int = 5
    fuzzy_threshold: float = 0.4
    final_context_size: int = 7

    llm_provider: Literal["openai", "local"] = "openai"
    llm_model: str = "gpt-4o-mini"
    llm_temperature: float = 0.2
    llm_max_tokens: int = 1000
    llm_top_p: float = 0.95
    llm_api_key: Optional[str] = None
    llm_base_url: str = "https://api.openai.com/v1/chat/completions"
    llm_timeout_seconds: float = 40.0
    llm_retries: int = 3
    llm_model_path: Optional[str] = None


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
