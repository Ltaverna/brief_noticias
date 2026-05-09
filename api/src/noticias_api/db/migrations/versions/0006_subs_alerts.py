"""add subscriptions and alerts

Revision ID: 0006_subs_alerts
Revises: 0005_entities
"""
from collections.abc import Sequence
from alembic import op
import sqlalchemy as sa

revision: str = "0006_subs_alerts"
down_revision: str | None = "0005_entities"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "subscriptions",
        sa.Column("id", sa.BigInteger, primary_key=True),
        sa.Column("channel", sa.String(32), nullable=False),    # 'telegram'
        sa.Column("chat_id", sa.String(64), nullable=False),
        sa.Column("kind", sa.String(16), nullable=False),       # 'entity'|'topic'|'all'
        sa.Column("value", sa.Text, nullable=True),             # canonical entity name OR topic OR null for 'all'
        sa.Column("alert_threshold_sources", sa.Integer, nullable=True),  # if set, send instant alerts when matching cluster has source_count >= this
        sa.Column("created_at", sa.DateTime(timezone=True),
                  server_default=sa.func.now(), nullable=False),
    )
    op.execute("CREATE INDEX ix_subs_channel_chat ON subscriptions(channel, chat_id)")
    op.execute("CREATE INDEX ix_subs_kind_value ON subscriptions(kind, value)")

    # Track which clusters already triggered an alert to a chat (idempotency)
    op.create_table(
        "alert_deliveries",
        sa.Column("id", sa.BigInteger, primary_key=True),
        sa.Column("channel", sa.String(32), nullable=False),
        sa.Column("chat_id", sa.String(64), nullable=False),
        sa.Column("cluster_id", sa.BigInteger,
                  sa.ForeignKey("clusters.id", ondelete="CASCADE"), nullable=False),
        sa.Column("subscription_id", sa.BigInteger,
                  sa.ForeignKey("subscriptions.id", ondelete="CASCADE"), nullable=True),
        sa.Column("sent_at", sa.DateTime(timezone=True),
                  server_default=sa.func.now(), nullable=False),
        sa.Column("status", sa.String(16), nullable=False),     # 'sent'|'failed'
        sa.Column("error", sa.Text, nullable=True),
        sa.UniqueConstraint("channel", "chat_id", "cluster_id", "subscription_id",
                            name="uq_alert_chan_chat_cluster_sub"),
    )
    op.execute("CREATE INDEX ix_alert_del_cluster ON alert_deliveries(cluster_id)")


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_alert_del_cluster")
    op.drop_table("alert_deliveries")
    op.execute("DROP INDEX IF EXISTS ix_subs_kind_value")
    op.execute("DROP INDEX IF EXISTS ix_subs_channel_chat")
    op.drop_table("subscriptions")
