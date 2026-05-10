"""add deliveries

Revision ID: 708d3d62e367
Revises: 47da95fe01a1
Create Date: 2026-05-09 16:52:21.631352

"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "708d3d62e367"
down_revision: str | None = "47da95fe01a1"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "deliveries",
        sa.Column("id", sa.BigInteger(), nullable=False),
        sa.Column("channel", sa.String(length=32), nullable=False),
        sa.Column("chat_id", sa.String(length=64), nullable=True),
        sa.Column("display_date", sa.Date(), nullable=False),
        sa.Column("message_hash", sa.String(length=64), nullable=False),
        sa.Column(
            "sent_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("error", sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "channel",
            "chat_id",
            "display_date",
            "message_hash",
            name="uq_deliveries_chan_chat_date_hash",
        ),
    )


def downgrade() -> None:
    op.drop_table("deliveries")
