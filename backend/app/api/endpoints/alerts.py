from fastapi import APIRouter, Depends, HTTPException, status, Request
import json
from sqlalchemy.ext.asyncio import AsyncSession

from app.crud.alert import create_alert, get_alerts
from app.db.session import get_db_session
from app.schemas.alert import AlertCreate, AlertRead
from app.core.config import settings

router = APIRouter()


@router.get("/", response_model=list[AlertRead])
async def read_alerts(limit: int = 20, db: AsyncSession = Depends(get_db_session)):
    return await get_alerts(db, limit=limit)


async def _verify_siem_auth(request: Request):
    # If no SIEM_SHARED_SECRET configured, allow (development/backwards compatibility)
    secret = settings.SIEM_SHARED_SECRET
    if not secret:
        return True
    # Check Authorization: Bearer <token>
    auth = request.headers.get("authorization") or request.headers.get("Authorization")
    if auth and auth.lower().startswith("bearer "):
        token = auth.split(None, 1)[1]
        if token == secret:
            return True
    # Check X-API-Key header
    api_key = request.headers.get("x-api-key")
    if api_key and api_key == secret:
        return True
    raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid SIEM auth")


@router.post("/", response_model=AlertRead, status_code=status.HTTP_201_CREATED)
async def create_alert_endpoint(request: Request, alert_in: AlertCreate, db: AsyncSession = Depends(get_db_session), _ok: bool = Depends(_verify_siem_auth)):
    alert = await create_alert(
        db,
        event_type=alert_in.event_type,
        severity=alert_in.severity,
        source=alert_in.source,
        payload=alert_in.payload,
        description=alert_in.description,
    )

    # Broadcast the new alert to any connected WebSocket clients
    try:
        from app.websocket.manager import manager

        payload = {
            "id": alert.id,
            "event_type": alert.event_type,
            "severity": alert.severity,
            "source": alert.source,
            "payload": alert.payload,
            "created_at": str(alert.created_at),
            "description": alert.description,
        }
        # fire-and-forget broadcast
        try:
            import asyncio
            # broadcast via local WebSocket manager
            asyncio.create_task(manager.broadcast({"type": "alert", "data": payload}))
            # also publish to Redis stream so other instances can pick it up
            try:
                from app.utils.redis_client import get_redis

                r = get_redis()
                # store JSON under field 'data'
                asyncio.create_task(r.xadd('alerts', {'data': json.dumps(payload)}))
            except Exception:
                pass
        except Exception:
            # If broadcasting fails, don't block alert creation
            pass
    except Exception:
        pass

    return alert
