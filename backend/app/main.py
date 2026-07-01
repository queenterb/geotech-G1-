from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import api_router
from app.core.config import settings

app = FastAPI(
    title="CIS Dashboard API",
    description="Backend for the Causal Immune Sentinel frontend dashboard.",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[origin.strip() for origin in settings.BACKEND_CORS_ORIGINS.split(",") if origin.strip()],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router, prefix="/api")

# Register websocket routes
try:
    from app.websocket.routes import register_websocket_routes
    register_websocket_routes(app)
except Exception:
    pass

# Start background Redis consumer if available
try:
    from app.redis_consumer import consume_forever
    @app.on_event("startup")
    async def start_redis_consumer():
        import asyncio
        asyncio.create_task(consume_forever())
except Exception:
    pass

@app.get("/healthz")
def healthz():
    return {"status": "ok"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
