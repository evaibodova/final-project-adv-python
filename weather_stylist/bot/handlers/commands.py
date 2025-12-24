import os
import random
from typing import Optional
from datetime import datetime

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
from weather_stylist.adapters.user_bd import SqlAlchemyUserRepo, SqlAlchemyFeedbackRepo
from weather_stylist.models import User, FeedbackRecord

from contextlib import asynccontextmanager

from weather_stylist.adapters.weather_api.openweather_client import get_forecast_for_city

from weather_stylist.recommendation.engine import build_today_advice
from weather_stylist.ml.online_shift import update_warmth_shift

from ...infra import (
    CityNotFoundError,
    WeatherAPIError,
    ModelError,
    ModelNotReadyError,
)


DEFAULT_CITY = os.getenv("DEFAULT_CITY")


# --- константы для термопрофиля ---

FB_COLD = "Было холодно"
FB_OK = "Было нормально"
FB_HOT = "Было жарко"


def build_user_with_city(existing: Optional[User], *, tg_id: int, name: str, city: str, thermo_profile: Optional[int] = None,
                         ) -> User:
    if existing is None:
        return User(
            tg_id=tg_id,
            city=city,
            name=name,
            region="unknown",
            thermo_profile=thermo_profile if thermo_profile is not None else 0,
            warmth_shift=0.0,
            feedback_count=0,
            cold_count=0,
            hot_count=0,
        )

    return User(
        tg_id=existing.tg_id,
        city=city,
        name=existing.name,
        region=existing.region,
        thermo_profile=(
            existing.thermo_profile
            if thermo_profile is None
            else thermo_profile
        ),
        warmth_shift=existing.warmth_shift,
        feedback_count=existing.feedback_count,
        cold_count=existing.cold_count,
        hot_count=existing.hot_count,
    )


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
        f"Привет, {html.bold(message.from_user.full_name)}!\n\n"
        "я бот-стилист по погоде: подсказываю, что надеть на весь день, чтобы внезапно не оказаться мокрым или ледяным посреди дня 🌦🥶. Нажми «Совет на сегодня», чтобы узнать, что надеть или введи /help чтобы увидеть, что я могу)",
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


# техническое

async def reply_city_not_found(message: Message) -> None:
    await message.answer(
        "не смог найти такой город 😿\n"
        "попробуй ещё раз, например: Омск или Prague."
    )


async def reply_weather_unavailable(message: Message) -> None:
    await message.answer(
        "сейчас не получается получить данные о погоде 🥺\n"
        "скорее всего, проблемы с внешним сервисом.\n"
        "попробуй ещё раз чуть позже."
    )


async def reply_model_not_ready(message: Message) -> None:
    await message.answer(
        "я ещё учусь подбирать образы и временно не могу дать совет 🧠✨\n"
        "попробуй немного позже, когда модель обновится."
    )

# основные команды


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

    if user is None:
        ...
        return

    city = user.city

    if not city:
        ...
        return

    # 3. город и профиль есть — даём совет
    try:
        forecast = await get_forecast_for_city(city)
    except CityNotFoundError:
        # до этого город был валидным, но вдруг API больше его не знает
        await reply_city_not_found(message)
        return
    except WeatherAPIError:
        await reply_weather_unavailable(message)
        return

    try:
        advice = build_today_advice(forecast, user)
    except ModelNotReadyError:
        await reply_model_not_ready(message)
        return
    except ModelError:
        # что-то сломалось в ML, но не критично — просто скажем, что не можем
        await message.answer(
            "у меня сейчас не получается подобрать персональный образ 🧵\n"
            "попробуй ещё раз немного позже."
        )
        return

    footer = (
        f"\n\nсейчас у тебя город по умолчанию: {forecast.city}.\n"
        "если хочешь сменить — нажми «Сменить город» или команду /change_city."
    )

    await message.answer(advice.text + footer)

    await state.update_data(
        last_forecast={
            "temp_min": forecast.min_temp,
            "temp_max": forecast.max_temp,
            "wind_max": forecast.wind_max,
            "will_rain": forecast.will_rain,
        },
        last_outfit_code=",".join(advice.items),
    )
    await state.set_state(FeedbackStates.waiting_for_feedback_then_today)

# --- первый выбор города ---


