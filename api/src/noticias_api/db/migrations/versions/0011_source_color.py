"""source color

Revision ID: 0011_source_color
Revises: 0010_authors
Create Date: 2026-05-28
"""
from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa

revision: str = "0011_source_color"
down_revision: str | None = "0010_authors"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "sources",
        sa.Column("color", sa.String(16), nullable=False, server_default="#94a3b8"),
    )
    # Pre-populate known sources (slugs match seed.py)
    op.execute("UPDATE sources SET color = '#1d4ed8' WHERE slug = 'clarin'")
    op.execute("UPDATE sources SET color = '#0f172a' WHERE slug = 'la-nacion'")
    op.execute("UPDATE sources SET color = '#0ea5e9' WHERE slug = 'infobae'")
    op.execute("UPDATE sources SET color = '#dc2626' WHERE slug = 'pagina-12'")
    op.execute("UPDATE sources SET color = '#f59e0b' WHERE slug = 'tiempo-argentino'")
    op.execute("UPDATE sources SET color = '#7c3aed' WHERE slug = 'el-destape'")
    op.execute("UPDATE sources SET color = '#16a34a' WHERE slug = 'ambito'")
    op.execute("UPDATE sources SET color = '#0d9488' WHERE slug = 'el-cronista'")
    op.execute("UPDATE sources SET color = '#475569' WHERE slug = 'bae'")


def downgrade() -> None:
    op.drop_column("sources", "color")
