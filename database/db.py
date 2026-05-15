from sqlalchemy import select
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from config import ADMIN_CHAT_ID, ADMIN_USER_ID, DATABASE_URL
from database.models import Admin, Base, NotificationChat

engine = create_async_engine(DATABASE_URL, echo=False)
async_session_factory = async_sessionmaker(engine, expire_on_commit=False)


async def init_db() -> None:
    """Create all tables if they don't exist yet."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        await conn.execute(
            text("ALTER TABLE users ADD COLUMN IF NOT EXISTS promocode VARCHAR(64)")
        )
        await conn.execute(
            text(
                "ALTER TABLE users ADD COLUMN IF NOT EXISTS "
                "promocode_asked BOOLEAN DEFAULT false"
            )
        )
    await seed_initial_admin_data()


async def seed_initial_admin_data() -> None:
    """Seed first admin and default notification chat from environment."""
    async with async_session_factory() as session:
        if ADMIN_USER_ID:
            result = await session.execute(
                select(Admin.id).where(Admin.telegram_id == ADMIN_USER_ID)
            )
            if result.scalar_one_or_none() is None:
                session.add(Admin(telegram_id=ADMIN_USER_ID))

        if ADMIN_CHAT_ID:
            result = await session.execute(
                select(NotificationChat.id).where(
                    NotificationChat.chat_id == ADMIN_CHAT_ID
                )
            )
            if result.scalar_one_or_none() is None:
                session.add(
                    NotificationChat(
                        chat_id=ADMIN_CHAT_ID,
                        title="Default application group",
                    )
                )

        await session.commit()


def get_session() -> AsyncSession:
    """Return a new async session. Caller is responsible for closing it."""
    return async_session_factory()
