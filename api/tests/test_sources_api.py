import pytest

from noticias_api.db.seed import seed_sources


@pytest.mark.asyncio
async def test_get_sources_returns_seeded_list(db_session, client):
    inserted = await seed_sources(db_session)
    assert inserted == 9

    response = client.get("/sources")
    assert response.status_code == 200
    body = response.json()
    assert len(body) == 9
    slugs = {s["slug"] for s in body}
    assert slugs == {
        "la-nacion", "clarin", "infobae",
        "pagina-12", "tiempo-argentino", "el-destape",
        "ambito", "el-cronista", "bae",
    }


@pytest.mark.asyncio
async def test_patch_source_toggles_enabled(db_session, client):
    await seed_sources(db_session)

    response = client.patch("/sources/la-nacion", json={"enabled": False})
    assert response.status_code == 200
    assert response.json()["enabled"] is False

    response = client.get("/sources")
    la_nacion = next(s for s in response.json() if s["slug"] == "la-nacion")
    assert la_nacion["enabled"] is False
