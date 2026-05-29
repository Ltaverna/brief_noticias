import pytest

from noticias_api.pipeline.authors import canonicalize_author, parse_byline


@pytest.mark.parametrize("raw,expected", [
    ("Juan Pérez", ["Juan Pérez"]),
    ("Por Juan Pérez", ["Juan Pérez"]),
    ("Juan Pérez y María López", ["Juan Pérez", "María López"]),
    ("Juan Pérez, María López", ["Juan Pérez", "María López"]),
    ("Juan Pérez / María López", ["Juan Pérez", "María López"]),
    ("Juan Pérez; María López", ["Juan Pérez", "María López"]),
    ("Juan Pérez (corresponsal)", ["Juan Pérez"]),
    ("Juan Pérez juan@diario.com", ["Juan Pérez"]),
    ("Redacción", []),
    ("REDACCIÓN", []),
    ("Agencia", []),
    ("", []),
    ("   ", []),
    ("Staff", []),
    ("Juan Pérez y Redacción", ["Juan Pérez"]),
])
def test_parse_byline(raw, expected):
    assert parse_byline(raw) == expected


def test_parse_byline_strips_whitespace():
    assert parse_byline("   Juan Pérez   ") == ["Juan Pérez"]


@pytest.mark.parametrize("name,expected", [
    ("Juan Pérez", "juan perez"),
    ("J. Pérez", "j perez"),
    ("María  López", "maria lopez"),
    ("José Ángel", "jose angel"),
    ("O'Brien", "o brien"),
])
def test_canonicalize_author(name, expected):
    assert canonicalize_author(name) == expected
