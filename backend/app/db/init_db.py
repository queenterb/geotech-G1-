from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.db.base import Base
from app.db.session import engine, AsyncSessionLocal
from app.models.user import User
from app.utils.hashing import hash_password


async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with AsyncSessionLocal() as session:
        result = await session.execute(select(User).where(User.is_superuser == True))
        admin = result.scalars().first()
        if not admin:
            admin_user = User(
                username="admin",
                email="admin@cis.local",
                hashed_password=hash_password("Admin123!"),
                is_active=True,
                is_superuser=True,
                role="administrator",
            )
            session.add(admin_user)
            await session.commit()
            await session.refresh(admin_user)
            print("Created default admin user: admin@cis.local / Admin123!")


if __name__ == "__main__":
    import asyncio
    asyncio.run(init_db())
