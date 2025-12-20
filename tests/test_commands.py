import pytest

from weather_stylist.bot.handlers.text_commands import (
    handle_photo,
    handle_unknown_text,
)


class DummyMessage:
    def __init__(self, text=None):
        self.text = text
        self.replies: list[str] = []

    async def answer(self, text: str, **kwargs):
        self.replies.append(text)


@pytest.mark.asyncio
async def test_handle_photo_reply():
    msg = DummyMessage()
    await handle_photo(msg)

    assert msg.replies, "должен быть хотя бы один ответ"
    assert "крутая картинка" in msg.replies[0]


@pytest.mark.asyncio
async def test_handle_unknown_command_with_slash():
    msg = DummyMessage("/unknown")
    await handle_unknown_text(msg)

    joined = "\n".join(msg.replies)
    assert "неверная команда" in joined
    assert "/help" in joined


@pytest.mark.asyncio
async def test_handle_unknown_plain_text():
    msg = DummyMessage("я люблю котиков")
    await handle_unknown_text(msg)

    joined = "\n".join(msg.replies)
    assert "неверная команда" in joined
    assert "Совет на сегодня" in joined