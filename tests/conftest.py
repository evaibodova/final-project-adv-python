"""
Общие фикстуры для тестов (DRY принцип).
Все тесты могут использовать эти моки вместо дублирования классов.
"""
from dataclasses import dataclass
from typing import List


@dataclass
class DummyForecast:
    """Мок для DayForecast - используется во всех тестах."""
    min_temp: float
    max_temp: float
    wind_max: float
    will_rain: bool
    city: str = "Москва"  # опциональное поле для тестов engine
    hourly: List = None  # опциональное поле, обычно не используется в тестах
    
    def __post_init__(self):
        if self.hourly is None:
            self.hourly = []


@dataclass
class DummyUser:
    """Мок для User - используется во всех тестах."""
    thermo_profile: int = 0
    warmth_shift: float = 0.0
    feedback_count: int = 0
    cold_count: int = 0
    hot_count: int = 0
    # Опциональные поля для тестов, которые их используют
    tg_id: int = 1
    name: str = "тест"
    city: str = "Москва"
    region: str = ""


@dataclass
class DummyMessage:
    """Мок для Telegram сообщения - используется в тестах команд."""
    def __init__(self, text=None):
        self.text = text
        self.replies: list[str] = []

    async def answer(self, text: str, **kwargs):
        self.replies.append(text)

