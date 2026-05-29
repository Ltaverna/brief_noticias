from datetime import date, datetime

from pgvector.sqlalchemy import Vector
from sqlalchemy import (
    BigInteger,
    Boolean,
    Computed,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB, TSVECTOR
from sqlalchemy.orm import Mapped, mapped_column, relationship


from noticias_api.db.base import Base

EMBEDDING_DIM = 1536


class Source(Base):
    __tablename__ = "sources"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    slug: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    editorial_group: Mapped[str] = mapped_column(String(32), nullable=False)
    rss_url: Mapped[str] = mapped_column(Text, nullable=False)
    base_url: Mapped[str] = mapped_column(Text, nullable=False)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True, server_default="true")
    color: Mapped[str] = mapped_column(
        String(16), nullable=False, default="#94a3b8", server_default=text("'#94a3b8'")
    )

    articles: Mapped[list["Article"]] = relationship(back_populates="source")


class Saga(Base):
    __tablename__ = "sagas"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    title: Mapped[str] = mapped_column(Text, nullable=False)
    centroid: Mapped[list[float] | None] = mapped_column(Vector(EMBEDDING_DIM), nullable=True)
    first_seen_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    last_seen_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    cluster_count: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    source_count: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    article_count: Mapped[int] = mapped_column(Integer, default=0, server_default="0")

    clusters: Mapped[list["Cluster"]] = relationship(back_populates="saga")


class Cluster(Base):
    __tablename__ = "clusters"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    centroid: Mapped[list[float] | None] = mapped_column(Vector(EMBEDDING_DIM), nullable=True)
    first_seen_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    last_seen_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    article_count: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    source_count: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    rank_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    is_top: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false")
    display_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    topic: Mapped[str | None] = mapped_column(String(32), nullable=True)
    saga_id: Mapped[int | None] = mapped_column(
        ForeignKey("sagas.id", ondelete="SET NULL"), nullable=True
    )

    articles: Mapped[list["Article"]] = relationship(back_populates="cluster")
    analysis: Mapped["Analysis | None"] = relationship(
        back_populates="cluster", uselist=False, cascade="all, delete-orphan"
    )
    saga: Mapped["Saga | None"] = relationship(back_populates="clusters")


class Article(Base):
    __tablename__ = "articles"
    __table_args__ = (UniqueConstraint("source_id", "external_id", name="uq_articles_source_ext"),)

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    source_id: Mapped[int] = mapped_column(ForeignKey("sources.id"), nullable=False)
    external_id: Mapped[str] = mapped_column(Text, nullable=False)
    url: Mapped[str] = mapped_column(Text, nullable=False)
    title: Mapped[str] = mapped_column(Text, nullable=False)
    summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    content: Mapped[str | None] = mapped_column(Text, nullable=True)
    has_full_text: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false")
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    fetched_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    embedding: Mapped[list[float] | None] = mapped_column(Vector(EMBEDDING_DIM), nullable=True)
    cluster_id: Mapped[int | None] = mapped_column(
        ForeignKey("clusters.id", ondelete="SET NULL"), nullable=True
    )
    tsv: Mapped[str | None] = mapped_column(
        TSVECTOR,
        Computed(
            "to_tsvector('spanish', coalesce(title, '') || ' ' || coalesce(content, summary, ''))",
            persisted=True,
        ),
        nullable=True,
    )

    source: Mapped[Source] = relationship(back_populates="articles")
    cluster: Mapped[Cluster | None] = relationship(back_populates="articles")


class Analysis(Base):
    __tablename__ = "analyses"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    cluster_id: Mapped[int] = mapped_column(
        ForeignKey("clusters.id", ondelete="CASCADE"), unique=True, nullable=False
    )
    headline: Mapped[str | None] = mapped_column(Text, nullable=True)
    common_facts: Mapped[list | None] = mapped_column(JSONB, nullable=True)
    by_source: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    omissions: Mapped[list | None] = mapped_column(JSONB, nullable=True)
    divergences: Mapped[list | None] = mapped_column(JSONB, nullable=True)
    model: Mapped[str | None] = mapped_column(String(64), nullable=True)
    prompt_version: Mapped[str | None] = mapped_column(String(16), nullable=True)
    generated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    tsv: Mapped[str | None] = mapped_column(
        TSVECTOR,
        Computed(
            "to_tsvector('spanish', coalesce(headline, '') || ' ' || coalesce(common_facts::text, ''))",
            persisted=True,
        ),
        nullable=True,
    )

    cluster: Mapped[Cluster] = relationship(back_populates="analysis")


