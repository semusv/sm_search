import logging

from fastapi import Depends, FastAPI
from sqlalchemy.ext.asyncio import AsyncSession

from common.config import get_settings
from common.db import get_db_session
from common.llm_client import LocalLLMClient, OpenAIClient
from common.reranker import CrossEncoderReranker
from common.schemas import SearchRequest, SearchResponse
from common.search_pipeline import PipelineDeps, SearchPipeline


logging.basicConfig(level=logging.INFO)
settings = get_settings()
app = FastAPI(title="SAP Search + LLM")


def build_pipeline() -> SearchPipeline:
    # Все компоненты пайплайна подключаются через конфиг и могут отключаться фичефлагами.
    reranker = CrossEncoderReranker(settings.reranker_model) if settings.enable_reranking else None
    llm_client = None
    if settings.enable_llm:
        llm_client = OpenAIClient(settings) if settings.llm_provider == "openai" else LocalLLMClient(settings)
    return SearchPipeline(PipelineDeps(settings=settings, reranker=reranker, llm_client=llm_client))


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/search", response_model=SearchResponse)
async def search(request: SearchRequest, session: AsyncSession = Depends(get_db_session)) -> SearchResponse:
    # Эндпоинт возвращает либо LLM-ответ + источники, либо search-only fallback.
    pipeline = build_pipeline()
    return await pipeline.run(session, request)
