from dataclasses import dataclass
from typing import List


@dataclass
class Outfit:
    base: str  # низ
    mid: str  # средний слой
    outer: str  # верхняя одежда
    accessories: List[str]  # аксессуары


@dataclass
class OutfitAdvice:
    text: str  # текст сообщения для пользователя
    outfit: Outfit  # структура с деталями комплекта
