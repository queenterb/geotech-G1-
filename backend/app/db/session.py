from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine, AsyncSession

from app.core.config import settings


database_url = settings.DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://")
engine: AsyncEngine = create_async_engine(database_url, future=True, echo=False)
AsyncSessionLocal = sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)


async def get_db_session():
    async with AsyncSessionLocal() as session:
        yield session
