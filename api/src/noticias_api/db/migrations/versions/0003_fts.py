"""add fts tsvector columns and GIN indexes

Revision ID: 0003_fts
Revises: 708d3d62e367
Create Date: 2026-05-09

"""
from collections.abc import Sequence

from alembic import op


revision: str = "0003_fts"
down_revision: str | None = "708d3d62e367"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Articles: title + content (or summary if no content)
    op.execute(
        """
        ALTER TABLE articles
        ADD COLUMN tsv tsvector
        GENERATED ALWAYS AS (
            to_tsvector('spanish',
                coalesce(title, '') || ' ' ||
                coalesce(content, summary, '')
            )
        ) STORED
        """
    )
    op.execute(
        "CREATE INDEX ix_articles_tsv ON articles USING GIN(tsv)"
    )

    # Analyses: headline + common_facts (jsonb cast to text)
    op.execute(
        """
        ALTER TABLE analyses
        ADD COLUMN tsv tsvector
        GENERATED ALWAYS AS (
            to_tsvector('spanish',
                coalesce(headline, '') || ' ' ||
                coalesce(common_facts::text, '')
            )
        ) STORED
        """
    )
    op.execute(
        "CREATE INDEX ix_analyses_tsv ON analyses USING GIN(tsv)"
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_analyses_tsv")
    op.execute("ALTER TABLE analyses DROP COLUMN IF EXISTS tsv")
    op.execute("DROP INDEX IF EXISTS ix_articles_tsv")
    op.execute("ALTER TABLE articles DROP COLUMN IF EXISTS tsv")
