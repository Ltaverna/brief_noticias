"""add clusters.topic

Revision ID: 0007_cluster_topic
Revises: 0006_subs_alerts
"""
from collections.abc import Sequence
from alembic import op
import sqlalchemy as sa

revision: str = "0007_cluster_topic"
down_revision: str | None = "0006_subs_alerts"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("clusters", sa.Column("topic", sa.String(32), nullable=True))
    op.execute("CREATE INDEX ix_clusters_topic ON clusters(topic)")


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_clusters_topic")
    op.drop_column("clusters", "topic")
