import pytest

from noticias_api.db.models import QaMessage
from noticias_api.qa.memory import (
    append_messages,
    load_recent_history,
    new_conversation_id,
)


@pytest.mark.asyncio
async def test_new_conversation_id_is_unique():
    a = new_conversation_id()
    b = new_conversation_id()
    assert a != b
    assert len(a) > 8


@pytest.mark.asyncio
async def test_append_and_load(db_session):
    cid = new_conversation_id()

    await append_messages(
        db_session, cid, "pregunta 1", "respuesta 1",
        citations=[], used_citations=[1],
    )
    await append_messages(
        db_session, cid, "pregunta 2", "respuesta 2",
    )

    msgs = await load_recent_history(db_session, cid, max_turns=10)
    assert len(msgs) == 4
    roles = [m.role for m in msgs]
    assert roles == ["user", "assistant", "user", "assistant"]
    contents = [m.content for m in msgs]
    assert contents[0] == "pregunta 1"
    assert contents[1] == "respuesta 1"
    assert contents[2] == "pregunta 2"
    assert contents[3] == "respuesta 2"


@pytest.mark.asyncio
async def test_assistant_message_stores_metadata(db_session):
    cid = new_conversation_id()
    await append_messages(
        db_session, cid, "q", "a",
        citations=[{"n": 1, "title": "test"}],
        used_citations=[1],
        hyde_query="hypothetical answer text",
        model="gpt-4o",
    )
    msgs = await load_recent_history(db_session, cid, max_turns=10)
    assistant = [m for m in msgs if m.role == "assistant"][0]
    assert assistant.hyde_query == "hypothetical answer text"
    assert assistant.model == "gpt-4o"
    assert assistant.used_citations == [1]
    assert assistant.citations[0]["n"] == 1


@pytest.mark.asyncio
async def test_load_recent_history_caps(db_session):
    cid = new_conversation_id()
    for i in range(10):
        await append_messages(db_session, cid, f"q{i}", f"a{i}")

    msgs = await load_recent_history(db_session, cid, max_turns=3)
    # 3 turns × 2 roles = 6 rows; they should be the *most recent* 3 turns
    assert len(msgs) == 6
    contents = [m.content for m in msgs]
    # most recent 3 turns are q7/a7, q8/a8, q9/a9
    assert "q7" in contents
    assert "q9" in contents
    assert "q0" not in contents


@pytest.mark.asyncio
async def test_load_recent_history_empty_for_unknown(db_session):
    msgs = await load_recent_history(db_session, "nonexistent-conv", max_turns=10)
    assert msgs == []


@pytest.mark.asyncio
async def test_load_recent_history_empty_string_returns_empty(db_session):
    msgs = await load_recent_history(db_session, "", max_turns=10)
    assert msgs == []


@pytest.mark.asyncio
async def test_conversations_are_isolated(db_session):
    cid1 = new_conversation_id()
    cid2 = new_conversation_id()

    await append_messages(db_session, cid1, "q1", "a1")
    await append_messages(db_session, cid2, "q2", "a2")

    msgs1 = await load_recent_history(db_session, cid1, max_turns=10)
    msgs2 = await load_recent_history(db_session, cid2, max_turns=10)

    assert len(msgs1) == 2
    assert len(msgs2) == 2
    assert all(m.conversation_id == cid1 for m in msgs1)
    assert all(m.conversation_id == cid2 for m in msgs2)
