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
