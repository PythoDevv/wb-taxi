from dataclasses import dataclass

from sqlalchemy import delete, func, select

from config import ADMIN_CHAT_ID
from database.db import get_session
from database.models import (
    Admin,
    Application,
    ApplicationNotification,
    BrandApplication,
    NotificationChat,
    User,
)


@dataclass(slots=True)
class DeleteUserResult:
    found: bool
    telegram_id: int
    driver_applications: int = 0
    brand_applications: int = 0
    notifications: int = 0


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
    if chat_id >= 0:
        return False

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
        result = await session.execute(
            select(NotificationChat)
            .where(NotificationChat.chat_id < 0)
            .order_by(NotificationChat.id)
        )
        return list(result.scalars().all())
    finally:
        await session.close()


async def get_notification_chat_ids() -> list[int]:
    chats = await list_notification_chats()
    chat_ids = [chat.chat_id for chat in chats if chat.chat_id < 0]
    if not chat_ids and ADMIN_CHAT_ID < 0:
        chat_ids.append(ADMIN_CHAT_ID)
    return chat_ids


async def list_user_chat_ids() -> list[int]:
    session = get_session()
    try:
        result = await session.execute(select(User.telegram_id).order_by(User.id))
        return list(result.scalars().all())
    finally:
        await session.close()


async def delete_bot_user(telegram_id: int) -> DeleteUserResult:
    session = get_session()
    try:
        user_result = await session.execute(
            select(User).where(User.telegram_id == telegram_id)
        )
        user = user_result.scalar_one_or_none()
        if user is None:
            return DeleteUserResult(found=False, telegram_id=telegram_id)

        driver_result = await session.execute(
            select(Application.id).where(Application.user_id == user.id)
        )
        driver_ids = list(driver_result.scalars().all())

        brand_result = await session.execute(
            select(BrandApplication.id).where(BrandApplication.user_id == user.id)
        )
        brand_ids = list(brand_result.scalars().all())

        notifications = 0
        if driver_ids:
            deleted = await session.execute(
                delete(ApplicationNotification)
                .where(ApplicationNotification.application_type == "driver")
                .where(ApplicationNotification.application_id.in_(driver_ids))
            )
            notifications += deleted.rowcount or 0

        if brand_ids:
            deleted = await session.execute(
                delete(ApplicationNotification)
                .where(ApplicationNotification.application_type == "brand")
                .where(ApplicationNotification.application_id.in_(brand_ids))
            )
            notifications += deleted.rowcount or 0

        await session.execute(delete(Application).where(Application.user_id == user.id))
        await session.execute(
            delete(BrandApplication).where(BrandApplication.user_id == user.id)
        )
        await session.execute(delete(User).where(User.id == user.id))
        await session.commit()

        return DeleteUserResult(
            found=True,
            telegram_id=telegram_id,
            driver_applications=len(driver_ids),
            brand_applications=len(brand_ids),
            notifications=notifications,
        )
    except Exception:
        await session.rollback()
        raise
    finally:
        await session.close()
