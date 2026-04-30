from sqlalchemy.ext.asyncio import AsyncSession

from common.repository import RetrievedChunk, fuzzy_search_tickets


async def search_fuzzy_chunks(
    session: AsyncSession,
    query: str,
    top_k: int,
    threshold: float,
    functional_area: str | None = None,
) -> list[RetrievedChunk]:
    fuzzy_hits = await fuzzy_search_tickets(
        session=session,
        query=query,
        top_k=top_k,
        threshold=threshold,
        functional_area=functional_area,
    )
    # Немного занижаем fuzzy-оценку относительно cross-encoder score.
    return [
        RetrievedChunk(
            ticket_id=item.ticket_id,
            chunk_index=item.chunk_index,
            chunk_text=item.chunk_text,
            functional_area=item.functional_area,
            score=item.score * 0.8,
            source_type="fuzzy",
        )
        for item in fuzzy_hits
    ]
