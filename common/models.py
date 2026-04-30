from sqlalchemy import Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from pgvector.sqlalchemy import Vector


class Base(DeclarativeBase):
    pass


class Ticket(Base):
    __tablename__ = "tickets"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    ticket_id: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    functional_area: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    user_question: Mapped[str] = mapped_column(Text)
    support_answer: Mapped[str] = mapped_column(Text)
    concat_text: Mapped[str] = mapped_column(Text)


class TicketEmbedding(Base):
    __tablename__ = "ticket_embeddings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    ticket_id: Mapped[int] = mapped_column(ForeignKey("tickets.id", ondelete="CASCADE"), index=True)
    external_ticket_id: Mapped[str] = mapped_column(String(64), index=True)
    chunk_index: Mapped[int] = mapped_column(Integer)
    chunk_text: Mapped[str] = mapped_column(Text)
    functional_area: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    embedding: Mapped[list[float]] = mapped_column(Vector(384))
    vector_score: Mapped[float | None] = mapped_column(Float, nullable=True)
