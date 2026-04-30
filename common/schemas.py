from typing import Literal, Optional

from pydantic import BaseModel, Field


class SearchRequest(BaseModel):
    query: str = Field(min_length=3)
    functional_area: Optional[str] = None
    vector_top_k: Optional[int] = None
    rerank_top_k: Optional[int] = None
    fuzzy_top_k: Optional[int] = None
    final_context_size: Optional[int] = None


class SearchSource(BaseModel):
    ticket_id: str
    chunk_index: int
    chunk_text: str
    relevance_score: float
    source_type: Literal["reranked", "fuzzy", "vector"]
    functional_area: Optional[str] = None


class SearchResponse(BaseModel):
    answer: Optional[str] = None
    sources: list[SearchSource]
    used_llm_model: Optional[str] = None
    llm_generated: bool = False
