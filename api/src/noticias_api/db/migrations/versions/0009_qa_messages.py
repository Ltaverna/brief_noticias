"""add qa_messages

Revision ID: 0009_qa_messages
Revises: 0008_cluster_notes
"""
from collections.abc import Sequence
from alembic import op
import sqlalchemy as sa

revision: str = "0009_qa_messages"
down_revision: str | None = "0008_cluster_notes"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "qa_messages",
        sa.Column("id", sa.BigInteger, primary_key=True),
        sa.Column("conversation_id", sa.String(64), nullable=False),
        sa.Column("role", sa.String(16), nullable=False),
        sa.Column("content", sa.Text, nullable=False),
        sa.Column("citations", sa.dialects.postgresql.JSONB, nullable=True),
        sa.Column("used_citations", sa.dialects.postgresql.JSONB, nullable=True),
        sa.Column("hyde_query", sa.Text, nullable=True),
        sa.Column("model", sa.String(64), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True),
                  server_default=sa.func.now(), nullable=False),
    )
    op.execute("CREATE INDEX ix_qa_messages_conv ON qa_messages(conversation_id, created_at)")


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_qa_messages_conv")
    op.drop_table("qa_messages")
