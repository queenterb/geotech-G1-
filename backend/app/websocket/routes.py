from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from app.websocket.manager import manager


def register_websocket_routes(app: FastAPI):
    @app.websocket('/ws/events')
    async def events_ws(websocket: WebSocket):
        await manager.connect(websocket)
        try:
            while True:
                # Keep connection open; receive to detect disconnects
                await websocket.receive_text()
        except WebSocketDisconnect:
            manager.disconnect(websocket)
        except Exception:
            manager.disconnect(websocket)
