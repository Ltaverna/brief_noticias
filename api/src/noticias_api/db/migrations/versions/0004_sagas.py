"""add sagas table and clusters.saga_id

Revision ID: 0004_sagas
Revises: 0003_fts
"""
from collections.abc import Sequence
from alembic import op
import sqlalchemy as sa
import pgvector.sqlalchemy

revision: str = "0004_sagas"
down_revision: str | None = "0003_fts"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "sagas",
        sa.Column("id", sa.BigInteger, primary_key=True),
        sa.Column("title", sa.Text, nullable=False),
        sa.Column("centroid", pgvector.sqlalchemy.Vector(1536), nullable=True),
        sa.Column("first_seen_at", sa.DateTime(timezone=True),
                  server_default=sa.func.now(), nullable=False),
        sa.Column("last_seen_at", sa.DateTime(timezone=True),
                  server_default=sa.func.now(), nullable=False),
        sa.Column("cluster_count", sa.Integer, server_default="0", nullable=False),
        sa.Column("source_count", sa.Integer, server_default="0", nullable=False),
        sa.Column("article_count", sa.Integer, server_default="0", nullable=False),
    )
    op.execute("CREATE INDEX ix_sagas_last_seen ON sagas (last_seen_at DESC)")
    op.add_column(
        "clusters",
        sa.Column("saga_id", sa.BigInteger,
                  sa.ForeignKey("sagas.id", ondelete="SET NULL"), nullable=True),
    )
    op.execute("CREATE INDEX ix_clusters_saga ON clusters(saga_id)")


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_clusters_saga")
    op.drop_column("clusters", "saga_id")
    op.execute("DROP INDEX IF EXISTS ix_sagas_last_seen")
    op.drop_table("sagas")
