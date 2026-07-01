import asyncio
import json
from app.utils.redis_client import get_redis
from app.websocket.manager import manager

STREAM_KEY = "alerts"
GROUP_NAME = "cis_consumers"
CONSUMER_NAME = "consumer_1"


async def ensure_group(r: 'redis.Redis'):
    try:
        await r.xgroup_create(STREAM_KEY, GROUP_NAME, id="$", mkstream=True)
    except Exception:
        # group may already exist
        pass


async def consume_forever():
    r = get_redis()
    await ensure_group(r)
    while True:
        try:
            resp = await r.xreadgroup(GROUP_NAME, CONSUMER_NAME, {STREAM_KEY: '>'}, count=10, block=5000)
            if not resp:
                continue
            for stream, messages in resp:
                for msg_id, data in messages:
                    try:
                        # data is dict of strings; expect a JSON payload under 'data'
                        payload = data.get('data') or data
                        if isinstance(payload, str):
                            parsed = json.loads(payload)
                        else:
                            parsed = payload
                        await manager.broadcast({"type": "alert", "data": parsed})
                    except Exception:
                        # ignore per-message errors
                        pass
                    try:
                        await r.xack(STREAM_KEY, GROUP_NAME, msg_id)
                    except Exception:
                        pass
        except Exception:
            await asyncio.sleep(1)
