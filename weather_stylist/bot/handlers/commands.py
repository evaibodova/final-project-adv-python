from aiogram import F, Router, html
from aiogram.filters import CommandStart, Command
from aiogram.types import (
    Message,
    KeyboardButton,
    ReplyKeyboardMarkup,
)
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State

from weather_stylist.adapters.weather_api.openweather_client import get_forecast_for_city
from weather_stylist.infra.config import DEFAULT_CITY

_user_default_cities: dict[int, str] = {}


def get_saved_city(user_id: int) -> str | None:
    return _user_default_cities.get(user_id)


def save_city(user_id: int, city: str) -> None:
    _user_default_cities[user_id] = city


class CityStates(StatesGroup):
    choosing_default = State()   # первый выбор города
    changing_city = State()      # смена города


command_router = Router()


# --- главное меню ---


def main_menu_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="Совет на сегодня")],
            [KeyboardButton(text="Изменить город")]
            [KeyboardButton(text="Настройки")],
        ],
        resize_keyboard=True,
    )


# --- /start ---


@command_router.message(CommandStart())
async def cmd_start(message: Message) -> None:
    await message.answer(
        f"Привет, {html.bold(message.from_user.full_name)}!\n\n"
        "я бот-стилист по погоде: подсказываю, что надеть на весь день 🌦🧥. Нажми /help чтобы увидеть, что я могу)",
        reply_markup=main_menu_keyboard(),
    )


# --- /help ---


@command_router.message(Command("help"))
async def cmd_help(message: Message) -> None:
    await message.answer(
        "я пока в режиме разработки.\n\n"
        "доступные команды:\n"
        "/today – совет на сегодня\n"
        "/change_city – сменить город\n"
        "/settings – настройки профиля\n"
        "или пользуйся кнопками внизу 👍",
    )


# --- Совет на сегодня ---


@command_router.message(Command("today"))
@command_router.message(F.text == "Совет на сегодня")
async def cmd_today(message: Message, state: FSMContext) -> None:
    user_id = message.from_user.id
    city = get_saved_city(user_id)

    # если город ещё не выбран
    if city is None:
        await message.answer(
            "давай сначала выберем город по умолчанию 🌍\n"
            f"напиши, пожалуйста, город текстом (например: {DEFAULT_CITY})."
        )
        await state.set_state(CityStates.choosing_default)
        return

    # город уже известен
    forecast = await get_forecast_for_city(city)

    summary = (
        f"сегодня в {forecast.city}: "
        f"от {round(forecast.min_temp)}°C до {round(forecast.max_temp)}°C, "
        f"ветер до {round(forecast.wind_max)} м/с"
    )

    if forecast.will_rain:
        summary += ", возможен дождь ☔️"
    else:
        summary += ", дождя не ожидается"

    # очень простой совет по одежде — тут потом можно подставить ваш engine
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

    footer = (
        f"\n\nсейчас у тебя город по умолчанию: {forecast.city}.\n"
        "если хочешь сменить — нажми «Сменить город» или команду /change_city."
    )

    await message.answer(summary + "\n\n" + outfit + footer)


# --- первый выбор города  ---


@command_router.message(CityStates.choosing_default)
async def process_first_city(message: Message, state: FSMContext) -> None:
    raw_city = (message.text or "").strip()
    if not raw_city:
        await message.answer("напиши, пожалуйста, название города текстом 🙏")
        return

    try:
        forecast = await get_forecast_for_city(raw_city)
    except Exception:
        await message.answer(
            "не смогла найти такой город 😿\n"
            "попробуй ещё раз, например: Омск или Prague."
        )
        return

    save_city(message.from_user.id, forecast.city)

    await state.clear()

    summary = (
        f"ок, буду использовать {forecast.city} как город по умолчанию 💾\n\n"
        f"сегодня от {round(forecast.min_temp)}°C до {round(forecast.max_temp)}°C, "
        f"ветер до {round(forecast.wind_max)} м/с"
    )

    if forecast.will_rain:
        summary += ", возможен дождь ☔️"
    else:
        summary += ", дождя не ожидается"

    await message.answer(
        summary
        + "\n\nесли захочешь сменить город, используй /change_city или кнопку «Сменить город»."
    )


# --- Сменить город ---


@command_router.message(Command("change_city"))
@command_router.message(F.text == "Сменить город")
async def cmd_change_city(message: Message, state: FSMContext) -> None:
    await message.answer(
        "на какой город поменять? 🌍\n"
        "просто напиши его названием."
    )
    await state.set_state(CityStates.changing_city)


@command_router.message(CityStates.changing_city)
async def process_change_city(message: Message, state: FSMContext) -> None:
    raw_city = (message.text or "").strip()
    if not raw_city:
        await message.answer("напиши, пожалуйста, название города.")
        return

    try:
        forecast = await get_forecast_for_city(raw_city)
    except Exception:
        await message.answer(
            "я не нашла такой город 😢\n"
            "проверь написание и попробуй снова.\n"
            "если это очень маленький населённый пункт, "
            "попробуй ближайший крупный город."
        )
        return

    save_city(message.from_user.id, forecast.city)
    await state.clear()

    await message.answer(
        f"обновила город по умолчанию на {forecast.city} ✅\n"
        "теперь «Совет на сегодня» будет использовать этот город."
    )


# --- Настройки ---


@command_router.message(Command("settings"))
@command_router.message(F.text == "Настройки")
async def cmd_settings(message: Message) -> None:
    await message.answer(
        "здесь будут настройки термочувствительности, стиля, города и времени рассылки.\n"
        "пока просто заглушка.",
    )
