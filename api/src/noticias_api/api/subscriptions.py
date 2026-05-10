from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import delete as sa_delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from noticias_api.config import Settings, get_settings
from noticias_api.db.models import Subscription
from noticias_api.db.session import get_session

router = APIRouter(tags=["subscriptions"])


class SubscriptionIn(BaseModel):
    kind: str = Field(pattern="^(entity|topic|all)$")
    value: str | None = Field(default=None, max_length=200)
    alert_threshold_sources: int | None = Field(default=None, ge=2, le=20)


class SubscriptionOut(BaseModel):
    id: int
    channel: str
    chat_id: str
    kind: str
    value: str | None
    alert_threshold_sources: int | None
    created_at: datetime

    model_config = {"from_attributes": True}


def _chat_id_or_400(settings: Settings) -> str:
    if not settings.telegram_chat_id:
        raise HTTPException(400, "telegram_chat_id not configured")
    return settings.telegram_chat_id


@router.get("/subscriptions", response_model=list[SubscriptionOut])
async def list_subscriptions(
    settings: Settings = Depends(get_settings),
    session: AsyncSession = Depends(get_session),
) -> list[Subscription]:
    chat_id = _chat_id_or_400(settings)
    rows = await session.scalars(
        select(Subscription)
        .where(Subscription.channel == "telegram")
        .where(Subscription.chat_id == chat_id)
        .order_by(Subscription.created_at.desc())
    )
    return list(rows.all())


@router.post("/subscriptions", response_model=SubscriptionOut, status_code=201)
async def create_subscription(
    body: SubscriptionIn,
    settings: Settings = Depends(get_settings),
    session: AsyncSession = Depends(get_session),
) -> Subscription:
    chat_id = _chat_id_or_400(settings)
    if body.kind in ("entity", "topic") and not body.value:
        raise HTTPException(400, "value required for kind=entity|topic")

    sub = Subscription(
        channel="telegram",
        chat_id=chat_id,
        kind=body.kind,
        value=body.value.lower().strip() if body.value else None,
        alert_threshold_sources=body.alert_threshold_sources,
    )
    session.add(sub)
    await session.commit()
    await session.refresh(sub)
    return sub


@router.delete("/subscriptions/{sub_id}", status_code=204)
async def delete_subscription(
    sub_id: int,
    settings: Settings = Depends(get_settings),
    session: AsyncSession = Depends(get_session),
) -> None:
    chat_id = _chat_id_or_400(settings)
    sub = await session.get(Subscription, sub_id)
    if not sub or sub.chat_id != chat_id:
        raise HTTPException(404, "subscription not found")
    await session.execute(sa_delete(Subscription).where(Subscription.id == sub_id))
    await session.commit()
