from fastapi import FastAPI
from pydantic import BaseModel
from sqlalchemy import delete, select, text
import re

from common.config import get_settings
from common.db import SessionLocal
from common.embeddings import embed_text
from common.models import Ticket, TicketEmbedding


settings = get_settings()
app = FastAPI(title="SAP Vectorizer")


class TicketIngest(BaseModel):
    ticket_id: str
    user_question: str
    support_answer: str
    functional_area: str | None = None


class IngestRequest(BaseModel):
    tickets: list[TicketIngest]


class SourceIngestRequest(BaseModel):
    limit: int | None = None
    offset: int = 0


def chunk_text(text: str, chunk_size: int, chunk_overlap: int) -> list[str]:
    # Простой символьный чанкинг с перекрытием соседних фрагментов.
    chunks: list[str] = []
    start = 0
    text = text.strip()
    if not text:
        return []
    while start < len(text):
        end = min(start + chunk_size, len(text))
        chunks.append(text[start:end])
        if end == len(text):
            break
        start = max(end - chunk_overlap, start + 1)
    return chunks


_IDENTIFIER_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


def _safe_identifier(name: str) -> str:
    """Проверяет имя схемы/таблицы/колонки для безопасной подстановки в SQL."""
    if not _IDENTIFIER_RE.match(name):
        raise ValueError(f"Invalid SQL identifier: {name}")
    return name


async def _upsert_ticket_chunks(session, ticket: TicketIngest) -> None:
    """Обновляет тикет и его чанки (идемпотентно)."""
    existing = await session.scalar(select(Ticket).where(Ticket.ticket_id == ticket.ticket_id))
    concat_text = f"{ticket.user_question}\n\n{ticket.support_answer}"

    if existing:
        existing.user_question = ticket.user_question
        existing.support_answer = ticket.support_answer
        existing.concat_text = concat_text
        existing.functional_area = ticket.functional_area
        db_ticket = existing
        await session.execute(delete(TicketEmbedding).where(TicketEmbedding.ticket_id == existing.id))
    else:
        db_ticket = Ticket(
            ticket_id=ticket.ticket_id,
            user_question=ticket.user_question,
            support_answer=ticket.support_answer,
            functional_area=ticket.functional_area,
            concat_text=concat_text,
        )
        session.add(db_ticket)
        await session.flush()

    chunks = chunk_text(concat_text, settings.chunk_size, settings.chunk_overlap)
    for idx, chunk in enumerate(chunks):
        session.add(
            TicketEmbedding(
                ticket_id=db_ticket.id,
                external_ticket_id=ticket.ticket_id,
                chunk_index=idx,
                chunk_text=chunk,
                functional_area=ticket.functional_area,
                embedding=embed_text(chunk),
            )
        )


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/index")
async def index_tickets(request: IngestRequest) -> dict[str, int]:
    # Индексация идемпотентная: при повторной загрузке тикета старые чанки удаляются.
    indexed = 0
    async with SessionLocal() as session:
        for ticket in request.tickets:
            await _upsert_ticket_chunks(session, ticket)
            indexed += 1
        await session.commit()
    return {"indexed_tickets": indexed}


@app.post("/index-from-source")
async def index_from_source(request: SourceIngestRequest) -> dict[str, int]:
    """
    Индексирует тикеты из внешней таблицы Postgres.
    Схема, таблица и названия колонок задаются через ENV.
    """
    schema = _safe_identifier(settings.source_schema)
    table = _safe_identifier(settings.source_table)
    c_ticket = _safe_identifier(settings.source_ticket_id_column)
    c_question = _safe_identifier(settings.source_question_column)
    c_answer = _safe_identifier(settings.source_answer_column)
    c_area = _safe_identifier(settings.source_functional_area_column)

    sql = (
        f'SELECT "{c_ticket}" AS ticket_id, '
        f'"{c_question}" AS user_question, '
        f'"{c_answer}" AS support_answer, '
        f'"{c_area}" AS functional_area '
        f'FROM "{schema}"."{table}" '
        "ORDER BY 1 "
        "LIMIT :limit OFFSET :offset"
    )
    limit = request.limit or 1000
    indexed = 0
    async with SessionLocal() as session:
        rows = (await session.execute(text(sql), {"limit": limit, "offset": request.offset})).mappings().all()
        for row in rows:
            ticket = TicketIngest(
                ticket_id=str(row["ticket_id"]),
                user_question=str(row["user_question"] or ""),
                support_answer=str(row["support_answer"] or ""),
                functional_area=(str(row["functional_area"]) if row["functional_area"] is not None else None),
            )
            await _upsert_ticket_chunks(session, ticket)
            indexed += 1
        await session.commit()
    return {"indexed_tickets": indexed}
