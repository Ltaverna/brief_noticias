"""add entities and cluster_entities tables

Revision ID: 0005_entities
Revises: 0004_sagas
"""
from collections.abc import Sequence
from alembic import op
import sqlalchemy as sa

revision: str = "0005_entities"
down_revision: str | None = "0004_sagas"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "entities",
        sa.Column("id", sa.BigInteger, primary_key=True),
        sa.Column("name", sa.Text, nullable=False),
        sa.Column("kind", sa.String(16), nullable=False),
        sa.Column("canonical", sa.Text, nullable=False),
        sa.Column("first_seen_at", sa.DateTime(timezone=True),
                  server_default=sa.func.now(), nullable=False),
        sa.Column("last_seen_at", sa.DateTime(timezone=True),
                  server_default=sa.func.now(), nullable=False),
        sa.Column("mention_count", sa.Integer, server_default="0", nullable=False),
        sa.UniqueConstraint("canonical", "kind", name="uq_entities_canon_kind"),
    )
    op.execute("CREATE INDEX ix_entities_canonical ON entities(canonical)")
    op.execute("CREATE INDEX ix_entities_kind ON entities(kind)")
    op.execute("CREATE INDEX ix_entities_last_seen ON entities(last_seen_at DESC)")

    op.create_table(
        "cluster_entities",
        sa.Column("cluster_id", sa.BigInteger,
                  sa.ForeignKey("clusters.id", ondelete="CASCADE"), nullable=False),
        sa.Column("entity_id", sa.BigInteger,
                  sa.ForeignKey("entities.id", ondelete="CASCADE"), nullable=False),
        sa.Column("mention_count", sa.Integer, server_default="1", nullable=False),
        sa.PrimaryKeyConstraint("cluster_id", "entity_id"),
    )
    op.execute("CREATE INDEX ix_cluster_entities_entity ON cluster_entities(entity_id)")


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_cluster_entities_entity")
    op.drop_table("cluster_entities")
    op.execute("DROP INDEX IF EXISTS ix_entities_last_seen")
    op.execute("DROP INDEX IF EXISTS ix_entities_kind")
    op.execute("DROP INDEX IF EXISTS ix_entities_canonical")
    op.drop_table("entities")
