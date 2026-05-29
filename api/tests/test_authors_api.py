import pytest

from noticias_api.db.models import (
    Analysis, Article, ArticleAuthor, Author, Cluster, Source,
)


@pytest.fixture
async def seeded(db_session):
    src = Source(slug="clarin", name="Clarín", editorial_group="mainstream",
                 rss_url="x", base_url="x")
    db_session.add(src)
    await db_session.commit()
    await db_session.refresh(src)

    author = Author(name="Juan Pérez", canonical="juan perez", source_id=src.id)
    db_session.add(author)
    await db_session.flush()

    cluster = Cluster(topic="politica", is_top=True)
    db_session.add(cluster)
    await db_session.flush()

    art = Article(source_id=src.id, external_id="e", url="u", title="t",
                  cluster_id=cluster.id, published_at=None)
    db_session.add(art)
    await db_session.flush()
    db_session.add(ArticleAuthor(article_id=art.id, author_id=author.id, position=0))
    await db_session.commit()
    return {"author": author, "source": src, "cluster": cluster, "article": art}


def test_list_authors(client, seeded):
    r = client.get("/authors")
    assert r.status_code == 200
    data = r.json()
    assert any(a["canonical"] == "juan perez" for a in data["authors"])


def test_author_stats(client, seeded):
    a = seeded["author"]
    r = client.get(f"/authors/{a.canonical.replace(' ', '-')}/stats")
    assert r.status_code == 200
    data = r.json()
    assert data["totals"]["articles"] == 1
    assert data["by_topic"][0]["topic"] == "politica"


def test_byline_coverage(client, seeded):
    r = client.get(f"/sources/{seeded['source'].slug}/byline-coverage")
    assert r.status_code == 200
    data = r.json()
    assert "monthly" in data


def test_author_scorecard_with_no_analysis(client, seeded):
    a = seeded["author"]
    slug = a.canonical.replace(" ", "-")
    r = client.get(f"/authors/{slug}/scorecard")
    assert r.status_code == 200
    data = r.json()
    assert data["n"] == 0
    assert data["tone"]["avg"] is None


def test_similar_excludes_authors_without_centroid(client, seeded):
    a = seeded["author"]
    slug = a.canonical.replace(" ", "-")
    r = client.get(f"/authors/{slug}/similar")
    assert r.status_code == 200
    # The seeded author has no centroid → response returns empty list with a reason
    data = r.json()
    assert data["similar"] == []


def test_profile_regenerate_blocked_when_sample_too_small(client, seeded):
    a = seeded["author"]
    slug = a.canonical.replace(" ", "-")
    # seeded fixture has 1 article and 0 analyses → n_sample = 0
    r = client.post(f"/authors/{slug}/profile/regenerate")
    assert r.status_code == 400
    detail = r.json()["detail"].lower()
    assert "muestra" in detail or "sample" in detail


@pytest.fixture
async def two_authors(db_session, seeded):
    other = Author(name="María López", canonical="maria lopez",
                   source_id=seeded["source"].id)
    db_session.add(other)
    await db_session.commit()
    await db_session.refresh(other)
    return {"a": seeded["author"], "b": other, "source": seeded["source"]}


def test_compare_no_overlap(client, two_authors):
    a_slug = two_authors["a"].canonical.replace(" ", "-")
    b_slug = two_authors["b"].canonical.replace(" ", "-")
    r = client.post("/authors/compare", json={"a": a_slug, "b": b_slug})
    assert r.status_code == 200
    data = r.json()
    assert data["overlap_clusters"] == 0


def test_author_radar_returns_6_dimensions(client, seeded):
    a = seeded["author"]
    slug = a.canonical.replace(" ", "-")
    r = client.get(f"/authors/{slug}/radar")
    assert r.status_code == 200
    data = r.json()
    assert len(data["dimensions"]) == 6
    for d in data["dimensions"]:
        assert 0.0 <= d["value"] <= 1.0
    assert data["source"]["color"].startswith("#")
