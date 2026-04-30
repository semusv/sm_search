"""initial schema with pgvector and pg_trgm

Revision ID: 0001_initial
Revises:
Create Date: 2026-04-30 10:40:00
"""

from alembic import op
import sqlalchemy as sa
from pgvector.sqlalchemy import Vector


revision = "0001_initial"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")
    op.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm")

    op.create_table(
        "tickets",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("ticket_id", sa.String(length=64), nullable=False, unique=True),
        sa.Column("functional_area", sa.String(length=255), nullable=True),
        sa.Column("user_question", sa.Text(), nullable=False),
        sa.Column("support_answer", sa.Text(), nullable=False),
        sa.Column("concat_text", sa.Text(), nullable=False),
    )
    op.create_index("ix_tickets_ticket_id", "tickets", ["ticket_id"], unique=True)
    op.create_index("ix_tickets_functional_area", "tickets", ["functional_area"])

    op.create_table(
        "ticket_embeddings",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("ticket_id", sa.Integer(), sa.ForeignKey("tickets.id", ondelete="CASCADE"), nullable=False),
        sa.Column("external_ticket_id", sa.String(length=64), nullable=False),
        sa.Column("chunk_index", sa.Integer(), nullable=False),
        sa.Column("chunk_text", sa.Text(), nullable=False),
        sa.Column("functional_area", sa.String(length=255), nullable=True),
        sa.Column("embedding", Vector(384), nullable=False),
        sa.Column("vector_score", sa.Float(), nullable=True),
    )
    op.create_index("ix_ticket_embeddings_ticket_id", "ticket_embeddings", ["ticket_id"])
    op.create_index("ix_ticket_embeddings_external_ticket_id", "ticket_embeddings", ["external_ticket_id"])
    op.create_index("ix_ticket_embeddings_functional_area", "ticket_embeddings", ["functional_area"])

    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_ticket_embeddings_vector_ivfflat "
        "ON ticket_embeddings USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_tickets_trgm "
        "ON tickets USING gin (concat_text gin_trgm_ops)"
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS idx_tickets_trgm")
    op.execute("DROP INDEX IF EXISTS idx_ticket_embeddings_vector_ivfflat")
    op.drop_table("ticket_embeddings")
    op.drop_table("tickets")
