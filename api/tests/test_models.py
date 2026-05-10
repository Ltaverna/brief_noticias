from noticias_api.db.models import Analysis, Article, Cluster, Run, Source


def test_models_are_registered():
    assert Source.__tablename__ == "sources"
    assert Article.__tablename__ == "articles"
    assert Cluster.__tablename__ == "clusters"
    assert Analysis.__tablename__ == "analyses"
    assert Run.__tablename__ == "runs"


def test_articles_have_unique_source_external_id():
    constraints = [c.name for c in Article.__table_args__]
    assert "uq_articles_source_ext" in constraints
