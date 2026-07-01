from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from app.utils.hashing import hash_password


async def get_user_by_email(session: AsyncSession, email: str):
    result = await session.execute(select(User).where(User.email == email))
    return result.scalars().first()


async def get_user_by_username(session: AsyncSession, username: str):
    result = await session.execute(select(User).where(User.username == username))
    return result.scalars().first()


async def create_user(session: AsyncSession, username: str, email: str, password: str, role: str = "analyst"):
    user = User(
        username=username,
        email=email,
        hashed_password=hash_password(password),
        role=role,
        is_active=True,
        is_superuser=False,
    )
    session.add(user)
    await session.commit()
    await session.refresh(user)
    return user


async def authenticate_user(session: AsyncSession, username_or_email: str, password: str):
    user = await get_user_by_email(session, username_or_email)
    if not user:
        user = await get_user_by_username(session, username_or_email)
    if not user:
        return None
    if not user.is_active:
        return None
    from app.utils.hashing import verify_password
    if not verify_password(password, user.hashed_password):
        return None
    return user
