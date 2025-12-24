import os
import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage

from weather_stylist.bot.handlers.commands import command_router
from weather_stylist.bot.handlers.text_commands import text_router
from weather_stylist.infra.alerts_scheduler import run_weather_alerts_loop

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass


def setup_logging() -> None:
    logging.basicConfig(
        level=logging.DEBUG,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        filename="bot.log",
        filemode="a",
        force=True,
    )
    logging.getLogger("aiogram").setLevel(
        logging.INFO)  # или DEBUG, если хочешь спам


async def main() -> None:
    setup_logging()
    logger = logging.getLogger(__name__)
    logger.debug("BOOT: starting bot process")

    bot_token = os.getenv("BOT_TOKEN")
    if not bot_token:
        raise RuntimeError("BOT_TOKEN is not set")

    bot = Bot(token=bot_token, default=DefaultBotProperties(
        parse_mode=ParseMode.HTML))
    dp = Dispatcher(storage=MemoryStorage())
    dp.include_router(command_router)
    dp.include_router(text_router)

    asyncio.create_task(run_weather_alerts_loop(bot, interval_hours=6))
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
