from sqlalchemy import delete, func, select

from config import ADMIN_CHAT_ID
from database.db import get_session
from database.models import Admin, NotificationChat, User


async def is_admin(telegram_id: int) -> bool:
    session = get_session()
    try:
        result = await session.execute(
            select(Admin.id).where(Admin.telegram_id == telegram_id)
        )
        return result.scalar_one_or_none() is not None
    finally:
        await session.close()


async def add_admin(telegram_id: int) -> bool:
    session = get_session()
    try:
        exists = await session.execute(
            select(Admin.id).where(Admin.telegram_id == telegram_id)
        )
        if exists.scalar_one_or_none() is not None:
            return False

        session.add(Admin(telegram_id=telegram_id))
        await session.commit()
        return True
    except Exception:
        await session.rollback()
        raise
    finally:
        await session.close()


async def remove_admin(telegram_id: int) -> bool:
    session = get_session()
    try:
        count_result = await session.execute(select(func.count(Admin.id)))
        if count_result.scalar_one() <= 1:
            return False

        result = await session.execute(
            delete(Admin).where(Admin.telegram_id == telegram_id)
        )
        await session.commit()
        return bool(result.rowcount)
    except Exception:
        await session.rollback()
        raise
    finally:
        await session.close()


async def list_admins() -> list[int]:
    session = get_session()
    try:
        result = await session.execute(select(Admin.telegram_id).order_by(Admin.id))
        return list(result.scalars().all())
    finally:
        await session.close()


async def add_notification_chat(chat_id: int, title: str | None = None) -> bool:
    session = get_session()
    try:
        exists = await session.execute(
            select(NotificationChat.id).where(NotificationChat.chat_id == chat_id)
        )
        if exists.scalar_one_or_none() is not None:
            return False

        session.add(NotificationChat(chat_id=chat_id, title=title))
        await session.commit()
        return True
    except Exception:
        await session.rollback()
        raise
    finally:
        await session.close()


async def remove_notification_chat(chat_id: int) -> bool:
    session = get_session()
    try:
        result = await session.execute(
            delete(NotificationChat).where(NotificationChat.chat_id == chat_id)
        )
        await session.commit()
        return bool(result.rowcount)
    except Exception:
        await session.rollback()
        raise
    finally:
        await session.close()


async def list_notification_chats() -> list[NotificationChat]:
    session = get_session()
    try:
        result = await session.execute(select(NotificationChat).order_by(NotificationChat.id))
        return list(result.scalars().all())
    finally:
        await session.close()


async def get_notification_chat_ids() -> list[int]:
    chats = await list_notification_chats()
    chat_ids = [chat.chat_id for chat in chats]
    if not chat_ids and ADMIN_CHAT_ID:
        chat_ids.append(ADMIN_CHAT_ID)
    return chat_ids


async def list_user_chat_ids() -> list[int]:
    session = get_session()
    try:
        result = await session.execute(select(User.telegram_id).order_by(User.id))
        return list(result.scalars().all())
    finally:
        await session.close()
