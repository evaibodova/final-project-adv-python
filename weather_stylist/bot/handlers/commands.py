from aiogram import F, Router, html
from aiogram.filters import CommandStart, Command
from aiogram.types import (
    Message,
    KeyboardButton,
    ReplyKeyboardMarkup,
)
from weather_stylist.adapters.weather_api.openweather_client import get_forecast_for_city
from weather_stylist.infra.config import DEFAULT_CITY

command_router = Router()


# --- вспомогательная функция: главное меню ---


def main_menu_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="Совет на сегодня")],
            [KeyboardButton(text="Настройки")],
            [KeyboardButton(text="Изменить район")],
            [KeyboardButton(text="Изменить стиль")],
        ],
        resize_keyboard=True,
    )


# --- /start ---


@command_router.message(CommandStart())
async def cmd_start(message: Message) -> None:
    await message.answer(
        f"Привет, {html.bold(message.from_user.full_name)}!\n\n"
        "я бот-стилист по погоде: подсказываю, что надеть на весь день 🌦🧥",
        reply_markup=main_menu_keyboard(),
    )


# --- /help ---


@command_router.message(Command("help"))
async def cmd_help(message: Message) -> None:
    await message.answer(
        "я пока в режиме разработки.\n\n"
        "доступные команды:\n"
        "/today – совет на сегодня\n"
        "/settings – настройки профиля\n"
        "/change_area – изменить район\n"
        "/change_style – изменить стиль одежды\n\n"
        "или пользуйся кнопками внизу 👍",
    )


# --- Совет на сегодня ---


@command_router.message(Command("today"))
@command_router.message(F.text == "Совет на сегодня")
async def cmd_today(message: Message) -> None:
    # пока берём город по умолчанию, потом подставим из настроек пользователя
    forecast = await get_forecast_for_city(DEFAULT_CITY)

    summary = (
        f"сегодня в {forecast.city}: "
        f"от {round(forecast.min_temp)}°C до {round(forecast.max_temp)}°C, "
        f"ветер до {round(forecast.wind_max)} м/с"
    )

    if forecast.will_rain:
        summary += ", возможен дождь ☔️"
    else:
        summary += ", дождя не ожидается"

    # очень простой совет по одежде — потом усложним
    if forecast.max_temp < 0:
        outfit = "надень тёплые штаны, свитер, шарф и зимнюю куртку"
    elif forecast.max_temp < 8:
        outfit = "надень джинсы, худи и тёплую куртку"
    elif forecast.max_temp < 16:
        outfit = "надень джинсы и лёгкую куртку или ветровку"
    else:
        outfit = "можно лёгкую одежду: футболка и брюки/шорты"

    if forecast.will_rain:
        outfit += ", и обязательно возьми зонт"

    await message.answer(summary + "\n\n" + outfit)

# --- Настройки ---


@command_router.message(Command("settings"))
@command_router.message(F.text == "Настройки")
async def cmd_settings(message: Message) -> None:
    await message.answer(
        "здесь будут настройки термочувствительности, стиля, города и времени рассылки.\n"
        "пока просто заглушка.",
    )


# --- Изменить район ---


@command_router.message(Command("change_area"))
@command_router.message(F.text == "Изменить район")
async def cmd_change_area(message: Message) -> None:
    await message.answer(
        "здесь мы позже спросим, в каком районе ты будешь сегодня "
        "(дом, кампус, другой район).\n"
        "сейчас это просто заглушка.",
    )


# --- Изменить стиль ---


@command_router.message(Command("change_style"))
@command_router.message(F.text == "Изменить стиль")
async def cmd_change_style(message: Message) -> None:
    await message.answer(
        "здесь позже можно будет выбрать стиль одежды: "
        "casual / офис / спорт / минимализм.\n"
        "пока заглушка.",
    )
