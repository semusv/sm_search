from dataclasses import dataclass
from typing import Optional

from sqlalchemy import Select, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from common.models import TicketEmbedding


@dataclass
class RetrievedChunk:
    ticket_id: str
    chunk_index: int
    chunk_text: str
    functional_area: Optional[str]
    score: float
    source_type: str


async def vector_search(
    session: AsyncSession,
    query_embedding: list[float],
    top_k: int,
    functional_area: Optional[str] = None,
) -> list[RetrievedChunk]:
    stmt: Select[tuple[TicketEmbedding, float]] = (
        select(
            TicketEmbedding,
            (1 - TicketEmbedding.embedding.cosine_distance(query_embedding)).label("score"),
        )
        .order_by(text("score DESC"))
        .limit(top_k)
    )
    if functional_area:
        stmt = stmt.where(TicketEmbedding.functional_area == functional_area)

    rows = (await session.execute(stmt)).all()
    return [
        RetrievedChunk(
            ticket_id=row[0].external_ticket_id,
            chunk_index=row[0].chunk_index,
            chunk_text=row[0].chunk_text,
            functional_area=row[0].functional_area,
            score=float(row[1]),
            source_type="vector",
        )
        for row in rows
    ]


async def fuzzy_search_tickets(
    session: AsyncSession,
    query: str,
    top_k: int,
    threshold: float,
    functional_area: Optional[str] = None,
) -> list[RetrievedChunk]:
    sql = """
    SELECT
      te.external_ticket_id,
      te.chunk_index,
      te.chunk_text,
      te.functional_area,
      similarity(t.concat_text, :query) AS score
    FROM tickets t
    JOIN ticket_embeddings te ON te.ticket_id = t.id
    WHERE similarity(t.concat_text, :query) >= :threshold
      AND (:functional_area IS NULL OR te.functional_area = :functional_area)
    ORDER BY score DESC
    LIMIT :top_k
    """
    rows = (await session.execute(text(sql), {
        "query": query,
        "threshold": threshold,
        "top_k": top_k,
        "functional_area": functional_area,
    })).all()
    return [
        RetrievedChunk(
            ticket_id=row[0],
            chunk_index=row[1],
            chunk_text=row[2],
            functional_area=row[3],
            score=float(row[4]),
            source_type="fuzzy",
        )
        for row in rows
    ]
