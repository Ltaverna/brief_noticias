from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import delete as sa_delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from noticias_api.db.models import Cluster, ClusterNote
from noticias_api.db.session import get_session

router = APIRouter(tags=["notes"])


class NoteIn(BaseModel):
    note: str = Field(min_length=1, max_length=2000)


class NoteOut(BaseModel):
    id: int
    cluster_id: int
    note: str
    created_at: datetime


@router.get("/clusters/{cluster_id}/notes", response_model=list[NoteOut])
async def list_notes(cluster_id: int, session: AsyncSession = Depends(get_session)):
    cluster = await session.get(Cluster, cluster_id)
    if not cluster:
        raise HTTPException(404, "cluster not found")
    rows = await session.scalars(
        select(ClusterNote)
        .where(ClusterNote.cluster_id == cluster_id)
        .order_by(ClusterNote.created_at.desc())
    )
    return list(rows.all())


@router.post("/clusters/{cluster_id}/notes", response_model=NoteOut, status_code=201)
async def add_note(
    cluster_id: int, body: NoteIn, session: AsyncSession = Depends(get_session)
):
    cluster = await session.get(Cluster, cluster_id)
    if not cluster:
        raise HTTPException(404, "cluster not found")
    note = ClusterNote(cluster_id=cluster_id, note=body.note.strip())
    session.add(note)
    await session.commit()
    await session.refresh(note)
    return note


@router.delete("/notes/{note_id}", status_code=204)
async def delete_note(note_id: int, session: AsyncSession = Depends(get_session)):
    note = await session.get(ClusterNote, note_id)
    if not note:
        raise HTTPException(404, "note not found")
    await session.execute(sa_delete(ClusterNote).where(ClusterNote.id == note_id))
    await session.commit()
