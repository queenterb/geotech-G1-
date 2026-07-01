from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.alert import Alert


async def create_alert(session: AsyncSession, event_type: str, severity: str, source: str, payload: dict, description: str | None = None):
    alert = Alert(
        event_type=event_type,
        severity=severity,
        source=source,
        payload=payload,
        description=description,
    )
    session.add(alert)
    await session.commit()
    await session.refresh(alert)
    return alert


async def get_alerts(session: AsyncSession, limit: int = 50):
    result = await session.execute(select(Alert).order_by(Alert.created_at.desc()).limit(limit))
    return result.scalars().all()
