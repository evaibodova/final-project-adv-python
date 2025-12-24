from weather_stylist.adapters.user_bd.bd import AsyncSessionLocal, UserORM, FeedbackORM
from sqlalchemy import select
import os
import random

from aiogram import F, Router, html
from aiogram.filters import CommandStart, Command
from aiogram.types import (
    Message,
    KeyboardButton,
    ReplyKeyboardMarkup,
    FSInputFile,
    InputMediaPhoto,
)
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State

from weather_stylist.adapters.user_bd.bd import AsyncSessionLocal
from weather_stylist.adapters.user_bd.bd import UserORM, FeedbackORM
from datetime import datetime
from weather_stylist.adapters.user_bd.sqlalchemy_user_repo import SqlAlchemyUserRepo
from weather_stylist.models import User

from contextlib import asynccontextmanager

from weather_stylist.adapters.weather_api.openweather_client import get_forecast_for_city

from weather_stylist.recommendation.engine import build_today_advice
from weather_stylist.ml.online_shift import update_warmth_shift

DEFAULT_CITY = os.getenv("DEFAULT_CITY")


# --- константы для термопрофиля ---

FB_COLD = "Было холодно"
FB_OK = "Было нормально"
FB_HOT = "Было жарко"


def feedback_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=FB_COLD)],
            [KeyboardButton(text=FB_OK)],
            [KeyboardButton(text=FB_HOT)],
        ],
        resize_keyboard=True,
    )


TEXT_COLD = "Я мерзляк"
TEXT_HOT = "Мне всегда жарко"
TEXT_NEUTRAL = "У меня нет предпочтений"


@asynccontextmanager
async def user_repo_ctx():
    async with AsyncSessionLocal() as session:
        repo = SqlAlchemyUserRepo(session)
        yield repo


class CityStates(StatesGroup):
    choosing_default = State()
    changing_city = State()


class StyleStates(StatesGroup):
    choosing_style = State()


class FeedbackStates(StatesGroup):
    waiting_for_feedback_then_today = State()


command_router = Router()


# --- главное меню ---


def main_menu_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="Совет на сегодня")],
            [KeyboardButton(text="Выбрать стиль")],
            [KeyboardButton(text="Изменить город")],
            [KeyboardButton(text="Настройки")],
        ],
        resize_keyboard=True,
    )


def thermo_choice_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=TEXT_COLD)],
            [KeyboardButton(text=TEXT_HOT)],
            [KeyboardButton(text=TEXT_NEUTRAL)],
        ],
        resize_keyboard=True,
    )


def style_choice_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="Casual"), KeyboardButton(text="Офисный")],
            [KeyboardButton(text="Спортивный")],
        ],
        resize_keyboard=True,
    )


# --- /start ---


@command_router.message(CommandStart())
async def cmd_start(message: Message) -> None:
    await message.answer(
        f"Привет, {html.bold(message.from_user.full_name)} 🦜!\n\n"
        "я бот-стилист по погоде 🧸: подсказываю, что надеть на весь день, чтобы внезапно не оказаться мокрым или ледяным посреди дня 🌦🥶. Нажми «Совет на сегодня», чтобы узнать, что надеть или введи /help чтобы увидеть, что я могу)",
        reply_markup=main_menu_keyboard(),
    )


# --- /help ---


@command_router.message(Command("help"))
async def cmd_help(message: Message) -> None:
    await message.answer(
        "доступные команды:\n"
        "/today – совет на сегодня\n"
        "/change_city – сменить город\n"
        "/settings – настройки профиля\n"
        "или пользуйся кнопками внизу ⬇️",
    )


# --- Совет на сегодня ---


@command_router.message(Command("today"))
@command_router.message(F.text == "Совет на сегодня")
async def cmd_today(message: Message, state: FSMContext) -> None:
    user_tg_id = message.from_user.id

    async with user_repo_ctx() as user_repo:
        user = await user_repo.get_user_by_tg_id(user_tg_id)

    if user is not None:
        await message.answer(
            "А как тебе был прошлый образ?\n"
            "Было холодно, жарко или нормально?",
            reply_markup=feedback_keyboard(),
        )

    # 1. если пользователя нет в БД — сначала спрашиваем термочувствительность
    if user is None:
        await state.update_data(expect_city_after_thermo=True)
        await message.answer(
            "давай познакомимся! \n"
            "как ты обычно ощущаешь погоду? 🧊🔥",
            reply_markup=thermo_choice_keyboard(),
        )
        return

    city = user.city

    # 2. пользователь есть, но города ещё нет — просим город
    if not city:
        await message.answer(
            "давай выберем город по умолчанию 🌍\n"
            f"напиши, пожалуйста, город текстом (например: {DEFAULT_CITY})."
        )
        await state.set_state(CityStates.choosing_default)
        return

    # 3. и термопрофиль, и город уже есть — даём совет
        # город уже известен
    forecast = await get_forecast_for_city(city)

    # вызываем наш engine, который уже учитывает термопрофиль и фидбеки
    advice = build_today_advice(forecast, user)

    footer = (
        f"\n\nсейчас у тебя город по умолчанию: {forecast.city}.\n"
        "если хочешь сменить — нажми «Сменить город» или команду /change_city."
    )

    await message.answer(advice.text + footer)


