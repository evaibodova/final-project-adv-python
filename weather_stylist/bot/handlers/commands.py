from aiogram import F, Router, html
from aiogram.filters import CommandStart, Command
from aiogram.types import (
    Message,
    KeyboardButton,
    ReplyKeyboardMarkup,
)
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State

from weather_stylist.models import User
from weather_stylist.adapters.user_bd.bd import SessionLocal
from weather_stylist.adapters.user_bd.sqlalchemy_user_repo import SqlAlchemyUserRepo


from contextlib import contextmanager
from sqlalchemy.orm import Session

from weather_stylist.adapters.weather_api.openweather_client import get_forecast_for_city
from weather_stylist.infra.config import DEFAULT_CITY

THERMO_PREFS: dict[int, str] = {}

TEXT_COLD = "Я мерзляк"
TEXT_HOT = "Мне всегда жарко"
TEXT_NEUTRAL = "У меня нет предпочтений"


@contextmanager
def user_repo_ctx():
    session: Session = SessionLocal()
    try:
        repo = SqlAlchemyUserRepo(session)
        yield repo
    finally:
        session.close()


class CityStates(StatesGroup):
    choosing_default = State()   # первый выбор города
    changing_city = State()      # смена города


command_router = Router()


# главное меню


def main_menu_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="Совет на сегодня")],
            [KeyboardButton(text="Изменить город")],
            [KeyboardButton(text="Настройки")],
        ],
        resize_keyboard=True,
    )


def thermo_prefs_keyboard() -> ReplyKeyboardMarkup:
    """кнопки выбора термопрофиля"""
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=TEXT_COLD)],
            [KeyboardButton(text=TEXT_HOT)],
            [KeyboardButton(text=TEXT_NEUTRAL)],
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


#  Совет на сегодня


@command_router.message(Command("today"))
@command_router.message(F.text == "Совет на сегодня")
async def cmd_today(message: Message, state: FSMContext) -> None:
    user_tg_id = message.from_user.id

    with user_repo_ctx() as user_repo:
        user = user_repo.get_user_by_tg_id(user_tg_id)

    city = user.city if user is not None else None

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

    # тут будет engine
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


#  первый выбор города


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
            "я не нашла такой город 😢\n"
            "проверь написание и попробуй снова.\n"
            "если это очень маленький населённый пункт, "
            "попробуй ближайший крупный город, для этого воспользуйся командой /change_city"
        )
        await state.clear()
        return

    user_tg_id = message.from_user.id
    user_name = message.from_user.full_name

    # бд
    with user_repo_ctx() as user_repo:
        existing = user_repo.get_user_by_tg_id(user_tg_id)

        if existing is None:
            user = User(
                tg_id=user_tg_id,
                city=forecast.city,
                name=user_name,
                region="unknown",   # пока заглушка
                thermo_profile=0,
                warmth_shift=0.0,
                feedback_count=0,
                cold_count=0,
                hot_count=0,
            )
        else:
            user = User(
                tg_id=existing.tg_id,
                city=forecast.city,           # обновили город
                name=user_name,
                region=existing.region,
                thermo_profile=existing.thermo_profile,
                warmth_shift=existing.warmth_shift,
                feedback_count=existing.feedback_count,
                cold_count=existing.cold_count,
                hot_count=existing.hot_count,
            )

        user_repo.save(user)

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

    # если для этого пользователя ещё не выбраны предпочтения
    if user_tg_id not in THERMO_PREFS:
        await message.answer(
            "и ещё один вопросик: как ты обычно ощущаешь погоду? 🧊🥵\n"
            "выбери вариант ниже:",
            reply_markup=thermo_prefs_keyboard(),
        )

#  Сменить город


@command_router.message(Command("change_city"))
@command_router.message(F.text == "Изменить город")
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
            "попробуй ближайший крупный город, для этого воспользуйся командой /change_city"
        )
        await state.clear()
        return

    user_tg_id = message.from_user.id
    user_name = message.from_user.full_name

    with user_repo_ctx() as user_repo:
        existing = user_repo.get_user_by_tg_id(user_tg_id)

        if existing is None:
            user = User(
                tg_id=user_tg_id,
                city=forecast.city,
                name=user_name,
                region="unknown",
                thermo_profile=0,
                warmth_shift=0.0,
                feedback_count=0,
                cold_count=0,
                hot_count=0,
            )
        else:
            user = User(
                tg_id=existing.tg_id,
                city=forecast.city,          # меняем город
                name=existing.name,
                region=existing.region,
                thermo_profile=existing.thermo_profile,
                warmth_shift=existing.warmth_shift,
                feedback_count=existing.feedback_count,
                cold_count=existing.cold_count,
                hot_count=existing.hot_count,
            )

        user_repo.save(user)

    await state.clear()

    await message.answer(
        f"обновила город по умолчанию на {forecast.city} ✅\n"
        "теперь «Совет на сегодня» будет использовать этот город."
    )


# термопрофиль
@command_router.message(Command("settings"))
@command_router.message(F.text == "Настройки")
async def cmd_settings(message: Message) -> None:
    user_id = message.from_user.id
    current = THERMO_PREFS.get(user_id)

    if current == "cold":
        status = "сейчас у тебя профиль: «я мерзляк»."
    elif current == "hot":
        status = "сейчас у тебя профиль: «мне всегда жарко»."
    elif current == "neutral":
        status = "сейчас у тебя профиль: «у меня нет предпочтений»."
    else:
        status = "у тебя пока не выбраны термопредпочтения."

    await message.answer(
        status
        + "\n\nвыбери, как ты обычно ощущаешь погоду:",
        reply_markup=thermo_prefs_keyboard(),
    )


# --- обработчик выбора термопрофиля ---


@command_router.message(F.text.in_([TEXT_COLD, TEXT_HOT, TEXT_NEUTRAL]))
async def handle_thermo_choice(message: Message) -> None:
    user_id = message.from_user.id
    choice = message.text

    if choice == TEXT_COLD:
        THERMO_PREFS[user_id] = "cold"
        reply = "запомнила: ты мерзляк 🧊\nбуду советовать чуть теплее."
    elif choice == TEXT_HOT:
        THERMO_PREFS[user_id] = "hot"
        reply = "запомнила: тебе всегда жарко 🔥\nбуду советовать полегче."
    else:
        THERMO_PREFS[user_id] = "neutral"
        reply = "ок, без особых предпочтений 😌\nбуду советовать что-то среднее."

    await message.answer(reply, reply_markup=main_menu_keyboard())
