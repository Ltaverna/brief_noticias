"""add cluster_notes

Revision ID: 0008_cluster_notes
Revises: 0007_cluster_topic
"""
from collections.abc import Sequence
from alembic import op
import sqlalchemy as sa

revision: str = "0008_cluster_notes"
down_revision: str | None = "0007_cluster_topic"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "cluster_notes",
        sa.Column("id", sa.BigInteger, primary_key=True),
        sa.Column("cluster_id", sa.BigInteger,
                  sa.ForeignKey("clusters.id", ondelete="CASCADE"), nullable=False),
        sa.Column("note", sa.Text, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True),
                  server_default=sa.func.now(), nullable=False),
    )
    op.execute("CREATE INDEX ix_cluster_notes_cluster ON cluster_notes(cluster_id)")


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_cluster_notes_cluster")
    op.drop_table("cluster_notes")
