import logging
import asyncio
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage
from weather_stylist.bot.handlers.commands import command_router
from weather_stylist.bot.handlers.text_commands import text_router
from weather_stylist.infra.alerts_scheduler import run_weather_alerts_loop


logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

bot = Bot(token='8343951267:AAF8Me-frmJ4Jblqczyhb2cFE9_bwIYqGik',
          default=DefaultBotProperties(parse_mode=ParseMode.HTML))
dp = Dispatcher(storage=MemoryStorage())
dp.include_router(command_router)
dp.include_router(text_router)


async def main() -> None:
    """Точка входа: запускаем polling."""
    asyncio.create_task(run_weather_alerts_loop(bot, interval_hours=6))
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
