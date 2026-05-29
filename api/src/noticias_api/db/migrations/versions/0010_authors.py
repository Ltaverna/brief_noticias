"""authors

Revision ID: 0010_authors
Revises: 0009_qa_messages
Create Date: 2026-05-28
"""
from alembic import op
import sqlalchemy as sa
from pgvector.sqlalchemy import Vector

revision = "0010_authors"
down_revision = "0009_qa_messages"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "authors",
        sa.Column("id", sa.BigInteger, primary_key=True),
        sa.Column("name", sa.Text, nullable=False),
        sa.Column("canonical", sa.Text, nullable=False),
        sa.Column("source_id", sa.Integer, sa.ForeignKey("sources.id"), nullable=True),
        sa.Column("is_synthetic", sa.Boolean, nullable=False, server_default=sa.false()),
        sa.Column("first_seen_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("last_seen_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("article_count", sa.Integer, nullable=False, server_default="0"),
        sa.Column("centroid", Vector(1536), nullable=True),
        sa.Column("profile_vector", Vector(20), nullable=True),
        sa.Column("centroid_updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.UniqueConstraint("canonical", "source_id", name="uq_authors_canon_source"),
    )
    op.create_index("ix_authors_canonical", "authors", ["canonical"])

    op.create_table(
        "article_authors",
        sa.Column("article_id", sa.BigInteger, sa.ForeignKey("articles.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("author_id", sa.BigInteger, sa.ForeignKey("authors.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("position", sa.SmallInteger, nullable=False, server_default="0"),
    )
    op.create_index("ix_article_authors_author", "article_authors", ["author_id", "article_id"])

    op.create_table(
        "author_aliases",
        sa.Column("id", sa.BigInteger, primary_key=True),
        sa.Column("alias_canonical", sa.Text, nullable=False, unique=True),
        sa.Column("author_id", sa.BigInteger, sa.ForeignKey("authors.id", ondelete="CASCADE"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    op.create_table(
        "author_profiles",
        sa.Column("author_id", sa.BigInteger, sa.ForeignKey("authors.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("profile_json", sa.dialects.postgresql.JSONB, nullable=False),
        sa.Column("model", sa.String(64), nullable=True),
        sa.Column("n_sample", sa.Integer, nullable=False),
        sa.Column("generated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    op.create_table(
        "author_comparisons",
        sa.Column("id", sa.BigInteger, primary_key=True),
        sa.Column("author_a_id", sa.BigInteger, sa.ForeignKey("authors.id", ondelete="CASCADE"), nullable=False),
        sa.Column("author_b_id", sa.BigInteger, sa.ForeignKey("authors.id", ondelete="CASCADE"), nullable=False),
        sa.Column("comparison_json", sa.dialects.postgresql.JSONB, nullable=False),
        sa.Column("model", sa.String(64), nullable=True),
        sa.Column("since", sa.Date, nullable=True),
        sa.Column("until", sa.Date, nullable=True),
        sa.Column("generated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("author_a_id", "author_b_id", "since", "until", name="uq_author_compare"),
    )


def downgrade() -> None:
    op.drop_table("author_comparisons")
    op.drop_table("author_profiles")
    op.drop_table("author_aliases")
    op.drop_index("ix_article_authors_author", table_name="article_authors")
    op.drop_table("article_authors")
    op.drop_index("ix_authors_canonical", table_name="authors")
    op.drop_table("authors")