class Entity(Base):
    __tablename__ = "entities"
    __table_args__ = (
        UniqueConstraint("canonical", "kind", name="uq_entities_canon_kind"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    name: Mapped[str] = mapped_column(Text, nullable=False)
    kind: Mapped[str] = mapped_column(String(16), nullable=False)
    canonical: Mapped[str] = mapped_column(Text, nullable=False)
    first_seen_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    last_seen_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    mention_count: Mapped[int] = mapped_column(Integer, default=0, server_default="0")


class ClusterEntity(Base):
    __tablename__ = "cluster_entities"

    cluster_id: Mapped[int] = mapped_column(
        ForeignKey("clusters.id", ondelete="CASCADE"), primary_key=True
    )
    entity_id: Mapped[int] = mapped_column(
        ForeignKey("entities.id", ondelete="CASCADE"), primary_key=True
    )
    mention_count: Mapped[int] = mapped_column(Integer, default=1, server_default="1")


class Run(Base):
    __tablename__ = "runs"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    trigger: Mapped[str] = mapped_column(String(16), nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False)
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    stats: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)


class Delivery(Base):
    __tablename__ = "deliveries"
    __table_args__ = (
        UniqueConstraint("channel", "chat_id", "display_date", "message_hash",
                         name="uq_deliveries_chan_chat_date_hash"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    channel: Mapped[str] = mapped_column(String(32), nullable=False)
    chat_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    display_date: Mapped[date] = mapped_column(Date, nullable=False)
    message_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    sent_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    status: Mapped[str] = mapped_column(String(16), nullable=False)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)


class Subscription(Base):
    __tablename__ = "subscriptions"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    channel: Mapped[str] = mapped_column(String(32), nullable=False)
    chat_id: Mapped[str] = mapped_column(String(64), nullable=False)
    kind: Mapped[str] = mapped_column(String(16), nullable=False)
    value: Mapped[str | None] = mapped_column(Text, nullable=True)
    alert_threshold_sources: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )


class ClusterNote(Base):
    __tablename__ = "cluster_notes"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    cluster_id: Mapped[int] = mapped_column(
        ForeignKey("clusters.id", ondelete="CASCADE"), nullable=False
    )
    note: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )


class AlertDelivery(Base):
    __tablename__ = "alert_deliveries"
    __table_args__ = (
        UniqueConstraint("channel", "chat_id", "cluster_id", "subscription_id",
                         name="uq_alert_chan_chat_cluster_sub"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    channel: Mapped[str] = mapped_column(String(32), nullable=False)
    chat_id: Mapped[str] = mapped_column(String(64), nullable=False)
    cluster_id: Mapped[int] = mapped_column(
        ForeignKey("clusters.id", ondelete="CASCADE"), nullable=False
    )
    subscription_id: Mapped[int | None] = mapped_column(
        ForeignKey("subscriptions.id", ondelete="CASCADE"), nullable=True
    )
    sent_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    status: Mapped[str] = mapped_column(String(16), nullable=False)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)


class QaMessage(Base):
    __tablename__ = "qa_messages"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    conversation_id: Mapped[str] = mapped_column(String(64), nullable=False)
    role: Mapped[str] = mapped_column(String(16), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    citations: Mapped[list | None] = mapped_column(JSONB, nullable=True)
    used_citations: Mapped[list | None] = mapped_column(JSONB, nullable=True)
    hyde_query: Mapped[str | None] = mapped_column(Text, nullable=True)
    model: Mapped[str | None] = mapped_column(String(64), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )


class Author(Base):
    __tablename__ = "authors"
    __table_args__ = (
        UniqueConstraint("canonical", "source_id", name="uq_authors_canon_source"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    name: Mapped[str] = mapped_column(Text, nullable=False)
    canonical: Mapped[str] = mapped_column(Text, nullable=False, index=True)
    source_id: Mapped[int | None] = mapped_column(
        ForeignKey("sources.id"), nullable=True
    )
    is_synthetic: Mapped[bool] = mapped_column(
        Boolean, default=False, server_default="false"
    )
    kind: Mapped[str] = mapped_column(
        String(16), default="person", server_default="person", nullable=False
    )
    first_seen_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    last_seen_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    article_count: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    centroid: Mapped[list[float] | None] = mapped_column(Vector(EMBEDDING_DIM), nullable=True)
    profile_vector: Mapped[list[float] | None] = mapped_column(Vector(20), nullable=True)
    centroid_updated_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )


class ArticleAuthor(Base):
    __tablename__ = "article_authors"

    article_id: Mapped[int] = mapped_column(
        ForeignKey("articles.id", ondelete="CASCADE"), primary_key=True
    )
    author_id: Mapped[int] = mapped_column(
        ForeignKey("authors.id", ondelete="CASCADE"), primary_key=True
    )
    position: Mapped[int] = mapped_column(Integer, default=0, server_default="0")


class AuthorAlias(Base):
    __tablename__ = "author_aliases"
    __table_args__ = (
        UniqueConstraint("alias_canonical", name="uq_author_aliases_alias_canonical"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    alias_canonical: Mapped[str] = mapped_column(Text, nullable=False)
    author_id: Mapped[int] = mapped_column(
        ForeignKey("authors.id", ondelete="CASCADE"), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )


class AuthorProfile(Base):
    __tablename__ = "author_profiles"

    author_id: Mapped[int] = mapped_column(
        ForeignKey("authors.id", ondelete="CASCADE"), primary_key=True
    )
    profile_json: Mapped[dict] = mapped_column(JSONB, nullable=False)
    model: Mapped[str | None] = mapped_column(String(64), nullable=True)
    n_sample: Mapped[int] = mapped_column(Integer, nullable=False)
    generated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )


class AuthorComparison(Base):
    __tablename__ = "author_comparisons"
    __table_args__ = (
        UniqueConstraint(
            "author_a_id", "author_b_id", "since", "until",
            name="uq_author_compare",
        ),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    author_a_id: Mapped[int] = mapped_column(
        ForeignKey("authors.id", ondelete="CASCADE"), nullable=False
    )
    author_b_id: Mapped[int] = mapped_column(
        ForeignKey("authors.id", ondelete="CASCADE"), nullable=False
    )
    comparison_json: Mapped[dict] = mapped_column(JSONB, nullable=False)
    model: Mapped[str | None] = mapped_column(String(64), nullable=True)
    since: Mapped[date | None] = mapped_column(Date, nullable=True)
    until: Mapped[date | None] = mapped_column(Date, nullable=True)
    generated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
