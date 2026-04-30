import logging
import time
from dataclasses import dataclass

from sqlalchemy.ext.asyncio import AsyncSession

from common.config import Settings
from common.embeddings import embed_text
from common.fuzzy_search import search_fuzzy_chunks
from common.prompt_templates import build_answer_prompt
from common.repository import RetrievedChunk, vector_search
from common.reranker import BaseReranker
from common.schemas import SearchRequest, SearchResponse, SearchSource


logger = logging.getLogger(__name__)


@dataclass
class PipelineDeps:
    settings: Settings
    reranker: BaseReranker | None = None
    llm_client: object | None = None


class SearchPipeline:
    def __init__(self, deps: PipelineDeps):
        self.deps = deps

    async def run(self, session: AsyncSession, request: SearchRequest) -> SearchResponse:
        # Параметры ранжирования можно переопределить в конкретном запросе.
        settings = self.deps.settings
        timing: dict[str, float] = {}

        vector_top_k = request.vector_top_k or settings.vector_top_k
        rerank_top_k = request.rerank_top_k or settings.rerank_top_k
        fuzzy_top_k = request.fuzzy_top_k or settings.fuzzy_top_k
        final_context_size = request.final_context_size or settings.final_context_size

        vector_hits: list[RetrievedChunk] = []
        reranked_hits: list[RetrievedChunk] = []
        fuzzy_hits: list[RetrievedChunk] = []

        if settings.enable_vector_search:
            # Шаг 1: грубый отбор кандидатов через векторный поиск.
            t0 = time.perf_counter()
            query_embedding = embed_text(request.query)
            vector_hits = await vector_search(
                session=session,
                query_embedding=query_embedding,
                top_k=vector_top_k,
                functional_area=request.functional_area,
            )
            timing["vector_search_s"] = time.perf_counter() - t0

        if settings.enable_reranking and self.deps.reranker and vector_hits:
            # Шаг 2: точное переупорядочивание найденных векторных кандидатов.
            t0 = time.perf_counter()
            reranked_hits = await self.deps.reranker.rerank(request.query, vector_hits, rerank_top_k)
            timing["rerank_s"] = time.perf_counter() - t0
        else:
            reranked_hits = vector_hits[:rerank_top_k]

        if settings.enable_fuzzy_search:
            # Шаг 3: параллельный/дополнительный fuzzy-поиск по текстовым полям.
            t0 = time.perf_counter()
            fuzzy_hits = await search_fuzzy_chunks(
                session=session,
                query=request.query,
                top_k=fuzzy_top_k,
                threshold=settings.fuzzy_threshold,
                functional_area=request.functional_area,
            )
            timing["fuzzy_search_s"] = time.perf_counter() - t0

        merged = self._merge_and_deduplicate(reranked_hits, fuzzy_hits)
        final_chunks = merged[:final_context_size]

        llm_generated = False
        answer = None
        used_llm_model = None
        if settings.enable_llm and self.deps.llm_client and final_chunks:
            # Шаг 4: генерация ответа по собранному контексту (RAG).
            t0 = time.perf_counter()
            prompt = build_answer_prompt(request.query, final_chunks)
            try:
                answer = await self.deps.llm_client.generate(prompt)
                llm_generated = True
                used_llm_model = settings.llm_model
            except Exception as exc:  # noqa: BLE001
                logger.exception("LLM generation failed; fallback to search-only: %s", exc)
            timing["llm_s"] = time.perf_counter() - t0

        logger.info("search_pipeline_timing=%s", timing)
        return SearchResponse(
            answer=answer,
            llm_generated=llm_generated,
            used_llm_model=used_llm_model,
            sources=[
                SearchSource(
                    ticket_id=item.ticket_id,
                    chunk_index=item.chunk_index,
                    chunk_text=item.chunk_text,
                    relevance_score=item.score,
                    source_type=item.source_type if item.source_type in {"reranked", "fuzzy"} else "vector",
                    functional_area=item.functional_area,
                )
                for item in final_chunks
            ],
        )

    @staticmethod
    def _merge_and_deduplicate(*groups: list[RetrievedChunk]) -> list[RetrievedChunk]:
        # Дедупликация по (ticket_id, chunk_index) с сохранением лучшего score.
        merged: dict[tuple[str, int], RetrievedChunk] = {}
        for group in groups:
            for item in group:
                key = (item.ticket_id, item.chunk_index)
                existing = merged.get(key)
                if existing is None or item.score > existing.score:
                    merged[key] = item
        return sorted(merged.values(), key=lambda x: x.score, reverse=True)
