import os
import random

from aiogram import F, Router, html
from aiogram.filters import CommandStart, Command
from aiogram.types import (
    Message,
    KeyboardButton,
    ReplyKeyboardMarkup,
    FSInputFile,
)
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State

from weather_stylist.adapters.user_bd.bd import SessionLocal
from weather_stylist.adapters.user_bd.sqlalchemy_user_repo import SqlAlchemyUserRepo
from weather_stylist.models import User

from contextlib import contextmanager
from sqlalchemy.orm import Session

from weather_stylist.adapters.weather_api.openweather_client import get_forecast_for_city
from weather_stylist.infra.config import DEFAULT_CITY


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


class StyleStates(StatesGroup):
    choosing_style = State()     # выбор стиля одежды


command_router = Router()


# --- главное меню ---


def main_menu_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="Совет на сегодня")],
            [KeyboardButton(text="Изменить город")],
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

# --- Сменить город ---


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
            "попробуй ближайший крупный город."
        )
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


# --- Настройки ---



@command_router.message(Command("settings"))
@command_router.message(F.text == "Настройки")
async def cmd_settings(message: Message) -> None:
    await message.answer(
        "здесь будут настройки термочувствительности, стиля, города и времени рассылки.\n"
        "пока просто заглушка.",
    )


# --- Функция для выбора фото стиля ---


def get_style_photo_paths(style_key: str, max_temp: float, count: int = 3) -> list[str]:
    """вернуть пути к нескольким случайным фоткам с образом нужного стиля под погоду"""
    base_dir = os.path.dirname(__file__)
    styles_root = os.path.join(base_dir, "styles")

    style_folder_map = {
        "casual": os.path.join(styles_root, "casual_style"),
        "office": os.path.join(styles_root, "office_style"),
        "sport": os.path.join(styles_root, "sport_style"),
    }

    style_folder = style_folder_map.get(style_key)
    if style_folder is None:
        return []

    # выбор подходящей подпапки по температуре
    if max_temp <= 5:
        subfolder = "photos_winter_temp"
    elif max_temp <= 20:
        subfolder = "photos_aut_spr_temp"
    else:
        subfolder = "photos_summer_temp"

    photos_dir = os.path.join(style_folder, subfolder)

    try:
        files = [
            f
            for f in os.listdir(photos_dir)
            if not f.startswith(".") and os.path.isfile(os.path.join(photos_dir, f))
        ]
    except FileNotFoundError:
        return []

    if not files:
        return []

    if len(files) <= count:
        chosen = files
    else:
        chosen = random.sample(files, count)

    return [os.path.join(photos_dir, filename) for filename in chosen]



# --- Выбор стиля ---


@command_router.message(StyleStates.choosing_style)
async def process_style_choice(message: Message, state: FSMContext) -> None:
    text = (message.text or "").strip().lower()

    style_map = {
        "casual": "casual",
        "кэжуал": "casual",
        "повседневный": "casual",
        "office": "office",
        "офисный": "office",
        "офис": "office",
        "sport": "sport",
        "спорт": "sport",
        "спортивный": "sport",
    }

    style_key = style_map.get(text)
    if style_key is None:
        await message.answer(
            "пожалуйста, выбери стиль с кнопок: Casual, Офисный или Спортивный 😊"
        )
        return

    data_state = await state.get_data()
    city = data_state.get("city")

    user_tg_id = message.from_user.id
    if city is None:
        with user_repo_ctx() as user_repo:
            user = user_repo.get_user_by_tg_id(user_tg_id)
        city = user.city if user is not None else DEFAULT_CITY

    forecast = await get_forecast_for_city(city)

    photo_paths = get_style_photo_paths(style_key, forecast.max_temp, count=3)

    caption = (
        f"город: {forecast.city}\n"
        f"максимальная температура сегодня: {round(forecast.max_temp)}°C\n"
        f"выбранный стиль: {style_key.capitalize()}"
    )

    if not photo_paths:
        await message.answer(
            caption + "\n\nпока не нашла подходящих фото для этого стиля и температуры 🥲",
            reply_markup=main_menu_keyboard(),
        )
    else:
        # первую фотку с подписью
        first = FSInputFile(photo_paths[0])
        await message.answer_photo(
            first,
            caption=caption,
            reply_markup=main_menu_keyboard(),
        )

        # остальные две просто картинками
        for path in photo_paths[1:]:
            await message.answer_photo(FSInputFile(path))

    await state.clear()

