from sqlalchemy import select

from database.db import get_session
from database.models import User


async def get_or_create_user(telegram_id: int, username: str | None) -> User:
    session = get_session()
    try:
        result = await session.execute(
            select(User).where(User.telegram_id == telegram_id)
        )
        user = result.scalar_one_or_none()
        if user is None:
            user = User(telegram_id=telegram_id, username=username)
            session.add(user)
            await session.commit()
            await session.refresh(user)
            return user

        if user.username != username:
            user.username = username
            await session.commit()
            await session.refresh(user)

        return user
    except Exception:
        await session.rollback()
        raise
    finally:
        await session.close()


async def set_user_promocode(
    telegram_id: int,
    username: str | None,
    promocode: str | None,
) -> None:
    session = get_session()
    try:
        result = await session.execute(
            select(User).where(User.telegram_id == telegram_id)
        )
        user = result.scalar_one_or_none()
        if user is None:
            user = User(telegram_id=telegram_id, username=username)
            session.add(user)

        user.username = username
        user.promocode = promocode
        user.promocode_asked = True
        await session.commit()
    except Exception:
        await session.rollback()
        raise
    finally:
        await session.close()
