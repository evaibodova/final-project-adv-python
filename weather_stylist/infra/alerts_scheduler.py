import asyncio
import logging
import random
from datetime import datetime

from aiogram import Bot

from weather_stylist.models import User
from weather_stylist.adapters.weather_api.openweather_client import get_two_days_forecast
from weather_stylist.adapters.user_bd.bd import AsyncSessionLocal
from weather_stylist.adapters.user_bd.sqlalchemy_user_repo import SqlAlchemyUserRepo

logger = logging.getLogger(__name__)

# пороги резкой смены
TEMP_JUMP = 7.0      # градусов разница по максимуму
STRONG_WIND = 12.0   # м/с


async def check_user_weather_change(bot: Bot, user: User) -> None:
    """
    Проверяем, нет ли для пользователя резкой смены погоды.
    Если есть — шлём одно рандомное сообщение.
    """
    city = user.city

    try:
        days = await get_two_days_forecast(city)
    except Exception as e:
        logger.warning("cannot load forecast for %s: %s", city, e)
        return

    if len(days) < 2:
        return

    today, tomorrow = days[0], days[1]
    now = datetime.now()
    current_hour = now.hour

    # ищем дождь в ближайшие 6 часов
    rain_soon = None
    msgs: list[str] = []

    for h in today.hourly:
        # h.hour – час по локальному времени
        if h.hour <= current_hour:
            continue
        if h.hour > current_hour + 12:
            continue

        if h.will_rain:
            rain_soon = h.hour
            break

    if rain_soon is not None:
        msgs.append(
            f"сегодня в {city} ожидается дождь примерно к {rain_soon}:00 ☔️\n"
            f"если ещё не вышел(а), подумай про зонт или капюшон."
        )

    # резкое похолодание / потепление
    delta = tomorrow.max_temp - today.max_temp

    if delta <= -TEMP_JUMP:
        msgs.append(
            f"привет, {user.name}! завтра в {city} резко похолодает 🥶\n"
            f"сегодня максимум около {round(today.max_temp)}°, "
            f"а завтра всего {round(tomorrow.max_temp)}°. "
            f"давай подумаем про более тёплый лук?"
        )
    elif delta >= TEMP_JUMP:
        msgs.append(
            f"эй, {user.name}! завтра в {city} заметно потеплеет 😎\n"
            f"сегодня максимум {round(today.max_temp)}°, "
            f"а завтра до {round(tomorrow.max_temp)}°. "
            f"можно будет снять лишние слои."
        )

    # сильный ветер
    if tomorrow.wind_max >= STRONG_WIND and today.wind_max < STRONG_WIND:
        msgs.append(
            f"завтра в {city} обещают сильный ветер до {round(tomorrow.wind_max)} м/с 🌬️\n"
            f"лучше взять что-нибудь с капюшоном и не брать зонт-трость."
        )

    # дождь завтра, сегодня сухо
    if not today.will_rain and tomorrow.will_rain:
        msgs.append(
            f"сегодня ещё сухо, но завтра в {city} обещают дождь ☔️\n"
            f"можно заранее продумать образ с капюшоном или зонтом."
        )

    if not msgs:
        return

    text = random.choice(msgs)
    await bot.send_message(chat_id=user.tg_id, text=text)


async def run_weather_alerts_loop(bot: Bot, interval_hours: int = 12) -> None:
    """
    Фоновый цикл: раз в interval_hours часов пробегаемся по всем пользователям,
    проверяем погоду и при необходимости шлём уведомления.
    """
    while True:
        try:
            async with AsyncSessionLocal() as session:

                user_repo = SqlAlchemyUserRepo(session)
                users: list[User] = await user_repo.get_all_users()

                for user in users:
                    await check_user_weather_change(bot, user)

        except Exception as e:
            logger.error("error in alerts loop: %s", e)

        await asyncio.sleep(interval_hours * 3600)
