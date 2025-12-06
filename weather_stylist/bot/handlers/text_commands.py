# weather_stylist/bot/handlers/text_commands.py

from aiogram import Router, F
from aiogram.types import Message

text_router = Router()


@text_router.message(F.photo)
async def handle_photo(message: Message) -> None:
    await message.answer("крутая картинка 😎")


@text_router.message(F.text)
async def handle_unknown_text(message: Message) -> None:
    text = (message.text or "").strip()

    if not text:
        return

    # если это одна из наших кнопок/команд — пусть их обрабатывает commands.py
    known_texts = {
        "Совет на сегодня",
        "Изменить город",
        "Настройки",
        "Изменить стиль",
    }
    if text in known_texts:
        return

    if text.startswith("/"):
        # неизвестная команда
        await message.answer(
            "неверная команда 🙃\n"
            "посмотри, что я умею в /help\n"
        )
        return

    await message.answer(
        "неверная команда 🧐\n"
        "если хочешь совет по одежде, жми «Совет на сегодня».\n"
        "если хочешь поменять город — «Изменить город» \n"
        "либо нажимай /help, чтобы посмотреть все команды"
    )