@command_router.message(CityStates.choosing_default)
async def process_first_city(message: Message, state: FSMContext) -> None:
    raw_city = (message.text or "").strip()
    if not raw_city:
        await message.answer("напиши, пожалуйста, название города текстом 🙏")
        return

    try:
        forecast = await get_forecast_for_city(raw_city)
    except CityNotFoundError:
        await reply_city_not_found(message)
        return
    except WeatherAPIError:
        await reply_weather_unavailable(message)
        return

    user_tg_id = message.from_user.id
    user_name = message.from_user.full_name

    data_state = await state.get_data()
    thermo_from_state: Optional[int] = data_state.get("thermo_profile")
    return_to_style: bool = data_state.get("return_to_style", False)

    async with user_repo_ctx() as user_repo:
        existing = await user_repo.get_user_by_tg_id(user_tg_id)

        user = build_user_with_city(
            existing=existing,
            tg_id=user_tg_id,
            name=user_name,
            city=forecast.city,
            thermo_profile=thermo_from_state,
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


# --- обновление фидбека
@command_router.message(F.text.in_([FB_COLD, FB_OK, FB_HOT]))
async def handle_daily_feedback(message: Message, state: FSMContext) -> None:
    user_tg_id = message.from_user.id

    data = await state.get_data()
    last = data.get("last_forecast")
    outfit_code = data.get("last_outfit_code")

    if not last or not outfit_code:
        await message.answer("Сначала нажми «Совет на сегодня», потом оцени 🙂")
        await state.clear()
        return

    async with AsyncSessionLocal() as session:
        user_repo = SqlAlchemyUserRepo(session)
        fb_repo = SqlAlchemyFeedbackRepo(session)

        user = await user_repo.get_user_by_tg_id(user_tg_id)
        if user is None:
            await message.answer(
                "я ещё ни разу не давала тебе совет по одежде, "
                "так что пока нечего оценивать 🥺"
            )
            return

        text = (message.text or "").strip()
        if text == FB_COLD:
            label = -1
            reply = "поняла: в прошлый раз было холодно ❄️\nбуду советовать одежду потеплее."
        elif text == FB_HOT:
            label = 1
            reply = "поняла: в прошлый раз было жарко 🔥\nбуду советовать одежду полегче."
        else:
            label = 0
            reply = "круто, значит продолжаем в том же духе, буду советовать одежду среднего теплоощущения 😌"

        await fb_repo.save(FeedbackRecord(
            user_tg_id=user_tg_id,
            created_at=datetime.utcnow(),
            temp_min=float(last["temp_min"]),
            temp_max=float(last["temp_max"]),
            wind_max=float(last["wind_max"]),
            will_rain=bool(last["will_rain"]),
            thermo_profile=int(user.thermo_profile),
            outfit_code=str(outfit_code),
            label=int(label),
        ))

        # тут обновляется: feedback_count, cold/hot_count, warmth_shift
        updated = update_warmth_shift(user, label)
        await user_repo.save(updated)

    await message.answer(
        reply + "\n\nспасибо за обратную связь! ❤️ \n мы стараемся сделать работу лучше, ты очень помогаешь нам в этом 💗",
        reply_markup=main_menu_keyboard(),
    )

    await state.clear()


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
    except CityNotFoundError:
        await reply_city_not_found(message)
        await state.clear()
        return
    except WeatherAPIError:
        await reply_weather_unavailable(message)
        await state.clear()
        return

    user_tg_id = message.from_user.id
    user_name = message.from_user.full_name

    async with user_repo_ctx() as user_repo:
        existing = await user_repo.get_user_by_tg_id(user_tg_id)

        user = build_user_with_city(
            existing=existing,
            tg_id=user_tg_id,
            name=user_name,
            city=forecast.city,
        )
        await user_repo.save(user)

    await state.clear()

    await message.answer(
        f"обновил город по умолчанию на {forecast.city} ✅\n"
        "теперь «Совет на сегодня» будет использовать этот город."
    )

# --- настройки термочувствительности ---


def build_thermo_profile(user: User, new_value: int) -> User:
    return User(
        tg_id=user.tg_id,
        city=user.city,
        name=user.name,
        region=user.region,
        thermo_profile=new_value,
        warmth_shift=user.warmth_shift,
        feedback_count=user.feedback_count,
        cold_count=user.cold_count,
        hot_count=user.hot_count,
    )


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
            updated = build_thermo_profile(user, value)
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
