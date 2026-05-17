import asyncio
import contextlib
import logging

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage

from config import BOT_TOKEN
from database.db import init_db
from handlers import admin, brand, driver, start
from services.google_sheets import run_periodic_google_sheets_sync

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


async def main() -> None:
    await init_db()
    logger.info("Database initialised.")

    bot = Bot(
        token=BOT_TOKEN,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )
    dp = Dispatcher(storage=MemoryStorage())

    dp.include_router(admin.router)
    dp.include_router(start.router)
    dp.include_router(driver.router)
    dp.include_router(brand.router)

    google_sheets_task = asyncio.create_task(run_periodic_google_sheets_sync())

    try:
        logger.info("Starting polling …")
        await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())
    finally:
        google_sheets_task.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await google_sheets_task


if __name__ == "__main__":
    asyncio.run(main())
