"""author kind

Revision ID: 0012_author_kind
Revises: 0011_source_color
Create Date: 2026-05-29
"""
from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa

revision: str = "0012_author_kind"
down_revision: str | None = "0011_source_color"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


KNOWN_AGENCIES = (
    "reuters", "ap", "afp", "telam", "efe", "dpa", "bloomberg", "ansa",
    "associated press", "agencia",
)


def upgrade() -> None:
    op.add_column(
        "authors",
        sa.Column("kind", sa.String(16), nullable=False, server_default="person"),
    )
    # Re-clasificar:
    #   sintéticos existentes (Redacción <Diario>) -> 'newsroom'
    op.execute(
        "UPDATE authors SET kind = 'newsroom' WHERE is_synthetic = TRUE"
    )
    # Autores cuyo nombre canonical coincide con una agencia conocida -> agency
    # (también los marcamos sintéticos porque no son personas reales)
    agency_canons = [a for a in KNOWN_AGENCIES]
    canon_list = ", ".join(f"'{a}'" for a in agency_canons)
    op.execute(
        f"""
        UPDATE authors
        SET kind = 'agency', is_synthetic = TRUE
        WHERE canonical IN ({canon_list})
           OR canonical ~ '^(reuters|afp|ap|telam|efe|dpa|bloomberg|ansa)( |$)'
        """
    )


def downgrade() -> None:
    op.drop_column("authors", "kind")