# --- первый выбор города ---


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
            "не смог найти такой город 😿\n"
            "попробуй ещё раз, например: Омск или Prague."
        )
        return

    user_tg_id = message.from_user.id
    user_name = message.from_user.full_name

    data_state = await state.get_data()
    thermo_from_state = data_state.get("thermo_profile")
    return_to_style = data_state.get("return_to_style", False)

    async with user_repo_ctx() as user_repo:
        existing = await user_repo.get_user_by_tg_id(user_tg_id)

        if existing is None:
            thermo_value = int(
                thermo_from_state) if thermo_from_state is not None else 0
            user = User(
                tg_id=user_tg_id,
                city=forecast.city,
                name=user_name,
                region="unknown",
                thermo_profile=thermo_value,
                warmth_shift=0.0,
                feedback_count=0,
                cold_count=0,
                hot_count=0,
            )
        else:
            user = User(
                tg_id=existing.tg_id,
                city=forecast.city,
                name=existing.name,
                region=existing.region,
                thermo_profile=existing.thermo_profile,
                warmth_shift=existing.warmth_shift,
                feedback_count=existing.feedback_count,
                cold_count=existing.cold_count,
                hot_count=existing.hot_count,
            )

        await user_repo.save(user)

    if return_to_style:
        await state.update_data(city=forecast.city, return_to_style=False)
        await message.answer(
            f"ок, буду использовать {forecast.city} как город по умолчанию \n\n"
            "теперь выбери стиль одежды, если хочешь посмотреть аутфиты для твоей погоды 👔",
            reply_markup=style_choice_keyboard(),
        )
        await state.set_state(StyleStates.choosing_style)
        return

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
        + "\n\nв следующий раз просто жми «Совет на сегодня»."
    )

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
        + "\n\nв следующий раз просто жми «Совет на сегодня».",
        reply_markup=main_menu_keyboard(),
    )


# --- обновление фидбека


@command_router.message(F.text.in_([FB_COLD, FB_OK, FB_HOT]))
async def handle_daily_feedback(message: Message) -> None:
    user_tg_id = message.from_user.id
    text = (message.text or "").strip()

    if text == FB_COLD:
        label = -1
        reply = (
            "поняла: в прошлый раз было холодно ❄️\n"
            "буду советовать одежду потеплее."
        )
    elif text == FB_HOT:
        label = 1
        reply = (
            "поняла: в прошлый раз было жарко 🔥\n"
            "буду советовать одежду полегче."
        )
    else:
        label = 0
        reply = (
            "круто, значит продолжаем в том же духе, "
            "буду советовать одежду среднего теплоощущения 😌"
        )

    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(UserORM).where(UserORM.tg_id == user_tg_id)
        )
        user: UserORM | None = result.scalar_one_or_none()

        if user is None:
            await message.answer(
                "я ещё ни разу не давала тебе совет по одежде, "
                "так что пока нечего оценивать 🥺",
                reply_markup=main_menu_keyboard(),
            )
            return

        fb = FeedbackORM(
            user_tg_id=user_tg_id,
            created_at=datetime.utcnow(),
            temp_min=0.0,
            temp_max=0.0,
            wind_max=0.0,
            will_rain=False,
            thermo_profile=user.thermo_profile,
            outfit_code="unknown",
            label=label,
        )
        session.add(fb)

        user.feedback_count = (user.feedback_count or 0) + 1
        if label == -1:
            user.cold_count = (user.cold_count or 0) + 1
        elif label == 1:
            user.hot_count = (user.hot_count or 0) + 1

        await session.commit()

    await message.answer(
        reply
        + "\n\nспасибо за обратную связь! ❤️\n"
          "ты очень помогаешь мне лучше подбирать образы 💗",
        reply_markup=main_menu_keyboard(),
    )

# --- смена города ---


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
            "я не нашел такой город 😢\n"
            "проверь написание и попробуй снова.\n"
            "если это очень маленький населённый пункт, "
            "попробуй ближайший крупный город."
        )
        await state.clear()
        return

    user_tg_id = message.from_user.id
    user_name = message.from_user.full_name

    async with user_repo_ctx() as user_repo:
        existing = await user_repo.get_user_by_tg_id(user_tg_id)

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
                city=forecast.city,
                name=existing.name,
                region=existing.region,
                thermo_profile=existing.thermo_profile,
                warmth_shift=existing.warmth_shift,
                feedback_count=existing.feedback_count,
                cold_count=existing.cold_count,
                hot_count=existing.hot_count,
            )

        await user_repo.save(user)

    await state.clear()

    await message.answer(
        f"обновил город по умолчанию на {forecast.city} ✅\n"
        "теперь «Совет на сегодня» будет использовать этот город."
    )


