"""Tests for C3 saga clustering."""
import pytest
from datetime import UTC, datetime, timedelta
from sqlalchemy import select

from noticias_api.db.models import Analysis, Cluster, Saga, Source
from noticias_api.pipeline.saga import assign_sagas


def _vec(direction: int, dim: int = 1536) -> list[float]:
    """Unit vector with a 1.0 at the given dimension index."""
    v = [0.0] * dim
    v[direction % dim] = 1.0
    return v


async def _seed_cluster(
    db_session,
    *,
    centroid_vec: list[float],
    last_seen: datetime,
    headline: str | None = None,
    article_count: int = 1,
    source_count: int = 1,
) -> Cluster:
    c = Cluster(
        article_count=article_count,
        source_count=source_count,
        last_seen_at=last_seen,
        first_seen_at=last_seen,
        centroid=centroid_vec,
    )
    db_session.add(c)
    await db_session.commit()
    if headline:
        db_session.add(
            Analysis(
                cluster_id=c.id,
                headline=headline,
                common_facts=[],
                by_source={},
                omissions=[],
                divergences=[],
                model="x",
                prompt_version="v2",
            )
        )
        await db_session.commit()
    return c


@pytest.mark.asyncio
async def test_two_similar_clusters_form_saga(db_session):
    now = datetime.now(UTC)
    c_a = await _seed_cluster(
        db_session,
        centroid_vec=_vec(0),
        last_seen=now,
        headline="Adornigate primer movimiento",
    )
    c_b = await _seed_cluster(
        db_session,
        centroid_vec=_vec(0),
        last_seen=now - timedelta(hours=2),
        headline="Adornigate segundo movimiento",
    )
    stats = await assign_sagas(db_session, threshold=0.78, window_hours=168)
    assert stats["clusters_in_sagas"] == 2
    assert stats["active_sagas"] == 1

    a = await db_session.get(Cluster, c_a.id)
    b = await db_session.get(Cluster, c_b.id)
    assert a.saga_id is not None
    assert a.saga_id == b.saga_id

    saga = await db_session.get(Saga, a.saga_id)
    assert saga.cluster_count == 2
    # Title should come from newest cluster (c_a)
    assert saga.title == "Adornigate primer movimiento"


@pytest.mark.asyncio
async def test_dissimilar_clusters_no_saga(db_session):
    now = datetime.now(UTC)
    await _seed_cluster(db_session, centroid_vec=_vec(0), last_seen=now)
    await _seed_cluster(db_session, centroid_vec=_vec(700), last_seen=now)
    stats = await assign_sagas(db_session, threshold=0.78, window_hours=168)
    assert stats["clusters_in_sagas"] == 0

    sagas = (await db_session.scalars(select(Saga))).all()
    assert sagas == []


@pytest.mark.asyncio
async def test_cluster_outside_window_not_assigned(db_session):
    old = datetime.now(UTC) - timedelta(hours=200)
    now = datetime.now(UTC)
    c_old = await _seed_cluster(db_session, centroid_vec=_vec(0), last_seen=old)
    c_a = await _seed_cluster(db_session, centroid_vec=_vec(0), last_seen=now)
    c_b = await _seed_cluster(db_session, centroid_vec=_vec(0), last_seen=now)
    await assign_sagas(db_session, threshold=0.78, window_hours=168)

    # Old cluster should not have been touched
    refreshed_old = await db_session.get(Cluster, c_old.id)
    assert refreshed_old.saga_id is None

    # In-window clusters should be assigned
    refreshed_a = await db_session.get(Cluster, c_a.id)
    refreshed_b = await db_session.get(Cluster, c_b.id)
    assert refreshed_a.saga_id is not None
    assert refreshed_a.saga_id == refreshed_b.saga_id


@pytest.mark.asyncio
async def test_idempotent(db_session):
    now = datetime.now(UTC)
    c_a = await _seed_cluster(db_session, centroid_vec=_vec(0), last_seen=now)
    c_b = await _seed_cluster(db_session, centroid_vec=_vec(0), last_seen=now)
    s1 = await assign_sagas(db_session, threshold=0.78, window_hours=168)
    s2 = await assign_sagas(db_session, threshold=0.78, window_hours=168)
    assert s1["clusters_in_sagas"] == 2
    assert s2["clusters_in_sagas"] == 2

    sagas = (await db_session.scalars(select(Saga))).all()
    assert len(sagas) == 1


@pytest.mark.asyncio
async def test_two_sagas_merge_via_new_cluster(db_session):
    """Two separate sagas get merged when a bridging cluster is added."""
    now = datetime.now(UTC)
    # Pair A — similar to each other
    c_a1 = await _seed_cluster(db_session, centroid_vec=_vec(0), last_seen=now)
    c_a2 = await _seed_cluster(db_session, centroid_vec=_vec(0), last_seen=now)
    # Pair B — similar to each other but orthogonal to pair A
    c_b1 = await _seed_cluster(db_session, centroid_vec=_vec(700), last_seen=now)
    c_b2 = await _seed_cluster(db_session, centroid_vec=_vec(700), last_seen=now)
    await assign_sagas(db_session, threshold=0.78, window_hours=168)
    sagas = (await db_session.scalars(select(Saga))).all()
    assert len(sagas) == 2

    # Bridge cluster: close enough to both at a relaxed threshold
    bridge_vec = [0.0] * 1536
    bridge_vec[0] = 0.71
    bridge_vec[700] = 0.71
    c_bridge = await _seed_cluster(db_session, centroid_vec=bridge_vec, last_seen=now)
    # Use a lower threshold so the bridge actually connects
    await assign_sagas(db_session, threshold=0.5, window_hours=168)
    sagas2 = (await db_session.scalars(select(Saga))).all()
    assert len(sagas2) == 1


@pytest.mark.asyncio
async def test_singleton_clears_saga_id(db_session):
    """When a cluster's only companion drops out of the window, its saga_id is cleared
    and the now-empty saga is deleted."""
    now = datetime.now(UTC)
    long_ago = now - timedelta(hours=300)

    c_a = await _seed_cluster(db_session, centroid_vec=_vec(0), last_seen=now)
    c_b = await _seed_cluster(db_session, centroid_vec=_vec(0), last_seen=now)
    await assign_sagas(db_session, threshold=0.78, window_hours=168)

    a = await db_session.get(Cluster, c_a.id)
    saga_id = a.saga_id
    assert saga_id is not None

    # Move c_b out of window
    await db_session.execute(
        Cluster.__table__.update()
        .where(Cluster.id == c_b.id)
        .values(last_seen_at=long_ago)
    )
    await db_session.commit()

    await assign_sagas(db_session, threshold=0.78, window_hours=168)

    # c_a is now singleton in window → saga cleared
    a2 = await db_session.get(Cluster, c_a.id)
    assert a2.saga_id is None
    # Saga should be deleted (no clusters reference it)
    saga = await db_session.get(Saga, saga_id)
    assert saga is None


@pytest.mark.asyncio
async def test_empty_sagas_cleaned_up(db_session):
    """Sagas with no clusters are removed."""
    # Create a saga directly with no clusters
    orphan = Saga(title="orphan")
    db_session.add(orphan)
    await db_session.commit()
    orphan_id = orphan.id

    # Calling assign_sagas with no clusters in window → cleanup runs
    stats = await assign_sagas(db_session, threshold=0.78, window_hours=168)

    gone = await db_session.get(Saga, orphan_id)
    assert gone is None
