from abc import ABC, abstractmethod

from common.repository import RetrievedChunk


class BaseReranker(ABC):
    @abstractmethod
    async def rerank(self, query: str, chunks: list[RetrievedChunk], top_k: int) -> list[RetrievedChunk]:
        raise NotImplementedError


class CrossEncoderReranker(BaseReranker):
    def __init__(self, model_name: str):
        from sentence_transformers import CrossEncoder

        self.model = CrossEncoder(model_name)

    async def rerank(self, query: str, chunks: list[RetrievedChunk], top_k: int) -> list[RetrievedChunk]:
        # Реранжер оценивает пару (запрос, чанк) и возвращает наиболее релевантные.
        if not chunks:
            return []
        pairs = [(query, c.chunk_text) for c in chunks]
        scores = self.model.predict(pairs)
        reranked: list[RetrievedChunk] = []
        for chunk, score in zip(chunks, scores):
            reranked.append(
                RetrievedChunk(
                    ticket_id=chunk.ticket_id,
                    chunk_index=chunk.chunk_index,
                    chunk_text=chunk.chunk_text,
                    functional_area=chunk.functional_area,
                    score=float(score),
                    source_type="reranked",
                )
            )
        reranked.sort(key=lambda item: item.score, reverse=True)
        return reranked[:top_k]