# --- настройки термочувствительности ---


@command_router.message(Command("settings"))
@command_router.message(F.text == "Настройки")
async def cmd_settings(message: Message, state: FSMContext) -> None:
    user_tg_id = message.from_user.id

    async with user_repo_ctx() as user_repo:
        user = await user_repo.get_user_by_tg_id(user_tg_id)

    if user is None:
        await state.update_data(expect_city_after_thermo=False)
        await message.answer(
            "я пока ничего о тебе не знаю 🥺\n"
            "давай сначала настроим, как ты ощущаешь погоду:",
            reply_markup=thermo_choice_keyboard(),
        )
        return

    if user.thermo_profile == -1:
        status = "сейчас у тебя профиль: «я мерзляк»."
    elif user.thermo_profile == 1:
        status = "сейчас у тебя профиль: «мне всегда жарко»."
    else:
        status = "сейчас у тебя профиль: «у меня нет предпочтений»."

    await state.update_data(expect_city_after_thermo=False)
    await message.answer(
        status + "\n\nесли хочешь изменить термочувствительность — выбери вариант ниже:",
        reply_markup=thermo_choice_keyboard(),
    )


# --- обработчик выбора термопрофиля ---


@command_router.message(F.text.in_([TEXT_COLD, TEXT_HOT, TEXT_NEUTRAL]))
async def handle_thermo_choice(message: Message, state: FSMContext) -> None:
    user_tg_id = message.from_user.id
    text = (message.text or "").strip()

    if text == TEXT_COLD:
        value = -1
        desc = "запомнил: ты мерзляк 🧊 — буду советовать теплее."
    elif text == TEXT_HOT:
        value = 1
        desc = "запомнил: тебе всегда жарко 🔥 — буду советовать полегче."
    else:
        value = 0
        desc = "запомнил: без особых предпочтений 😌 — буду советовать что-то среднее."

    data = await state.get_data()
    expect_city = data.get("expect_city_after_thermo", False)

    async with user_repo_ctx() as user_repo:
        user = await user_repo.get_user_by_tg_id(user_tg_id)

        if user is None:
            if expect_city:
                await state.update_data(thermo_profile=value)
            else:
                user = User(
                    tg_id=user_tg_id,
                    city=None,
                    name=message.from_user.full_name,
                    region="unknown",
                    thermo_profile=value,
                    warmth_shift=0.0,
                    feedback_count=0,
                    cold_count=0,
                    hot_count=0,
                )
                await user_repo.save(user)
        else:
            updated = User(
                tg_id=user.tg_id,
                city=user.city,
                name=user.name,
                region=user.region,
                thermo_profile=value,
                warmth_shift=user.warmth_shift,
                feedback_count=user.feedback_count,
                cold_count=user.cold_count,
                hot_count=user.hot_count,
            )
            await user_repo.save(updated)

    if expect_city:
        await message.answer(
            desc
            + "\n\nа теперь давай выберем город по умолчанию 🌍\n"
              f"напиши, пожалуйста, город текстом (например: {DEFAULT_CITY})."
        )
        await state.set_state(CityStates.choosing_default)
    else:
        await state.clear()
        await message.answer(
            desc + "\n\nесли захочешь поменять настройки — заходи в «Настройки».",
            reply_markup=main_menu_keyboard(),
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


@command_router.message(Command("choose_style"))
@command_router.message(F.text == "Выбрать стиль")
async def cmd_choose_style(message: Message, state: FSMContext) -> None:
    user_tg_id = message.from_user.id

    async with user_repo_ctx() as user_repo:
        user = await user_repo.get_user_by_tg_id(user_tg_id)

    city = user.city if user is not None else None

    if city is None:
        await message.answer(
            "давай сначала выберем город по умолчанию 🌍\n"
            f"напиши, пожалуйста, город текстом (например: {DEFAULT_CITY})."
        )
        await state.set_state(CityStates.choosing_default)
        await state.update_data(return_to_style=True)
        return

    await state.update_data(city=city)
    await message.answer(
        "выбери стиль одежды 👔\n"
        "Casual — повседневный стиль\n"
        "Офисный — деловой стиль\n"
        "Спортивный — для активного отдыха",
        reply_markup=style_choice_keyboard(),
    )
    await state.set_state(StyleStates.choosing_style)


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
            "пожалуйста, выбери стиль с кнопок: Casual, Офисный или Спортивный 😊",
            reply_markup=style_choice_keyboard(),
        )
        return

    data_state = await state.get_data()
    city = data_state.get("city")

    user_tg_id = message.from_user.id
    if city is None:
        async with user_repo_ctx() as user_repo:
            user = await user_repo.get_user_by_tg_id(user_tg_id)
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
        await message.answer(caption)

        media_group = [
            InputMediaPhoto(media=FSInputFile(path))
            for path in photo_paths
        ]
        await message.answer_media_group(media_group)

        await message.answer(
            "выбери действие:",
            reply_markup=main_menu_keyboard(),
        )

    await state.clear()
