from aiogram import Router, F
from aiogram.types import Message

text_router = Router()

# --- константы ---

KNOWN_TEXT_BUTTONS: set[str] = {
    "Совет на сегодня",
    "Изменить город",
    "Настройки",
    "Выбрать стиль",
}

UNKNOWN_COMMAND_MSG = (
    "неверная команда 🙃\n"
    "посмотри, что я умею в /help\n"
)

UNKNOWN_TEXT_MSG = (
    "неверная команда 🧐\n"
    "если хочешь совет по одежде, жми «Совет на сегодня».\n"
    "если хочешь поменять город — «Изменить город» \n"
    "либо нажимай /help, чтобы посмотреть все команды"
)


@text_router.message(F.photo)
async def handle_photo(message: Message) -> None:
    await message.answer("крутая картинка 😎")


@text_router.message(F.text)
async def handle_unknown_text(message: Message) -> None:
    text = (message.text or "").strip()

    if not text:
        return

    if text in KNOWN_TEXT_BUTTONS:
        return

    if text.startswith("/"):
        # неизвестная команда
        await message.answer(UNKNOWN_TEXT_MSG)
        return

    await message.answer(UNKNOWN_COMMAND_MSG)
